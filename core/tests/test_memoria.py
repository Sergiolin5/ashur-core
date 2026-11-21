import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ashur_core import memoria
from ashur_core.app import app

EJEMPLO = Path(__file__).resolve().parents[2] / "contracts" / "recuerdo.ejemplo.json"
CLAVE = "clave-de-prueba"


def leer_ejemplo():
    return json.loads(EJEMPLO.read_text(encoding="utf-8"))


def nuevo_ejemplo():
    datos = leer_ejemplo()
    del datos["id"]
    return datos


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", CLAVE)
    return TestClient(app, headers={"X-Ashur-Clave": CLAVE})


# Contrato


def test_el_ejemplo_del_contrato_es_valido():
    memoria.Recuerdo.model_validate(leer_ejemplo())


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d.update(sensibilidad="secreto"),
        lambda d: d.update(extra=1),
        lambda d: d["objetos"][1].pop("inventario_id"),
        lambda d: d.pop("opinion"),
        lambda d: d.update(fecha="2026-11-20T18:30:00"),
        lambda d: d["personas"][1].pop("contacto_id"),
    ],
    ids=["sensibilidad-desconocida", "campo-extra", "falta-inventario-id", "falta-opinion", "fecha-sin-zona", "falta-contacto-id"],
)
def test_rechaza_lo_que_el_schema_no_permite(cambio):
    datos = leer_ejemplo()
    cambio(datos)
    with pytest.raises(ValidationError):
        memoria.Recuerdo.model_validate(datos)


# Endpoints


def test_crear_listar_y_borrar(cliente):
    creado = cliente.post("/recuerdos", json=nuevo_ejemplo())
    assert creado.status_code == 201
    recuerdo = creado.json()
    assert recuerdo["id"] == 1
    assert recuerdo["objetos"][1] == {"nombre": "casco", "inventario_id": None}

    assert cliente.get("/recuerdos").json() == [recuerdo]

    assert cliente.delete("/recuerdos/1").status_code == 204
    assert cliente.get("/recuerdos").json() == []
    assert cliente.delete("/recuerdos/1").status_code == 404


def test_sin_clave_o_con_clave_equivocada_responde_401(cliente):
    assert cliente.get("/recuerdos", headers={"X-Ashur-Clave": "otra"}).status_code == 401
    sin_clave = TestClient(app)
    assert sin_clave.get("/recuerdos").status_code == 401


def test_sin_ashur_clave_configurada_la_memoria_queda_cerrada(cliente, monkeypatch):
    monkeypatch.delenv("ASHUR_CLAVE")
    assert cliente.get("/recuerdos").status_code == 503
    assert cliente.get("/vivo").status_code == 200


# Base de datos


def test_el_recuerdo_queda_en_disco(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    memoria.crear(con, memoria.RecuerdoNuevo.model_validate(nuevo_ejemplo()))
    con.close()

    con = memoria.abrir(ruta)
    assert [r.texto for r in memoria.listar(con)] == [leer_ejemplo()["texto"]]
    con.close()


def test_rechaza_una_base_con_esquema_mas_nuevo(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = sqlite3.connect(ruta)
    con.execute("PRAGMA user_version = 99")
    con.close()
    with pytest.raises(RuntimeError):
        memoria.abrir(ruta)
