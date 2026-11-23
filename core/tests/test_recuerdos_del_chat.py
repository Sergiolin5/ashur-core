"""Los mensajes son historial y un nodo decide qué recordar tras cada respuesta (docs/adr/0028-recuerdos-del-chat.md).
Datos inventados."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ashur_core import chat, memoria, nodos, personas
from ashur_core.app import app
from bases import quitar_desde, recordar_del_chat

ADMIN = {"X-Ashur-Clave-Admin": "a"}
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": 4_700_000_000, "capacidades": ["completion", "tools"]}
CONTRATO = Path(__file__).resolve().parents[2] / "contracts" / "conversacion.schema.json"


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


def entregar(cliente, nodo, trabajo, texto=None, error=None):
    cuerpo = {"error": error} if error else {"salida": {"mensaje": {"role": "assistant", "content": texto}}}
    return cliente.post(f"/nodo/trabajos/{trabajo['id']}", json=cuerpo, headers=nodo)


def decir(cliente, nodo, texto, respuesta="Listo.", conv="con-1", quien=None):
    """Un mensaje y su respuesta. Devuelve el pedido que recibió el nodo; el trabajo de los recuerdos queda en la cola."""
    assert (quien or cliente).post(f"/conversaciones/{conv}/mensajes", json={"texto": texto}).status_code == 202
    trabajo = tomar(cliente, nodo)
    assert entregar(cliente, nodo, trabajo, respuesta).status_code == 204
    return trabajo


def sistema_de(trabajo):
    return trabajo["entrada"]["messages"][0]["content"]


def persona(cliente, nombre="Christian"):
    id_ = cliente.post("/identidades", json={"nombre": nombre, "clase": "persona"}).json()["id"]
    clave = cliente.post(f"/identidades/{id_}/clave", headers=ADMIN).json()["clave"]
    return id_, TestClient(app, headers={"X-Ashur-Clave": clave})


# ── El nodo decide qué recordar ──


def test_tras_cada_respuesta_un_nodo_decide_que_recordar(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "Hola, el martes tengo dentista a las 4.", "Anotado. ¿Te lo recuerdo?")
    assert cliente.get("/recuerdos").json() == []  # los mensajes solos no son memoria

    trabajo = recordar_del_chat(
        cliente, nodo, "Esto es lo que guardo:\n- Sergio tiene dentista el martes a las 4.\n- " + "a" * 400 + "\n- Tres.\n- Cuatro."
    )
    entrada = trabajo["entrada"]
    assert trabajo["necesidad"] == "conversar" and "tools" not in entrada
    assert "con Sergio" in entrada["messages"][0]["content"]
    assert entrada["messages"][1]["content"] == (
        "Último intercambio:\nSergio: Hola, el martes tengo dentista a las 4.\nAshur: Anotado. ¿Te lo recuerdo?"
    )

    # Como máximo tres, cortos, con origen «chat» y la fecha del mensaje del que salieron.
    recuerdos = cliente.get("/recuerdos").json()
    assert [r["texto"] for r in recuerdos] == ["Sergio tiene dentista el martes a las 4.", "a" * 300, "Tres."]
    mensaje = cliente.get("/conversaciones/con-1").json()["mensajes"][0]
    assert {(r["origen"], r["sensibilidad"]) for r in recuerdos} == {("chat", "normal")}
    assert {datetime.fromisoformat(r["fecha"]) for r in recuerdos} == {datetime.fromisoformat(mensaje["fecha"])}
    assert tomar(cliente, nodo) is None


def test_nada_o_un_texto_sin_lineas_no_deja_recuerdos(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    for respuesta in ("NADA", "- Nada que guardar.", "No encuentro nada importante."):
        decir(cliente, nodo, "Hola")
        recordar_del_chat(cliente, nodo, respuesta)
    assert cliente.get("/recuerdos").json() == []


def test_el_nodo_ve_los_mensajes_anteriores_solo_para_entender(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    for i in range(3):
        decir(cliente, nodo, f"Mensaje {i}", f"Respuesta {i}")
        trabajo = recordar_del_chat(cliente, nodo)
    transcripcion = trabajo["entrada"]["messages"][1]["content"]
    assert transcripcion == (
        "Antes, solo para entender:\nSergio: Mensaje 0\nAshur: Respuesta 0\nSergio: Mensaje 1\nAshur: Respuesta 1\n\n"
        "Último intercambio:\nSergio: Mensaje 2\nAshur: Respuesta 2"
    )


def test_el_chat_va_antes_que_decidir_que_recordar(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "Uno")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Dos"})  # no espera al trabajo de fondo
    assert "proposito" not in tomar(cliente, nodo)["entrada"]
    assert tomar(cliente, nodo)["entrada"]["proposito"] == "recuerdos"


def test_si_decidir_que_recordar_falla_tres_veces_no_queda_nada_y_el_chat_sigue(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "Vivo en Medellín.")
    for _ in range(nodos.INTENTOS):
        assert entregar(cliente, nodo, tomar(cliente, nodo), error="sin memoria").status_code == 204
    assert tomar(cliente, nodo) is None
    assert cliente.get("/recuerdos").json() == []
    decir(cliente, nodo, "¿Sigues ahí?")


def test_un_intercambio_borrado_mientras_el_nodo_pensaba_no_deja_recuerdos(cliente, tmp_path):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "Mi clave es 1234.")
    con = sqlite3.connect(tmp_path / "ashur.db")
    con.execute("UPDATE mensajes SET texto = ?", (chat.BORRADO,))
    con.commit()
    con.close()
    recordar_del_chat(cliente, nodo, "- La clave de Sergio es 1234.")
    assert cliente.get("/recuerdos").json() == []


def test_borrar_algo_que_el_nodo_leyo_como_contexto_tampoco_deja_recuerdos(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "Mi clave del wifi es pulpo77.")
    recordar_del_chat(cliente, nodo, "- La clave del wifi de Sergio es pulpo77.")
    decir(cliente, nodo, "Gracias.")  # su trabajo lleva el intercambio anterior como contexto
    cliente.delete("/recuerdos/1", headers=ADMIN)
    trabajo = recordar_del_chat(cliente, nodo, "- La clave del wifi de Sergio es pulpo77.")
    assert "pulpo77" in trabajo["entrada"]["messages"][1]["content"]
    assert cliente.get("/recuerdos").json() == []


def test_la_persona_sube_de_nivel_con_los_recuerdos_de_su_chat(cliente):
    id_, christian = persona(cliente)
    nodo = nuevo_nodo(cliente)
    christian.post("/conversaciones")
    decir(cliente, nodo, "Tengo un perro.", quien=christian)
    recordar_del_chat(cliente, nodo, "- Christian tiene un perro.")
    identidad = cliente.get("/identidades").json()[0]
    assert (identidad["id"], identidad["menciones"], identidad["nivel"]) == (id_, 1, 1)


def test_una_respuesta_que_llega_tras_actualizar_el_core_no_deja_recuerdos_y_se_olvida_con_su_mensaje(cliente, tmp_path):
    """El mensaje se guardó antes del ADR 0028, cuando era también un recuerdo, y Ashur lo responde después."""
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Mi clave del wifi es pulpo77."})
    datos = {"texto": "Mi clave del wifi es pulpo77.", "origen": "chat", "fecha": "2026-11-01T10:00:00+00:00",
             "sensibilidad": "normal", "identidades": [], "objetos": [], "opinion": None}
    recuerdo = cliente.post("/recuerdos", json=datos).json()["id"]
    con = sqlite3.connect(tmp_path / "ashur.db")
    con.execute("UPDATE mensajes SET recuerdo_id = ?", (recuerdo,))
    con.execute("UPDATE recuerdos SET mensaje_id = 1")
    con.commit()
    con.close()

    entregar(cliente, nodo, tomar(cliente, nodo), "Anotado, pulpo77.")
    assert tomar(cliente, nodo) is None  # el mensaje ya es un recuerdo: no sale el trabajo
    cliente.delete(f"/recuerdos/{recuerdo}", headers=ADMIN)
    assert [m["texto"] for m in cliente.get("/conversaciones/con-1").json()["mensajes"]] == [chat.BORRADO, chat.BORRADO]


def test_buscar_recuerdos_no_devuelve_lo_que_el_modelo_ya_ve(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "El pasaporte está en la caja fuerte.")
    recordar_del_chat(cliente, nodo)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-2/mensajes", json={"texto": "¿Dónde dejé el pasaporte?"})
    llamada = {"function": {"name": "buscar_recuerdos", "arguments": {"texto": "pasaporte"}}}
    salida = {"mensaje": {"role": "assistant", "content": "", "tool_calls": [llamada]}}
    assert cliente.post(f"/nodo/trabajos/{tomar(cliente, nodo)['id']}", json={"salida": salida}, headers=nodo).status_code == 204
    resultado = [m for m in tomar(cliente, nodo)["entrada"]["messages"] if m["role"] == "tool"][0]["content"]
    assert "Sergio: El pasaporte está en la caja fuerte." in resultado
    assert "¿Dónde dejé el pasaporte?" not in resultado


def test_leer_recuerdos():
    assert memoria.leer_recuerdos("- Uno.\n• Dos.\n-\n- Tres.\n- Cuatro.") == ["Uno.", "Dos.", "Tres."]
    assert memoria.leer_recuerdos("nada") == []
    assert memoria.leer_recuerdos("Nada.\n- Uno.") == []
    # Solo la palabra entera es ninguna.
    assert memoria.leer_recuerdos("- Nadar es el deporte de Sergio.\n- Nada más.") == ["Nadar es el deporte de Sergio."]


# ── La búsqueda sigue encontrando el historial ──


def test_lo_que_se_dijo_y_no_quedo_como_recuerdo_se_encuentra_desde_otra_conversacion(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "La bicicleta quedó en el garaje de Laura.", "Entendido, la bicicleta está " + "muy " * 100 + "bien.")
    recordar_del_chat(cliente, nodo)
    # En la misma conversación ya está a la vista: no se repite.
    visto = decir(cliente, nodo, "¿Dónde quedó la bicicleta?", "La bicicleta, en el garaje.")
    assert "De conversaciones anteriores" not in sistema_de(visto)
    recordar_del_chat(cliente, nodo)

    cliente.post("/conversaciones")
    sistema = sistema_de(decir(cliente, nodo, "¿Dónde quedó la bicicleta?", conv="con-2"))
    assert "De conversaciones anteriores; úsalo solo si viene al caso:" in sistema
    fecha = cliente.get("/conversaciones/con-1").json()["mensajes"][0]["fecha"][:10]
    assert f"- {fecha}, Sergio: La bicicleta quedó en el garaje de Laura." in sistema
    assert "Recuerdos que pueden servir" not in sistema
    # Como máximo tres mensajes, y los largos van cortados.
    assert sistema.count(f"- {fecha}, ") == chat.HISTORIAL_EN_EL_PEDIDO
    assert max(len(linea) for linea in sistema.splitlines()) < chat.LARGO_EN_EL_PEDIDO + 40


def test_un_recuerdo_que_salio_de_lo_que_el_modelo_ya_ve_no_se_repite(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "La bicicleta quedó en el garaje.")
    recordar_del_chat(cliente, nodo, "- La bicicleta de Sergio está en el garaje.")
    assert "Recuerdos que pueden servir" not in sistema_de(decir(cliente, nodo, "¿Dónde quedó la bicicleta?"))
    recordar_del_chat(cliente, nodo)
    cliente.post("/conversaciones")
    sistema = sistema_de(decir(cliente, nodo, "¿Dónde quedó la bicicleta?", conv="con-2"))
    assert "La bicicleta de Sergio está en el garaje." in sistema


def test_otra_persona_no_encuentra_el_historial_de_sergio_ni_el_de_otra(cliente):
    _, christian = persona(cliente)
    _, erick = persona(cliente, "Erick")
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "La bicicleta quedó en el garaje.")
    recordar_del_chat(cliente, nodo, "- La bicicleta de Sergio está en el garaje.")
    erick.post("/conversaciones")
    decir(cliente, nodo, "Mi bicicleta es verde.", conv="con-2", quien=erick)
    recordar_del_chat(cliente, nodo, "- La bicicleta de Erick es verde.")

    christian.post("/conversaciones")
    sistema = sistema_de(decir(cliente, nodo, "¿Dónde está la bicicleta?", conv="con-3", quien=christian))
    assert "garaje" not in sistema and "verde" not in sistema
    recordar_del_chat(cliente, nodo)

    # Sergio sí, y lo de Erick llega marcado.
    cliente.post("/conversaciones")
    sistema = sistema_de(decir(cliente, nodo, "¿De qué color es la bicicleta?", conv="con-4"))
    assert "La bicicleta de Erick es verde. (lo dijo Erick en su chat)" in sistema
    assert "Erick: Mi bicicleta es verde. (en el chat de Erick)" in sistema
    assert "Christian: ¿Dónde está la bicicleta? (en el chat de Christian)" in sistema


def test_el_contrato_acepta_mensajes_sin_recuerdo(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    decir(cliente, nodo, "Hola")
    mensajes = cliente.get("/conversaciones/con-1").json()["mensajes"]
    assert [m["recuerdo_id"] for m in mensajes] == [None, None]
    definicion = json.loads(CONTRATO.read_text(encoding="utf-8"))["$defs"]["mensaje"]
    assert set(mensajes[0]) == set(definicion["required"]) == set(definicion["properties"])
    assert definicion["properties"]["recuerdo_id"]["type"] == ["integer", "null"]


# ── Migración ──


def test_una_base_de_la_version_14_conserva_sus_mensajes_y_sabe_de_donde_salio_cada_recuerdo(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    quitar_desde(con, 15)
    # Como era en la versión 14: cada mensaje es un recuerdo, y recuerdo_id es obligatorio.
    con.execute("DROP TABLE mensajes")
    con.execute(
        "CREATE TABLE mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, conversacion_id TEXT NOT NULL, rol TEXT NOT NULL,"
        " texto TEXT NOT NULL, fecha TEXT NOT NULL, recuerdo_id INTEGER NOT NULL)"
    )
    con.execute("INSERT INTO identidades (id, nombre, clase) VALUES ('ide-1', 'Christian', 'persona')")
    fecha = "2026-11-01T10:00:00+00:00"
    con.execute("INSERT INTO conversaciones (id, creada, actualizada, identidad_id) VALUES ('con-1', ?, ?, 'ide-1')", (fecha, fecha))
    for rol, origen, texto in (("user", "chat", "Mi perro se llama Toby."), ("assistant", "chat-ashur", "Qué lindo.")):
        recuerdo = con.execute(
            "INSERT INTO recuerdos (texto, origen, fecha, sensibilidad, identidades, objetos) VALUES (?, ?, ?, 'normal', '[]', '[]')",
            (texto, origen, fecha),
        ).lastrowid
        con.execute(
            "INSERT INTO mensajes (id, conversacion_id, rol, texto, fecha, recuerdo_id) VALUES (?, 'con-1', ?, ?, ?, ?)",
            (recuerdo + 6, rol, texto, fecha, recuerdo),
        )
    con.execute("INSERT INTO recuerdos (texto, origen, fecha, sensibilidad, identidades, objetos) VALUES ('Una nota.', 'manual', ?, 'normal', '[]', '[]')", (fecha,))
    con.execute("PRAGMA user_version = 14")
    con.commit()
    con.close()

    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert [(m.id, m.texto, m.recuerdo_id) for m in chat.mensajes(con, "con-1")] == [
        (7, "Mi perro se llama Toby.", 1), (8, "Qué lindo.", 2)
    ]
    # Los recuerdos de antes no se tocan, y siguen siendo de la conversación de la que salieron.
    assert con.execute("SELECT id, mensaje_id FROM recuerdos ORDER BY id").fetchall() == [(1, 7), (2, 8), (3, None)]
    assert personas.recuerdos_de(con, "ide-1") == {1, 2}
    assert personas.autores(con, [1, 2, 3]) == {1: "Christian", 2: "Christian"}
    # Los mensajes nuevos ya no necesitan recuerdo, siguen la numeración y se encuentran por palabras.
    nuevo = chat.agregar(con, "con-1", "user", "También tengo un gato.")
    assert (nuevo.id, nuevo.recuerdo_id) == (9, None)
    assert len(chat.buscar(con, memoria.consulta_de("gato"), None)) == 1
    # Los de antes ya se encuentran como recuerdos: no salen dos veces.
    assert chat.buscar(con, memoria.consulta_de("Toby"), None) == []
    assert memoria.buscar_alguna(con, "Toby") == [1]
    con.close()
