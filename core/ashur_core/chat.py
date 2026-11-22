"""Chat con Ashur: el historial y quién responde (docs/adr/0014-chat.md).

El modelo que responde está detrás de un Proveedor, para seguir el orden de niveles de docs/ASHUR.md: nodos de casa,
modelo en el dispositivo y nube. Hoy hay un proveedor: un servidor Ollama en un nodo de casa, por HTTP, sin paquetes.
"""

import json
import os
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
    """No hay un modelo configurado o no responde."""


class Proveedor(Protocol):
    nombre: str

    def responder(self, historial: list[dict]) -> str: ...


class ProveedorOllama:
    """Un modelo local en un nodo de casa, servido por Ollama (POST /api/chat)."""

    def __init__(self, url: str, modelo: str, espera: float = 120):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.espera = espera
        self.nombre = f"ollama:{modelo}"

    def responder(self, historial: list[dict]) -> str:
        cuerpo = json.dumps(
            {"model": self.modelo, "messages": [{"role": "system", "content": PERSONA}, *historial], "stream": False}
        ).encode()
        pedido = urllib.request.Request(f"{self.url}/api/chat", data=cuerpo, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(pedido, timeout=self.espera) as respuesta:
                return json.loads(respuesta.read())["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            raise SinModelo(f"El nodo de casa no respondió: {e}") from None


def proveedor_configurado() -> Proveedor | None:
    """ASHUR_OLLAMA_URL y ASHUR_OLLAMA_MODELO eligen el nodo de casa. Sin ellas, no hay modelo."""
    url, modelo = os.environ.get("ASHUR_OLLAMA_URL"), os.environ.get("ASHUR_OLLAMA_MODELO")
    return ProveedorOllama(url, modelo) if url and modelo else None


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
