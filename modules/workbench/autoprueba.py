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
