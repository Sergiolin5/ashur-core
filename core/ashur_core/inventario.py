"""Inventario: los objetos físicos de Sergio y dónde están (contracts/objeto.schema.json, docs/adr/0014-inventario.md)."""

import json
import sqlite3
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

Ranura = Annotated[str, Field(min_length=1)]


class ObjetoNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    lugar: str | None = Field(min_length=1)
    padre_id: str | None = Field(default=None, min_length=1)
    ranura: str | None = Field(default=None, min_length=1)
    ranuras: list[Ranura] = Field(default_factory=list)
    identificadores: dict[str, Any] | None = None
    especificaciones: dict[str, Any] | None = None
    evidencia: dict[str, Any] | None = None
    estado: str | None = Field(default=None, min_length=1)


class Objeto(ObjetoNuevo):
    id: str = Field(min_length=1)
    archivado: bool
    menciones: int = Field(ge=0)


class CambiosObjeto(BaseModel):
    """Editar, mover, archivar o restaurar. Solo se tocan los campos enviados."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1)
    lugar: str | None = Field(default=None, min_length=1)
    archivado: bool | None = None
    padre_id: str | None = Field(default=None, min_length=1)
    ranura: str | None = Field(default=None, min_length=1)
    ranuras: list[Ranura] | None = None
    identificadores: dict[str, Any] | None = None
    especificaciones: dict[str, Any] | None = None
    evidencia: dict[str, Any] | None = None
    estado: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def solo_lugar_puede_ser_null(self) -> "CambiosObjeto":
        pueden_ser_null = {"lugar", "padre_id", "ranura", "identificadores", "especificaciones", "evidencia", "estado"}
        nulos = [c for c in self.model_fields_set if c not in pueden_ser_null and getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


class ErrorInventario(ValueError):
    """Una relación o cambio del inventario no cumple sus reglas."""


def crear_tabla(conexion: sqlite3.Connection) -> None:
    # num nunca se reusa (AUTOINCREMENT); el id público es "obj-<num>".
    conexion.execute(
        """CREATE TABLE objetos (
            num INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            lugar TEXT,
            archivado INTEGER NOT NULL DEFAULT 0
        )"""
    )
    # Antes del inventario se aceptaba cualquier inventario_id. Para que un recuerdo viejo con "obj-3" no quede
    # enlazado a un objeto nuevo que no tiene que ver, la numeración empieza después del mayor obj-N ya usado.
    mayor = conexion.execute(
        "SELECT MAX(CAST(substr(json_extract(j.value, '$.inventario_id'), 5) AS INTEGER))"
        " FROM recuerdos r, json_each(r.objetos) j WHERE json_extract(j.value, '$.inventario_id') GLOB 'obj-[0-9]*'"
    ).fetchone()[0]
    if mayor:
        conexion.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('objetos', ?)", (mayor,))


def migrar_13_a_14(conexion: sqlite3.Connection) -> None:
    """Versión 14: jerarquía, identificadores, especificaciones, evidencia y estado opcionales."""
    conexion.execute("ALTER TABLE objetos ADD COLUMN padre_id TEXT")
    conexion.execute("ALTER TABLE objetos ADD COLUMN ranura TEXT")
    conexion.execute("ALTER TABLE objetos ADD COLUMN ranuras TEXT NOT NULL DEFAULT '[]'")
    conexion.execute("ALTER TABLE objetos ADD COLUMN identificadores TEXT")
    conexion.execute("ALTER TABLE objetos ADD COLUMN especificaciones TEXT")
    conexion.execute("ALTER TABLE objetos ADD COLUMN evidencia TEXT")
    conexion.execute("ALTER TABLE objetos ADD COLUMN estado TEXT")


def _menciones(conexion: sqlite3.Connection, id_: str) -> int:
    return conexion.execute(
        "SELECT COUNT(DISTINCT r.id) FROM recuerdos r, json_each(r.objetos) j"
        " WHERE json_extract(j.value, '$.inventario_id') = ?",
        (id_,),
    ).fetchone()[0]


def _json_desde_columna(valor: str | None) -> Any:
    return json.loads(valor) if valor is not None else None


def _desde_fila(conexion: sqlite3.Connection, fila: tuple) -> Objeto:
    id_, nombre, lugar, archivado, padre_id, ranura, ranuras, identificadores, especificaciones, evidencia, estado = fila
    return Objeto(
        id=id_,
        nombre=nombre,
        lugar=lugar,
        archivado=bool(archivado),
        menciones=_menciones(conexion, id_),
        padre_id=padre_id,
        ranura=ranura,
        ranuras=json.loads(ranuras),
        identificadores=_json_desde_columna(identificadores),
        especificaciones=_json_desde_columna(especificaciones),
        evidencia=_json_desde_columna(evidencia),
        estado=estado,
    )


_COLUMNAS = "id, nombre, lugar, archivado, padre_id, ranura, ranuras, identificadores, especificaciones, evidencia, estado"


def _json_para_columna(valor: dict[str, Any] | None) -> str | None:
    return json.dumps(valor, ensure_ascii=False) if valor is not None else None


def _validar_jerarquia(
    conexion: sqlite3.Connection,
    id_: str | None,
    padre_id: str | None,
    ranura: str | None,
    lugar: str | None,
    ranuras: list[str],
    archivado: bool,
) -> None:
    if padre_id is None:
        if ranura is not None:
            raise ErrorInventario("Una raíz no puede declarar una ranura de padre.")
    else:
        if lugar is not None:
            raise ErrorInventario("Un componente debe tener lugar null; hereda el lugar de su raíz.")
        if padre_id == id_:
            raise ErrorInventario("Un objeto no puede ser su propio padre.")
        fila_padre = conexion.execute("SELECT archivado, ranuras FROM objetos WHERE id = ?", (padre_id,)).fetchone()
        if fila_padre is None:
            raise ErrorInventario(f"No existe el padre {padre_id}.")
        archivado_padre, ranuras_padre = fila_padre
        if archivado_padre:
            raise ErrorInventario("No se puede asignar un componente a un padre archivado.")
        if ranura is not None and ranura not in json.loads(ranuras_padre):
            raise ErrorInventario(f"El padre no declara la ranura {ranura}.")
        vistos = {id_} if id_ is not None else set()
        ancestro = padre_id
        while ancestro is not None:
            if ancestro in vistos:
                raise ErrorInventario("La jerarquía no puede contener ciclos.")
            vistos.add(ancestro)
            fila = conexion.execute("SELECT padre_id FROM objetos WHERE id = ?", (ancestro,)).fetchone()
            if fila is None:
                raise ErrorInventario(f"No existe el padre {ancestro}.")
            ancestro = fila[0]

    if id_ is not None:
        hijos_activos = conexion.execute(
            "SELECT id, ranura FROM objetos WHERE padre_id = ? AND archivado = 0", (id_,)
        ).fetchall()
        if archivado and hijos_activos:
            raise ErrorInventario("No se puede archivar un objeto con hijos activos.")
        for id_hijo, ranura_hijo in hijos_activos:
            if ranura_hijo not in ranuras:
                raise ErrorInventario(f"La ranura {ranura_hijo} está en uso por {id_hijo}.")


def crear(conexion: sqlite3.Connection, nuevo: ObjetoNuevo) -> Objeto:
    _validar_jerarquia(
        conexion, None, nuevo.padre_id, nuevo.ranura, nuevo.lugar, nuevo.ranuras, False
    )
    cursor = conexion.execute(
        "INSERT INTO objetos (id, nombre, lugar, padre_id, ranura, ranuras, identificadores, especificaciones, evidencia, estado)"
        " VALUES ('pendiente', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            nuevo.nombre,
            nuevo.lugar,
            nuevo.padre_id,
            nuevo.ranura,
            json.dumps(nuevo.ranuras, ensure_ascii=False),
            _json_para_columna(nuevo.identificadores),
            _json_para_columna(nuevo.especificaciones),
            _json_para_columna(nuevo.evidencia),
            nuevo.estado,
        ),
    )
    id_ = f"obj-{cursor.lastrowid}"
    conexion.execute("UPDATE objetos SET id = ? WHERE num = ?", (id_, cursor.lastrowid))
    conexion.commit()
    return obtener(conexion, id_)


def obtener(conexion: sqlite3.Connection, id_: str) -> Objeto | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM objetos WHERE id = ?", (id_,)).fetchone()
    return _desde_fila(conexion, fila) if fila else None


def listar(conexion: sqlite3.Connection, archivados: bool = False) -> list[Objeto]:
    filtro = "" if archivados else " WHERE archivado = 0"
    filas = conexion.execute(f"SELECT {_COLUMNAS} FROM objetos{filtro} ORDER BY num").fetchall()
    return [_desde_fila(conexion, f) for f in filas]


def contar(conexion: sqlite3.Connection) -> int:
    """Los objetos sin archivar: lo que pesa el planeta Objetos."""
    return conexion.execute("SELECT COUNT(*) FROM objetos WHERE archivado = 0").fetchone()[0]


def editar(conexion: sqlite3.Connection, id_: str, cambios: CambiosObjeto) -> Objeto | None:
    actual = obtener(conexion, id_)
    if actual is None:
        return None
    valores = actual.model_dump()
    for campo in cambios.model_fields_set:
        valores[campo] = getattr(cambios, campo)
    _validar_jerarquia(
        conexion,
        id_,
        valores["padre_id"],
        valores["ranura"],
        valores["lugar"],
        valores["ranuras"],
        valores["archivado"],
    )
    for campo in cambios.model_fields_set:
        valor = getattr(cambios, campo)
        if campo == "archivado":
            valor = int(valor)
        elif campo == "ranuras":
            valor = json.dumps(valor, ensure_ascii=False)
        elif campo in {"identificadores", "especificaciones", "evidencia"}:
            valor = _json_para_columna(valor)
        conexion.execute(f"UPDATE objetos SET {campo} = ? WHERE id = ?", (valor, id_))
    conexion.commit()
    return obtener(conexion, id_)


def desconocidos(conexion: sqlite3.Connection, ids: list[str]) -> list[str]:
    """Los ids que no existen en el inventario, para no guardar recuerdos con enlaces rotos."""
    return [i for i in ids if conexion.execute("SELECT 1 FROM objetos WHERE id = ?", (i,)).fetchone() is None]
