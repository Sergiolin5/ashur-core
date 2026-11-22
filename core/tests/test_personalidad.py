from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ashur_core import memoria, personalidad
from ashur_core.app import app
from bases import quitar_desde

ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
# Inventada: la personalidad de Sergio vive solo en su base.
INVENTADA = {
    "base": "Eres Ashur, un asistente de prueba.",
    "sobre_sergio": "A Sergio le gustan los trenes.",
    "madurez": {"inicial": "Preguntas antes de suponer.", "intermedio": "Propones una cosa.", "pleno": "Discutes."},
    "trato": ["Sin halagos."],
    "umbrales": {"intermedio": 3, "pleno": 6},
}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
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
    salida = {"mensaje": {"role": "assistant", "content": texto}}
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"salida": salida}, headers=nodo).status_code == 204


def sistema_de(trabajo):
    return trabajo["entrada"]["messages"][0]["content"]


def conversar(cliente, nodo, texto, respuesta="Listo.", conv="con-1", quien=None):
    (quien or cliente).post(f"/conversaciones/{conv}/mensajes", json={"texto": texto})
    trabajo = tomar(cliente, nodo)
    responder(cliente, nodo, trabajo, respuesta)
    return trabajo


def test_cargar_la_personalidad_pide_administrador_y_se_valida(cliente):
    vista = cliente.get("/personalidad").json()
    assert vista["personalidad"] is None and vista["correcciones"] == []
    assert vista["madurez"] == {"nivel": "inicial", "recuerdos": 0, "umbrales": {"intermedio": 2000, "pleno": 20000}}
    assert cliente.put("/personalidad", json=INVENTADA).status_code == 401
    assert cliente.put("/personalidad", json={**INVENTADA, "umbrales": {"intermedio": 9, "pleno": 3}}, headers=ADMIN).status_code == 422
    assert cliente.put("/personalidad", json={**INVENTADA, "extra": 1}, headers=ADMIN).status_code == 422
    assert cliente.put("/personalidad", json=INVENTADA, headers=ADMIN).json()["personalidad"]["sobre_sergio"] == INVENTADA["sobre_sergio"]
    assert TestClient(app).get("/personalidad").status_code == 401


def test_la_madurez_sube_con_los_recuerdos_y_solo_entra_la_actual(cliente):
    cliente.put("/personalidad", json=INVENTADA, headers=ADMIN)
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    primero = conversar(cliente, nodo, "Hola")  # 1 recuerdo al mandar
    assert "Tu madurez es inicial: Preguntas antes de suponer." in sistema_de(primero)
    assert "Discutes" not in sistema_de(primero)
    assert "Sin halagos." in sistema_de(primero) and "A Sergio le gustan los trenes." in sistema_de(primero)
    segundo = conversar(cliente, nodo, "¿Y?")  # 3 recuerdos al mandar: intermedio
    assert "Tu madurez es intermedio" in sistema_de(segundo)
    conversar(cliente, nodo, "Ajá")
    assert cliente.get("/personalidad").json()["madurez"]["nivel"] == "pleno"  # 6 recuerdos


def test_con_otra_persona_no_entra_lo_de_sergio_y_sabe_con_quien_habla(cliente):
    cliente.put("/personalidad", json=INVENTADA, headers=ADMIN)
    nodo = nuevo_nodo(cliente)
    id_ = cliente.post("/identidades", json={"nombre": "Christian", "clase": "persona"}).json()["id"]
    christian = TestClient(app, headers={"X-Ashur-Clave": cliente.post(f"/identidades/{id_}/clave", headers=ADMIN).json()["clave"]})
    conv = christian.post("/conversaciones").json()["id"]
    sistema = sistema_de(conversar(cliente, nodo, "Hola", conv=conv, quien=christian))
    assert "trenes" not in sistema and "Estás hablando con Christian, no con Sergio." in sistema
    assert "Eres Ashur, un asistente de prueba." in sistema


