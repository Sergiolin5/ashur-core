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
CLAVE_ADMIN = "clave-admin-de-prueba"
ADMIN = {"X-Ashur-Clave-Admin": CLAVE_ADMIN}


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
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", CLAVE_ADMIN)
    c = TestClient(app, headers={"X-Ashur-Clave": CLAVE})
    # El recuerdo de ejemplo enlaza a ide-1, así que esa identidad tiene que existir.
    assert c.post("/identidades", json={"nombre": "Ana", "clase": "persona"}).json()["id"] == "ide-1"
    return c


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
        lambda d: d["identidades"][1].pop("identidad_id"),
    ],
    ids=["sensibilidad-desconocida", "campo-extra", "falta-inventario-id", "falta-opinion", "fecha-sin-zona", "falta-identidad-id"],
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

    assert cliente.delete("/recuerdos/1", headers=ADMIN).status_code == 204
    assert cliente.get("/recuerdos").json() == []
    assert cliente.delete("/recuerdos/1", headers=ADMIN).status_code == 404


def test_editar_solo_cambia_lo_enviado(cliente):
    cliente.post("/recuerdos", json=nuevo_ejemplo())
    editado = cliente.patch("/recuerdos/1", json={"opinion": None, "sensibilidad": "privado"}, headers=ADMIN)
    assert editado.status_code == 200
    assert editado.json()["opinion"] is None
    assert editado.json()["sensibilidad"] == "privado"
    assert editado.json()["texto"] == leer_ejemplo()["texto"]
    assert cliente.get("/recuerdos").json() == [editado.json()]
    assert cliente.patch("/recuerdos/9", json={"texto": "x"}, headers=ADMIN).status_code == 404
    assert cliente.patch("/recuerdos/1", json={"extra": 1}, headers=ADMIN).status_code == 422
    assert cliente.patch("/recuerdos/1", json={"texto": None}, headers=ADMIN).status_code == 422


def test_editar_y_borrar_piden_la_clave_de_administrador(cliente, monkeypatch):
    cliente.post("/recuerdos", json=nuevo_ejemplo())
    assert cliente.patch("/recuerdos/1", json={"texto": "x"}).status_code == 401
    assert cliente.delete("/recuerdos/1").status_code == 401
    assert cliente.delete("/recuerdos/1", headers={"X-Ashur-Clave-Admin": CLAVE}).status_code == 401
    monkeypatch.delenv("ASHUR_CLAVE_ADMIN")
    assert cliente.delete("/recuerdos/1", headers=ADMIN).status_code == 503


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


