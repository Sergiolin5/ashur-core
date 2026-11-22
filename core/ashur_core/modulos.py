"""Módulos: cómo se registran y corren dentro del core (docs/MODULOS.md, docs/adr/0013-modulos-en-el-core.md).

Cada modules/<id>/ trae modulo.json (contracts/modulo.schema.json) y modulo.py, con una función por acción:

    def <accion>(contexto, **parametros) -> dict

El core los descubre al arrancar. Un módulo roto aparece con su error y nunca tumba el core.
"""

import importlib.util
import json
import os
import sqlite3
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

PATRON_ID = r"^[a-z][a-z0-9_]*$"


class Accion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PATRON_ID)
    descripcion: str = Field(min_length=1)
    escribe: bool


class Manifiesto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PATRON_ID)
    nombre: str = Field(min_length=1)
    version: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    acciones: list[Accion]


class EstadoModulo(BaseModel):
    """Lo que GET /modulos muestra de cada carpeta de modules/."""

    id: str
    manifiesto: Manifiesto | None
    error: str | None


@dataclass
class ModuloCargado:
    manifiesto: Manifiesto
    funciones: dict[str, Callable]

    def accion(self, id_: str) -> Accion | None:
        return next((a for a in self.manifiesto.acciones if a.id == id_), None)


@dataclass
class Registro:
    modulos: dict[str, ModuloCargado] = field(default_factory=dict)
    errores: dict[str, str] = field(default_factory=dict)

    def estados(self) -> list[EstadoModulo]:
        buenos = [EstadoModulo(id=i, manifiesto=m.manifiesto, error=None) for i, m in self.modulos.items()]
        rotos = [EstadoModulo(id=i, manifiesto=None, error=e) for i, e in self.errores.items()]
        return sorted(buenos + rotos, key=lambda e: e.id)


def carpeta_por_defecto() -> Path:
    """modules/ al lado de core/, tanto en el repo como en la imagen (/app/core y /app/modules)."""
    return Path(os.environ.get("ASHUR_MODULOS", Path(__file__).resolve().parents[2] / "modules"))


