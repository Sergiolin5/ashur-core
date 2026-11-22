import json
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from ashur_core import memoria, personas
from ashur_core.app import RUTAS_DE_PERSONAS, app
from bases import quitar_desde

ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
EJEMPLO = Path(__file__).resolve().parents[2] / "contracts" / "recuerdo.ejemplo.json"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    carpeta = tmp_path / "modules"
    (carpeta / "luces").mkdir(parents=True)
    (carpeta / "luces" / "modulo.json").write_text(json.dumps({
        "id": "luces", "nombre": "Luces", "version": "0.1.0", "descripcion": "Las luces.",
        "acciones": [{"id": "apagar", "descripcion": "Apaga.", "escribe": True}]}), encoding="utf-8")
    (carpeta / "luces" / "modulo.py").write_text("def apagar(contexto, sala=''):\n    return {}\n", encoding="utf-8")
    monkeypatch.setenv("ASHUR_MODULOS", str(carpeta))
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    from ashur_core.app import _registro

    _registro.cache_clear()
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def persona(cliente, nombre="Christian"):
    """Crea la identidad y su clave; devuelve (id, cliente con su clave)."""
    id_ = cliente.post("/identidades", json={"nombre": nombre, "clase": "persona"}).json()["id"]
    creada = cliente.post(f"/identidades/{id_}/clave", headers=ADMIN)
    assert creada.status_code == 201 and creada.json()["identidad"]["con_clave"]
    return id_, TestClient(app, headers={"X-Ashur-Clave": creada.json()["clave"]})


def nuevo_nodo(cliente):
    creado = cliente.post("/nodos", json={"nombre": "windows"}, headers=ADMIN).json()
    nodo = {"X-Ashur-Clave-Nodo": creado["clave"]}
    cliente.post("/nodo/latido", json={"modo": "full", "modelos": [QWEN7]}, headers=nodo)
    return nodo


def tomar(cliente, nodo):
    r = cliente.post("/nodo/trabajos/tomar", headers=nodo)
    return r.json() if r.status_code == 200 else None


def responder(cliente, nodo, trabajo, texto="", llamadas=None):
    mensaje = {"role": "assistant", "content": texto}
    if llamadas:
        mensaje["tool_calls"] = [{"function": {"name": n, "arguments": a}} for n, a in llamadas]
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"salida": {"mensaje": mensaje}}, headers=nodo).status_code == 204


def herramientas_de(trabajo):
    return [t["function"]["name"] for t in trabajo["entrada"].get("tools", [])]


# ── Cerrado por defecto ──


def test_la_clave_de_una_persona_solo_abre_el_chat(cliente):
    _, christian = persona(cliente)
    revisadas = 0
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute) or ruta.path in RUTAS_DE_PERSONAS or ruta.path == "/vivo":
            continue
        if ruta.path.startswith("/nodo/"):
            continue  # piden la clave de nodo, en otro encabezado
        camino = re.sub(r"\{[^}]+\}", "1", ruta.path)
        for metodo in ruta.methods:
            respuesta = christian.request(metodo, camino, json={})
            assert respuesta.status_code == 401, (metodo, ruta.path, respuesta.status_code)
            revisadas += 1
    assert revisadas > 20  # el recorrido de verdad pasó por las rutas
    # Y las del chat sí le abren.
    assert christian.post("/conversaciones").status_code == 201


def test_sin_ashur_clave_todo_queda_cerrado(cliente, monkeypatch):
    _, christian = persona(cliente)
    monkeypatch.delenv("ASHUR_CLAVE")
    assert christian.get("/conversaciones").status_code == 503


def test_cada_uno_ve_solo_sus_conversaciones_y_las_ajenas_no_existen(cliente):
    _, christian = persona(cliente, "Christian")
    _, erick = persona(cliente, "Erick")
    de_sergio = cliente.post("/conversaciones").json()["id"]
    de_christian = christian.post("/conversaciones").json()["id"]
    assert [c["id"] for c in cliente.get("/conversaciones").json()] == [de_sergio]
    assert [c["id"] for c in christian.get("/conversaciones").json()] == [de_christian]
    assert erick.get("/conversaciones").json() == []
    for ajena in (de_sergio, de_christian):
        assert erick.get(f"/conversaciones/{ajena}").status_code == 404
        assert erick.post(f"/conversaciones/{ajena}/mensajes", json={"texto": "Hola"}).status_code == 404
    assert cliente.get(f"/conversaciones/{de_christian}").status_code == 404  # tampoco Sergio, por esta ruta


