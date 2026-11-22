"""Nodos de casa y su cola de trabajos (contracts/nodo.schema.json, docs/adr/0016-chat-y-nodos.md).

El core piensa y los nodos solo ejecutan: un nodo se registra, avisa que sigue vivo con su modo y sus modelos, y va
a buscar trabajos. El core nunca llama a un nodo (docs/REFERENCIA-ANTERIOR.md, punto 2). Ashur decide qué nodo y qué
modelo atienden cada trabajo, según lo que necesita y lo que cada nodo ofrece en ese momento.
"""

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ashur_core import significado

# Un nodo queda fuera de línea tras tres latidos perdidos: 3 × 15 s (docs/REFERENCIA-ANTERIOR.md, punto 2).
LATIDO_S = 15
FUERA_DE_LINEA_S = 3 * LATIDO_S
# Cuánto tiempo tiene un nodo para devolver un trabajo antes de que vuelva a la cola.
PLAZO_S = 300
INTENTOS = 3
# Un modelo de hasta este tamaño es liviano: un nodo en modo light puede correrlo.
LIVIANO_BYTES = 2_500_000_000
# Mientras un trabajo es reciente, solo lo toma el nodo que mejor puede atenderlo; después, cualquiera que pueda.
ESPERA_MEJOR_S = 10

Modo = Literal["full", "light", "busy", "off"]
Necesidad = Literal["conversar", "embedding"]
_CAPACIDAD = {"conversar": "completion", "embedding": "embedding"}


class Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    tamano: int = Field(ge=0)
    capacidades: list[str]


class Latido(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modo: Modo
    modelos: list[Modelo]


class NodoNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)


class Horario(BaseModel):
    """Cuándo presta el equipo su modelo, en la hora local del equipo. Si hasta < desde, cruza la medianoche."""

    model_config = ConfigDict(extra="forbid")

    desde: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    hasta: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class AjustesNodo(BaseModel):
    """Lo que Sergio decide de cada nodo desde la app (docs/adr/0019-ajustes-de-modulos-y-nodos.md). null: lo que
    el nodo decida por su cuenta (todos sus modelos, su contexto por defecto, a toda hora)."""

    model_config = ConfigDict(extra="forbid")

    modelos_ofrecidos: list[str] | None = None
    num_ctx: int | None = Field(default=None, ge=512, le=131072)
    horario: Horario | None = None


class Nodo(NodoNuevo):
    id: str
    archivado: bool
    en_linea: bool
    modo: Modo
    modelos: list[Modelo]
    ultimo_latido: str | None
    ajustes: AjustesNodo

    def prestados(self) -> list[Modelo]:
        """Los modelos que Sergio le deja prestar a este nodo. El core lo hace cumplir, diga lo que diga el nodo."""
        ofrecidos = self.ajustes.modelos_ofrecidos
        if ofrecidos is None:
            return self.modelos
        return [m for m in self.modelos if m.nombre in ofrecidos or m.nombre.split(":")[0] in ofrecidos]


class NodoCreado(BaseModel):
    nodo: Nodo
    clave: str  # se muestra una sola vez; el core solo guarda su hash


class CambiosNodo(BaseModel):
    """Solo se tocan los campos enviados. archivado no puede ser null; los ajustes en null vuelven a lo del nodo."""

    model_config = ConfigDict(extra="forbid")

    archivado: bool | None = None
    modelos_ofrecidos: list[str] | None = None
    num_ctx: int | None = Field(default=None, ge=512, le=131072)
    horario: Horario | None = None

    @model_validator(mode="after")
    def archivado_no_null(self) -> "CambiosNodo":
        if "archivado" in self.model_fields_set and self.archivado is None:
            raise ValueError("archivado no puede ser null")
        return self


class Trabajo(BaseModel):
    """Lo que recibe un nodo: el pedido al modelo, ya armado por el core, en formato OpenAI."""

    id: int
    necesidad: Necesidad
    modelo: str
    entrada: dict


class Resultado(BaseModel):
    """Lo que devuelve un nodo: la respuesta cruda del modelo, o el error que tuvo."""

    model_config = ConfigDict(extra="forbid")

    salida: dict | None = None
    error: str | None = Field(default=None, min_length=1)


# ── Política: funciones puras, se prueban en cualquier sistema (docs/REFERENCIA-ANTERIOR.md, punto 5) ──


