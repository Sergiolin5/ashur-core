"""Otras personas en el chat: su clave, sus roles y qué recuerdos puede usar Ashur con ellas
(contracts/rol.schema.json, docs/adr/0022-personas-y-roles.md).

Sergio usa ASHUR_CLAVE. Cada identidad puede tener su propia clave, que solo abre sus conversaciones. Con otra
persona, Ashur solo usa los recuerdos que salieron de los mensajes de esa persona, y solo las herramientas de su rol.
"""

import hashlib
import json
import secrets
import sqlite3

from pydantic import BaseModel, ConfigDict, Field, field_validator

PATRON = r"^[a-z][a-z0-9_-]*\*?$"


class RolNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    herramientas: list[str]

    @field_validator("herramientas")
    @classmethod
    def patrones(cls, valores: list[str]) -> list[str]:
        """Un nombre exacto, o uno con un solo * al final: "modulo-luces-*"."""
        import re

        for v in valores:
            if not re.match(PATRON, v):
                raise ValueError(f"{v!r} no es un nombre de herramienta ni un prefijo terminado en *")
        return valores


class Rol(RolNuevo):
    id: str


class CambiosRol(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1)
    herramientas: list[str] | None = None

    @field_validator("herramientas")
    @classmethod
    def patrones(cls, valores: list[str] | None) -> list[str] | None:
        return valores if valores is None else RolNuevo.patrones(valores)


def permite(patrones: list[str], nombre: str) -> bool:
    """Coincidencia exacta o por prefijo con un * al final, distinguiendo mayúsculas. No usa fnmatch: en Windows ignora
    las mayúsculas y da sentido a ? y [, y el core corre en Linux."""
    for p in patrones:
        if p.endswith("*") and nombre.startswith(p[:-1]):
            return True
        if p == nombre:
            return True
    return False


def migrar(conexion: sqlite3.Connection) -> None:
    """Versión 12: roles, la clave y el rol de cada identidad, el dueño de cada conversación y quién pidió cada pedido."""
    conexion.execute(
        """CREATE TABLE roles (
            num INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            herramientas TEXT NOT NULL
        )"""
    )
    conexion.execute("ALTER TABLE identidades ADD COLUMN clave_hash TEXT")
    conexion.execute("ALTER TABLE identidades ADD COLUMN rol TEXT")
    conexion.execute("ALTER TABLE conversaciones ADD COLUMN identidad_id TEXT")
    conexion.execute("ALTER TABLE pedidos ADD COLUMN pedido_por TEXT")


def _hash(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


def nueva_clave(conexion: sqlite3.Connection, identidad_id: str) -> str:
    """Crea o reemplaza la clave de una identidad. Se muestra una sola vez; el core solo guarda su hash."""
    clave = secrets.token_hex(32)
    conexion.execute("UPDATE identidades SET clave_hash = ? WHERE id = ?", (_hash(clave), identidad_id))
    conexion.commit()
    return clave


def autenticar(conexion: sqlite3.Connection, clave: str) -> str | None:
    """La identidad dueña de esa clave, si no está archivada: archivarla revoca la clave."""
    fila = conexion.execute(
        "SELECT id FROM identidades WHERE clave_hash = ? AND archivada = 0", (_hash(clave),)
    ).fetchone()
    return fila[0] if fila else None


# ── Roles ──


def _rol(fila: tuple) -> Rol:
    id_, nombre, herramientas = fila
    return Rol(id=id_, nombre=nombre, herramientas=json.loads(herramientas))


def crear_rol(conexion: sqlite3.Connection, nuevo: RolNuevo) -> Rol:
    cursor = conexion.execute(
        "INSERT INTO roles (id, nombre, herramientas) VALUES ('pendiente', ?, ?)",
        (nuevo.nombre, json.dumps(nuevo.herramientas)),
    )
    id_ = f"rol-{cursor.lastrowid}"
    conexion.execute("UPDATE roles SET id = ? WHERE num = ?", (id_, cursor.lastrowid))
    conexion.commit()
    return obtener_rol(conexion, id_)


def obtener_rol(conexion: sqlite3.Connection, id_: str) -> Rol | None:
    fila = conexion.execute("SELECT id, nombre, herramientas FROM roles WHERE id = ?", (id_,)).fetchone()
    return _rol(fila) if fila else None


def listar_roles(conexion: sqlite3.Connection) -> list[Rol]:
    return [_rol(f) for f in conexion.execute("SELECT id, nombre, herramientas FROM roles ORDER BY num")]


def cambiar_rol(conexion: sqlite3.Connection, id_: str, cambios: CambiosRol) -> Rol | None:
    rol = obtener_rol(conexion, id_)
    if rol is None:
        return None
    nombre = cambios.nombre if cambios.nombre is not None else rol.nombre
    herramientas = cambios.herramientas if cambios.herramientas is not None else rol.herramientas
    conexion.execute("UPDATE roles SET nombre = ?, herramientas = ? WHERE id = ?", (nombre, json.dumps(herramientas), id_))
    conexion.commit()
    return obtener_rol(conexion, id_)


def patrones_de(conexion: sqlite3.Connection, identidad_id: str) -> list[str]:
    """Las herramientas que permite el rol actual de la identidad. Sin rol, ninguna: solo conversa."""
    fila = conexion.execute(
        "SELECT r.herramientas FROM identidades i JOIN roles r ON r.id = i.rol WHERE i.id = ?", (identidad_id,)
    ).fetchone()
    return json.loads(fila[0]) if fila else []


# ── Privacidad ──


def autores(conexion: sqlite3.Connection, ids: list[int]) -> dict[int, str]:
    """De esos recuerdos, los que salieron de la conversación de otra persona, con su nombre."""
    if not ids:
        return {}
    marcas = ",".join("?" * len(ids))
    filas = conexion.execute(
        "SELECT m.recuerdo_id, i.nombre FROM mensajes m JOIN conversaciones c ON c.id = m.conversacion_id"
        f" JOIN identidades i ON i.id = c.identidad_id WHERE m.recuerdo_id IN ({marcas})",
        ids,
    ).fetchall()
    return dict(filas)


def recuerdos_de(conexion: sqlite3.Connection, identidad_id: str) -> set[int]:
    """Los únicos recuerdos que Ashur puede usar con esa persona: los de los mensajes de sus conversaciones. No los
    que la mencionan: esos son las notas de Sergio sobre ella."""
    filas = conexion.execute(
        "SELECT m.recuerdo_id FROM mensajes m JOIN conversaciones c ON c.id = m.conversacion_id"
        " WHERE c.identidad_id = ?",
        (identidad_id,),
    ).fetchall()
    return {f[0] for f in filas}
