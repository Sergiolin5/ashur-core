"""Memoria de Ashur: modelos de contracts/recuerdo.schema.json y su tabla SQLite (docs/adr/0004-memoria.md)."""

import json
import sqlite3
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

VERSION_ESQUEMA = 2


class Identidad(BaseModel):
    """Una persona o una mascota que aparece en el recuerdo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    identidad_id: str | None = Field(min_length=1)


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
    identidades: list[Identidad]
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
    identidades: list[Identidad] | None = None
    objetos: list[Objeto] | None = None
    opinion: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def solo_opinion_puede_ser_null(self) -> "CambiosRecuerdo":
        nulos = [c for c in self.model_fields_set if c != "opinion" and getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


def abrir(ruta: str) -> sqlite3.Connection:
    """Abre la base y la deja en la versión de esquema que conoce este código."""
    # Una conexión por pedido; FastAPI la usa desde varios hilos.
    conexion = sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
    try:
        conexion.execute("BEGIN IMMEDIATE")  # un solo pedido migra a la vez
        version = conexion.execute("PRAGMA user_version").fetchone()[0]
        if version > VERSION_ESQUEMA:
            raise RuntimeError(
                f"La base tiene el esquema {version} y este código solo conoce hasta el {VERSION_ESQUEMA}."
            )
        if version == 0:
            conexion.execute(
                """CREATE TABLE recuerdos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    texto TEXT NOT NULL,
                    origen TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    sensibilidad TEXT NOT NULL,
                    identidades TEXT NOT NULL,
                    objetos TEXT NOT NULL,
                    opinion TEXT
                )"""
            )
        elif version == 1:
            _migrar_1_a_2(conexion)
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
        conexion.execute("COMMIT")
    except BaseException:
        if conexion.in_transaction:
            conexion.execute("ROLLBACK")
        conexion.close()
        raise
    conexion.isolation_level = ""  # de aquí en adelante, transacciones normales con commit()
    return conexion


def _migrar_1_a_2(conexion: sqlite3.Connection) -> None:
    """Versión 1: personas con contacto_id. Versión 2: identidades con identidad_id."""
    conexion.execute("ALTER TABLE recuerdos RENAME COLUMN personas TO identidades")
    for id_, identidades in conexion.execute("SELECT id, identidades FROM recuerdos").fetchall():
        nuevas = [{"nombre": i["nombre"], "identidad_id": i["contacto_id"]} for i in json.loads(identidades)]
        conexion.execute(
            "UPDATE recuerdos SET identidades = ? WHERE id = ?", (json.dumps(nuevas, ensure_ascii=False), id_)
        )


def _desde_fila(fila: tuple) -> Recuerdo:
    id_, texto, origen, fecha, sensibilidad, identidades, objetos, opinion = fila
    return Recuerdo(
        id=id_,
        texto=texto,
        origen=origen,
        fecha=fecha,
        sensibilidad=sensibilidad,
        identidades=json.loads(identidades),
        objetos=json.loads(objetos),
        opinion=opinion,
    )


def crear(conexion: sqlite3.Connection, nuevo: RecuerdoNuevo) -> Recuerdo:
    cursor = conexion.execute(
        "INSERT INTO recuerdos (texto, origen, fecha, sensibilidad, identidades, objetos, opinion)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            nuevo.texto,
            nuevo.origen,
            nuevo.fecha.isoformat(),
            nuevo.sensibilidad,
            json.dumps([i.model_dump() for i in nuevo.identidades], ensure_ascii=False),
            json.dumps([o.model_dump() for o in nuevo.objetos], ensure_ascii=False),
            nuevo.opinion,
        ),
    )
    conexion.commit()
    return Recuerdo(id=cursor.lastrowid, **nuevo.model_dump())


def listar(conexion: sqlite3.Connection) -> list[Recuerdo]:
    filas = conexion.execute(
        "SELECT id, texto, origen, fecha, sensibilidad, identidades, objetos, opinion FROM recuerdos ORDER BY id"
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def obtener(conexion: sqlite3.Connection, id_: int) -> Recuerdo | None:
    fila = conexion.execute(
        "SELECT id, texto, origen, fecha, sensibilidad, identidades, objetos, opinion FROM recuerdos WHERE id = ?", (id_,)
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
        "UPDATE recuerdos SET texto = ?, origen = ?, fecha = ?, sensibilidad = ?, identidades = ?, objetos = ?,"
        " opinion = ? WHERE id = ?",
        (
            nuevo.texto,
            nuevo.origen,
            nuevo.fecha.isoformat(),
            nuevo.sensibilidad,
            json.dumps([i.model_dump() for i in nuevo.identidades], ensure_ascii=False),
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