def puede_correr(modo: str, modelo: Modelo) -> bool:
    """Sergio siempre gana en sus máquinas: busy y off no toman nada, light solo lo liviano."""
    if modo == "full":
        return True
    if modo == "light":
        return modelo.tamano <= LIVIANO_BYTES
    return False


def mejor_modelo(necesidad: str, modo: str, modelos: list[Modelo], requiere: str | None = None) -> Modelo | None:
    """El modelo más grande que el nodo ofrece para esa necesidad y que su modo le deja correr. Para embeddings, solo el
    de significado.MODELO: vectores de modelos distintos no se pueden comparar."""
    candidatos = [
        m for m in modelos
        if _CAPACIDAD[necesidad] in m.capacidades and puede_correr(modo, m)
        and (necesidad != "embedding" or significado.es_el_modelo(m.nombre))
        and (requiere is None or requiere in m.capacidades)
    ]
    return max(candidatos, key=lambda m: m.tamano, default=None)


def le_toca(
    necesidad: str, propio: Modelo, otros: list[tuple[str, list[Modelo]]], edad_s: float, requiere: str | None = None
) -> bool:
    """Un trabajo reciente solo lo toma el nodo con el mejor modelo en línea; pasado ESPERA_MEJOR_S, cualquiera."""
    if edad_s >= ESPERA_MEJOR_S:
        return True
    mejores = [mejor_modelo(necesidad, modo, modelos, requiere) for modo, modelos in otros]
    return all(m is None or m.tamano <= propio.tamano for m in mejores)


# ── Base ──


