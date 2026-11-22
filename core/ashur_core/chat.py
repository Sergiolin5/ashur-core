"""Chat con Ashur: el historial y quién responde (docs/adr/0014-chat.md).

Ashur responde con el primer nodo disponible según los niveles de docs/ASHUR.md. Todos los nodos hablan la API
compatible con OpenAI, por HTTP y sin paquetes.
"""

import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

PERSONA = (
    "Eres Ashur, la IA personal de Sergio. Respondes en español, breve y con calidez. "
    "Si no sabes algo, lo dices."
)


class MensajeNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1)


class Mensaje(BaseModel):
    id: int
    autor: Literal["sergio", "ashur"]
    texto: str
    fecha: str


class SinModelo(Exception):
    """Ningún nodo respondió."""


# ── Nodos: dónde corren los modelos (docs/adr/0014-chat.md) ──
# Cada nodo habla la API compatible con OpenAI (POST /v1/chat/completions), como el servidor que propone PrivateLM
# dentro de la app (docs/REFERENCIA-PRIVATELM.md, punto 5), llama.cpp u Ollama. Así la Zima, el teléfono y después
# Macs, Windows u otros servidores entran igual. El nivel sigue docs/ASHUR.md: 1 nodo de casa, 2 dispositivo, 3 nube.

Nivel = Literal[1, 2, 3]


class NodoNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    url: str = Field(min_length=1, description="Base del servidor, por ejemplo http://servidor:8080")
    modelo: str = Field(min_length=1)
    nivel: Nivel = 1
    clave: str | None = Field(default=None, description="Bearer, si el nodo la pide. Nunca se devuelve.")
    activo: bool = True


class Nodo(BaseModel):
    id: int
    nombre: str
    url: str
    modelo: str
    nivel: Nivel
    activo: bool
    tiene_clave: bool


class CambiosNodo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1)
    url: str | None = Field(default=None, min_length=1)
    modelo: str | None = Field(default=None, min_length=1)
    nivel: Nivel | None = None
    clave: str | None = None
    activo: bool | None = None


def crear_tabla_nodos(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE nodos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            url TEXT NOT NULL,
            modelo TEXT NOT NULL,
            nivel INTEGER NOT NULL,
            clave TEXT,
            activo INTEGER NOT NULL DEFAULT 1
        )"""
    )


_COLUMNAS_NODO = "id, nombre, url, modelo, nivel, activo, clave"


def _nodo(fila: tuple) -> Nodo:
    id_, nombre, url, modelo, nivel, activo, clave = fila
    return Nodo(id=id_, nombre=nombre, url=url, modelo=modelo, nivel=nivel, activo=bool(activo), tiene_clave=bool(clave))


def crear_nodo(conexion: sqlite3.Connection, nuevo: NodoNuevo) -> Nodo:
    cursor = conexion.execute(
        "INSERT INTO nodos (nombre, url, modelo, nivel, clave, activo) VALUES (?, ?, ?, ?, ?, ?)",
        (nuevo.nombre, nuevo.url.rstrip("/"), nuevo.modelo, nuevo.nivel, nuevo.clave, int(nuevo.activo)),
    )
    conexion.commit()
    return obtener_nodo(conexion, cursor.lastrowid)


def obtener_nodo(conexion: sqlite3.Connection, id_: int) -> Nodo | None:
    fila = conexion.execute(f"SELECT {_COLUMNAS_NODO} FROM nodos WHERE id = ?", (id_,)).fetchone()
    return _nodo(fila) if fila else None


def listar_nodos(conexion: sqlite3.Connection) -> list[Nodo]:
    return [_nodo(f) for f in conexion.execute(f"SELECT {_COLUMNAS_NODO} FROM nodos ORDER BY nivel, id").fetchall()]


def editar_nodo(conexion: sqlite3.Connection, id_: int, cambios: CambiosNodo) -> Nodo | None:
    if obtener_nodo(conexion, id_) is None:
        return None
    for campo in cambios.model_fields_set:
        valor = getattr(cambios, campo)
        if valor is None and campo != "clave":
            continue
        if campo == "activo":
            valor = int(valor)
        if campo == "url":
            valor = valor.rstrip("/")
        conexion.execute(f"UPDATE nodos SET {campo} = ? WHERE id = ?", (valor, id_))
    conexion.commit()
    return obtener_nodo(conexion, id_)


class ProveedorOpenAI:
    """Un nodo que habla la API compatible con OpenAI. Sin paquetes: urllib de la librería estándar."""

    def __init__(self, url: str, modelo: str, clave: str | None, nombre: str, espera: float = 120):
        self.url, self.modelo, self.clave, self.nombre, self.espera = url, modelo, clave, nombre, espera

    def responder(self, historial: list[dict]) -> str:
        cuerpo = json.dumps(
            {"model": self.modelo, "messages": [{"role": "system", "content": PERSONA}, *historial], "stream": False}
        ).encode()
        cabeceras = {"Content-Type": "application/json"}
        if self.clave:
            cabeceras["Authorization"] = f"Bearer {self.clave}"
        pedido = urllib.request.Request(f"{self.url}/v1/chat/completions", data=cuerpo, headers=cabeceras)
        try:
            with urllib.request.urlopen(pedido, timeout=self.espera) as respuesta:
                return json.loads(respuesta.read())["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as e:
            raise SinModelo(f"{self.nombre} no respondió: {e}") from None


def proveedores(conexion: sqlite3.Connection) -> list[ProveedorOpenAI]:
    """Los nodos activos, en el orden de docs/ASHUR.md: primero el nivel más bajo disponible."""
    filas = conexion.execute(
        "SELECT nombre, url, modelo, clave FROM nodos WHERE activo = 1 ORDER BY nivel, id"
    ).fetchall()
    return [ProveedorOpenAI(url, modelo, clave, nombre) for nombre, url, modelo, clave in filas]


def responder(conexion: sqlite3.Connection, historial: list[dict]) -> tuple[str, str]:
    """Prueba los nodos en orden, k* = min{k : D_k}, y devuelve (texto, nombre del nodo que respondió)."""
    fallos = []
    for proveedor in proveedores(conexion):
        try:
            return proveedor.responder(historial), proveedor.nombre
        except SinModelo as e:
            fallos.append(str(e))
    raise SinModelo("Ningún nodo respondió. " + " ".join(fallos) if fallos else "No hay nodos configurados.")


def crear_tabla(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor TEXT NOT NULL,
            texto TEXT NOT NULL,
            fecha TEXT NOT NULL
        )"""
    )


def guardar(conexion: sqlite3.Connection, autor: str, texto: str) -> Mensaje:
    fecha = datetime.now(timezone.utc).isoformat()
    cursor = conexion.execute("INSERT INTO mensajes (autor, texto, fecha) VALUES (?, ?, ?)", (autor, texto, fecha))
    conexion.commit()
    return Mensaje(id=cursor.lastrowid, autor=autor, texto=texto, fecha=fecha)


def historial(conexion: sqlite3.Connection, ultimos: int = 50) -> list[Mensaje]:
    filas = conexion.execute(
        "SELECT id, autor, texto, fecha FROM (SELECT * FROM mensajes ORDER BY id DESC LIMIT ?) ORDER BY id", (ultimos,)
    ).fetchall()
    return [Mensaje(id=i, autor=a, texto=t, fecha=f) for i, a, t, f in filas]


def para_el_modelo(mensajes: list[Mensaje]) -> list[dict]:
    return [{"role": "user" if m.autor == "sergio" else "assistant", "content": m.texto} for m in mensajes]
