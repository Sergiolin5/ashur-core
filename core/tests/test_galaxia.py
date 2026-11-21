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
