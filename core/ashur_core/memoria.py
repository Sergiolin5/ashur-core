"""Memoria de Ashur: modelos de contracts/recuerdo.schema.json y su tabla SQLite (docs/adr/0004-memoria.md)."""

import json
import sqlite3
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

VERSION_ESQUEMA = 1


class Persona(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    contacto_id: str | None = Field(min_length=1)


class Objeto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    inventario_id: str | None = Field(min_length=1)


class RecuerdoNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1)
    origen: str = Field(min_length=1)
    fecha: AwareDatetime
    sensibilidad: Literal["normal", "privado", "sensible"]
    personas: list[Persona]
    objetos: list[Objeto]
    opinion: str | None = Field(min_length=1)


class Recuerdo(RecuerdoNuevo):
    id: int = Field(ge=1)


class CambiosRecuerdo(BaseModel):
    """Lo que se cambia de un recuerdo. Solo se tocan los campos enviados."""

    model_config = ConfigDict(extra="forbid")

    texto: str | None = Field(default=None, min_length=1)
    origen: str | None = Field(default=None, min_length=1)
    fecha: AwareDatetime | None = None
    sensibilidad: Literal["normal", "privado", "sensible"] | None = None
    personas: list[Persona] | None = None
    objetos: list[Objeto] | None = None
    opinion: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def solo_opinion_puede_ser_null(self) -> "CambiosRecuerdo":
        nulos = [c for c in self.model_fields_set if c != "opinion" and getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


def abrir(ruta: str) -> sqlite3.Connection:
    """Abre la base y crea o valida su esquema."""
    conexion = sqlite3.connect(ruta, check_same_thread=False)  # una conexión por pedido; FastAPI la usa desde varios hilos
    version = conexion.execute("PRAGMA user_version").fetchone()[0]
    if version == 0:
        conexion.execute(
            """CREATE TABLE IF NOT EXISTS recuerdos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT NOT NULL,
                origen TEXT NOT NULL,
                fecha TEXT NOT NULL,
                sensibilidad TEXT NOT NULL,
                personas TEXT NOT NULL,
                objetos TEXT NOT NULL,
                opinion TEXT
            )"""
        )
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
        conexion.commit()
    elif version > VERSION_ESQUEMA:
        conexion.close()
        raise RuntimeError(f"La base tiene el esquema {version} y este código solo conoce hasta el {VERSION_ESQUEMA}.")
    return conexion


def _desde_fila(fila: tuple) -> Recuerdo:
    id_, texto, origen, fecha, sensibilidad, personas, objetos, opinion = fila
    return Recuerdo(
        id=id_,
        texto=texto,
        origen=origen,
        fecha=fecha,
        sensibilidad=sensibilidad,
        personas=json.loads(personas),
        objetos=json.loads(objetos),
        opinion=opinion,
    )


def crear(conexion: sqlite3.Connection, nuevo: RecuerdoNuevo) -> Recuerdo:
    cursor = conexion.execute(
        "INSERT INTO recuerdos (texto, origen, fecha, sensibilidad, personas, objetos, opinion)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            nuevo.texto,
            nuevo.origen,
            nuevo.fecha.isoformat(),
            nuevo.sensibilidad,
            json.dumps([p.model_dump() for p in nuevo.personas], ensure_ascii=False),
            json.dumps([o.model_dump() for o in nuevo.objetos], ensure_ascii=False),
            nuevo.opinion,
        ),
    )
    conexion.commit()
    return Recuerdo(id=cursor.lastrowid, **nuevo.model_dump())


def listar(conexion: sqlite3.Connection) -> list[Recuerdo]:
    filas = conexion.execute(
        "SELECT id, texto, origen, fecha, sensibilidad, personas, objetos, opinion FROM recuerdos ORDER BY id"
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def obtener(conexion: sqlite3.Connection, id_: int) -> Recuerdo | None:
    fila = conexion.execute(
        "SELECT id, texto, origen, fecha, sensibilidad, personas, objetos, opinion FROM recuerdos WHERE id = ?", (id_,)
    ).fetchone()
    return _desde_fila(fila) if fila else None


def editar(conexion: sqlite3.Connection, id_: int, cambios: CambiosRecuerdo) -> Recuerdo | None:
    actual = obtener(conexion, id_)
    if actual is None:
        return None
    datos = actual.model_dump(exclude={"id"})
    datos.update({campo: getattr(cambios, campo) for campo in cambios.model_fields_set})
    nuevo = RecuerdoNuevo.model_validate(datos)
    conexion.execute(
        "UPDATE recuerdos SET texto = ?, origen = ?, fecha = ?, sensibilidad = ?, personas = ?, objetos = ?,"
        " opinion = ? WHERE id = ?",
        (
            nuevo.texto,
            nuevo.origen,
            nuevo.fecha.isoformat(),
            nuevo.sensibilidad,
            json.dumps([p.model_dump() for p in nuevo.personas], ensure_ascii=False),
            json.dumps([o.model_dump() for o in nuevo.objetos], ensure_ascii=False),
            nuevo.opinion,
            id_,
        ),
    )
    conexion.commit()
    return Recuerdo(id=id_, **nuevo.model_dump())


def borrar(conexion: sqlite3.Connection, id_: int) -> bool:
    cursor = conexion.execute("DELETE FROM recuerdos WHERE id = ?", (id_,))
    conexion.commit()
    return cursor.rowcount > 0
