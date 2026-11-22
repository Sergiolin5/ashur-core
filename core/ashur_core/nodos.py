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

from pydantic import BaseModel, ConfigDict, Field

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


class Nodo(NodoNuevo):
    id: str
    archivado: bool
    en_linea: bool
    modo: Modo
    modelos: list[Modelo]
    ultimo_latido: str | None


class NodoCreado(BaseModel):
    nodo: Nodo
    clave: str  # se muestra una sola vez; el core solo guarda su hash


class CambiosNodo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archivado: bool


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


def mejor_modelo(necesidad: str, modo: str, modelos: list[Modelo]) -> Modelo | None:
    """El modelo más grande que el nodo ofrece para esa necesidad y que su modo le deja correr."""
    candidatos = [m for m in modelos if _CAPACIDAD[necesidad] in m.capacidades and puede_correr(modo, m)]
    return max(candidatos, key=lambda m: m.tamano, default=None)


def le_toca(necesidad: str, propio: Modelo, otros: list[tuple[str, list[Modelo]]], edad_s: float) -> bool:
    """Un trabajo reciente solo lo toma el nodo con el mejor modelo en línea; pasado ESPERA_MEJOR_S, cualquiera."""
    if edad_s >= ESPERA_MEJOR_S:
        return True
    mejores = [mejor_modelo(necesidad, modo, modelos) for modo, modelos in otros]
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
    id_, nombre, archivado, modo, modelos, ultimo = fila
    en_linea = ultimo is not None and ahora - datetime.fromisoformat(ultimo) < timedelta(seconds=FUERA_DE_LINEA_S)
    return Nodo(
        id=id_, nombre=nombre, archivado=bool(archivado), en_linea=en_linea and not archivado, modo=modo,
        modelos=json.loads(modelos), ultimo_latido=ultimo,
    )


_COLUMNAS = "id, nombre, archivado, modo, modelos, ultimo_latido"


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


def archivar(conexion: sqlite3.Connection, id_: str, archivado: bool) -> Nodo | None:
    if obtener(conexion, id_) is None:
        return None
    conexion.execute("UPDATE nodos SET archivado = ? WHERE id = ?", (int(archivado), id_))
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
    mismo. Un trabajo cuyo plazo venció vuelve a estar disponible."""
    ahora = ahora or _ahora()
    nodo = obtener(conexion, id_nodo, ahora)
    if nodo is None or not nodo.en_linea:
        return None
    otros = [(n.modo, n.modelos) for n in listar(conexion, ahora) if n.en_linea and n.id != id_nodo]
    disponibles = conexion.execute(
        "SELECT id, necesidad, creado FROM trabajos"
        " WHERE estado = 'pendiente' OR (estado = 'tomado' AND vence < ?) ORDER BY id",
        (ahora.isoformat(),),
    ).fetchall()
    for id_, necesidad, creado in disponibles:
        modelo = mejor_modelo(necesidad, nodo.modo, nodo.modelos)
        if modelo is None:
            continue
        edad = (ahora - datetime.fromisoformat(creado)).total_seconds()
        if not le_toca(necesidad, modelo, otros, edad):
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
        "SELECT estado, nodo_id, intentos, necesidad, conversacion_id FROM trabajos WHERE id = ?", (id_,)
    ).fetchone()
    if fila is None or fila[0] != "tomado" or fila[1] != id_nodo:
        raise TrabajoAjeno()
    _, _, intentos, necesidad, conversacion_id = fila
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
    return estado, {"necesidad": necesidad, "conversacion_id": conversacion_id}


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