def test_archivar_revoca_la_clave_y_regenerarla_reemplaza_la_anterior(cliente):
    id_, christian = persona(cliente)
    nueva = cliente.post(f"/identidades/{id_}/clave", headers=ADMIN).json()["clave"]
    assert christian.get("/conversaciones").status_code == 401  # la vieja ya no abre
    otra = TestClient(app, headers={"X-Ashur-Clave": nueva})
    assert otra.get("/conversaciones").status_code == 200
    cliente.patch(f"/identidades/{id_}", json={"archivada": True}, headers=ADMIN)
    assert otra.get("/conversaciones").status_code == 401
    assert cliente.post(f"/identidades/{id_}/clave", headers=ADMIN).status_code == 409
    assert cliente.post("/identidades/ide-99/clave", headers=ADMIN).status_code == 404
    assert "clave" not in cliente.get("/identidades", params={"archivadas": True}).json()[0]


# ── Privacidad ──


def test_con_otra_persona_ashur_solo_usa_lo_que_salio_de_ella(cliente):
    id_, christian = persona(cliente)
    # Una nota de Sergio sobre Christian: lo menciona, pero no salió de él.
    datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    del datos["id"]
    datos.update(texto="Christian me debe la plata del almuerzo.", identidades=[{"nombre": "Christian", "identidad_id": id_}],
                 objetos=[], opinion=None)
    assert cliente.post("/recuerdos", json=datos).status_code == 201
    nodo = nuevo_nodo(cliente)

    conv = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Mi perro se llama Toby y le gusta el almuerzo."})
    primero = tomar(cliente, nodo)
    assert "plata" not in primero["entrada"]["messages"][0]["content"]
    responder(cliente, nodo, primero, "Qué lindo nombre.")

    otra = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{otra}/mensajes", json={"texto": "¿Qué te conté del almuerzo?"})
    sistema = tomar(cliente, nodo)["entrada"]["messages"][0]["content"]
    assert "Toby" in sistema and "plata" not in sistema  # lo suyo sí, la nota de Sergio no

    # Con Sergio, lo que dijo Christian llega marcado con su nombre.
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-3/mensajes", json={"texto": "¿Cómo se llama el perro de Christian?"})
    sistema_sergio = tomar(cliente, nodo)["entrada"]["messages"][0]["content"]  # el de Christian sigue tomado
    assert "Toby y le gusta el almuerzo. (lo dijo Christian en su chat)" in sistema_sergio

    # Lo que dice Christian también es memoria de Sergio, y lo enlaza.
    textos = {r["texto"]: r for r in cliente.get("/recuerdos").json()}
    assert textos["Mi perro se llama Toby y le gusta el almuerzo."]["identidades"] == [{"nombre": "Christian", "identidad_id": id_}]
    assert cliente.get("/identidades").json()[0]["menciones"] >= 3


# ── Roles ──


def test_los_patrones_de_rol():
    assert personas.permite(["buscar_objetos"], "buscar_objetos")
    assert personas.permite(["modulo-luces-*"], "modulo-luces-apagar")
    assert not personas.permite(["modulo-luces-*"], "modulo-lucesx")  # sin el guion no
    assert not personas.permite(["Buscar_objetos"], "buscar_objetos")  # distingue mayúsculas, también en Windows
    assert not personas.permite([], "buscar_objetos")