def test_al_cerrar_una_conversacion_ashur_saca_sus_correcciones_una_vez(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    conversar(cliente, nodo, "¿Qué hora es?", "Son las 3 de la tarde, ¡qué gran pregunta!")
    assert cliente.post("/conversaciones/con-1/cerrar").status_code == 202
    trabajo = tomar(cliente, nodo)
    assert trabajo["entrada"]["proposito"] == "correcciones" and "tools" not in trabajo["entrada"]
    assert "Persona: ¿Qué hora es?" in trabajo["entrada"]["messages"][1]["content"]
    responder(cliente, nodo, trabajo, "- No adular las preguntas.\n- Responder la hora sin adornos.\n- Una tercera de más.")

    correcciones = cliente.get("/personalidad").json()["correcciones"]
    assert [c["texto"] for c in correcciones] == ["No adular las preguntas.", "Responder la hora sin adornos."]
    assert correcciones[0]["fuente"] == "Sergio, con-1"
    cliente.post("/conversaciones/con-1/cerrar")  # una sola vez por conversación
    assert tomar(cliente, nodo) is None

    # Entran al pedido siguiente, sin su fuente.
    cliente.post("/conversaciones")
    sistema = sistema_de(conversar(cliente, nodo, "Hola", conv="con-2"))
    assert "- No adular las preguntas." in sistema and "con-1" not in sistema


def test_cerrar_una_conversacion_ajena_o_ocupada(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    assert cliente.post("/conversaciones/con-1/cerrar").status_code == 409  # Ashur todavía está respondiendo
    responder(cliente, nodo, tomar(cliente, nodo), "Hola.")
    id_ = cliente.post("/identidades", json={"nombre": "Erick", "clase": "persona"}).json()["id"]
    erick = TestClient(app, headers={"X-Ashur-Clave": cliente.post(f"/identidades/{id_}/clave", headers=ADMIN).json()["clave"]})
    assert erick.post("/conversaciones/con-1/cerrar").status_code == 404


def test_tras_30_minutos_sin_mensajes_tambien_salen_y_nada_es_nada(cliente, tmp_path):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    conversar(cliente, nodo, "Hola", "Hola.")
    assert tomar(cliente, nodo) is None  # todavía no pasaron los 30 minutos
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    viejo = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    con.execute("UPDATE conversaciones SET actualizada = ?", (viejo,))
    con.commit()
    con.close()
    trabajo = tomar(cliente, nodo)
    assert trabajo["entrada"]["proposito"] == "correcciones"
    responder(cliente, nodo, trabajo, "NADA")
    assert cliente.get("/personalidad").json()["correcciones"] == []
    assert tomar(cliente, nodo) is None  # no vuelve a salir


def test_solo_se_guardan_las_ultimas_20_y_sergio_las_puede_reemplazar(cliente, tmp_path):
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    for i in range(25):
        personalidad.agregar_correcciones(con, [f"Corrección {i}"], "prueba")
    assert [c.texto for c in personalidad.correcciones(con)] == [f"Corrección {i}" for i in range(5, 25)]
    con.close()
    assert cliente.put("/personalidad/correcciones", json=[]).status_code == 401
    vista = cliente.put("/personalidad/correcciones", json=[{"texto": "Solo esta."}], headers=ADMIN).json()
    assert vista["correcciones"] == [{"texto": "Solo esta.", "fuente": None, "fecha": None}]
    assert cliente.put("/personalidad/correcciones", json=[{"texto": "x" * 201}], headers=ADMIN).status_code == 422


def test_leer_correcciones():
    assert personalidad.leer_correcciones("NADA") == []
    assert personalidad.leer_correcciones("nada que corregir") == []
    assert personalidad.leer_correcciones("Texto suelto sin guion.") == []
    assert personalidad.leer_correcciones("- Nada que corregir.") == []
    assert personalidad.leer_correcciones("- nada.\n- Responder más corto.") == ["Responder más corto."]
    assert personalidad.leer_correcciones("- " + "a" * 300) == ["a" * 200]


def test_una_base_de_la_version_12_marca_sus_conversaciones_como_corregidas(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    quitar_desde(con, 13)
    con.execute("INSERT INTO conversaciones (id, creada, actualizada) VALUES ('con-1', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')")
    con.execute("PRAGMA user_version = 12")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert con.execute("SELECT corregida FROM conversaciones").fetchone()[0] == 1  # sin ráfaga al actualizar
    con.close()
