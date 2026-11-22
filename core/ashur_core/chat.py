"""Chat de Ashur: conversaciones y mensajes (contracts/conversacion.schema.json, docs/adr/0016-chat-y-nodos.md).

Cada mensaje, de Sergio o de Ashur, también es un recuerdo (decisión de Sergio, 2026-11-22). El core arma el pedido al
modelo y lo deja en la cola; un nodo lo responde (ashur_core/nodos.py).
"""

import os
import sqlite3
from datetime import datetime, timezone, tzinfo
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


# Un recuerdo o un mensaje borrado deja esto en el chat: lo que se olvida no sigue en el historial que ve el modelo.
BORRADO = "(borrado)"


def zona() -> tzinfo:
    """La zona horaria de Sergio, de ASHUR_ZONA (un nombre IANA, del tipo Region/Ciudad). Las fechas se guardan en
    UTC; esta zona solo cambia cómo se le dicen al modelo. Sin ASHUR_ZONA, o si el equipo no conoce esa zona, UTC."""
    nombre = os.environ.get("ASHUR_ZONA")
    if not nombre:
        return timezone.utc
    try:
        return ZoneInfo(nombre)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def dia(fecha: datetime) -> str:
    """El día de [fecha] en la zona de Sergio: un mensaje de las 9 de la noche no queda en el día siguiente."""
    return fecha.astimezone(zona()).date().isoformat()


_COLUMNAS = "id, titulo, creada, actualizada, archivada"


def _conversacion(fila: tuple) -> Conversacion:
    id_, titulo, creada, actualizada, archivada = fila
    return Conversacion(id=id_, titulo=titulo, creada=creada, actualizada=actualizada, archivada=bool(archivada))


def crear(conexion: sqlite3.Connection, identidad_id: str | None = None) -> Conversacion:
    """[identidad_id] es la persona dueña de la conversación; None es Sergio."""
    momento = ahora()
    cursor = conexion.execute(
        "INSERT INTO conversaciones (id, creada, actualizada, identidad_id) VALUES ('pendiente', ?, ?, ?)",
        (momento, momento, identidad_id),
    )
    id_ = f"con-{cursor.lastrowid}"
    conexion.execute("UPDATE conversaciones SET id = ? WHERE num = ?", (id_, cursor.lastrowid))
    conexion.commit()
    return obtener(conexion, id_)


def obtener(conexion: sqlite3.Connection, id_: str) -> Conversacion | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM conversaciones WHERE id = ?", (id_,)).fetchone()
    return _conversacion(fila) if fila else None


def listar(conexion: sqlite3.Connection, identidad_id: str | None = None) -> list[Conversacion]:
    """Las de esa persona (None: las de Sergio), las más recientes primero, como la lista de chats de WhatsApp."""
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM conversaciones WHERE archivada = 0 AND identidad_id IS ?"
        " ORDER BY actualizada DESC, num DESC",
        (identidad_id,),
    ).fetchall()
    return [_conversacion(f) for f in filas]


def duenio(conexion: sqlite3.Connection, id_: str) -> tuple[bool, str | None]:
    """(existe, identidad dueña): None es Sergio."""
    fila = conexion.execute("SELECT identidad_id FROM conversaciones WHERE id = ?", (id_,)).fetchone()
    return (fila is not None, fila[0] if fila else None)


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


