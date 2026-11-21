import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ashur_core.galaxia import EstadoGalaxia

EJEMPLO = Path(__file__).resolve().parents[2] / "contracts" / "galaxy-state.ejemplo.json"


def leer_ejemplo():
    return json.loads(EJEMPLO.read_text(encoding="utf-8"))


def test_el_ejemplo_del_contrato_es_valido():
    EstadoGalaxia.model_validate(leer_ejemplo())


def test_rechaza_campos_que_el_schema_no_tiene():
    datos = leer_ejemplo()
    datos["cuerpos"][0]["extra"] = 1
    with pytest.raises(ValidationError):
        EstadoGalaxia.model_validate(datos)


def test_orbita_es_obligatoria_aunque_pueda_ser_null():
    datos = leer_ejemplo()
    del datos["cuerpos"][0]["orbita"]
    with pytest.raises(ValidationError):
        EstadoGalaxia.model_validate(datos)


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d["cuerpos"][0].pop("ref"),
        lambda d: d["cuerpos"][1].update(ref={"tipo": "recuerdo", "id": "x"}),
        lambda d: d.pop("aprendizaje"),
        lambda d: d["aprendizaje"].update(inicio="2026-11-01T09:00:00"),
        lambda d: d["aprendizaje"].update(recuerdos=-1),
    ],
    ids=["falta-ref", "ref-tipo-desconocido", "falta-aprendizaje", "inicio-sin-zona", "recuerdos-negativos"],
)
def test_rechaza_lo_nuevo_que_el_schema_no_permite(cambio):
    datos = leer_ejemplo()
    cambio(datos)
    with pytest.raises(ValidationError):
        EstadoGalaxia.model_validate(datos)
