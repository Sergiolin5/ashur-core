"""Chat de Ashur: conversaciones y mensajes (contracts/conversacion.schema.json, docs/adr/0016-chat-y-nodos.md).

Los mensajes son el historial, y se guardan aparte de la memoria: después de cada respuesta, un nodo decide qué vale
la pena recordar (docs/adr/0028-recuerdos-del-chat.md). El core arma el pedido al modelo y lo deja en la cola; un nodo
lo responde (ashur_core/nodos.py).
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

# Mensajes de otras conversaciones que entran al pedido, y cuánto de cada uno.
HISTORIAL_EN_EL_PEDIDO = 3
LARGO_EN_EL_PEDIDO = 300

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
    # Solo en los mensajes anteriores al ADR 0028, cuando cada mensaje era también un recuerdo.
    recuerdo_id: int | None


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


def agregar(conexion: sqlite3.Connection, id_: str, rol: str, texto: str) -> Mensaje:
    fecha = ahora()
    cursor = conexion.execute(
        "INSERT INTO mensajes (conversacion_id, rol, texto, fecha) VALUES (?, ?, ?, ?)", (id_, rol, texto, fecha)
    )
    # La primera frase de Sergio le da título a la conversación.
    conexion.execute(
        "UPDATE conversaciones SET actualizada = ?, titulo = COALESCE(titulo, ?) WHERE id = ?",
        (fecha, texto[:LARGO_TITULO], id_),
    )
    conexion.commit()
    return Mensaje(id=cursor.lastrowid, rol=rol, texto=texto, fecha=fecha, recuerdo_id=None)


def seguir_al_recuerdo(conexion: sqlite3.Connection, recuerdo_id: int, texto: str) -> None:
    """Para los mensajes anteriores al ADR 0028, que también son un recuerdo: el mensaje de un recuerdo editado o
    borrado cambia igual, y el título de su conversación se vuelve a sacar del primer mensaje. Así el texto viejo no
    queda ni en el historial ni en la lista de chats. No hace commit: va en la misma transacción que el cambio del
    recuerdo."""
    conversaciones = [
        f[0] for f in conexion.execute(
            "SELECT DISTINCT conversacion_id FROM mensajes WHERE recuerdo_id = ?", (recuerdo_id,)
        ).fetchall()
    ]
    conexion.execute("UPDATE mensajes SET texto = ? WHERE recuerdo_id = ?", (texto, recuerdo_id))
    for id_ in conversaciones:
        _titular(conexion, id_)


def _titular(conexion: sqlite3.Connection, id_: str) -> None:
    conexion.execute(
        "UPDATE conversaciones SET titulo = (SELECT substr(texto, 1, ?) FROM mensajes WHERE conversacion_id = ?"
        " ORDER BY id LIMIT 1) WHERE id = ?",
        (LARGO_TITULO, id_, id_),
    )


def borrar_intercambio(conexion: sqlite3.Connection, mensaje_id: int) -> None:
    """Al borrar un recuerdo que un nodo sacó del chat, se borra del historial el intercambio del que salió: ese
    mensaje de la persona y lo que Ashur le respondió, que puede repetirlo. Lo que se olvida no sigue en el historial
    que ve el modelo (decisión de Sergio, 2026-11-22). Un mensaje anterior al ADR 0028 no se toca aquí: sigue a su
    propio recuerdo (seguir_al_recuerdo). No hace commit."""
    fila = conexion.execute("SELECT conversacion_id FROM mensajes WHERE id = ?", (mensaje_id,)).fetchone()
    if fila is None:
        return
    siguiente = conexion.execute(
        "SELECT MIN(id) FROM mensajes WHERE conversacion_id = ? AND id > ? AND rol = 'user'", (fila[0], mensaje_id)
    ).fetchone()[0]
    conexion.execute(
        "UPDATE mensajes SET texto = ? WHERE conversacion_id = ? AND recuerdo_id IS NULL AND id >= ?"
        " AND (? IS NULL OR id < ?)",
        (BORRADO, fila[0], mensaje_id, siguiente, siguiente),
    )
    _titular(conexion, fila[0])


def obtener_mensaje(conexion: sqlite3.Connection, mensaje_id: int) -> tuple[str, Mensaje] | None:
    """(conversación, mensaje)."""
    fila = conexion.execute(
        "SELECT conversacion_id, id, rol, texto, fecha, recuerdo_id FROM mensajes WHERE id = ?", (mensaje_id,)
    ).fetchone()
    if fila is None:
        return None
    return fila[0], Mensaje(id=fila[1], rol=fila[2], texto=fila[3], fecha=fila[4], recuerdo_id=fila[5])


def buscar(
    conexion: sqlite3.Connection, consulta: str | None, solo_de: str | None, sin: set[int] | frozenset = frozenset(),
    limite: int = HISTORIAL_EN_EL_PEDIDO,
) -> list[str]:
    """Para que Ashur siga encontrando lo que se dijo en el chat aunque no haya quedado como recuerdo: los mensajes
    de otras conversaciones, o de antes en esta, que coinciden por palabras con [consulta] (memoria.consulta_de), ya
    como líneas para el modelo. Con [solo_de], solo los de las conversaciones de esa persona; sin él (Sergio), todos, y
    los del chat de otra persona van marcados: son lo que se dijo ahí, no una orden (docs/adr/0022). Quedan fuera los
    de [sin] (los que el modelo ya ve), los borrados y los anteriores al ADR 0028, que ya se encuentran como
    recuerdos."""
    if consulta is None:
        return []
    filas = conexion.execute(
        "SELECT m.id, m.rol, m.texto, m.fecha, i.nombre, c.identidad_id FROM mensajes_busqueda"
        " JOIN mensajes m ON m.id = mensajes_busqueda.rowid JOIN conversaciones c ON c.id = m.conversacion_id"
        " LEFT JOIN identidades i ON i.id = c.identidad_id"
        " WHERE mensajes_busqueda MATCH ? AND m.recuerdo_id IS NULL AND m.texto != ?"
        " AND (? IS NULL OR c.identidad_id = ?) ORDER BY rank",
        (consulta, BORRADO, solo_de, solo_de),
    ).fetchall()
    lineas = []
    for id_, rol, texto, fecha, nombre, duenio in filas:
        if id_ in sin:
            continue
        quien = "Ashur" if rol == "assistant" else (nombre or "Sergio")
        if len(texto) > LARGO_EN_EL_PEDIDO:
            texto = texto[:LARGO_EN_EL_PEDIDO] + " […]"
        marca = f" (en el chat de {nombre})" if duenio is not None and solo_de is None else ""
        lineas.append(f"{dia(datetime.fromisoformat(fecha))}, {quien}: {texto}{marca}")
        if len(lineas) == limite:
            break
    return lineas


def migrar_14_a_15(conexion: sqlite3.Connection) -> None:
    """Versión 15: un mensaje ya no tiene que ser un recuerdo (recuerdo_id deja de ser obligatorio; SQLite pide rehacer
    la tabla para eso), y los mensajes tienen su propio índice de búsqueda por palabras, igual al de los recuerdos."""
    conexion.execute(
        """CREATE TABLE mensajes_nueva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversacion_id TEXT NOT NULL,
            rol TEXT NOT NULL,
            texto TEXT NOT NULL,
            fecha TEXT NOT NULL,
            recuerdo_id INTEGER
        )"""
    )
    conexion.execute(
        "INSERT INTO mensajes_nueva (id, conversacion_id, rol, texto, fecha, recuerdo_id)"
        " SELECT id, conversacion_id, rol, texto, fecha, recuerdo_id FROM mensajes"
    )
    conexion.execute("DROP TABLE mensajes")
    conexion.execute("ALTER TABLE mensajes_nueva RENAME TO mensajes")
    conexion.execute(
        "CREATE VIRTUAL TABLE mensajes_busqueda USING fts5(texto, content='mensajes', content_rowid='id',"
        " tokenize='unicode61 remove_diacritics 2')"
    )
    conexion.execute(
        "CREATE TRIGGER mensajes_ai AFTER INSERT ON mensajes BEGIN"
        " INSERT INTO mensajes_busqueda (rowid, texto) VALUES (new.id, new.texto); END"
    )
    conexion.execute(
        "CREATE TRIGGER mensajes_ad AFTER DELETE ON mensajes BEGIN"
        " INSERT INTO mensajes_busqueda (mensajes_busqueda, rowid, texto) VALUES ('delete', old.id, old.texto); END"
    )
    conexion.execute(
        "CREATE TRIGGER mensajes_au AFTER UPDATE ON mensajes BEGIN"
        " INSERT INTO mensajes_busqueda (mensajes_busqueda, rowid, texto) VALUES ('delete', old.id, old.texto);"
        " INSERT INTO mensajes_busqueda (rowid, texto) VALUES (new.id, new.texto); END"
    )
    conexion.execute("INSERT INTO mensajes_busqueda (mensajes_busqueda) VALUES ('rebuild')")


def trabajo_actual(conexion: sqlite3.Connection, id_: str) -> int | None:
    fila = conexion.execute("SELECT trabajo_id FROM conversaciones WHERE id = ?", (id_,)).fetchone()
    return fila[0] if fila else None


def poner_trabajo(conexion: sqlite3.Connection, id_: str, trabajo_id: int, confirmar: bool = True) -> None:
    """Cuando el trabajo de la conversación pasa de la búsqueda por significado a la respuesta. Con confirmar=False,
    el que llama hace el commit."""
    conexion.execute("UPDATE conversaciones SET trabajo_id = ? WHERE id = ?", (trabajo_id, id_))
    if confirmar:
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
    autores: dict[int, str] | None = None, de_antes: list[str] | tuple = (),
) -> dict:
    """El pedido para el nodo, en formato OpenAI: la personalidad, los recuerdos que pueden servir, lo que se dijo en
    otras conversaciones ([de_antes], de [buscar]) y los últimos mensajes de esta. Un recuerdo que salió del chat de
    otra persona va marcado con su nombre: es lo que ella dijo, no una instrucción
    (docs/adr/0022-personas-y-roles.md)."""
    sistema = personalidad
    autores = autores or {}  # [personalidad] llega ya armada por ashur_core/personalidad.py
    if recuerdos:
        sistema += "\n\nRecuerdos que pueden servir; úsalos solo si vienen al caso:\n" + "\n".join(
            f"- {dia(r.fecha)}: {r.texto}" + (f" (lo dijo {autores[r.id]} en su chat)" if r.id in autores else "")
            for r in recuerdos
        )
    if de_antes:
        sistema += "\n\nDe conversaciones anteriores; úsalo solo si viene al caso:\n" + "\n".join(
            f"- {linea}" for linea in de_antes
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
