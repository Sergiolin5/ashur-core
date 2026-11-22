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


def test_objeto_antiguo_sin_campos_nuevos_sigue_valido():
    datos = json.loads((RAIZ / "objeto.ejemplo.json").read_text(encoding="utf-8"))
    for campo in ("padre_id", "ranura", "ranuras", "identificadores", "especificaciones", "evidencia", "estado"):
        datos.pop(campo, None)
    inventario.Objeto.model_validate(datos)


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


def test_crear_raiz_y_componente_en_ranura_valida_conserva_evidencia_y_estado(cliente):
    raiz = cliente.post(
        "/objetos",
        json={"nombre": "equipo", "lugar": "estudio", "ranuras": ["pci-1"]},
    ).json()
    evidencia = {"source_files": ["foto-inventada.jpg"], "confidence": {"modelo": "visto"}}
    hijo = cliente.post(
        "/objetos",
        json={
            "nombre": "placa inventada",
            "lugar": None,
            "padre_id": raiz["id"],
            "ranura": "pci-1",
            "identificadores": {"model": "MODELO-FALSO"},
            "especificaciones": {"ram_gb": 16},
            "evidencia": evidencia,
            "estado": "sin_confirmar",
        },
    )
    assert hijo.status_code == 201
    assert hijo.json()["padre_id"] == raiz["id"]
    assert hijo.json()["ranura"] == "pci-1"
    assert hijo.json()["evidencia"] == evidencia
    assert hijo.json()["estado"] == "sin_confirmar"
    assert cliente.get("/objetos").json()[0]["ranuras"] == ["pci-1"]


def test_un_componente_con_ranura_sin_confirmar_conserva_el_padre(cliente):
    raiz = cliente.post("/objetos", json={"nombre": "equipo", "lugar": None}).json()
    hijo = cliente.post("/objetos", json={"nombre": "componente", "lugar": None, "padre_id": raiz["id"]})
    assert hijo.status_code == 201
    assert hijo.json()["padre_id"] == raiz["id"]
    assert hijo.json()["ranura"] is None


def test_rechaza_nombres_de_ranura_vacios(cliente):
    respuesta = cliente.post("/objetos", json={"nombre": "equipo", "lugar": None, "ranuras": [""]})
    assert respuesta.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"nombre": "hijo", "lugar": None, "padre_id": "obj-99", "ranura": "pci-1"},
        {"nombre": "hijo", "lugar": None, "padre_id": "obj-1", "ranura": "no-ofrecida"},
        {"nombre": "hijo", "lugar": None, "ranura": "pci-1"},
        {"nombre": "hijo", "lugar": "estudio", "padre_id": "obj-1", "ranura": "pci-1"},
    ],
    ids=["padre-inexistente", "ranura-no-declarada", "falta-ranura", "componente-con-lugar"],
)
def test_rechaza_jerarquia_o_lugar_de_componente_invalidos(cliente, payload):
    cliente.post("/objetos", json={"nombre": "equipo", "lugar": "estudio", "ranuras": ["pci-1"]})
    assert cliente.post("/objetos", json=payload).status_code == 422


def test_rechaza_ciclo_y_archivar_padre_con_hijo_activo(cliente):
    a = cliente.post("/objetos", json={"nombre": "A", "lugar": None, "ranuras": ["b"]}).json()
    b = cliente.post(
        "/objetos", json={"nombre": "B", "lugar": None, "padre_id": a["id"], "ranura": "b", "ranuras": ["a"]}
    ).json()
    assert cliente.patch("/objetos/obj-1", json={"padre_id": b["id"], "ranura": "a"}, headers=ADMIN).status_code == 422
    assert cliente.patch("/objetos/obj-1", json={"archivado": True}, headers=ADMIN).status_code == 422


def test_mover_hijo_a_otro_padre(cliente):
    a = cliente.post("/objetos", json={"nombre": "A", "lugar": None, "ranuras": ["uno"]}).json()
    b = cliente.post("/objetos", json={"nombre": "B", "lugar": None, "ranuras": ["dos"]}).json()
    hijo = cliente.post(
        "/objetos", json={"nombre": "C", "lugar": None, "padre_id": a["id"], "ranura": "uno"}
    ).json()
    movido = cliente.patch(
        f"/objetos/{hijo['id']}", json={"padre_id": b["id"], "ranura": "dos"}, headers=ADMIN
    )
    assert movido.status_code == 200
    assert (movido.json()["padre_id"], movido.json()["ranura"]) == (b["id"], "dos")


def test_no_se_puede_quitar_una_ranura_en_uso(cliente):
    raiz = cliente.post("/objetos", json={"nombre": "A", "lugar": None, "ranuras": ["uno"]}).json()
    cliente.post("/objetos", json={"nombre": "B", "lugar": None, "padre_id": raiz["id"], "ranura": "uno"})
    assert cliente.patch("/objetos/obj-1", json={"ranuras": []}, headers=ADMIN).status_code == 422


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


def test_migracion_de_la_version_13_conserva_objetos_y_agrega_campos_opcionales(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    viejo = inventario.crear(con, inventario.ObjetoNuevo(nombre="objeto antiguo", lugar="caja"))
    quitar_desde(con, 14)
    con.execute("PRAGMA user_version = 13")
    con.close()
    con = memoria.abrir(ruta)
    recuperado = inventario.obtener(con, viejo.id)
    assert memoria.VERSION_ESQUEMA == 14
    assert (recuperado.nombre, recuperado.lugar, recuperado.padre_id, recuperado.ranuras) == (
        "objeto antiguo", "caja", None, []
    )
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
