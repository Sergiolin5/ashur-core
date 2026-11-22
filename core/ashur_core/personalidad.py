"""La personalidad de Ashur, su madurez y las correcciones que aprende de cada conversación
(docs/adr/0024-personalidad-madurez-y-correcciones.md).

La personalidad de Sergio vive solo en su base, nunca en el repo, que es público (docs/REFERENCIA-ANTERIOR.md,
punto 8). Las pruebas usan texto inventado.
"""

import json
import sqlite3
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

NIVELES = ("inicial", "intermedio", "pleno")
CORRECCIONES = 20  # se guardan solo las últimas
LARGO_CORRECCION = 200
POR_CONVERSACION = 2
INACTIVA_S = 30 * 60  # una conversación termina tras 30 minutos sin mensajes, o cuando se cierra


class Madurez(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicial: str = Field(min_length=1)
    intermedio: str = Field(min_length=1)
    pleno: str = Field(min_length=1)


class Umbrales(BaseModel):
    """Con cuántos recuerdos sube la madurez (decisión de Sergio, 2026-11-22). Ajustable por el administrador."""

    model_config = ConfigDict(extra="forbid")

    intermedio: int = Field(default=2000, gt=0)
    pleno: int = Field(default=20000, gt=0)

    @model_validator(mode="after")
    def en_orden(self) -> "Umbrales":
        if self.intermedio >= self.pleno:
            raise ValueError("el umbral de intermedio tiene que ser menor que el de pleno")
        return self


class Personalidad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: str = Field(min_length=1)
    sobre_sergio: str | None = None  # solo entra cuando habla Sergio
    madurez: Madurez
    trato: list[str] = Field(default_factory=list)
    umbrales: Umbrales = Field(default_factory=Umbrales)


class Correccion(BaseModel):
    """El texto va al pedido; la fuente y la fecha son solo para Sergio."""

    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1, max_length=LARGO_CORRECCION)
    fuente: str | None = None
    fecha: str | None = None


class EstadoMadurez(BaseModel):
    nivel: str
    recuerdos: int
    umbrales: Umbrales


class VistaPersonalidad(BaseModel):
    personalidad: Personalidad | None
    correcciones: list[Correccion]
    madurez: EstadoMadurez


def _leer(conexion: sqlite3.Connection, clave: str):
    fila = conexion.execute("SELECT valor FROM meta WHERE clave = ?", (clave,)).fetchone()
    return json.loads(fila[0]) if fila else None


def _escribir(conexion: sqlite3.Connection, clave: str, valor) -> None:
    conexion.execute(
        "INSERT OR REPLACE INTO meta (clave, valor) VALUES (?, ?)", (clave, json.dumps(valor, ensure_ascii=False))
    )
    conexion.commit()


def obtener(conexion: sqlite3.Connection) -> Personalidad | None:
    datos = _leer(conexion, "personalidad")
    return Personalidad.model_validate(datos) if datos else None


def guardar(conexion: sqlite3.Connection, personalidad: Personalidad) -> None:
    _escribir(conexion, "personalidad", personalidad.model_dump())


def correcciones(conexion: sqlite3.Connection) -> list[Correccion]:
    return [Correccion.model_validate(c) for c in (_leer(conexion, "correcciones") or [])]


def reemplazar_correcciones(conexion: sqlite3.Connection, lista: list[Correccion]) -> None:
    _escribir(conexion, "correcciones", [c.model_dump() for c in lista[-CORRECCIONES:]])


def agregar_correcciones(conexion: sqlite3.Connection, textos: list[str], fuente: str) -> None:
    fecha = datetime.now(timezone.utc).isoformat()
    nuevas = [Correccion(texto=t, fuente=fuente, fecha=fecha) for t in textos]
    reemplazar_correcciones(conexion, correcciones(conexion) + nuevas)


def nivel(recuerdos: int, umbrales: Umbrales) -> str:
    if recuerdos >= umbrales.pleno:
        return "pleno"
    if recuerdos >= umbrales.intermedio:
        return "intermedio"
    return "inicial"


