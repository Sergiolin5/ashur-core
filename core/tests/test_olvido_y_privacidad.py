"""Decisiones de Sergio del 2026-11-22: lo que se olvida se olvida en el chat, WAL, la espera sin detalles para otras
personas, las fechas en su zona y el aviso que solo nombra lo que se ofrece."""

import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest
from fastapi.testclient import TestClient

from ashur_core import chat, herramientas
from ashur_core.app import app

ADMIN = {"X-Ashur-Clave-Admin": "a"}
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": 4_700_000_000, "capacidades": ["completion", "tools"]}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    carpeta = tmp_path / "modules"
    carpeta.mkdir()
    monkeypatch.setenv("ASHUR_MODULOS", str(carpeta))
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    monkeypatch.delenv("ASHUR_ZONA", raising=False)
    from ashur_core.app import _registro

    _registro.cache_clear()
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def nuevo_nodo(cliente):
    creado = cliente.post("/nodos", json={"nombre": "windows"}, headers=ADMIN).json()
    nodo = {"X-Ashur-Clave-Nodo": creado["clave"]}
    cliente.post("/nodo/latido", json={"modo": "full", "modelos": [QWEN7]}, headers=nodo)
    return nodo


def tomar(cliente, nodo):
    r = cliente.post("/nodo/trabajos/tomar", headers=nodo)
    return r.json() if r.status_code == 200 else None


def responder(cliente, nodo, trabajo, texto):
    mensaje = {"role": "assistant", "content": texto}
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"salida": {"mensaje": mensaje}}, headers=nodo).status_code == 204


def persona(cliente, nombre="Christian"):
    id_ = cliente.post("/identidades", json={"nombre": nombre, "clase": "persona"}).json()["id"]
    clave = cliente.post(f"/identidades/{id_}/clave", headers=ADMIN).json()["clave"]
    return id_, TestClient(app, headers={"X-Ashur-Clave": clave})


# ── El mensaje sigue a su recuerdo ──


def test_borrar_el_recuerdo_de_un_mensaje_lo_borra_del_chat_y_del_titulo(cliente):
    nodo = nuevo_nodo(cliente)
    conv = cliente.post("/conversaciones").json()["id"]
    cliente.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Mi clave del banco es 1234"})
    responder(cliente, nodo, tomar(cliente, nodo), "Anotado.")
    recuerdo = cliente.get(f"/conversaciones/{conv}").json()["mensajes"][0]["recuerdo_id"]

    assert cliente.delete(f"/recuerdos/{recuerdo}", headers=ADMIN).status_code == 204

    completa = cliente.get(f"/conversaciones/{conv}").json()
    assert [m["texto"] for m in completa["mensajes"]] == [chat.BORRADO, "Anotado."]
    assert completa["conversacion"]["titulo"] == chat.BORRADO
    assert "1234" not in str(cliente.get("/conversaciones").json())
    cliente.post(f"/conversaciones/{conv}/mensajes", json={"texto": "¿Qué te dije?"})
    pedido = tomar(cliente, nodo)["entrada"]["messages"]
    assert "1234" not in str(pedido)


def test_editar_el_recuerdo_de_un_mensaje_cambia_el_mensaje_y_el_titulo(cliente):
    conv = cliente.post("/conversaciones").json()["id"]
    cliente.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Las llaves están en la mesa"})
    recuerdo = cliente.get(f"/conversaciones/{conv}").json()["mensajes"][0]["recuerdo_id"]

    cliente.patch(f"/recuerdos/{recuerdo}", json={"texto": "Las llaves están en el cajón"}, headers=ADMIN)

    completa = cliente.get(f"/conversaciones/{conv}").json()
    assert completa["mensajes"][0]["texto"] == "Las llaves están en el cajón"
    assert completa["conversacion"]["titulo"] == "Las llaves están en el cajón"


def test_editar_otro_campo_no_toca_el_mensaje(cliente):
    conv = cliente.post("/conversaciones").json()["id"]
    cliente.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Hola"})
    recuerdo = cliente.get(f"/conversaciones/{conv}").json()["mensajes"][0]["recuerdo_id"]
    cliente.patch(f"/recuerdos/{recuerdo}", json={"opinion": "saludo"}, headers=ADMIN)
    assert cliente.get(f"/conversaciones/{conv}").json()["mensajes"][0]["texto"] == "Hola"


