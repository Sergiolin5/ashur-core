"""La cola de trabajos ante nodos que se caen, salidas inválidas, entregas tardías y fallas a medias (revisión del
core, 2026-11-22). Datos inventados."""

import sqlite3
from array import array

import pytest
from fastapi.testclient import TestClient

from ashur_core import app as app_mod, chat, memoria, nodos, significado
from ashur_core.app import app

ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
BGE = {"nombre": "bge-m3", "tamano": int(1.2 * GB), "capacidades": ["embedding"]}
VIEJO = "2000-01-01T00:00:00+00:00"


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "modules").mkdir()
    monkeypatch.setenv("ASHUR_MODULOS", str(tmp_path / "modules"))
    db = str(tmp_path / "ashur.db")
    monkeypatch.setenv("ASHUR_DB", db)
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": "c"}, raise_server_exceptions=False), db


def sql(db, q, p=()):
    con = sqlite3.connect(db)
    filas = con.execute(q, p).fetchall()
    con.commit()
    con.close()
    return filas


def nuevo_nodo(c, nombre, modelos):
    creado = c.post("/nodos", json={"nombre": nombre}, headers=ADMIN).json()
    h = {"X-Ashur-Clave-Nodo": creado["clave"]}
    assert c.post("/nodo/latido", json={"modo": "full", "modelos": list(modelos)}, headers=h).status_code == 200
    return creado["nodo"]["id"], h


def texto(t):
    return {"salida": {"mensaje": {"role": "assistant", "content": t}}}


def test_un_trabajo_vencido_cuenta_como_intento(entorno):
    c, db = entorno
    _, h = nuevo_nodo(c, "a", [QWEN7])
    c.post("/conversaciones")
    c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    for intento in range(nodos.INTENTOS):
        j = c.post("/nodo/trabajos/tomar", headers=h).json()["id"]
        sql(db, "UPDATE trabajos SET vence = ? WHERE id = ?", (VIEJO, j))  # el nodo se cayó con el trabajo
    assert c.post("/nodo/trabajos/tomar", headers=h).status_code == 204
    assert sql(db, "SELECT estado, intentos FROM trabajos WHERE id = ?", (j,)) == [("fallido", nodos.INTENTOS)]
    espera = c.get("/conversaciones/con-1").json()["espera"]
    assert espera["estado"] == "fallido" and espera["error"] == "El nodo no respondió a tiempo."
    assert c.post("/conversaciones/con-1/mensajes", json={"texto": "¿Hola?"}).status_code == 202


def test_una_salida_mal_formada_agota_los_intentos(entorno):
    c, db = entorno
    _, h = nuevo_nodo(c, "a", [QWEN7])
    c.post("/conversaciones")
    c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    mala = {"salida": {"mensaje": {"role": "assistant", "tool_calls": [{"function": "x"}]}}}
    for _ in range(nodos.INTENTOS):
        j = c.post("/nodo/trabajos/tomar", headers=h).json()["id"]
        assert c.post(f"/nodo/trabajos/{j}", json=mala, headers=h).status_code == 422
    assert sql(db, "SELECT estado FROM trabajos WHERE id = ?", (j,)) == [("fallido",)]
    assert c.post("/conversaciones/con-1/mensajes", json={"texto": "¿Hola?"}).status_code == 202


def test_una_entrega_tardia_no_duplica_la_respuesta(entorno, monkeypatch):
    c, db = entorno
    _, ha = nuevo_nodo(c, "a", [QWEN7])
    b, hb = nuevo_nodo(c, "b", [QWEN7])
    c.post("/conversaciones")
    c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    j = c.post("/nodo/trabajos/tomar", headers=ha).json()["id"]
    sql(db, "UPDATE trabajos SET vence = ? WHERE id = ?", (VIEJO, j))  # A tardó más que el plazo
    original, intentos_de_b = chat.agregar, []

    def agregar(con, *args):
        mensaje = original(con, *args)
        if args[1] == "assistant" and not intentos_de_b:  # mientras A entrega, B quiere retomar el trabajo vencido
            intentos_de_b.append(nodos.tomar(con, b))
        return mensaje

    monkeypatch.setattr(chat, "agregar", agregar)
    assert c.post(f"/nodo/trabajos/{j}", json=texto("respuesta de A"), headers=ha).status_code == 204
    monkeypatch.setattr(chat, "agregar", original)
    assert intentos_de_b == [None]
    assert c.post(f"/nodo/trabajos/{j}", json=texto("respuesta de B"), headers=hb).status_code == 409
    assert sql(db, "SELECT COUNT(*) FROM recuerdos WHERE origen = 'chat-ashur'")[0][0] == 1


