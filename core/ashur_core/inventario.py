"""Inventario: los objetos físicos de Sergio y dónde están (contracts/objeto.schema.json, docs/adr/0014-inventario.md)."""

import sqlite3

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ObjetoNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    lugar: str | None = Field(min_length=1)


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

    @model_validator(mode="after")
    def solo_lugar_puede_ser_null(self) -> "CambiosObjeto":
        nulos = [c for c in self.model_fields_set if c != "lugar" and getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


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


def _menciones(conexion: sqlite3.Connection, id_: str) -> int:
    return conexion.execute(
        "SELECT COUNT(DISTINCT r.id) FROM recuerdos r, json_each(r.objetos) j"
        " WHERE json_extract(j.value, '$.inventario_id') = ?",
        (id_,),
    ).fetchone()[0]


def _desde_fila(conexion: sqlite3.Connection, fila: tuple) -> Objeto:
    id_, nombre, lugar, archivado = fila
    return Objeto(id=id_, nombre=nombre, lugar=lugar, archivado=bool(archivado), menciones=_menciones(conexion, id_))


_COLUMNAS = "id, nombre, lugar, archivado"


def crear(conexion: sqlite3.Connection, nuevo: ObjetoNuevo) -> Objeto:
    cursor = conexion.execute(
        "INSERT INTO objetos (id, nombre, lugar) VALUES ('pendiente', ?, ?)", (nuevo.nombre, nuevo.lugar)
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
    if obtener(conexion, id_) is None:
        return None
    for campo in cambios.model_fields_set:
        valor = getattr(cambios, campo)
        conexion.execute(f"UPDATE objetos SET {campo} = ? WHERE id = ?", (int(valor) if campo == "archivado" else valor, id_))
    conexion.commit()
    return obtener(conexion, id_)


def desconocidos(conexion: sqlite3.Connection, ids: list[str]) -> list[str]:
    """Los ids que no existen en el inventario, para no guardar recuerdos con enlaces rotos."""
    return [i for i in ids if conexion.execute("SELECT 1 FROM objetos WHERE id = ?", (i,)).fetchone() is None]