def crear_tablas(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE nodos (
            num INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            clave_hash TEXT NOT NULL UNIQUE,
            archivado INTEGER NOT NULL DEFAULT 0,
            modo TEXT NOT NULL DEFAULT 'off',
            modelos TEXT NOT NULL DEFAULT '[]',
            ultimo_latido TEXT
        )"""
    )
    conexion.execute(
        """CREATE TABLE trabajos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            necesidad TEXT NOT NULL,
            entrada TEXT NOT NULL,
            conversacion_id TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            creado TEXT NOT NULL,
            nodo_id TEXT,
            modelo TEXT,
            vence TEXT,
            intentos INTEGER NOT NULL DEFAULT 0,
            salida TEXT,
            error TEXT
        )"""
    )


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _hash(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


def _nodo(fila: tuple, ahora: datetime) -> Nodo:
    id_, nombre, archivado, modo, modelos, ultimo, ajustes = fila
    en_linea = ultimo is not None and ahora - datetime.fromisoformat(ultimo) < timedelta(seconds=FUERA_DE_LINEA_S)
    return Nodo(
        id=id_, nombre=nombre, archivado=bool(archivado), en_linea=en_linea and not archivado, modo=modo,
        modelos=json.loads(modelos), ultimo_latido=ultimo, ajustes=AjustesNodo.model_validate_json(ajustes or "{}"),
    )


_COLUMNAS = "id, nombre, archivado, modo, modelos, ultimo_latido, ajustes"


def agregar_ajustes(conexion: sqlite3.Connection) -> None:
    """Versión 11: los ajustes de cada nodo."""
    conexion.execute("ALTER TABLE nodos ADD COLUMN ajustes TEXT")


def crear(conexion: sqlite3.Connection, nuevo: NodoNuevo) -> NodoCreado:
    clave = secrets.token_hex(32)
    cursor = conexion.execute(
        "INSERT INTO nodos (id, nombre, clave_hash) VALUES ('pendiente', ?, ?)", (nuevo.nombre, _hash(clave))
    )
    id_ = f"nod-{cursor.lastrowid}"
    conexion.execute("UPDATE nodos SET id = ? WHERE num = ?", (id_, cursor.lastrowid))
    conexion.commit()
    return NodoCreado(nodo=obtener(conexion, id_), clave=clave)


def obtener(conexion: sqlite3.Connection, id_: str, ahora: datetime | None = None) -> Nodo | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS} FROM nodos WHERE id = ?", (id_,)).fetchone()
    return _nodo(fila, ahora or _ahora()) if fila else None


def listar(conexion: sqlite3.Connection, ahora: datetime | None = None) -> list[Nodo]:
    filas = conexion.execute(f"SELECT {_COLUMNAS} FROM nodos ORDER BY num").fetchall()
    return [_nodo(f, ahora or _ahora()) for f in filas]


def cambiar(conexion: sqlite3.Connection, id_: str, cambios: CambiosNodo) -> Nodo | None:
    """Archiva o restaura, y cambia los ajustes enviados."""
    nodo = obtener(conexion, id_)
    if nodo is None:
        return None
    if "archivado" in cambios.model_fields_set:
        conexion.execute("UPDATE nodos SET archivado = ? WHERE id = ?", (int(cambios.archivado), id_))
    campos = cambios.model_fields_set - {"archivado"}
    if campos:
        ajustes = nodo.ajustes.model_copy(update={c: getattr(cambios, c) for c in campos})
        conexion.execute("UPDATE nodos SET ajustes = ? WHERE id = ?", (ajustes.model_dump_json(), id_))
    conexion.commit()
    return obtener(conexion, id_)


def autenticar(conexion: sqlite3.Connection, clave: str) -> str | None:
    """El id del nodo dueño de esa clave, si existe y no está archivado."""
    fila = conexion.execute(
        "SELECT id FROM nodos WHERE clave_hash = ? AND archivado = 0", (_hash(clave),)
    ).fetchone()
    return fila[0] if fila else None


def latir(conexion: sqlite3.Connection, id_: str, latido: Latido, ahora: datetime | None = None) -> Nodo:
    conexion.execute(
        "UPDATE nodos SET modo = ?, modelos = ?, ultimo_latido = ? WHERE id = ?",
        (latido.modo, json.dumps([m.model_dump() for m in latido.modelos]), (ahora or _ahora()).isoformat(), id_),
    )
    conexion.commit()
    return obtener(conexion, id_, ahora)


def encolar(
    conexion: sqlite3.Connection, necesidad: str, entrada: dict, conversacion_id: str | None = None,
    estado: str = "pendiente",
) -> int:
    """Con estado "preparando", ningún nodo lo toma hasta que [preparar] le ponga su entrada."""
    cursor = conexion.execute(
        "INSERT INTO trabajos (necesidad, entrada, conversacion_id, creado, estado) VALUES (?, ?, ?, ?, ?)",
        (necesidad, json.dumps(entrada, ensure_ascii=False), conversacion_id, _ahora().isoformat(), estado),
    )
    conexion.commit()
    return cursor.lastrowid


def preparar(conexion: sqlite3.Connection, id_: int, entrada: dict) -> None:
    conexion.execute(
        "UPDATE trabajos SET entrada = ?, estado = 'pendiente', creado = ? WHERE id = ? AND estado = 'preparando'",
        (json.dumps(entrada, ensure_ascii=False), _ahora().isoformat(), id_),
    )
    conexion.commit()


def descartar(conexion: sqlite3.Connection, id_: int) -> None:
    conexion.execute("UPDATE trabajos SET estado = 'descartado' WHERE id = ? AND estado = 'preparando'", (id_,))
    conexion.commit()


def tomar(conexion: sqlite3.Connection, id_nodo: str, ahora: datetime | None = None) -> Trabajo | None:
    """El trabajo más viejo que este nodo puede y le toca atender, tomado de forma atómica: dos nodos nunca toman el
    mismo. Primero los de una conversación, después los de fondo. Un trabajo cuyo plazo venció vuelve a estar
    disponible."""
    ahora = ahora or _ahora()
    nodo = obtener(conexion, id_nodo, ahora)
    if nodo is None or not nodo.en_linea:
        return None
    otros = [(n.modo, n.prestados()) for n in listar(conexion, ahora) if n.en_linea and n.id != id_nodo]
    disponibles = conexion.execute(
        "SELECT id, necesidad, creado, json_extract(entrada, '$.tools') IS NOT NULL FROM trabajos"
        " WHERE estado = 'pendiente' OR (estado = 'tomado' AND vence < ?)"
        " ORDER BY conversacion_id IS NULL, id",  # primero lo que alguien está esperando en el chat
        (ahora.isoformat(),),
    ).fetchall()
    for id_, necesidad, creado, con_herramientas in disponibles:
        requiere = "tools" if con_herramientas else None  # un pedido con herramientas necesita un modelo que las use
        modelo = mejor_modelo(necesidad, nodo.modo, nodo.prestados(), requiere)
        if modelo is None:
            continue
        edad = (ahora - datetime.fromisoformat(creado)).total_seconds()
        if not le_toca(necesidad, modelo, otros, edad, requiere):
            continue
        cursor = conexion.execute(
            "UPDATE trabajos SET estado = 'tomado', nodo_id = ?, modelo = ?, vence = ?"
            " WHERE id = ? AND (estado = 'pendiente' OR (estado = 'tomado' AND vence < ?))",
            (id_nodo, modelo.nombre, (ahora + timedelta(seconds=PLAZO_S)).isoformat(), id_, ahora.isoformat()),
        )
        conexion.commit()
        if cursor.rowcount == 1:
            entrada = json.loads(conexion.execute("SELECT entrada FROM trabajos WHERE id = ?", (id_,)).fetchone()[0])
            return Trabajo(id=id_, necesidad=necesidad, modelo=modelo.nombre, entrada=entrada)
    return None


class TrabajoAjeno(Exception):
    """El trabajo no existe, no es de este nodo o ya se cerró."""


def entregar(conexion: sqlite3.Connection, id_nodo: str, id_: int, resultado: Resultado) -> tuple[str, dict | None]:
    """Cierra el trabajo con su salida, o lo devuelve a la cola si falló y le quedan intentos. Devuelve el estado
    nuevo y la fila (necesidad, conversacion_id) para que el core siga con lo que corresponda."""
    fila = conexion.execute(
        "SELECT estado, nodo_id, intentos, necesidad, conversacion_id, entrada, modelo FROM trabajos WHERE id = ?", (id_,)
    ).fetchone()
    if fila is None or fila[0] != "tomado" or fila[1] != id_nodo:
        raise TrabajoAjeno()
    _, _, intentos, necesidad, conversacion_id, entrada, modelo = fila
    if resultado.salida is not None:
        conexion.execute(
            "UPDATE trabajos SET estado = 'hecho', salida = ?, error = NULL WHERE id = ?",
            (json.dumps(resultado.salida, ensure_ascii=False), id_),
        )
        estado = "hecho"
    else:
        estado = "pendiente" if intentos + 1 < INTENTOS else "fallido"
        conexion.execute(
            "UPDATE trabajos SET estado = ?, intentos = ?, error = ?, nodo_id = NULL, vence = NULL WHERE id = ?",
            (estado, intentos + 1, resultado.error or "El nodo no devolvió salida.", id_),
        )
    conexion.commit()
    return estado, {
        "necesidad": necesidad, "conversacion_id": conversacion_id, "entrada": json.loads(entrada), "modelo": modelo
    }


def tomado_por(conexion: sqlite3.Connection, id_: int, id_nodo: str) -> dict | None:
    """La necesidad y la entrada de un trabajo que este nodo tiene tomado, para validar su salida antes de cerrarlo."""
    fila = conexion.execute(
        "SELECT necesidad, entrada, conversacion_id, intentos FROM trabajos"
        " WHERE id = ? AND estado = 'tomado' AND nodo_id = ?",
        (id_, id_nodo),
    ).fetchone()
    if fila is None:
        return None
    return {"necesidad": fila[0], "entrada": json.loads(fila[1]), "conversacion_id": fila[2], "intentos": fila[3]}


def hay_quien(conexion: sqlite3.Connection, necesidad: str, requiere: str | None = None) -> bool:
    """Si algún nodo en línea puede atender esa necesidad en este momento."""
    return any(n.en_linea and mejor_modelo(necesidad, n.modo, n.prestados(), requiere) for n in listar(conexion))


def pendientes(conexion: sqlite3.Connection, necesidad: str, con_conversacion: bool) -> list[tuple[int, str, str | None]]:
    """Trabajos pendientes de esa necesidad: (id, creado, conversacion_id)."""
    condicion = "IS NOT NULL" if con_conversacion else "IS NULL"
    return conexion.execute(
        "SELECT id, creado, conversacion_id FROM trabajos"
        f" WHERE estado = 'pendiente' AND necesidad = ? AND conversacion_id {condicion}",
        (necesidad,),
    ).fetchall()


def abandonar(conexion: sqlite3.Connection, id_: int) -> bool:
    """Saca de la cola un trabajo que nadie tomó, de forma atómica."""
    cursor = conexion.execute("UPDATE trabajos SET estado = 'descartado' WHERE id = ? AND estado = 'pendiente'", (id_,))
    conexion.commit()
    return cursor.rowcount == 1


def estado_de(conexion: sqlite3.Connection, id_: int) -> dict | None:
    fila = conexion.execute(
        "SELECT estado, creado, nodo_id, modelo, error FROM trabajos WHERE id = ?", (id_,)
    ).fetchone()
    if fila is None:
        return None
    estado, creado, nodo_id, modelo, error = fila
    if estado == "preparando":
        estado = "pendiente"
    return {"estado": estado, "desde": creado, "nodo": nodo_id, "modelo": modelo, "error": error}
