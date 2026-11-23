from datetime import datetime, timedelta, timezone

import pytest
from bases import quitar_desde
from fastapi.testclient import TestClient

from ashur_core import memoria, nodos
from ashur_core.app import app

ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
QWEN3 = {"nombre": "qwen2.5:3b", "tamano": int(1.9 * GB), "capacidades": ["completion", "tools"]}
BGE = {"nombre": "bge-m3", "tamano": int(1.2 * GB), "capacidades": ["embedding"]}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def nuevo_nodo(cliente, nombre="windows", modo="full", modelos=(QWEN7,)):
    creado = cliente.post("/nodos", json={"nombre": nombre}, headers=ADMIN).json()
    encabezado = {"X-Ashur-Clave-Nodo": creado["clave"]}
    assert cliente.post("/nodo/latido", json={"modo": modo, "modelos": list(modelos)}, headers=encabezado).status_code == 200
    return creado["nodo"]["id"], encabezado


def responder(cliente, encabezado, texto):
    trabajo = cliente.post("/nodo/trabajos/tomar", headers=encabezado)
    assert trabajo.status_code == 200
    salida = {"mensaje": {"role": "assistant", "content": texto}}
    assert cliente.post(f"/nodo/trabajos/{trabajo.json()['id']}", json={"salida": salida}, headers=encabezado).status_code == 204
    return trabajo.json()


# ── Política (funciones puras) ──


def M(datos):
    return nodos.Modelo(**datos)


def test_sergio_gana_en_sus_maquinas():
    assert nodos.puede_correr("full", M(QWEN7))
    assert nodos.puede_correr("light", M(QWEN3)) and not nodos.puede_correr("light", M(QWEN7))
    assert not nodos.puede_correr("busy", M(QWEN3)) and not nodos.puede_correr("off", M(BGE))


def test_ashur_elige_el_mejor_modelo_que_el_modo_permite():
    modelos = [M(QWEN7), M(QWEN3), M(BGE)]
    assert nodos.mejor_modelo("conversar", "full", modelos).nombre == "qwen2.5:7b"
    assert nodos.mejor_modelo("conversar", "light", modelos).nombre == "qwen2.5:3b"
    assert nodos.mejor_modelo("embedding", "light", modelos).nombre == "bge-m3"
    assert nodos.mejor_modelo("conversar", "busy", modelos) is None


def test_un_trabajo_reciente_espera_al_mejor_nodo():
    otros = [("full", [M(QWEN7)])]
    assert not nodos.le_toca("conversar", M(QWEN3), otros, edad_s=2)
    assert nodos.le_toca("conversar", M(QWEN3), otros, edad_s=nodos.ESPERA_MEJOR_S)
    assert nodos.le_toca("conversar", M(QWEN7), [("light", [M(QWEN7)])], edad_s=0)  # light no puede con el 7B


def test_un_nodo_en_bateria_es_el_ultimo_recurso():
    # Un nodo light (con batería o en uso) espera mientras haya un nodo full en línea que pueda atender el trabajo,
    # aunque su modelo sea igual o más liviano.
    full = [("full", [M(QWEN3)])]
    assert not nodos.le_toca("conversar", M(QWEN3), full, edad_s=nodos.ESPERA_MEJOR_S, modo="light")
    assert not nodos.le_toca("conversar", M(QWEN3), full, edad_s=nodos.ESPERA_LIGERO_S - 1, modo="light")
    assert nodos.le_toca("conversar", M(QWEN3), full, edad_s=nodos.ESPERA_LIGERO_S, modo="light")
    # Si el único otro nodo full no puede con el trabajo, o no hay ninguno, el light no espera de más.
    solo_embeddings = [("full", [M(BGE)])]
    assert nodos.le_toca("conversar", M(QWEN3), solo_embeddings, edad_s=0, modo="light")
    assert nodos.le_toca("conversar", M(QWEN3), [("light", [M(QWEN3)])], edad_s=0, modo="light")
    # Un nodo full no espera a los light.
    assert nodos.le_toca("conversar", M(QWEN3), [("light", [M(QWEN3)])], edad_s=0, modo="full")


# ── Chat de punta a punta con un nodo falso ──


