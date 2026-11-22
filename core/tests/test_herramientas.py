import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ashur_core import herramientas
from ashur_core.app import app

ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
SIN_HERRAMIENTAS = {"nombre": "gemma:2b", "tamano": int(1.5 * GB), "capacidades": ["completion"]}


def escribir_modulo(carpeta: Path) -> None:
    (carpeta / "luces").mkdir(parents=True)
    manifiesto = {"id": "luces", "nombre": "Luces", "version": "0.1.0", "descripcion": "Las luces de la casa.",
                  "acciones": [{"id": "estado", "descripcion": "Dice cómo están.", "escribe": False},
                               {"id": "apagar", "descripcion": "Apaga una luz.", "escribe": True},
                               {"id": "romper", "descripcion": "Falla.", "escribe": False}]}
    (carpeta / "luces" / "modulo.json").write_text(json.dumps(manifiesto), encoding="utf-8")
    (carpeta / "luces" / "modulo.py").write_text(
        "def estado(contexto, sala=''):\n    return {'sala': sala, 'encendida': True}\n"
        "def apagar(contexto, sala=''):\n    return {'apagada': sala}\n"
        "def romper(contexto):\n    raise RuntimeError('sin corriente')\n",
        encoding="utf-8",
    )


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    carpeta = tmp_path / "modules"
    carpeta.mkdir()
    escribir_modulo(carpeta)
    monkeypatch.setenv("ASHUR_MODULOS", str(carpeta))
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    c = TestClient(app, headers={"X-Ashur-Clave": "c"})
    c.post("/objetos", json={"nombre": "bicicleta roja", "lugar": "garaje"})
    c.post("/objetos", json={"nombre": "casco", "lugar": None})
    c.post("/identidades", json={"nombre": "Ana", "clase": "persona"})
    return c


def nuevo_nodo(cliente, modelos=(QWEN7,)):
    creado = cliente.post("/nodos", json={"nombre": "windows"}, headers=ADMIN).json()
    encabezado = {"X-Ashur-Clave-Nodo": creado["clave"]}
    cliente.post("/nodo/latido", json={"modo": "full", "modelos": list(modelos)}, headers=encabezado)
    return encabezado


def tomar(cliente, nodo):
    r = cliente.post("/nodo/trabajos/tomar", headers=nodo)
    return r.json() if r.status_code == 200 else None


def entregar(cliente, nodo, trabajo, contenido="", llamadas=None):
    mensaje = {"role": "assistant", "content": contenido}
    if llamadas is not None:
        mensaje["tool_calls"] = [{"function": {"name": n, "arguments": a}} for n, a in llamadas]
    return cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"salida": {"mensaje": mensaje}}, headers=nodo)


def herramientas_de(trabajo):
    return [t["function"]["name"] for t in trabajo["entrada"].get("tools", [])]


def resultados(trabajo):
    return {m["tool_name"]: m["content"] for m in trabajo["entrada"]["messages"] if m["role"] == "tool"}