def test_crear_y_cambiar_roles(cliente):
    assert cliente.post("/roles", json={"nombre": "x", "herramientas": ["modulo-[a]*"]}, headers=ADMIN).status_code == 422
    assert cliente.post("/roles", json={"nombre": "x", "herramientas": ["a*b"]}, headers=ADMIN).status_code == 422
    assert cliente.post("/roles", json={"nombre": "Familia", "herramientas": []}).status_code == 401
    rol = cliente.post("/roles", json={"nombre": "Familia", "herramientas": ["buscar_objetos"]}, headers=ADMIN).json()
    assert rol == {"id": "rol-1", "nombre": "Familia", "herramientas": ["buscar_objetos"]}
    cambiado = cliente.patch("/roles/rol-1", json={"herramientas": ["buscar_*"]}, headers=ADMIN).json()
    assert cambiado["herramientas"] == ["buscar_*"] and cambiado["nombre"] == "Familia"
    assert cliente.get("/roles").json() == [cambiado]
    assert cliente.patch("/roles/rol-9", json={}, headers=ADMIN).status_code == 404
    id_, _ = persona(cliente)
    assert cliente.patch(f"/identidades/{id_}", json={"rol": "rol-9"}, headers=ADMIN).status_code == 422
    assert cliente.patch(f"/identidades/{id_}", json={"rol": "rol-1"}, headers=ADMIN).json()["rol"] == "rol-1"
    assert cliente.patch(f"/identidades/{id_}", json={"rol": None}, headers=ADMIN).json()["rol"] is None


def test_sin_rol_solo_conversa_y_con_rol_usa_sus_herramientas(cliente):
    id_, christian = persona(cliente)
    nodo = nuevo_nodo(cliente)
    conv = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Hola"})
    sin_rol = tomar(cliente, nodo)
    assert herramientas_de(sin_rol) == []
    responder(cliente, nodo, sin_rol, "Hola.")

    cliente.post("/roles", json={"nombre": "Familia", "herramientas": ["buscar_objetos", "modulo-luces-*"]}, headers=ADMIN)
    cliente.patch(f"/identidades/{id_}", json={"rol": "rol-1"}, headers=ADMIN)
    christian.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Apaga la sala"})
    con_rol = tomar(cliente, nodo)
    assert herramientas_de(con_rol) == ["buscar_objetos", "modulo-luces-apagar"]
    responder(cliente, nodo, con_rol, llamadas=[("modulo-luces-apagar", {"sala": "sala"})])
    pedidos = cliente.get("/pedidos").json()
    assert [(p["accion"], p["pedido_por"]) for p in pedidos] == [("apagar", id_)]  # Sergio sabe quién lo pidió


def test_quitar_el_rol_corta_en_la_ronda_siguiente(cliente):
    id_, christian = persona(cliente)
    cliente.post("/roles", json={"nombre": "Familia", "herramientas": ["buscar_objetos"]}, headers=ADMIN)
    cliente.patch(f"/identidades/{id_}", json={"rol": "rol-1"}, headers=ADMIN)
    nodo = nuevo_nodo(cliente)
    conv = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{conv}/mensajes", json={"texto": "¿Dónde está la bici?"})
    primero = tomar(cliente, nodo)
    assert herramientas_de(primero) == ["buscar_objetos"]
    cliente.patch(f"/identidades/{id_}", json={"rol": None}, headers=ADMIN)  # Sergio se lo quita a mitad de camino
    responder(cliente, nodo, primero, llamadas=[("buscar_objetos", {"texto": "bici"})])
    resultado = [m for m in tomar(cliente, nodo)["entrada"]["messages"] if m["role"] == "tool"][0]
    assert resultado["content"] == "No existe la herramienta buscar_objetos."


def test_buscar_recuerdos_respeta_la_privacidad_aunque_el_rol_la_permita(cliente):
    id_, christian = persona(cliente)
    datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    del datos["id"]
    datos.update(texto="La clave del wifi de Sergio está en la nevera.", identidades=[], objetos=[], opinion=None)
    cliente.post("/recuerdos", json=datos)
    cliente.post("/roles", json={"nombre": "Todo", "herramientas": ["buscar_*"]}, headers=ADMIN)
    cliente.patch(f"/identidades/{id_}", json={"rol": "rol-1"}, headers=ADMIN)
    nodo = nuevo_nodo(cliente)
    conv = christian.post("/conversaciones").json()["id"]
    christian.post(f"/conversaciones/{conv}/mensajes", json={"texto": "Hola"})
    responder(cliente, nodo, tomar(cliente, nodo), llamadas=[("buscar_recuerdos", {"texto": "wifi nevera"})])
    resultado = [m for m in tomar(cliente, nodo)["entrada"]["messages"] if m["role"] == "tool"][0]
    assert resultado["content"] == "No hay recuerdos con eso."


def test_una_base_de_la_version_11_recibe_personas_y_roles(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    quitar_desde(con, 12)
    con.execute("PRAGMA user_version = 11")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert personas.listar_roles(con) == []
    con.close()
