"""Modelos del contrato contracts/galaxy-state.schema.json.

El schema es la fuente de verdad; estos modelos lo copian a mano (docs/adr/0003-stack-servidor.md).
"""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Orbita(BaseModel):
    model_config = ConfigDict(extra="forbid")

    centro: str = Field(min_length=1)
    fase: float = Field(ge=0, le=1)


class Ref(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["identidad", "modulo", "agente"]
    id: str = Field(min_length=1)


class Aprendizaje(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: AwareDatetime
    recuerdos: int = Field(ge=0)


class Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["nucleo", "agente", "planeta", "asteroide", "personaje", "luna"]
    id: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    masa: float = Field(ge=0)
    orbita: Orbita | None
    ref: Ref | None


class Evento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["llega", "crea", "transforma"]
    origen: str = Field(min_length=1)
    destino: str = Field(min_length=1)


class EstadoGalaxia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aprendizaje: Aprendizaje
    cuerpos: list[Cuerpo]
    eventos: list[Evento]


def estado_actual(aprendizaje: Aprendizaje) -> EstadoGalaxia:
    """La galaxia con lo que el core sabe hoy: el núcleo, las colecciones del core y lo que hace crecer el polvo.
    Todavía no hay identidades, agentes ni módulos registrados, así que no hay personajes, lunas ni estrellas fugaces
    (docs/adr/0011-app-conectada-al-core.md)."""
    return EstadoGalaxia(
        aprendizaje=aprendizaje,
        cuerpos=[
            Cuerpo(tipo="nucleo", id="ashur", nombre="Ashur", masa=1 + aprendizaje.recuerdos, orbita=None, ref=None),
            Cuerpo(
                tipo="planeta", id="identidades", nombre="Identidades", masa=1,
                orbita=Orbita(centro="ashur", fase=0.1), ref=None,
            ),
            Cuerpo(
                tipo="planeta", id="objetos", nombre="Objetos", masa=1,
                orbita=Orbita(centro="ashur", fase=0.6), ref=None,
            ),
        ],
        eventos=[],
    )