# ── WAL ──


def test_la_base_queda_en_modo_wal(cliente, tmp_path):
    cliente.get("/recuerdos")
    con = sqlite3.connect(tmp_path / "ashur.db")
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        con.close()


# ── La espera ──


def test_otra_persona_no_ve_el_nodo_ni_el_modelo_y_sergio_si(cliente):
    _, christian = persona(cliente)
    nodo = nuevo_nodo(cliente)
    suya = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{suya}/mensajes", json={"texto": "Hola"})
    tomar(cliente, nodo)
    espera = christian.get(f"/conversaciones/{suya}").json()["espera"]
    assert espera["estado"] == "tomado"
    assert (espera["nodo"], espera["modelo"], espera["error"]) == (None, None, None)

    mia = cliente.post("/conversaciones").json()["id"]
    cliente.post(f"/conversaciones/{mia}/mensajes", json={"texto": "Hola"})
    tomar(cliente, nodo)
    assert cliente.get(f"/conversaciones/{mia}").json()["espera"]["nodo"] is not None


# ── El aviso de herramientas ──


def test_el_aviso_solo_nombra_lo_que_se_ofrece():
    solo_objetos = [h for h in herramientas.DEL_CORE if h.nombre == "buscar_objetos"]
    assert herramientas.aviso(solo_objetos).startswith("Tienes herramientas para consultar el inventario de objetos.")
    modulo = herramientas.Herramienta("modulo-luces-estado", "", {}, modulo="luces", accion="estado")
    texto = herramientas.aviso(list(herramientas.DEL_CORE) + [modulo])
    assert "el inventario de objetos, las personas y mascotas que conoces, tu memoria y los módulos." in texto


def test_con_un_rol_limitado_el_aviso_no_promete_la_memoria(cliente):
    id_, christian = persona(cliente)
    cliente.post("/roles", json={"nombre": "Familia", "herramientas": ["buscar_objetos"]}, headers=ADMIN)
    cliente.patch(f"/identidades/{id_}", json={"rol": "rol-1"}, headers=ADMIN)
    nodo = nuevo_nodo(cliente)
    conv = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{conv}/mensajes", json={"texto": "¿Dónde está la bici?"})
    sistema = tomar(cliente, nodo)["entrada"]["messages"][0]["content"]
    assert "consultar el inventario de objetos." in sistema
    assert "tu memoria" not in sistema


# ── Fechas en la zona de Sergio ──


def test_sin_zona_o_con_una_desconocida_las_fechas_van_en_utc(monkeypatch):
    noche = datetime(2026, 11, 22, 3, 0, tzinfo=timezone.utc)
    monkeypatch.delenv("ASHUR_ZONA", raising=False)
    assert chat.dia(noche) == "2026-11-22"
    monkeypatch.setenv("ASHUR_ZONA", "Zona/Inventada")
    assert chat.dia(noche) == "2026-11-22"


def test_con_zona_un_mensaje_de_la_noche_queda_en_su_dia(monkeypatch):
    monkeypatch.setattr(chat, "zona", lambda: timezone(timedelta(hours=-6)))
    assert chat.dia(datetime(2026, 11, 22, 3, 0, tzinfo=timezone.utc)) == "2026-11-21"
    assert chat.dia(datetime(2026, 11, 22, 7, 0, tzinfo=timezone.utc)) == "2026-11-22"


def test_ashur_zona_lee_un_nombre_iana(monkeypatch):
    try:
        ZoneInfo("Etc/GMT+6")
    except ZoneInfoNotFoundError:
        pytest.skip("Este equipo no tiene la base de zonas horarias.")
    monkeypatch.setenv("ASHUR_ZONA", "Etc/GMT+6")  # en IANA, GMT+6 es seis horas detrás de UTC
    assert chat.dia(datetime(2026, 11, 22, 3, 0, tzinfo=timezone.utc)) == "2026-11-21"
