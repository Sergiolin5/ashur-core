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
    potencia: int = Field(default=1, ge=1, description="Qué tan capaz es su modelo, relativo a los otros nodos.")


class EstadoNodo(BaseModel):
    """Lo que un dispositivo informa de sí mismo. La Zima no informa nada: siempre está enchufada."""

    model_config = ConfigDict(extra="forbid")

    cargando: bool
    en_bateria: bool
    bloqueado: bool
    app_abierta: bool


class Nodo(BaseModel):
    id: int
    nombre: str
    url: str
    modelo: str
    nivel: Nivel
    activo: bool
    tiene_clave: bool
    potencia: int
    estado: EstadoNodo | None
    visto: str | None


class CambiosNodo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1)
    url: str | None = Field(default=None, min_length=1)
    modelo: str | None = Field(default=None, min_length=1)
    nivel: Nivel | None = None
    clave: str | None = None
    activo: bool | None = None
    potencia: int | None = Field(default=None, ge=1)


def crear_tabla_nodos(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        """CREATE TABLE nodos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            url TEXT NOT NULL,
            modelo TEXT NOT NULL,
            nivel INTEGER NOT NULL,
            clave TEXT,
            activo INTEGER NOT NULL DEFAULT 1,
            potencia INTEGER NOT NULL DEFAULT 1,
            estado TEXT
        )"""
    )


_COLUMNAS_NODO = "id, nombre, url, modelo, nivel, activo, clave, potencia, estado"


def _nodo(fila: tuple) -> Nodo:
    id_, nombre, url, modelo, nivel, activo, clave, potencia, estado = fila
    datos = json.loads(estado) if estado else None
    return Nodo(
        id=id_, nombre=nombre, url=url, modelo=modelo, nivel=nivel, activo=bool(activo), tiene_clave=bool(clave),
        potencia=potencia, estado=EstadoNodo(**datos["estado"]) if datos else None, visto=datos["visto"] if datos else None,
    )


def crear_nodo(conexion: sqlite3.Connection, nuevo: NodoNuevo) -> Nodo:
    cursor = conexion.execute(
        "INSERT INTO nodos (nombre, url, modelo, nivel, clave, activo, potencia) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nuevo.nombre, nuevo.url.rstrip("/"), nuevo.modelo, nuevo.nivel, nuevo.clave, int(nuevo.activo), nuevo.potencia),
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


def informar_estado(conexion: sqlite3.Connection, id_: int, estado: EstadoNodo) -> Nodo | None:
    if obtener_nodo(conexion, id_) is None:
        return None
    datos = {"estado": estado.model_dump(), "visto": datetime.now(timezone.utc).isoformat()}
    conexion.execute("UPDATE nodos SET estado = ? WHERE id = ?", (json.dumps(datos), id_))
    conexion.commit()
    return obtener_nodo(conexion, id_)


VIGENCIA_ESTADO_S = 300  # un dispositivo que no informa hace más de 5 minutos no está disponible


def disponible(nodo: Nodo, ahora: datetime) -> bool:
    """Un nodo que nunca informa estado (la Zima, un servidor) siempre está; uno que informa, solo si lo hizo hace poco."""
    if not nodo.activo:
        return False
    if nodo.visto is None:
        return True
    return (ahora - datetime.fromisoformat(nodo.visto)).total_seconds() <= VIGENCIA_ESTADO_S


def holgado(nodo: Nodo) -> bool:
    """Puede aportar sin gastarse: siempre enchufado, cargando, o con la app abierta y desbloqueado."""
    e = nodo.estado
    return e is None or not e.en_bateria or e.cargando or (e.app_abierta and not e.bloqueado)


def ordenar(nodos: list[Nodo], ahora: datetime) -> list[Nodo]:
    """Orden en que Ashur prueba los nodos (decisión de Sergio, docs/adr/0014-chat.md):
    1. los holgados, por nivel y del modelo más capaz al menos capaz;
    2. al final, los que están en batería, del más liviano al más pesado, para no gastarlos."""
    vivos = [n for n in nodos if disponible(n, ahora)]
    holgados = sorted((n for n in vivos if holgado(n)), key=lambda n: (n.nivel, -n.potencia, n.id))
    en_bateria = sorted((n for n in vivos if not holgado(n)), key=lambda n: (n.potencia, n.nivel, n.id))
    return holgados + en_bateria


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
    """Los nodos disponibles, en el orden de ordenar()."""
    claves = dict(conexion.execute("SELECT id, clave FROM nodos").fetchall())
    orden = ordenar(listar_nodos(conexion), datetime.now(timezone.utc))
    return [ProveedorOpenAI(n.url, n.modelo, claves[n.id], n.nombre) for n in orden]


INSTRUCCION_RECUERDOS = (
    "Lee la última parte de la conversación entre Sergio y Ashur. Si hay algo que valga la pena recordar a largo "
    "plazo sobre Sergio, su gente, sus mascotas, sus cosas o sus planes, escríbelo como frases cortas. "
    'Responde solo con JSON, así: {"recordar": ["frase", "frase"]}. Si no hay nada, responde {"recordar": []}.'
)


def extraer_recuerdos(proveedor: "ProveedorOpenAI", historial: list[dict]) -> list[str]:
    """Le pregunta al mismo nodo qué vale la pena recordar (decisión de Sergio, opción A). Si la respuesta no es el JSON
    pedido, no guarda nada: es mejor perder un recuerdo que guardar ruido."""
    pedido = [*historial[-6:], {"role": "user", "content": INSTRUCCION_RECUERDOS}]
    try:
        texto = proveedor.responder(pedido)
    except SinModelo:
        return []
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fin < inicio:
        return []
    try:
        frases = json.loads(texto[inicio : fin + 1]).get("recordar", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    return [f.strip() for f in frases if isinstance(f, str) and f.strip()][:5]


def responder(conexion: sqlite3.Connection, historial: list[dict]) -> tuple[str, "ProveedorOpenAI"]:
    """Prueba los nodos en orden y devuelve (texto, el nodo que respondió)."""
    fallos = []
    for proveedor in proveedores(conexion):
        try:
            return proveedor.responder(historial), proveedor
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
