"""Identidades: las personas y mascotas que conoce Ashur (contracts/identidad.schema.json, docs/adr/0012-identidades.md)."""

import sqlite3
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Umbrales de masa (menciones) para subir de nivel, θ₁ < θ₂ < θ₃, y margen η para bajar (docs/GALAXIA.md). Provisionales.
UMBRALES = (1, 5, 20)
MARGEN = 0.2

Clase = Literal["persona", "mascota"]


class IdentidadNueva(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    clase: Clase


class Identidad(IdentidadNueva):
    id: str = Field(min_length=1)
    archivada: bool
    menciones: int = Field(ge=0)
    nivel: int = Field(ge=0, le=3)


class CambiosIdentidad(BaseModel):
    """Editar, archivar o restaurar. Solo se tocan los campos enviados."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1)
    clase: Clase | None = None
    archivada: bool | None = None

    @model_validator(mode="after")
    def sin_nulos(self) -> "CambiosIdentidad":
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


def crear_tabla(conexion: sqlite3.Connection) -> None:
    # num nunca se reusa (AUTOINCREMENT); el id público es "ide-<num>".
    conexion.execute(
        """CREATE TABLE identidades (
            num INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            clase TEXT NOT NULL,
            archivada INTEGER NOT NULL DEFAULT 0,
            nivel INTEGER NOT NULL DEFAULT 0
        )"""
    )


def reservar_ids_enlazados(conexion: sqlite3.Connection) -> None:
    """Antes de la versión 5 se aceptaba cualquier identidad_id. Para que un recuerdo viejo con "ide-9" no quede
    enlazado a una identidad nueva que no tiene que ver, la numeración sigue después del mayor ide-N ya usado.
    Nunca la hace retroceder."""
    mayor = conexion.execute(
        "SELECT MAX(CAST(substr(json_extract(j.value, '$.identidad_id'), 5) AS INTEGER))"
        " FROM recuerdos r, json_each(r.identidades) j WHERE json_extract(j.value, '$.identidad_id') GLOB 'ide-[0-9]*'"
    ).fetchone()[0]
    if not mayor:
        return
    actual = conexion.execute("SELECT seq FROM sqlite_sequence WHERE name = 'identidades'").fetchone()
    if actual is None:
        conexion.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('identidades', ?)", (mayor,))
    elif actual[0] < mayor:
        conexion.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'identidades'", (mayor,))


def nivel_siguiente(nivel: int, masa: int) -> int:
    """Sube al nivel j cuando m ≥ θ_j y solo baja de él cuando m < (1 − η) θ_j, para no parpadear."""
    while nivel < 3 and masa >= UMBRALES[nivel]:
        nivel += 1
    while nivel > 0 and masa < (1 - MARGEN) * UMBRALES[nivel - 1]:
        nivel -= 1
    return nivel


def _menciones(conexion: sqlite3.Connection, id_: str) -> int:
    return conexion.execute(
        "SELECT COUNT(DISTINCT r.id) FROM recuerdos r, json_each(r.identidades) j"
        " WHERE json_extract(j.value, '$.identidad_id') = ?",
        (id_,),
    ).fetchone()[0]


def _desde_fila(conexion: sqlite3.Connection, fila: tuple) -> Identidad:
    id_, nombre, clase, archivada, nivel = fila
    return Identidad(
        id=id_, nombre=nombre, clase=clase, archivada=bool(archivada), menciones=_menciones(conexion, id_), nivel=nivel
    )


_COLUMNAS = "id, nombre, clase, archivada, nivel"


def recalcular_niveles(conexion: sqlite3.Connection) -> None:
    """Se llama después de cada escritura que cambia las menciones, para que leer la galaxia no escriba nada."""
    for id_, nivel in conexion.execute("SELECT id, nivel FROM identidades").fetchall():
        nuevo = nivel_siguiente(nivel, _menciones(conexion, id_))
        if nuevo != nivel:
            conexion.execute("UPDATE identidades SET nivel = ? WHERE id = ?", (nuevo, id_))
    conexion.commit()


def crear(conexion: sqlite3.Connection, nueva: IdentidadNueva) -> Identidad:
    cursor = conexion.execute(
        "INSERT INTO identidades (id, nombre, clase) VALUES ('pendiente', ?, ?)", (nueva.nombre, nueva.clase)
    )
    id_ = f"ide-{cursor.lastrowid}"
    conexion.execute("UPDATE identidades SET id = ? WHERE num = ?", (id_, cursor.lastrowid))
    conexion.commit()
    return obtener(conexion, id_)


def obtener(conexion: sqlite3.Connection, id_: str) -> Identidad | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM identidades WHERE id = ?", (id_,)).fetchone()
    return _desde_fila(conexion, fila) if fila else None


def listar(conexion: sqlite3.Connection, archivadas: bool = False) -> list[Identidad]:
    filtro = "" if archivadas else " WHERE archivada = 0"
    filas = conexion.execute(f"SELECT {_COLUMNAS} FROM identidades{filtro} ORDER BY num").fetchall()
    return [_desde_fila(conexion, f) for f in filas]


def editar(conexion: sqlite3.Connection, id_: str, cambios: CambiosIdentidad) -> Identidad | None:
    if obtener(conexion, id_) is None:
        return None
    for campo in cambios.model_fields_set:
        valor = getattr(cambios, campo)
        conexion.execute(f"UPDATE identidades SET {campo} = ? WHERE id = ?", (int(valor) if campo == "archivada" else valor, id_))
    conexion.commit()
    recalcular_niveles(conexion)
    return obtener(conexion, id_)


def desconocidas(conexion: sqlite3.Connection, ids: list[str]) -> list[str]:
    """Los ids que no existen en la lista, para no guardar recuerdos con enlaces rotos."""
    return [i for i in ids if conexion.execute("SELECT 1 FROM identidades WHERE id = ?", (i,)).fetchone() is None]