def cargar_uno(carpeta: Path) -> ModuloCargado:
    """Carga modules/<carpeta>/. Lanza ValueError con un motivo legible si algo no cumple el contrato."""
    esperado = carpeta.name.lstrip("_")  # _plantilla se carga en las pruebas como "plantilla"
    try:
        manifiesto = Manifiesto.model_validate_json((carpeta / "modulo.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("Falta modulo.json.") from None
    except ValidationError as e:
        raise ValueError(f"modulo.json no cumple el contrato: {e.errors()[0]['msg']} en {e.errors()[0]['loc']}") from None
    if manifiesto.id != esperado:
        raise ValueError(f"El id del manifiesto ({manifiesto.id}) no es el nombre de la carpeta ({esperado}).")
    archivo = carpeta / "modulo.py"
    if not archivo.exists():
        raise ValueError("Falta modulo.py.")
    nombre = f"ashur_modulos.{manifiesto.id}"  # un nombre propio por módulo, para que no se pisen
    especificacion = importlib.util.spec_from_file_location(nombre, archivo)
    codigo = importlib.util.module_from_spec(especificacion)
    sys.modules[nombre] = codigo  # dataclasses y anotaciones diferidas buscan el módulo aquí
    try:
        especificacion.loader.exec_module(codigo)
    except Exception as e:  # el error del módulo, no del core
        del sys.modules[nombre]
        raise ValueError(f"modulo.py falló al cargar: {type(e).__name__}: {e}") from None
    funciones = {}
    for accion in manifiesto.acciones:
        funcion = getattr(codigo, accion.id, None)
        if not callable(funcion):
            raise ValueError(f"modulo.py no tiene la función {accion.id}().")
        funciones[accion.id] = funcion
    return ModuloCargado(manifiesto=manifiesto, funciones=funciones)


def descubrir(carpeta: Path) -> Registro:
    """Registra cada modules/<id>/ que no empiece con _."""
    registro = Registro()
    if not carpeta.is_dir():
        return registro
    for sub in sorted(p for p in carpeta.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        try:
            registro.modulos[sub.name] = cargar_uno(sub)
        except ValueError as e:
            registro.errores[sub.name] = str(e)
    return registro


class Contexto:
    """Lo único que un módulo recibe del core. No hay conexión a la base: el módulo no guarda memoria propia."""

    def __init__(self, id_modulo: str, guardar_recuerdo: Callable[[dict], dict]):
        self.id_modulo = id_modulo
        self._guardar = guardar_recuerdo

    def recordar(
        self,
        texto: str,
        *,
        fecha: datetime | None = None,
        sensibilidad: str = "normal",
        identidades: list[dict] | None = None,
        objetos: list[dict] | None = None,
        opinion: str | None = None,
    ) -> dict:
        """Guarda un recuerdo en el core con origen igual al id del módulo, y lo devuelve."""
        return self._guardar(
            {
                "texto": texto,
                "origen": self.id_modulo,
                "fecha": (fecha or datetime.now(timezone.utc)).isoformat(),
                "sensibilidad": sensibilidad,
                "identidades": identidades or [],
                "objetos": objetos or [],
                "opinion": opinion,
            }
        )


def ejecutar(modulo: ModuloCargado, accion: str, parametros: dict, contexto: Contexto) -> dict:
    """Corre la acción. Si el módulo falla, lanza ErrorDeModulo con su mensaje."""
    try:
        resultado = modulo.funciones[accion](contexto, **parametros)
    except Exception as e:
        raise ErrorDeModulo(f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)) from None
    if not isinstance(resultado, dict):
        raise ErrorDeModulo(f"La acción {accion} devolvió {type(resultado).__name__}, no un dict.", "")
    return resultado


class ErrorDeModulo(Exception):
    def __init__(self, mensaje: str, detalle: str):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle


# ── Pedidos: acciones que escriben y esperan la aprobación de un administrador ──


class Pedido(BaseModel):
    id: int
    modulo: str
    accion: str
    parametros: dict
    estado: str  # pendiente, corriendo, hecho, rechazado o fallido
    creado: str
    resultado: dict | None
    error: str | None


def crear_tabla_pedidos(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modulo TEXT NOT NULL,
            accion TEXT NOT NULL,
            parametros TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            creado TEXT NOT NULL,
            resultado TEXT,
            error TEXT
        )"""
    )


def _pedido(fila: tuple) -> Pedido:
    id_, modulo, accion, parametros, estado, creado, resultado, error = fila
    return Pedido(
        id=id_, modulo=modulo, accion=accion, parametros=json.loads(parametros), estado=estado, creado=creado,
        resultado=json.loads(resultado) if resultado else None, error=error,
    )


_COLUMNAS = "id, modulo, accion, parametros, estado, creado, resultado, error"


def pedir(conexion: sqlite3.Connection, modulo: str, accion: str, parametros: dict) -> Pedido:
    cursor = conexion.execute(
        "INSERT INTO pedidos (modulo, accion, parametros, creado) VALUES (?, ?, ?, ?)",
        (modulo, accion, json.dumps(parametros, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
    )
    conexion.commit()
    return obtener_pedido(conexion, cursor.lastrowid)


def obtener_pedido(conexion: sqlite3.Connection, id_: int) -> Pedido | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM pedidos WHERE id = ?", (id_,)).fetchone()
    return _pedido(fila) if fila else None


def listar_pedidos(conexion: sqlite3.Connection, estado: str | None = None) -> list[Pedido]:
    if estado:
        filas = conexion.execute(f"SELECT {_COLUMNAS} FROM pedidos WHERE estado = ? ORDER BY id", (estado,)).fetchall()
    else:
        filas = conexion.execute(f"SELECT {_COLUMNAS} FROM pedidos ORDER BY id").fetchall()
    return [_pedido(f) for f in filas]


def tomar_pendiente(conexion: sqlite3.Connection, id_: int, nuevo_estado: str) -> bool:
    """Pasa el pedido de pendiente a otro estado de forma atómica: dos aprobaciones nunca lo corren dos veces."""
    cursor = conexion.execute(
        "UPDATE pedidos SET estado = ? WHERE id = ? AND estado = 'pendiente'", (nuevo_estado, id_)
    )
    conexion.commit()
    return cursor.rowcount == 1


def cerrar_pedido(conexion: sqlite3.Connection, id_: int, estado: str, resultado: dict | None, error: str | None) -> None:
    conexion.execute(
        "UPDATE pedidos SET estado = ?, resultado = ?, error = ? WHERE id = ?",
        (estado, json.dumps(resultado, ensure_ascii=False) if resultado is not None else None, error, id_),
    )
    conexion.commit()