def test_conversar_con_un_nodo(cliente):
    _, nodo = nuevo_nodo(cliente)
    conversacion = cliente.post("/conversaciones").json()
    assert conversacion["id"] == "con-1" and conversacion["titulo"] is None

    enviado = cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola, ¿dónde dejé las llaves?"})
    assert enviado.status_code == 202
    assert enviado.json()["espera"]["estado"] == "pendiente"
    # Mientras Ashur no responde, no se puede mandar otro mensaje.
    assert cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Hola?"}).status_code == 409

    trabajo = responder(cliente, nodo, "No lo sé todavía.")
    assert trabajo["modelo"] == "qwen2.5:7b" and trabajo["necesidad"] == "conversar"
    mensajes = trabajo["entrada"]["messages"]
    assert mensajes[0]["role"] == "system" and mensajes[-1] == {"role": "user", "content": "Hola, ¿dónde dejé las llaves?"}

    completa = cliente.get("/conversaciones/con-1").json()
    assert completa["espera"] is None
    assert [(m["rol"], m["texto"]) for m in completa["mensajes"]] == [
        ("user", "Hola, ¿dónde dejé las llaves?"), ("assistant", "No lo sé todavía.")
    ]
    assert completa["conversacion"]["titulo"] == "Hola, ¿dónde dejé las llaves?"

    # Los mensajes son historial, no memoria: qué se recuerda lo decide un nodo después (ADR 0028).
    assert cliente.get("/recuerdos").json() == []
    assert [m["recuerdo_id"] for m in completa["mensajes"]] == [None, None]

    # El segundo mensaje lleva la conversación entera, y va antes que el trabajo de fondo de los recuerdos.
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Gracias."})
    segundo = responder(cliente, nodo, "De nada.")
    assert "proposito" not in segundo["entrada"]
    assert [m["role"] for m in segundo["entrada"]["messages"]] == ["system", "user", "assistant", "user"]
    assert [c["id"] for c in cliente.get("/conversaciones").json()] == ["con-1"]


def test_sin_nodos_el_mensaje_espera(cliente):
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    assert cliente.get("/conversaciones/con-1").json()["espera"]["estado"] == "pendiente"
    _, nodo = nuevo_nodo(cliente, modo="busy")
    assert cliente.post("/nodo/trabajos/tomar", headers=nodo).status_code == 204  # Sergio está usando el equipo


def test_un_error_del_nodo_reintenta_y_luego_falla(cliente):
    _, nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    for _ in range(nodos.INTENTOS):
        trabajo = cliente.post("/nodo/trabajos/tomar", headers=nodo).json()
        cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"error": "Ollama no responde"}, headers=nodo)
    espera = cliente.get("/conversaciones/con-1").json()["espera"]
    assert espera["estado"] == "fallido" and espera["error"] == "Ollama no responde"
    # Con el anterior fallido, se puede volver a escribir.
    assert cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Ahora?"}).status_code == 202


def test_las_claves_de_nodo_solo_abren_la_cola(cliente):
    id_, nodo = nuevo_nodo(cliente)
    sin_clave = TestClient(app)
    for ruta in ("/recuerdos", "/galaxia", "/objetos", "/identidades", "/modulos", "/pedidos", "/conversaciones", "/nodos"):
        assert sin_clave.get(ruta, headers=nodo).status_code == 401, ruta
    assert sin_clave.post("/nodo/trabajos/tomar", headers={"X-Ashur-Clave-Nodo": "otra"}).status_code == 401
    assert cliente.post("/nodo/trabajos/tomar").status_code == 401  # la clave de Sergio no es de nodo
    assert cliente.post("/nodos", json={"nombre": "x"}).status_code == 401  # crear un nodo pide administrador

    cliente.patch(f"/nodos/{id_}", json={"archivado": True}, headers=ADMIN)
    assert sin_clave.post("/nodo/trabajos/tomar", headers=nodo).status_code == 401  # archivado, pierde su clave


def test_la_clave_se_muestra_una_vez_y_se_guarda_como_hash(cliente, tmp_path):
    creado = cliente.post("/nodos", json={"nombre": "mac"}, headers=ADMIN).json()
    assert len(creado["clave"]) == 64 and "clave" not in cliente.get("/nodos").json()[0]
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    assert creado["clave"] not in str(con.execute("SELECT * FROM nodos").fetchall())
    con.close()


def test_un_nodo_no_entrega_el_trabajo_de_otro(cliente):
    _, uno = nuevo_nodo(cliente, "uno")
    _, otro = nuevo_nodo(cliente, "otro")
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    trabajo = cliente.post("/nodo/trabajos/tomar", headers=uno).json()
    assert cliente.post("/nodo/trabajos/tomar", headers=otro).status_code == 204  # ya está tomado
    salida = {"salida": {"mensaje": {"role": "assistant", "content": "x"}}}
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json=salida, headers=otro).status_code == 409
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"salida": {"mensaje": {}}}, headers=uno).status_code == 422
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={}, headers=uno).status_code == 422