def test_una_busqueda_de_un_nodo_caido_no_frena_la_respuesta(entorno):
    c, db = entorno
    e, he = nuevo_nodo(c, "mac-bge", [BGE])
    _, hq = nuevo_nodo(c, "win-qwen", [QWEN7])
    c.post("/conversaciones")
    c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    assert c.post("/nodo/trabajos/tomar", headers=he).json()["necesidad"] == "embedding"
    sql(db, "UPDATE nodos SET ultimo_latido = ? WHERE id = ?", (VIEJO, e))  # el nodo con bge se apagó
    trabajo = c.post("/nodo/trabajos/tomar", headers=hq).json()
    assert trabajo["necesidad"] == "conversar"  # responde solo con la búsqueda por palabras


def test_un_lote_viejo_no_pisa_el_vector_nuevo(entorno):
    c, db = entorno
    c.post("/recuerdos", json={"texto": "llaves en la mesa", "origen": "manual", "fecha": "2026-11-01T10:00:00+00:00",
                               "sensibilidad": "normal", "identidades": [], "objetos": [], "opinion": None})
    _, h = nuevo_nodo(c, "a", [BGE])  # el latido reparte el lote 1
    l1 = c.post("/nodo/trabajos/tomar", headers=h).json()
    assert c.patch("/recuerdos/1", json={"texto": "llaves en el cajón"}, headers=ADMIN).status_code == 200
    c.post("/nodo/latido", json={"modo": "full", "modelos": [BGE]}, headers=h)  # reparte el lote 2
    l2 = c.post("/nodo/trabajos/tomar", headers=h).json()
    assert c.post(f"/nodo/trabajos/{l2['id']}", json={"salida": {"vectores": [[0.0, 1.0]]}}, headers=h).status_code == 204
    assert c.post(f"/nodo/trabajos/{l1['id']}", json={"salida": {"vectores": [[1.0, 0.0]]}}, headers=h).status_code == 204
    vector = array("f")
    vector.frombytes(sql(db, "SELECT vector FROM embeddings WHERE recuerdo_id = 1")[0][0])
    assert list(vector) == [0.0, 1.0]  # el del texto nuevo


def test_apartar_ignora_un_recuerdo_borrado(tmp_path):
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    significado.apartar(con, [99], 1)
    assert con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
    con.close()


def test_una_falla_al_guardar_el_mensaje_no_traba_la_conversacion(entorno, monkeypatch):
    c, _ = entorno
    nuevo_nodo(c, "a", [QWEN7])
    c.post("/conversaciones")

    def roto(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    original = app_mod._decir
    monkeypatch.setattr(app_mod, "_decir", roto)
    assert c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"}).status_code == 500
    monkeypatch.setattr(app_mod, "_decir", original)
    assert c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"}).status_code == 202


def test_una_falla_al_rescatar_la_busqueda_no_traba_la_conversacion(entorno, monkeypatch):
    c, db = entorno
    nuevo_nodo(c, "mac-bge", [BGE])
    _, hq = nuevo_nodo(c, "win-qwen", [QWEN7])
    c.post("/conversaciones")
    c.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    sql(db, "UPDATE trabajos SET creado = ? WHERE necesidad = 'embedding'", (VIEJO,))  # nadie la tomó a tiempo

    def roto(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    original = app_mod._responder
    monkeypatch.setattr(app_mod, "_responder", roto)
    assert c.post("/nodo/trabajos/tomar", headers=hq).status_code == 500  # la búsqueda quedó descartada
    monkeypatch.setattr(app_mod, "_responder", original)
    assert c.get("/conversaciones/con-1").json()["espera"]["estado"] == "fallido"  # dentro del contrato
    assert c.post("/conversaciones/con-1/mensajes", json={"texto": "¿Hola?"}).status_code == 202