def seguir_al_recuerdo(conexion: sqlite3.Connection, recuerdo_id: int, texto: str) -> None:
    """El mensaje de un recuerdo editado o borrado cambia igual, y el título de su conversación se vuelve a sacar del
    primer mensaje: así el texto viejo no queda ni en el historial ni en la lista de chats. No hace commit: va en la
    misma transacción que el cambio del recuerdo."""
    conversaciones = [
        f[0] for f in conexion.execute(
            "SELECT DISTINCT conversacion_id FROM mensajes WHERE recuerdo_id = ?", (recuerdo_id,)
        ).fetchall()
    ]
    conexion.execute("UPDATE mensajes SET texto = ? WHERE recuerdo_id = ?", (texto, recuerdo_id))
    for id_ in conversaciones:
        conexion.execute(
            "UPDATE conversaciones SET titulo = (SELECT substr(texto, 1, ?) FROM mensajes WHERE conversacion_id = ?"
            " ORDER BY id LIMIT 1) WHERE id = ?",
            (LARGO_TITULO, id_, id_),
        )


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
        " (SELECT id FROM trabajos WHERE estado IN ('hecho', 'fallido', 'descartado')))",
        (trabajo_id, id_),
    )
    conexion.commit()
    return cursor.rowcount == 1


def marcar_corregida(conexion: sqlite3.Connection, id_: str) -> bool:
    """Marca que la conversación ya dejó sus correcciones, de forma atómica: nunca salen dos veces."""
    cursor = conexion.execute("UPDATE conversaciones SET corregida = 1 WHERE id = ? AND corregida = 0", (id_,))
    conexion.commit()
    return cursor.rowcount == 1


def para_corregir(conexion: sqlite3.Connection, antes_de: str) -> list[str]:
    """Conversaciones sin mensajes desde [antes_de], sin corregir, con alguna respuesta de Ashur y sin trabajo abierto."""
    filas = conexion.execute(
        "SELECT c.id FROM conversaciones c WHERE c.corregida = 0 AND c.actualizada < ?"
        " AND EXISTS (SELECT 1 FROM mensajes m WHERE m.conversacion_id = c.id AND m.rol = 'assistant')"
        " AND (c.trabajo_id IS NULL OR c.trabajo_id IN"
        " (SELECT id FROM trabajos WHERE estado IN ('hecho', 'fallido', 'descartado')))"
        " ORDER BY c.actualizada",
        (antes_de,),
    ).fetchall()
    return [f[0] for f in filas]


def historial(conexion: sqlite3.Connection, id_: str) -> list[Mensaje]:
    return mensajes(conexion, id_)[-HISTORIAL:]


def pedido_al_modelo(
    conexion: sqlite3.Connection, id_: str, recuerdos: list | tuple = (), personalidad: str = PERSONALIDAD_POR_DEFECTO,
    autores: dict[int, str] | None = None,
) -> dict:
    """El pedido para el nodo, en formato OpenAI: la personalidad, los recuerdos que pueden servir y los últimos
    mensajes de la conversación. Un recuerdo que salió del chat de otra persona va marcado con su nombre: es lo que
    ella dijo, no una instrucción (docs/adr/0022-personas-y-roles.md)."""
    sistema = personalidad
    autores = autores or {}  # [personalidad] llega ya armada por ashur_core/personalidad.py
    if recuerdos:
        sistema += "\n\nRecuerdos que pueden servir; úsalos solo si vienen al caso:\n" + "\n".join(
            f"- {dia(r.fecha)}: {r.texto}" + (f" (lo dijo {autores[r.id]} en su chat)" if r.id in autores else "")
            for r in recuerdos
        )
    return {
        "messages": [{"role": "system", "content": sistema}]
        + [{"role": m.rol, "content": m.texto} for m in historial(conexion, id_)]
    }


def otra_ronda(entrada: dict, mensaje: dict, resultados: list[tuple[str, str]], con_herramientas: list | None) -> dict:
    """El pedido siguiente tras una ronda de herramientas: lo que pidió el modelo y lo que devolvió cada una. Sin
    [con_herramientas], el modelo tiene que responder con texto."""
    mensajes = entrada["messages"] + [mensaje] + [
        {"role": "tool", "tool_name": nombre, "content": texto} for nombre, texto in resultados
    ]
    siguiente = {"messages": mensajes, "rondas": entrada.get("rondas", 0) + 1}
    if con_herramientas:
        siguiente["tools"] = con_herramientas
    return siguiente