def test_un_trabajo_vencido_vuelve_a_la_cola_y_un_nodo_callado_queda_fuera_de_linea(tmp_path):
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    t0 = datetime.now(timezone.utc)
    uno = nodos.crear(con, nodos.NodoNuevo(nombre="uno")).nodo.id
    otro = nodos.crear(con, nodos.NodoNuevo(nombre="otro")).nodo.id
    latido = nodos.Latido(modo="full", modelos=[M(QWEN7)])
    nodos.latir(con, uno, latido, t0)
    nodos.latir(con, otro, latido, t0)
    trabajo = nodos.encolar(con, "conversar", {"messages": []})
    assert nodos.tomar(con, uno, t0).id == trabajo
    assert nodos.tomar(con, otro, t0) is None

    despues = t0 + timedelta(seconds=nodos.PLAZO_S + 1)
    assert nodos.tomar(con, otro, despues) is None  # el otro también calló: fuera de línea
    nodos.latir(con, otro, latido, despues)
    assert nodos.tomar(con, otro, despues).id == trabajo  # el plazo de uno venció
    assert not nodos.obtener(con, uno, despues).en_linea
    con.close()


def test_el_trabajo_reciente_espera_al_nodo_full(tmp_path):
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    t0 = datetime.now(timezone.utc)
    potente = nodos.crear(con, nodos.NodoNuevo(nombre="windows")).nodo.id
    liviano = nodos.crear(con, nodos.NodoNuevo(nombre="ipad")).nodo.id
    nodos.latir(con, potente, nodos.Latido(modo="full", modelos=[M(QWEN7)]), t0)
    nodos.latir(con, liviano, nodos.Latido(modo="full", modelos=[M(QWEN3)]), t0)
    nodos.encolar(con, "conversar", {"messages": []})
    assert nodos.tomar(con, liviano, t0) is None  # Ashur prefiere el 7B
    assert nodos.tomar(con, potente, t0).modelo == "qwen2.5:7b"
    con.close()


def test_el_nodo_en_bateria_espera_a_la_zima_y_toma_si_nadie_mas_puede(tmp_path):
    from datetime import timedelta

    con = memoria.abrir(str(tmp_path / "ashur.db"))
    t0 = datetime.now(timezone.utc)
    zima = nodos.crear(con, nodos.NodoNuevo(nombre="zima")).nodo.id
    telefono = nodos.crear(con, nodos.NodoNuevo(nombre="telefono")).nodo.id
    nodos.latir(con, zima, nodos.Latido(modo="full", modelos=[M(QWEN3)]), t0)
    nodos.latir(con, telefono, nodos.Latido(modo="light", modelos=[M(QWEN3)]), t0)
    primero = nodos.encolar(con, "conversar", {"messages": []})
    tarde = t0 + timedelta(seconds=nodos.ESPERA_MEJOR_S + 5)
    nodos.latir(con, zima, nodos.Latido(modo="full", modelos=[M(QWEN3)]), tarde)
    nodos.latir(con, telefono, nodos.Latido(modo="light", modelos=[M(QWEN3)]), tarde)
    assert nodos.tomar(con, telefono, tarde) is None  # pasados los 10 s, el de batería sigue esperando
    assert nodos.tomar(con, zima, tarde).id == primero

    # Con la Zima ocupada (busy), el teléfono en batería toma el trabajo sin esperar.
    segundo = nodos.encolar(con, "conversar", {"messages": []})
    nodos.latir(con, zima, nodos.Latido(modo="busy", modelos=[M(QWEN3)]), tarde)
    assert nodos.tomar(con, telefono, tarde).id == segundo
    con.close()


def test_dos_mensajes_a_la_vez_dejan_un_solo_trabajo(cliente):
    import threading

    cliente.post("/conversaciones")
    codigos = []
    hilos = [
        threading.Thread(target=lambda: codigos.append(
            cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"}).status_code))
        for _ in range(8)
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(codigos) == [202] + [409] * 7
    assert len(cliente.get("/conversaciones/con-1").json()["mensajes"]) == 1


def test_una_base_de_la_version_8_recibe_el_chat(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    quitar_desde(con, 9)
    con.execute("PRAGMA user_version = 8")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert nodos.listar(con) == []
    con.close()
