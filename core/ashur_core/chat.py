"""Chat de Ashur: conversaciones y mensajes (contracts/conversacion.schema.json, docs/adr/0016-chat-y-nodos.md).

Cada mensaje, de Sergio o de Ashur, también es un recuerdo (decisión de Sergio, 2026-11-22). El core arma el pedido al
modelo y lo deja en la cola; un nodo lo responde (ashur_core/nodos.py).
"""

import sqlite3
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Sin personalidad cargada, Ashur usa esta. Es genérica a propósito: la de Sergio vive solo en su base, nunca en el
# repo, que es público (docs/REFERENCIA-ANTERIOR.md, punto 8).
PERSONALIDAD_POR_DEFECTO = (
    "Eres Ashur, un asistente personal. Hablas en español, en un tono cercano y directo. Escribes en texto plano, sin "
    "markdown, y das respuestas breves salvo que te pidan detalle. Si no sabes algo, lo dices."
)
# Cuántos mensajes de la conversación ve el modelo.
HISTORIAL = 20
LARGO_TITULO = 60

ORIGEN_SERGIO = "chat"
ORIGEN_ASHUR = "chat-ashur"

Rol = Literal["user", "assistant"]


class Conversacion(BaseModel):
    id: str
    titulo: str | None
    creada: str
    actualizada: str
    archivada: bool


class Mensaje(BaseModel):
    id: int
    rol: Rol
    texto: str
    fecha: str
    recuerdo_id: int


class MensajeNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1)


class Espera(BaseModel):
    """El trabajo que todavía no tiene respuesta: esperando un nodo, en un nodo, o fallido."""

    estado: str
    desde: str
    nodo: str | None
    modelo: str | None
    error: str | None


class ConversacionCompleta(BaseModel):
    conversacion: Conversacion
    mensajes: list[Mensaje]
    espera: Espera | None


def crear_tablas(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE conversaciones (
            num INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL UNIQUE,
            titulo TEXT,
            creada TEXT NOT NULL,
            actualizada TEXT NOT NULL,
            archivada INTEGER NOT NULL DEFAULT 0,
            trabajo_id INTEGER
        )"""
    )
    conexion.execute(
        """CREATE TABLE mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversacion_id TEXT NOT NULL,
            rol TEXT NOT NULL,
            texto TEXT NOT NULL,
            fecha TEXT NOT NULL,
            recuerdo_id INTEGER NOT NULL
        )"""
    )


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


_COLUMNAS = "id, titulo, creada, actualizada, archivada"


def _conversacion(fila: tuple) -> Conversacion:
    id_, titulo, creada, actualizada, archivada = fila
    return Conversacion(id=id_, titulo=titulo, creada=creada, actualizada=actualizada, archivada=bool(archivada))


def crear(conexion: sqlite3.Connection) -> Conversacion:
    momento = ahora()
    cursor = conexion.execute(
        "INSERT INTO conversaciones (id, creada, actualizada) VALUES ('pendiente', ?, ?)", (momento, momento)
    )
    id_ = f"con-{cursor.lastrowid}"
    conexion.execute("UPDATE conversaciones SET id = ? WHERE num = ?", (id_, cursor.lastrowid))
    conexion.commit()
    return obtener(conexion, id_)


def obtener(conexion: sqlite3.Connection, id_: str) -> Conversacion | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM conversaciones WHERE id = ?", (id_,)).fetchone()
    return _conversacion(fila) if fila else None


def listar(conexion: sqlite3.Connection) -> list[Conversacion]:
    """Las más recientes primero, como la lista de chats de WhatsApp."""
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM conversaciones WHERE archivada = 0 ORDER BY actualizada DESC, num DESC"
    ).fetchall()
    return [_conversacion(f) for f in filas]


def mensajes(conexion: sqlite3.Connection, id_: str) -> list[Mensaje]:
    filas = conexion.execute(
        "SELECT id, rol, texto, fecha, recuerdo_id FROM mensajes WHERE conversacion_id = ? ORDER BY id", (id_,)
    ).fetchall()
    return [Mensaje(id=i, rol=r, texto=t, fecha=f, recuerdo_id=rec) for i, r, t, f, rec in filas]


def agregar(conexion: sqlite3.Connection, id_: str, rol: str, texto: str, fecha: str, recuerdo_id: int) -> Mensaje:
    cursor = conexion.execute(
        "INSERT INTO mensajes (conversacion_id, rol, texto, fecha, recuerdo_id) VALUES (?, ?, ?, ?, ?)",
        (id_, rol, texto, fecha, recuerdo_id),
    )
    # La primera frase de Sergio le da título a la conversación.
    conexion.execute(
        "UPDATE conversaciones SET actualizada = ?, titulo = COALESCE(titulo, ?) WHERE id = ?",
        (fecha, texto[:LARGO_TITULO], id_),
    )
    conexion.commit()
    return Mensaje(id=cursor.lastrowid, rol=rol, texto=texto, fecha=fecha, recuerdo_id=recuerdo_id)


def trabajo_actual(conexion: sqlite3.Connection, id_: str) -> int | None:
    fila = conexion.execute("SELECT trabajo_id FROM conversaciones WHERE id = ?", (id_,)).fetchone()
    return fila[0] if fila else None


def poner_trabajo(conexion: sqlite3.Connection, id_: str, trabajo_id: int) -> None:
    """Cuando el trabajo de la conversación pasa de la búsqueda por significado a la respuesta."""
    conexion.execute("UPDATE conversaciones SET trabajo_id = ? WHERE id = ?", (trabajo_id, id_))
    conexion.commit()


def reservar(conexion: sqlite3.Connection, id_: str, trabajo_id: int) -> bool:
    """Le pone el trabajo a la conversación solo si no tiene otro abierto, de forma atómica: dos mensajes enviados a la
    vez nunca dejan dos respuestas."""
    cursor = conexion.execute(
        "UPDATE conversaciones SET trabajo_id = ? WHERE id = ? AND (trabajo_id IS NULL OR trabajo_id IN"
        " (SELECT id FROM trabajos WHERE estado IN ('hecho', 'fallido')))",
        (trabajo_id, id_),
    )
    conexion.commit()
    return cursor.rowcount == 1


def historial(conexion: sqlite3.Connection, id_: str) -> list[Mensaje]:
    return mensajes(conexion, id_)[-HISTORIAL:]


def pedido_al_modelo(
    conexion: sqlite3.Connection, id_: str, recuerdos: list | tuple = (), personalidad: str = PERSONALIDAD_POR_DEFECTO
) -> dict:
    """El pedido para el nodo, en formato OpenAI: la personalidad, los recuerdos que pueden servir y los últimos
    mensajes de la conversación."""
    sistema = personalidad
    if recuerdos:
        sistema += "\n\nRecuerdos que pueden servir; úsalos solo si vienen al caso:\n" + "\n".join(
            f"- {r.fecha.date().isoformat()}: {r.texto}" for r in recuerdos
        )
    return {
        "messages": [{"role": "system", "content": sistema}]
        + [{"role": m.rol, "content": m.texto} for m in historial(conexion, id_)]
    }
