"""Autoprueba del módulo: corre sin red ni core, con un contexto falso.

Desde core/: uv run pytest ../modules/workbench/autoprueba.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_especificacion = importlib.util.spec_from_file_location("modulo_workbench", Path(__file__).with_name("modulo.py"))
modulo = importlib.util.module_from_spec(_especificacion)
sys.modules["modulo_workbench"] = modulo  # como lo carga el core
_especificacion.loader.exec_module(modulo)


class DatosFalsos:
    """Imita a contexto.datos: registros en memoria, del más nuevo al más viejo."""

    def __init__(self):
        self.colecciones = {}
        self.cuenta = 0

    def listar(self, coleccion):
        return [dict(r) for r in reversed(self.colecciones.get(coleccion, {}).values())]

    def leer(self, coleccion, id_):
        registro = self.colecciones.get(coleccion, {}).get(id_)
        return dict(registro) if registro else None

    def guardar(self, coleccion, datos, id_=None):
        if id_ is None:
            self.cuenta += 1
            id_ = f"r{self.cuenta}"
        elif id_ not in self.colecciones.get(coleccion, {}):
            raise KeyError(id_)
        self.colecciones.setdefault(coleccion, {})[id_] = {**datos, "id": id_}
        return self.leer(coleccion, id_)

    def borrar(self, coleccion, id_):
        return self.colecciones.get(coleccion, {}).pop(id_, None) is not None


class ContextoFalso:
    def __init__(self, ajustes=None):
        self.datos = DatosFalsos()
        self.ajustes = ajustes or {}

    def ajuste(self, id_):
        return self.ajustes.get(id_)


def _crear(contexto, tipo, **datos):
    return modulo.crear(contexto, tipo, datos)["registro"]


def test_crear_editar_listar_y_borrar():
    c = ContextoFalso()
    tarea = _crear(c, "tareas", titulo="Probar")
    assert tarea["estado"] == "cola" and tarea["ejecuciones"] == 0
    assert modulo.editar(c, "tareas", tarea["id"], {"prioridad": "alta"})["registro"]["titulo"] == "Probar"
    assert [t["prioridad"] for t in modulo.listar(c, "tareas")["registros"]] == ["alta"]
    assert modulo.borrar(c, "tareas", tarea["id"]) == {"borrado": True}
    with pytest.raises(ValueError):
        modulo.crear(c, "tareas", {"titulo": " "})
    with pytest.raises(ValueError):
        modulo.listar(c, "gatos")


def test_repartir_cola_va_al_proveedor_con_mas_cuota_libre():
    c = ContextoFalso()
    poco = _crear(c, "proveedores", nombre="Poco", cuota=10, usadas=9)
    mucho = _crear(c, "proveedores", nombre="Mucho", cuota=10, usadas=8)
    _crear(c, "proveedores", nombre="Pausado", cuota=100, estado="pausado")
    for titulo in ("a", "b", "c", "d"):
        _crear(c, "tareas", titulo=titulo)
    assert modulo.repartir_cola(c) == {"asignadas": 3}  # solo hay 3 ejecuciones libres
    por_titulo = {t["titulo"]: t for t in c.datos.listar("tareas")}
    assert [por_titulo[t]["proveedor_id"] for t in "abc"] == [mucho["id"], mucho["id"], poco["id"]]
    assert por_titulo["d"]["estado"] == "cola"


def test_ejecutar_tarea_con_claude_guarda_el_resultado_y_gasta_cuota(monkeypatch):
    c = ContextoFalso({"clave_claude": "k"})
    proveedor = _crear(c, "proveedores", nombre="Claude", familia="claude")
    tarea = _crear(c, "tareas", titulo="Probar", proveedor_id=proveedor["id"], estado="asignada")
    pedidos = []

    def falso(url, cuerpo, cabeceras, espera, metodo=None):
        pedidos.append((url, cuerpo, cabeceras))
        return 200, json.dumps({"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": ""},
                                                                        {"type": "text", "text": "Hecho."}]})

    monkeypatch.setattr(modulo, "_pedir_http", falso)
    hecha = modulo.ejecutar_tarea(c, tarea["id"])["registro"]
    assert (hecha["estado"], hecha["resultado"], hecha["ejecuciones"]) == ("revision", "Hecho.", 1)
    assert hecha["modelo_usado"] == pedidos[0][1]["model"] == "claude-opus-5-5"
    assert pedidos[0][2]["x-api-key"] == "k" and "Tarea: Probar" in pedidos[0][1]["messages"][0]["content"]
    assert c.datos.leer("proveedores", proveedor["id"])["usadas"] == 1


def test_ejecutar_tarea_sin_clave_o_con_error_del_modelo_deja_la_tarea_con_error(monkeypatch):
    c = ContextoFalso({"clave_gpt": "k"})
    sin_clave = _crear(c, "proveedores", nombre="Gemini", familia="gemini", modelo="g")
    gpt = _crear(c, "proveedores", nombre="GPT", familia="gpt", modelo="m")
    una = _crear(c, "tareas", titulo="Una", proveedor_id=sin_clave["id"])
    otra = _crear(c, "tareas", titulo="Otra", proveedor_id=gpt["id"])
    monkeypatch.setattr(modulo, "_pedir_http", lambda *a, **k: (429, json.dumps({"error": {"message": "sin cuota"}})))
    assert "Falta la clave" in modulo.ejecutar_tarea(c, una["id"])["registro"]["error"]
    fallida = modulo.ejecutar_tarea(c, otra["id"])["registro"]
    assert fallida["estado"] == "error" and "sin cuota" in fallida["error"]
    assert c.datos.leer("proveedores", gpt["id"])["usadas"] == 0
    with pytest.raises(ValueError):
        modulo.ejecutar_tarea(c, _crear(c, "tareas", titulo="Suelta")["id"])


def test_probar_servidor_y_compilar_entrega(monkeypatch):
    c = ContextoFalso()
    servidor = _crear(c, "servidores", nombre="Zima", url="http://zima:8720/", ruta_compilacion="/hooks/build")
    entrega = _crear(c, "entregas", version="v1")
    llamadas = []

    def falso(url, cuerpo, cabeceras, espera, metodo=None):
        llamadas.append((url, cuerpo))
        return 200, "ok"

    monkeypatch.setattr(modulo, "_pedir_http", falso)
    probado = modulo.probar_servidor(c, servidor["id"])["registro"]
    assert probado["estado"] == "en_linea" and probado["detalle"] == "HTTP 200" and llamadas[0][0] == "http://zima:8720/"
    compilada = modulo.compilar_entrega(c, entrega["id"])
    assert compilada["aceptada"] and compilada["registro"]["estado"] == "compilando"
    assert llamadas[1] == ("http://zima:8720/hooks/build", {"version": "v1", "canal": "interno", "proyecto": None})

    def caido(*a, **k):
        raise OSError("sin ruta")

    monkeypatch.setattr(modulo, "_pedir_http", caido)
    assert modulo.probar_servidor(c, servidor["id"])["registro"]["estado"] == "sin_conexion"
    assert modulo.compilar_entrega(c, entrega["id"])["registro"]["estado"] == "fallida"


def test_una_tarea_de_equipo_espera_se_toma_y_se_entrega():
    c = ContextoFalso()
    proveedor = _crear(c, "proveedores", nombre="Claude Code", familia="claude_code", modelo="opus")
    otro = _crear(c, "proveedores", nombre="Codex", familia="codex")
    tarea = _crear(c, "tareas", titulo="Probar", proveedor_id=proveedor["id"])
    ajena = _crear(c, "tareas", titulo="De Codex", proveedor_id=otro["id"])
    assert modulo.tomar_tarea(c, "Mac", ["claude_code"]) == {"tarea": None}  # nadie pidió ejecutarla todavía

    en_espera = modulo.ejecutar_tarea(c, tarea["id"])["registro"]
    assert (en_espera["estado"], en_espera["espera_equipo"], en_espera["equipo"]) == ("ejecutando", True, None)
    modulo.ejecutar_tarea(c, ajena["id"])

    tomada = modulo.tomar_tarea(c, "Mac", ["claude_code", "inventada"])["tarea"]
    assert (tomada["id"], tomada["familia"], tomada["modelo"]) == (tarea["id"], "claude_code", "opus")
    assert "Tarea: Probar" in tomada["encargo"]
    assert [(e["nombre"], e["familias"]) for e in c.datos.listar("equipos")] == [("Mac", ["claude_code"])]
    assert modulo.tomar_tarea(c, "Mac", ["claude_code"]) == {"tarea": None}  # ya está tomada; la de Codex no es suya
    assert len(c.datos.listar("equipos")) == 1

    with pytest.raises(ValueError):
        modulo.entregar_tarea(c, tarea["id"], "Otra Mac", resultado="x")
    hecha = modulo.entregar_tarea(c, tarea["id"], "Mac", resultado="Hecho.", modelo="claude-code")["registro"]
    assert (hecha["estado"], hecha["resultado"], hecha["modelo_usado"], hecha["ejecuciones"]) == (
        "revision", "Hecho.", "claude-code", 1
    )
    assert hecha["espera_equipo"] is False and c.datos.leer("proveedores", proveedor["id"])["usadas"] == 1
    with pytest.raises(ValueError):
        modulo.entregar_tarea(c, tarea["id"], "Mac", resultado="otra vez")


def test_una_tarea_tomada_hace_mucho_se_vuelve_a_ofrecer_y_un_error_del_equipo_queda_anotado():
    c = ContextoFalso()
    proveedor = _crear(c, "proveedores", nombre="Claude Code", familia="claude_code")
    tarea = _crear(c, "tareas", titulo="Probar", proveedor_id=proveedor["id"])
    modulo.ejecutar_tarea(c, tarea["id"])
    assert modulo.tomar_tarea(c, "Mac", ["claude_code"])["tarea"]["id"] == tarea["id"]
    vieja = {**c.datos.leer("tareas", tarea["id"]), "tomada": "2020-01-01T00:00:00+00:00"}  # la Mac se apagó
    c.datos.guardar("tareas", vieja, tarea["id"])
    assert modulo.tomar_tarea(c, "iMac", ["claude_code"])["tarea"]["id"] == tarea["id"]
    with pytest.raises(ValueError):
        modulo.entregar_tarea(c, tarea["id"], "Mac", resultado="tarde")
    fallida = modulo.entregar_tarea(c, tarea["id"], "iMac", error="claude no inició sesión")["registro"]
    assert (fallida["estado"], fallida["error"]) == ("error", "claude no inició sesión")
    assert c.datos.leer("proveedores", proveedor["id"])["usadas"] == 0


_esp_ejecutor = importlib.util.spec_from_file_location("ejecutor_workbench", Path(__file__).with_name("ejecutor.py"))
ejecutor = importlib.util.module_from_spec(_esp_ejecutor)
_esp_ejecutor.loader.exec_module(ejecutor)


def test_el_ejecutor_arma_el_comando_y_lee_la_respuesta_de_claude():
    assert ejecutor.comando("claude_code", None)[:2] == ["claude", "-p"]
    assert ejecutor.comando("claude_code", "opus")[-2:] == ["--model", "opus"]
    assert ejecutor.leer_respuesta("claude_code", json.dumps({"is_error": False, "result": " Hecho. "})) == "Hecho."
    assert ejecutor.leer_respuesta("codex", " texto \n") == "texto"
    with pytest.raises(RuntimeError, match="sin sesión"):
        ejecutor.leer_respuesta("claude_code", json.dumps({"is_error": True, "result": "sin sesión"}))
    with pytest.raises(RuntimeError):
        ejecutor.leer_respuesta("claude_code", "no es json")


def test_el_ejecutor_toma_resuelve_y_entrega_contra_el_modulo():
    c = ContextoFalso()
    proveedor = _crear(c, "proveedores", nombre="Claude Code", familia="claude_code")
    buena = _crear(c, "tareas", titulo="Buena", proveedor_id=proveedor["id"])
    mala = _crear(c, "tareas", titulo="Mala", proveedor_id=proveedor["id"])
    modulo.ejecutar_tarea(c, buena["id"])
    modulo.ejecutar_tarea(c, mala["id"])

    def accion(core, clave, nombre, parametros):  # hace de core
        return getattr(modulo, nombre)(c, **parametros)

    def resolver(familia, modelo, encargo):
        if "Mala" in encargo:
            raise RuntimeError("claude terminó con error")
        return "Respuesta"

    atender = lambda: ejecutor.atender_una("http://core", "k", "Mac", ["claude_code"], resolver, accion)
    assert atender() and atender() and not atender()
    assert c.datos.leer("tareas", buena["id"])["resultado"] == "Respuesta"
    assert c.datos.leer("tareas", buena["id"])["modelo_usado"] == "claude"
    assert c.datos.leer("tareas", mala["id"])["error"] == "claude terminó con error"
