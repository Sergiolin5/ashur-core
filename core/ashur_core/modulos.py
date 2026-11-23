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
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

PATRON_ID = r"^[a-z][a-z0-9_]*$"


class Accion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PATRON_ID)
    descripcion: str = Field(min_length=1)
    escribe: bool


TipoAjuste = Literal["texto", "numero", "booleano"]


def _del_tipo(tipo: str, valor: Any) -> bool:
    if tipo == "texto":
        return isinstance(valor, str) and valor != ""
    if tipo == "numero":
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    return isinstance(valor, bool)


class Ajuste(BaseModel):
    """Un ajuste que el módulo declara y Sergio cambia desde la app (docs/adr/0019-ajustes-de-modulos-y-nodos.md)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PATRON_ID)
    tipo: TipoAjuste
    descripcion: str = Field(min_length=1)
    por_defecto: str | float | bool | None = None
    secreto: bool = False

    @model_validator(mode="after")
    def coherente(self) -> "Ajuste":
        if self.por_defecto is not None and not _del_tipo(self.tipo, self.por_defecto):
            raise ValueError(f"por_defecto de {self.id} no es de tipo {self.tipo}")
        if self.secreto and self.tipo != "texto":
            raise ValueError(f"{self.id}: solo un ajuste de tipo texto puede ser secreto")
        return self


class Manifiesto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PATRON_ID)
    nombre: str = Field(min_length=1)
    version: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    acciones: list[Accion]
    ajustes: list[Ajuste] = Field(default_factory=list)  # opcional: los manifiestos de antes siguen valiendo

    @model_validator(mode="after")
    def ajustes_unicos(self) -> "Manifiesto":
        ids = [a.id for a in self.ajustes]
        if len(ids) != len(set(ids)):
            raise ValueError("hay ajustes con el mismo id")
        return self


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


class Datos:
    """Los datos propios de un módulo (docs/adr/0029-datos-propios-de-los-modulos.md): registros JSON agrupados en
    colecciones. Un módulo solo ve los suyos. No son memoria de Ashur: lo que Ashur deba saber va con recordar()."""

    def __init__(self, conexion: sqlite3.Connection, id_modulo: str):
        self._con = conexion
        self._modulo = id_modulo

    def listar(self, coleccion: str) -> list[dict]:
        """Todos los registros de la colección, del más nuevo al más viejo."""
        filas = self._con.execute(
            "SELECT id, datos, creado, actualizado FROM datos_modulos WHERE modulo = ? AND coleccion = ?"
            " ORDER BY creado DESC, rowid DESC",
            (self._modulo, coleccion),
        ).fetchall()
        return [_registro_de_datos(f) for f in filas]

    def leer(self, coleccion: str, id_: str) -> dict | None:
        fila = self._con.execute(
            "SELECT id, datos, creado, actualizado FROM datos_modulos WHERE modulo = ? AND coleccion = ? AND id = ?",
            (self._modulo, coleccion, id_),
        ).fetchone()
        return _registro_de_datos(fila) if fila else None

    def guardar(self, coleccion: str, datos: dict, id_: str | None = None) -> dict:
        """Crea un registro (sin id) o reemplaza el que tiene ese id. Devuelve el registro con id, creado y
        actualizado."""
        if not isinstance(datos, dict):
            raise ValueError("Los datos de un registro tienen que ser un dict.")
        ahora = datetime.now(timezone.utc).isoformat()
        limpio = {k: v for k, v in datos.items() if k not in ("id", "creado", "actualizado")}
        texto = json.dumps(limpio, ensure_ascii=False)
        if id_ is None:
            id_ = uuid.uuid4().hex
            self._con.execute(
                "INSERT INTO datos_modulos (modulo, coleccion, id, datos, creado, actualizado) VALUES (?, ?, ?, ?, ?, ?)",
                (self._modulo, coleccion, id_, texto, ahora, ahora),
            )
        else:
            cursor = self._con.execute(
                "UPDATE datos_modulos SET datos = ?, actualizado = ? WHERE modulo = ? AND coleccion = ? AND id = ?",
                (texto, ahora, self._modulo, coleccion, id_),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"No hay un registro {id_} en {coleccion}.")
        self._con.commit()
        return self.leer(coleccion, id_)

    def borrar(self, coleccion: str, id_: str) -> bool:
        cursor = self._con.execute(
            "DELETE FROM datos_modulos WHERE modulo = ? AND coleccion = ? AND id = ?", (self._modulo, coleccion, id_)
        )
        self._con.commit()
        return cursor.rowcount == 1


def _registro_de_datos(fila: tuple) -> dict:
    id_, datos, creado, actualizado = fila
    return {**json.loads(datos), "id": id_, "creado": creado, "actualizado": actualizado}


def crear_tabla_datos(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE datos_modulos (
            modulo TEXT NOT NULL,
            coleccion TEXT NOT NULL,
            id TEXT NOT NULL,
            datos TEXT NOT NULL,
            creado TEXT NOT NULL,
            actualizado TEXT NOT NULL,
            PRIMARY KEY (modulo, coleccion, id)
        )"""
    )