def estado_madurez(conexion: sqlite3.Connection) -> EstadoMadurez:
    personalidad = obtener(conexion)
    umbrales = personalidad.umbrales if personalidad else Umbrales()
    recuerdos = conexion.execute("SELECT COUNT(*) FROM recuerdos").fetchone()[0]
    return EstadoMadurez(nivel=nivel(recuerdos, umbrales), recuerdos=recuerdos, umbrales=umbrales)


def vista(conexion: sqlite3.Connection) -> VistaPersonalidad:
    return VistaPersonalidad(
        personalidad=obtener(conexion), correcciones=correcciones(conexion), madurez=estado_madurez(conexion)
    )


def sistema(conexion: sqlite3.Connection, con_quien: str | None, por_defecto: str) -> str:
    """El texto de sistema del pedido. [con_quien] es el nombre de la otra persona; None es Sergio. Con otra persona
    no entra lo que Ashur sabe de Sergio, y el modelo sabe con quién habla. Solo entra la madurez actual."""
    personalidad = obtener(conexion)
    partes = [personalidad.base if personalidad else por_defecto]
    if con_quien is None:
        if personalidad and personalidad.sobre_sergio:
            partes.append("Lo que sabes de Sergio:\n" + personalidad.sobre_sergio)
    else:
        partes.append(f"Estás hablando con {con_quien}, no con Sergio.")
    if personalidad:
        actual = estado_madurez(conexion).nivel
        partes.append(f"Tu madurez es {actual}: {getattr(personalidad.madurez, actual)}")
        if personalidad.trato:
            partes.append("Trato:\n" + "\n".join(f"- {t}" for t in personalidad.trato))
    lista = correcciones(conexion)
    if lista:
        partes.append("Correcciones de conversaciones anteriores:\n" + "\n".join(f"- {c.texto}" for c in lista))
    return "\n\n".join(partes)


# ── Correcciones al terminar una conversación ──

INSTRUCCIONES = (
    "Revisas cómo respondió Ashur, un asistente personal, en la conversación que sigue. Si algo de cómo respondió "
    "Ashur debería cambiar en el futuro, escribe una o dos líneas, cada una empezando con «- », sobre cómo tiene que "
    "comportarse Ashur. Escribe sobre Ashur, nunca sobre la persona ni sobre lo que dijo, y sin nombres. Si no hay nada "
    "que corregir, escribe solo NADA."
)


def pedido_de_correcciones(mensajes: list, id_conversacion: str) -> dict:
    """El trabajo de fondo que resume las correcciones de una conversación. Nunca lleva herramientas."""
    transcripcion = "\n".join(f"{'Ashur' if m.rol == 'assistant' else 'Persona'}: {m.texto}" for m in mensajes)
    return {
        "messages": [{"role": "system", "content": INSTRUCCIONES}, {"role": "user", "content": transcripcion}],
        "proposito": "correcciones",
        "conversacion": id_conversacion,
    }


def leer_correcciones(texto: str) -> list[str]:
    """Las líneas «- …» de la respuesta, como máximo dos, de una línea y cortas. NADA es ninguna."""
    if texto.strip().upper().startswith("NADA"):
        return []
    lineas = [l.strip()[1:].strip() for l in texto.splitlines() if l.strip().startswith(("-", "•"))]
    # «- Nada que corregir.» también es ninguna: qwen suele contestar con viñetas.
    return [l[:LARGO_CORRECCION] for l in lineas if l and not l.upper().startswith("NADA")][:POR_CONVERSACION]


def migrar(conexion: sqlite3.Connection) -> None:
    """Versión 13: si cada conversación ya dejó sus correcciones. Las de antes cuentan como hechas, para que la primera
    vez no salga un trabajo por cada conversación vieja."""
    conexion.execute("ALTER TABLE conversaciones ADD COLUMN corregida INTEGER NOT NULL DEFAULT 0")
    conexion.execute("UPDATE conversaciones SET corregida = 1")
