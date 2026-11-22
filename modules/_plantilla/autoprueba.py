"""Autoprueba del módulo: corre sin red ni core, con un contexto falso.

Desde core/: uv run pytest ../modules/_plantilla/autoprueba.py
"""

import importlib.util
import sys
from pathlib import Path

_especificacion = importlib.util.spec_from_file_location("modulo_plantilla", Path(__file__).with_name("modulo.py"))
modulo = importlib.util.module_from_spec(_especificacion)
sys.modules["modulo_plantilla"] = modulo  # como lo carga el core
_especificacion.loader.exec_module(modulo)


class ContextoFalso:
    """Imita al contexto del core: guarda los recuerdos en una lista y da los ajustes que se le pasen."""

    def __init__(self, ajustes=None):
        self.recuerdos = []
        self.ajustes = {"saludo": "Hola", **(ajustes or {})}  # por_defecto de modulo.json

    def ajuste(self, id_):
        return self.ajustes.get(id_)

    def recordar(self, texto, **datos):
        self.recuerdos.append({"texto": texto, **datos})
        return self.recuerdos[-1]


def test_saludar():
    contexto = ContextoFalso()
    assert modulo.saludar(contexto, nombre="Ana") == {"saludo": "Hola, Ana."}
    assert contexto.recuerdos == [{"texto": "La plantilla saludó a Ana."}]


def test_saludar_con_el_ajuste_de_sergio():
    assert modulo.saludar(ContextoFalso({"saludo": "Buenas"}), nombre="Ana") == {"saludo": "Buenas, Ana."}
