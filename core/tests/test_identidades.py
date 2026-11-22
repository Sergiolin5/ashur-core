import json
import sqlite3
from pathlib import Path

import pytest

from bases import quitar_desde
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ashur_core import identidades, memoria
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
    datos["identidades"] = [{"nombre": "x", "identidad_id": i} for i in ids]
    datos["objetos"] = []
    return datos


def test_el_ejemplo_del_contrato_es_valido():
    identidades.Identidad.model_validate(json.loads((RAIZ / "identidad.ejemplo.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "cambio",
    [lambda d: d.update(clase="planta"), lambda d: d.update(extra=1), lambda d: d.update(nivel=4)],
    ids=["clase-desconocida", "campo-extra", "nivel-fuera-de-rango"],
)
def test_rechaza_lo_que_el_schema_no_permite(cambio):
    datos = json.loads((RAIZ / "identidad.ejemplo.json").read_text(encoding="utf-8"))
    cambio(datos)
    with pytest.raises(ValidationError):
        identidades.Identidad.model_validate(datos)


def test_los_niveles_suben_y_bajan_con_margen():
    assert identidades.nivel_siguiente(0, 0) == 0
    assert identidades.nivel_siguiente(0, 1) == 1
    assert identidades.nivel_siguiente(0, 5) == 2
    assert identidades.nivel_siguiente(0, 25) == 3
    # Con 4 menciones, una luna (umbral 5) no baja todavía: baja recién por debajo de 0.8 · 5 = 4.
    assert identidades.nivel_siguiente(2, 4) == 2
    assert identidades.nivel_siguiente(2, 3) == 1


def test_crear_listar_archivar_y_restaurar(cliente):
    ana = cliente.post("/identidades", json={"nombre": "Ana", "clase": "persona"}).json()
    nube = cliente.post("/identidades", json={"nombre": "Nube", "clase": "mascota"}).json()
    assert (ana["id"], nube["id"]) == ("ide-1", "ide-2")
    assert ana["menciones"] == 0 and ana["nivel"] == 0

    assert cliente.patch("/identidades/ide-2", json={"archivada": True}).status_code == 401
    assert cliente.patch("/identidades/ide-2", json={"archivada": True}, headers=ADMIN).json()["archivada"] is True
    assert [i["id"] for i in cliente.get("/identidades").json()] == ["ide-1"]
    assert [i["id"] for i in cliente.get("/identidades", params={"archivadas": True}).json()] == ["ide-1", "ide-2"]
    cliente.patch("/identidades/ide-2", json={"archivada": False}, headers=ADMIN)
    assert len(cliente.get("/identidades").json()) == 2
    assert cliente.patch("/identidades/ide-9", json={"nombre": "x"}, headers=ADMIN).status_code == 404
    assert cliente.patch("/identidades/ide-1", json={"nombre": None}, headers=ADMIN).status_code == 422
    assert cliente.delete("/identidades/ide-1", headers=ADMIN).status_code == 405  # no se borra, se archiva


def test_un_recuerdo_no_puede_enlazar_una_identidad_que_no_existe(cliente):
    assert cliente.post("/recuerdos", json=recuerdo_con("ide-7")).status_code == 422
    assert cliente.post("/recuerdos", json=recuerdo_con(None)).status_code == 201


def test_las_menciones_hacen_aparecer_y_crecer_a_la_identidad_en_la_galaxia(cliente):
    cliente.post("/identidades", json={"nombre": "Ana", "clase": "persona"})

    def cuerpo():
        cuerpos = {c["id"]: c for c in cliente.get("/galaxia").json()["cuerpos"]}
        return cuerpos.get("identidad-ide-1")

    assert cuerpo() is None  # sin menciones, no tiene peso
    cliente.post("/recuerdos", json=recuerdo_con("ide-1", "ide-1"))  # dos veces en un recuerdo cuenta una
    assert cliente.get("/identidades").json()[0]["menciones"] == 1
    primero = cuerpo()
    assert primero["tipo"] == "personaje" and primero["orbita"]["centro"] == "identidades"
    for _ in range(4):
        cliente.post("/recuerdos", json=recuerdo_con("ide-1"))
    luna = cuerpo()
    assert luna["tipo"] == "luna" and luna["orbita"]["fase"] == primero["orbita"]["fase"]  # misma fase, mismo id
    EstadoGalaxia.model_validate(cliente.get("/galaxia").json())

    cliente.patch("/identidades/ide-1", json={"archivada": True}, headers=ADMIN)
    assert cuerpo() is None


def test_una_base_de_la_version_4_recibe_la_tabla_de_identidades(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    con.execute("DROP TABLE identidades")
    con.execute("DROP TABLE pedidos")
    con.execute("DROP TABLE objetos")
    quitar_desde(con, 9)
    con.execute("PRAGMA user_version = 4")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert identidades.listar(con) == []
    con.close()
    assert sqlite3.connect(ruta).execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA


def test_un_enlace_viejo_a_una_identidad_no_lo_hereda_una_identidad_nueva(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    identidades.crear(con, identidades.IdentidadNueva(nombre="Ana", clase="persona"))
    # Antes de la versión 5 se aceptaba cualquier identidad_id, así que una base de la 7 puede traer ide-9.
    memoria.crear(con, memoria.RecuerdoNuevo.model_validate(recuerdo_con("ide-9", "ide-1", None)))
    quitar_desde(con, 9)
    con.execute("PRAGMA user_version = 7")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    nueva = identidades.crear(con, identidades.IdentidadNueva(nombre="Nube", clase="mascota"))
    assert (nueva.id, nueva.menciones) == ("ide-10", 0)
    assert identidades.obtener(con, "ide-1").menciones == 1  # la que ya existía conserva su enlace
    con.close()


def test_reservar_no_retrocede_la_numeracion(tmp_path):
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    for nombre in ("Ana", "Bruno", "Carla"):
        identidades.crear(con, identidades.IdentidadNueva(nombre=nombre, clase="persona"))
    memoria.crear(con, memoria.RecuerdoNuevo.model_validate(recuerdo_con("ide-2")))
    identidades.reservar_ids_enlazados(con)
    assert identidades.crear(con, identidades.IdentidadNueva(nombre="Dani", clase="persona")).id == "ide-4"
    con.close()
