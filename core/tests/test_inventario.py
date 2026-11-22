import json
from pathlib import Path

import pytest

from bases import quitar_desde
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ashur_core import inventario, memoria
from ashur_core.app import app
from ashur_core.galaxia import EstadoGalaxia

RAIZ = Path(__file__).resolve().parents[2] / "contracts"
CLAVE, ADMIN = "c", {"X-Ashur-Clave-Admin": "a"}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", CLAVE)
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": CLAVE})


def recuerdo_con(*ids):
    datos = json.loads((RAIZ / "recuerdo.ejemplo.json").read_text(encoding="utf-8"))
    del datos["id"]
    datos["identidades"] = []
    datos["objetos"] = [{"nombre": "x", "inventario_id": i} for i in ids]
    return datos


def test_el_ejemplo_del_contrato_es_valido():
    inventario.Objeto.model_validate(json.loads((RAIZ / "objeto.ejemplo.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "cambio",
    [lambda d: d.update(nombre=""), lambda d: d.update(extra=1), lambda d: d.pop("lugar"), lambda d: d.update(lugar="")],
    ids=["nombre-vacio", "campo-extra", "falta-lugar", "lugar-vacio"],
)
def test_rechaza_lo_que_el_schema_no_permite(cambio):
    datos = json.loads((RAIZ / "objeto.ejemplo.json").read_text(encoding="utf-8"))
    cambio(datos)
    with pytest.raises(ValidationError):
        inventario.Objeto.model_validate(datos)


def test_crear_listar_mover_archivar_y_restaurar(cliente):
    bici = cliente.post("/objetos", json={"nombre": "bicicleta roja", "lugar": "garaje"})
    assert bici.status_code == 201
    casco = cliente.post("/objetos", json={"nombre": "casco", "lugar": None}).json()
    assert (bici.json()["id"], casco["id"]) == ("obj-1", "obj-2")
    assert casco["lugar"] is None and casco["menciones"] == 0 and casco["archivado"] is False
    assert cliente.post("/objetos", json={"nombre": "casco"}).status_code == 422  # lugar es obligatorio, aunque sea null
    assert TestClient(app).get("/objetos").status_code == 401

    assert cliente.patch("/objetos/obj-2", json={"lugar": "clóset"}).status_code == 401
    assert cliente.patch("/objetos/obj-2", json={"lugar": "clóset"}, headers=ADMIN).json()["lugar"] == "clóset"
    assert cliente.patch("/objetos/obj-2", json={"lugar": None}, headers=ADMIN).json()["lugar"] is None

    assert cliente.patch("/objetos/obj-2", json={"archivado": True}, headers=ADMIN).json()["archivado"] is True
    assert [o["id"] for o in cliente.get("/objetos").json()] == ["obj-1"]
    assert [o["id"] for o in cliente.get("/objetos", params={"archivados": True}).json()] == ["obj-1", "obj-2"]
    cliente.patch("/objetos/obj-2", json={"archivado": False}, headers=ADMIN)
    assert len(cliente.get("/objetos").json()) == 2
    assert cliente.patch("/objetos/obj-9", json={"nombre": "x"}, headers=ADMIN).status_code == 404
    assert cliente.patch("/objetos/obj-1", json={"nombre": None}, headers=ADMIN).status_code == 422
    assert cliente.patch("/objetos/obj-1", json={"archivado": None}, headers=ADMIN).status_code == 422
    assert cliente.delete("/objetos/obj-1", headers=ADMIN).status_code == 405  # no se borra, se archiva


def test_un_recuerdo_no_puede_enlazar_un_objeto_que_no_existe(cliente):
    assert cliente.post("/recuerdos", json=recuerdo_con("obj-7")).status_code == 422
    assert cliente.post("/recuerdos", json=recuerdo_con(None)).status_code == 201
    cliente.post("/objetos", json={"nombre": "casco", "lugar": None})
    assert cliente.post("/recuerdos", json=recuerdo_con("obj-1")).status_code == 201
    assert cliente.patch("/recuerdos/1", json={"objetos": [{"nombre": "x", "inventario_id": "obj-7"}]}, headers=ADMIN).status_code == 422


def test_las_menciones_cuentan_recuerdos_distintos(cliente):
    cliente.post("/objetos", json={"nombre": "casco", "lugar": None})
    cliente.post("/recuerdos", json=recuerdo_con("obj-1", "obj-1"))  # dos veces en un recuerdo cuenta una
    cliente.post("/recuerdos", json=recuerdo_con("obj-1"))
    assert cliente.get("/objetos").json()[0]["menciones"] == 2


def test_el_planeta_objetos_pesa_segun_los_objetos_sin_archivar(cliente):
    def planeta():
        datos = cliente.get("/galaxia").json()
        EstadoGalaxia.model_validate(datos)
        return {c["id"]: c for c in datos["cuerpos"]}["objetos"]

    assert planeta()["masa"] == 1
    cliente.post("/objetos", json={"nombre": "casco", "lugar": None})
    cliente.post("/objetos", json={"nombre": "bicicleta roja", "lugar": "garaje"})
    assert planeta()["masa"] == 3
    cliente.patch("/objetos/obj-1", json={"archivado": True}, headers=ADMIN)
    assert planeta()["masa"] == 2
    # Los objetos no son cuerpos todavía (decisión 12).
    assert {c["id"] for c in cliente.get("/galaxia").json()["cuerpos"]} == {"ashur", "identidades", "objetos"}


def test_una_base_de_la_version_6_recibe_la_tabla_de_objetos(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    con.execute("DROP TABLE objetos")
    quitar_desde(con, 9)
    con.execute("PRAGMA user_version = 6")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert inventario.listar(con) == []
    con.close()


def test_un_enlace_viejo_a_un_objeto_no_lo_hereda_un_objeto_nuevo(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    con.execute("DROP TABLE objetos")
    quitar_desde(con, 9)
    con.execute("PRAGMA user_version = 6")
    con.commit()
    # En la versión 6 se aceptaba cualquier inventario_id.
    memoria.crear(con, memoria.RecuerdoNuevo.model_validate(recuerdo_con("obj-3", "obj-1", None)))
    con.close()
    con = memoria.abrir(ruta)
    nuevo = inventario.crear(con, inventario.ObjetoNuevo(nombre="paraguas", lugar=None))
    assert (nuevo.id, nuevo.menciones) == ("obj-4", 0)
    con.close()