def test_migra_una_base_de_la_version_1(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = sqlite3.connect(ruta)
    con.execute(
        "CREATE TABLE recuerdos (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL, origen TEXT NOT NULL,"
        " fecha TEXT NOT NULL, sensibilidad TEXT NOT NULL, personas TEXT NOT NULL, objetos TEXT NOT NULL,"
        " opinion TEXT)"
    )
    con.execute(
        "INSERT INTO recuerdos (texto, origen, fecha, sensibilidad, personas, objetos, opinion)"
        " VALUES ('Un paseo.', 'diario', '2026-11-20T18:30:00-05:00', 'normal', ?, '[]', NULL)",
        (json.dumps([{"nombre": "Ana", "contacto_id": "per-1"}, {"nombre": "Bruno", "contacto_id": None}]),),
    )
    con.execute("PRAGMA user_version = 1")
    con.commit()
    con.close()

    for _ in range(2):  # la segunda vez no debe cambiar nada
        con = memoria.abrir(ruta)
        assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
        [recuerdo] = memoria.listar(con)
        assert [i.model_dump() for i in recuerdo.identidades] == [
            {"nombre": "Ana", "identidad_id": "per-1"},
            {"nombre": "Bruno", "identidad_id": None},
        ]
        con.close()


def test_aprendizaje_empieza_al_crear_la_base_y_cuenta_recuerdos(cliente):
    antes = cliente.get("/aprendizaje")
    assert antes.status_code == 200
    assert antes.json()["recuerdos"] == 0
    inicio = antes.json()["inicio"]
    cliente.post("/recuerdos", json=nuevo_ejemplo())
    despues = cliente.get("/aprendizaje").json()
    assert despues == {"inicio": inicio, "recuerdos": 1}


def test_solo_un_administrador_cambia_el_inicio(cliente):
    nuevo = {"inicio": "2026-01-01T00:00:00-05:00"}
    assert cliente.patch("/aprendizaje", json=nuevo).status_code == 401
    cambiado = cliente.patch("/aprendizaje", json=nuevo, headers=ADMIN)
    assert cambiado.status_code == 200
    assert cambiado.json()["inicio"] == "2026-01-01T00:00:00-05:00"
    assert cliente.patch("/aprendizaje", json={"inicio": "2026-01-01T00:00:00"}, headers=ADMIN).status_code == 422
    assert TestClient(app).get("/aprendizaje").status_code == 401


def test_una_base_de_la_version_2_recibe_su_inicio(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    con.execute("DROP TABLE meta")
    for objeto in (
        "TRIGGER recuerdos_ai", "TRIGGER recuerdos_ad", "TRIGGER recuerdos_au", "TABLE recuerdos_busqueda",
        "TABLE identidades", "TABLE pedidos", "TABLE mensajes",
    ):
        con.execute(f"DROP {objeto}")
    con.execute("PRAGMA user_version = 2")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert memoria.aprendizaje(con).recuerdos == 0
    con.close()


def test_buscar_por_palabras_sin_tildes_y_por_prefijo(cliente):
    cliente.post("/recuerdos", json=nuevo_ejemplo())
    otro = nuevo_ejemplo() | {"texto": "Fuimos al médico por la mañana.", "opinion": None}
    cliente.post("/recuerdos", json=otro)

    def textos(consulta):
        return [r["texto"] for r in cliente.get("/recuerdos", params={"buscar": consulta}).json()]

    assert textos("medico") == ["Fuimos al médico por la mañana."]
    assert textos("bici") == [leer_ejemplo()["texto"]]
    assert textos("confianza") == [leer_ejemplo()["texto"]]  # también busca en la opinión
    assert textos("bici médico") == []
    assert textos("¿?") == []

    cliente.patch("/recuerdos/2", json={"texto": "Fuimos al dentista."}, headers=ADMIN)
    assert textos("medico") == []
    assert textos("dentista") == ["Fuimos al dentista."]
    cliente.delete("/recuerdos/2", headers=ADMIN)
    assert textos("dentista") == []


def test_una_base_de_la_version_3_indexa_sus_recuerdos(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    memoria.crear(con, memoria.RecuerdoNuevo.model_validate(nuevo_ejemplo()))
    for objeto in (
        "TRIGGER recuerdos_ai", "TRIGGER recuerdos_ad", "TRIGGER recuerdos_au", "TABLE recuerdos_busqueda",
        "TABLE identidades", "TABLE pedidos", "TABLE mensajes",
    ):
        con.execute(f"DROP {objeto}")
    con.execute("PRAGMA user_version = 3")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert [r.id for r in memoria.buscar(con, "bicicleta")] == [1]
    con.close()


def test_la_galaxia_real_trae_el_aprendizaje_de_la_base(cliente):
    cliente.post("/recuerdos", json=nuevo_ejemplo())
    respuesta = cliente.get("/galaxia")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["aprendizaje"] == cliente.get("/aprendizaje").json()
    # La identidad del recuerdo de ejemplo ya tiene una mención: aparece como personaje.
    assert {c["id"] for c in datos["cuerpos"]} == {"ashur", "identidades", "objetos", "identidad-ide-1"}
    assert datos["eventos"] == []
    from ashur_core.galaxia import EstadoGalaxia

    EstadoGalaxia.model_validate(datos)  # cumple el contrato
    assert TestClient(app).get("/galaxia").status_code == 401
