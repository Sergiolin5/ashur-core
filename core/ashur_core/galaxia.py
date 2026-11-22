"""Modelos del contrato contracts/galaxy-state.schema.json.

El schema es la fuente de verdad; estos modelos lo copian a mano (docs/adr/0003-stack-servidor.md).
"""

import zlib
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


def _fase(id_: str) -> float:
    """Una fase fija para cada identidad, para que no salte de lugar entre actualizaciones."""
    return (zlib.crc32(id_.encode()) % 1000) / 1000


def estado_actual(aprendizaje: Aprendizaje, identidades: list, modulos: list | tuple = ()) -> EstadoGalaxia:
    """La galaxia con lo que el core sabe hoy (docs/adr/0011-app-conectada-al-core.md, docs/adr/0012-identidades.md).
    Cada identidad no archivada aparece según su nivel: personaje sobre Identidades, luna alrededor de Identidades o
    planeta propio. El id del cuerpo no cambia al subir o bajar, para que la cámara pueda seguirlo."""
    visibles = [i for i in identidades if not i.archivada and i.nivel > 0]
    cuerpos = [
        Cuerpo(tipo="nucleo", id="ashur", nombre="Ashur", masa=1 + aprendizaje.recuerdos, orbita=None, ref=None),
        Cuerpo(
            tipo="planeta", id="identidades", nombre="Identidades",
            masa=1 + sum(i.menciones for i in visibles if i.nivel < 3),
            orbita=Orbita(centro="ashur", fase=0.1), ref=None,
        ),
        Cuerpo(tipo="planeta", id="objetos", nombre="Objetos", masa=1, orbita=Orbita(centro="ashur", fase=0.6), ref=None),
    ]
    # Cada módulo registrado es un planeta; su masa es la cantidad de recuerdos con origen igual a su id.
    for manifiesto, recuerdos in modulos:
        cuerpos.append(
            Cuerpo(
                tipo="planeta", id=f"modulo-{manifiesto.id}", nombre=manifiesto.nombre, masa=1 + recuerdos,
                orbita=Orbita(centro="ashur", fase=_fase(manifiesto.id)), ref=Ref(tipo="modulo", id=manifiesto.id),
            )
        )
    tipos = {1: "personaje", 2: "luna", 3: "planeta"}
    for i in visibles:
        centro = "ashur" if i.nivel == 3 else "identidades"
        cuerpos.append(
            Cuerpo(
                tipo=tipos[i.nivel], id=f"identidad-{i.id}", nombre=i.nombre, masa=i.menciones,
                orbita=Orbita(centro=centro, fase=_fase(i.id)), ref=Ref(tipo="identidad", id=i.id),
            )
        )
    return EstadoGalaxia(aprendizaje=aprendizaje, cuerpos=cuerpos, eventos=[])