def test_ashur_usa_el_inventario_y_responde_con_lo_que_encontro(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Dónde está la bici?"})
    primero = tomar(cliente, nodo)
    assert {"buscar_objetos", "listar_identidades", "buscar_recuerdos", "modulo-luces-estado"} <= set(herramientas_de(primero))
    assert entregar(cliente, nodo, primero, llamadas=[("buscar_objetos", {"texto": "bici"})]).status_code == 204

    segundo = tomar(cliente, nodo)
    assert resultados(segundo) == {"buscar_objetos": "bicicleta roja: garaje"}
    pedido = [m for m in segundo["entrada"]["messages"] if m["role"] == "assistant"][-1]
    assert pedido["tool_calls"][0]["function"]["name"] == "buscar_objetos"
    entregar(cliente, nodo, segundo, "Está en el garaje.")

    completa = cliente.get("/conversaciones/con-1").json()
    assert completa["espera"] is None
    assert [m["texto"] for m in completa["mensajes"]] == ["¿Dónde está la bici?", "Está en el garaje."]
    # Solo la respuesta final es mensaje y recuerdo; las rondas viven en los trabajos.
    assert [r["texto"] for r in cliente.get("/recuerdos").json()] == ["¿Dónde está la bici?", "Está en el garaje."]


def test_argumentos_como_texto_json_y_herramientas_varias(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[
        ("listar_identidades", "{}"), ("buscar_objetos", '{"texto": "zzz"}'), ("inventada", {}),
        ("buscar_objetos", {"color": "rojo"}), ("buscar_recuerdos", "{no es json"),
    ])
    contenidos = [m["content"] for m in tomar(cliente, nodo)["entrada"]["messages"] if m["role"] == "tool"]
    assert contenidos == [
        "Ana (persona)", "No hay objetos con eso.", "No existe la herramienta inventada.",
        "Argumentos inválidos: Extra inputs are not permitted.", "Los argumentos no son JSON válido.",
    ]


def test_las_acciones_de_modulos_que_escriben_quedan_pendientes(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Apaga la sala"})
    entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[
        ("modulo-luces-estado", {"sala": "sala"}), ("modulo-luces-apagar", {"sala": "sala"}), ("modulo-luces-romper", {}),
    ])
    r = resultados(tomar(cliente, nodo))
    assert json.loads(r["modulo-luces-estado"]) == {"sala": "sala", "encendida": True}
    assert r["modulo-luces-apagar"] == "Quedó pendiente de la aprobación de Sergio (pedido 1). Todavía no se hizo."
    assert r["modulo-luces-romper"].startswith("El módulo luces falló: RuntimeError: sin corriente")
    pedidos = cliente.get("/pedidos").json()
    assert [(p["accion"], p["estado"], p["parametros"]) for p in pedidos] == [("apagar", "pendiente", {"sala": "sala"})]


def test_tras_tres_rondas_ashur_responde_sin_herramientas(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    for ronda in range(herramientas.RONDAS):
        trabajo = tomar(cliente, nodo)
        assert herramientas_de(trabajo), ronda
        entregar(cliente, nodo, trabajo, llamadas=[("listar_identidades", {})])
    final = tomar(cliente, nodo)
    assert herramientas_de(final) == []
    # Sin herramientas ofrecidas, una llamada igual no se corre.
    entregar(cliente, nodo, final, "Hola, Sergio.", llamadas=[])
    assert cliente.get("/conversaciones/con-1").json()["mensajes"][-1]["texto"] == "Hola, Sergio."


def test_pasado_el_limite_las_llamadas_no_abren_otra_ronda(cliente):
    from ashur_core import nodos

    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    for _ in range(herramientas.RONDAS):
        entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[("listar_identidades", {})])
    # Ya sin herramientas, un modelo que igual pide una no abre otra ronda ni crea pedidos: falla y se reintenta.
    for _ in range(nodos.INTENTOS):
        final = tomar(cliente, nodo)
        assert herramientas_de(final) == [] and final["entrada"]["rondas"] == herramientas.RONDAS
        entregar(cliente, nodo, final, "", llamadas=[("modulo-luces-apagar", {"sala": "x"})])
    assert tomar(cliente, nodo) is None
    espera = cliente.get("/conversaciones/con-1").json()["espera"]
    assert espera["estado"] == "fallido" and "sin que se le ofrecieran" in espera["error"]
    assert cliente.get("/pedidos").json() == []


def test_pasado_el_limite_una_respuesta_con_texto_y_llamadas_termina(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    for _ in range(herramientas.RONDAS):
        entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[("listar_identidades", {})])
    entregar(cliente, nodo, tomar(cliente, nodo), "Hola.", llamadas=[("listar_identidades", {})])
    assert cliente.get("/conversaciones/con-1").json()["mensajes"][-1]["texto"] == "Hola."
    assert tomar(cliente, nodo) is None


def test_un_resultado_con_fechas_no_tumba_la_ronda(cliente, tmp_path):
    carpeta = tmp_path / "modules" / "reloj"
    carpeta.mkdir()
    (carpeta / "modulo.json").write_text(json.dumps({
        "id": "reloj", "nombre": "Reloj", "version": "0.1.0", "descripcion": "La hora.",
        "acciones": [{"id": "ahora", "descripcion": "Da la hora.", "escribe": False}]}), encoding="utf-8")
    (carpeta / "modulo.py").write_text(
        "from datetime import datetime\ndef ahora(contexto):\n    return {'hora': datetime(2026, 11, 22, 9, 30), 'x': {1}}\n",
        encoding="utf-8")
    from ashur_core.app import _registro

    _registro.cache_clear()  # el registro de módulos se lee una vez por carpeta
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Qué hora es?"})
    assert entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[("modulo-reloj-ahora", {})]).status_code == 204
    assert "2026-11-22 09:30:00" in resultados(tomar(cliente, nodo))["modulo-reloj-ahora"]


def test_los_argumentos_en_texto_vuelven_como_objeto(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[("buscar_objetos", '{"texto": "bici"}')])
    pedido = [m for m in tomar(cliente, nodo)["entrada"]["messages"] if m["role"] == "assistant"][-1]
    assert pedido["tool_calls"][0]["function"]["arguments"] == {"texto": "bici"}


def test_un_nodo_sin_modelo_de_herramientas_recibe_el_pedido_sin_ellas(cliente):
    nodo = nuevo_nodo(cliente, modelos=(SIN_HERRAMIENTAS,))
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    trabajo = tomar(cliente, nodo)
    assert trabajo["modelo"] == "gemma:2b" and herramientas_de(trabajo) == []


def test_un_pedido_con_herramientas_solo_lo_toma_un_modelo_que_las_use(cliente):
    con_herramientas = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    sin = nuevo_nodo(cliente, modelos=(SIN_HERRAMIENTAS,))
    assert tomar(cliente, sin) is None  # el pedido trae herramientas y gemma no las sabe usar
    assert tomar(cliente, con_herramientas)["modelo"] == "qwen2.5:7b"


def test_una_respuesta_vacia_sin_llamadas_se_rechaza(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    malas = {"salida": {"mensaje": {"role": "assistant", "content": "", "tool_calls": [{"function": {}}]}}}
    entregas = [
        lambda t: entregar(cliente, nodo, t, "  "),
        lambda t: entregar(cliente, nodo, t, "", llamadas=[]),
        lambda t: cliente.post(f"/nodo/trabajos/{t['id']}", json=malas, headers=nodo),
    ]
    for entrega in entregas:  # cada una cuenta como un intento; la tercera agota los intentos
        assert entrega(tomar(cliente, nodo)).status_code == 422
    assert tomar(cliente, nodo) is None
    assert cliente.get("/conversaciones/con-1").json()["espera"]["estado"] == "fallido"


def test_entre_un_paso_y_el_siguiente_no_se_cuela_otro_mensaje(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    entregar(cliente, nodo, tomar(cliente, nodo), llamadas=[("listar_identidades", {})])
    # La ronda siguiente ya está en la cola: la conversación sigue ocupada.
    assert cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Y?"}).status_code == 409
    entregar(cliente, nodo, tomar(cliente, nodo), "Listo.")
    assert cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Y?"}).status_code == 202