class Contexto:
    """Lo único que un módulo recibe del core: recordar(), ajuste() y sus datos propios. No hay conexión a la base."""

    def __init__(
        self,
        id_modulo: str,
        guardar_recuerdo: Callable[[dict], dict],
        leer_ajuste: Callable[[str], Any] | None = None,
        datos: Datos | None = None,
    ):
        self.id_modulo = id_modulo
        self._guardar = guardar_recuerdo
        self._ajuste = leer_ajuste or (lambda id_: None)
        self.datos = datos

    def ajuste(self, id_: str) -> Any:
        """El valor de un ajuste del manifiesto: el que puso Sergio, o el por_defecto. None si no tiene ninguno."""
        return self._ajuste(id_)

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
    pedido_por: str | None = None  # la identidad que lo pidió desde el chat; None es Sergio


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
    id_, modulo, accion, parametros, estado, creado, resultado, error, pedido_por = fila
    return Pedido(
        id=id_, modulo=modulo, accion=accion, parametros=json.loads(parametros), estado=estado, creado=creado,
        resultado=json.loads(resultado) if resultado else None, error=error, pedido_por=pedido_por,
    )


_COLUMNAS = "id, modulo, accion, parametros, estado, creado, resultado, error, pedido_por"


def pedir(
    conexion: sqlite3.Connection, modulo: str, accion: str, parametros: dict, pedido_por: str | None = None
) -> Pedido:
    cursor = conexion.execute(
        "INSERT INTO pedidos (modulo, accion, parametros, creado, pedido_por) VALUES (?, ?, ?, ?, ?)",
        (modulo, accion, json.dumps(parametros, ensure_ascii=False), datetime.now(timezone.utc).isoformat(), pedido_por),
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


# ── Ajustes de los módulos (docs/adr/0019-ajustes-de-modulos-y-nodos.md) ──


class EstadoAjuste(BaseModel):
    """Lo que la app ve de un ajuste. Un secreto nunca vuelve: solo se sabe si está configurado."""

    id: str
    tipo: str
    descripcion: str
    secreto: bool
    por_defecto: str | float | bool | None
    valor: str | float | bool | None
    configurado: bool


def crear_tabla_ajustes(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE ajustes_modulos (
            modulo TEXT NOT NULL,
            ajuste TEXT NOT NULL,
            valor TEXT NOT NULL,
            PRIMARY KEY (modulo, ajuste)
        )"""
    )


def _guardados(conexion: sqlite3.Connection, modulo: str) -> dict:
    filas = conexion.execute("SELECT ajuste, valor FROM ajustes_modulos WHERE modulo = ?", (modulo,)).fetchall()
    return {a: json.loads(v) for a, v in filas}


def valor_de(conexion: sqlite3.Connection, manifiesto: Manifiesto, id_: str) -> Any:
    ajuste = next((a for a in manifiesto.ajustes if a.id == id_), None)
    if ajuste is None:
        return None
    return _guardados(conexion, manifiesto.id).get(id_, ajuste.por_defecto)


def ajustes_de(conexion: sqlite3.Connection, manifiesto: Manifiesto) -> list[EstadoAjuste]:
    guardados = _guardados(conexion, manifiesto.id)
    estados = []
    for a in manifiesto.ajustes:
        valor = guardados.get(a.id, a.por_defecto)
        estados.append(
            EstadoAjuste(
                id=a.id, tipo=a.tipo, descripcion=a.descripcion, secreto=a.secreto,
                por_defecto=None if a.secreto else a.por_defecto, valor=None if a.secreto else valor,
                configurado=valor is not None,
            )
        )
    return estados


def cambiar_ajustes(conexion: sqlite3.Connection, manifiesto: Manifiesto, cambios: dict) -> list[EstadoAjuste]:
    """Cambia los ajustes enviados; null vuelve al por_defecto. Lanza ValueError si alguno no existe o no es del tipo."""
    declarados = {a.id: a for a in manifiesto.ajustes}
    for id_, valor in cambios.items():
        if id_ not in declarados:
            raise ValueError(f"El módulo {manifiesto.id} no declara el ajuste {id_}.")
        if valor is not None and not _del_tipo(declarados[id_].tipo, valor):
            raise ValueError(f"El ajuste {id_} es de tipo {declarados[id_].tipo}.")
    for id_, valor in cambios.items():
        if valor is None:
            conexion.execute("DELETE FROM ajustes_modulos WHERE modulo = ? AND ajuste = ?", (manifiesto.id, id_))
        else:
            conexion.execute(
                "INSERT OR REPLACE INTO ajustes_modulos (modulo, ajuste, valor) VALUES (?, ?, ?)",
                (manifiesto.id, id_, json.dumps(valor, ensure_ascii=False)),
            )
    conexion.commit()
    return ajustes_de(conexion, manifiesto)
