"""Autopruebas de Ashur Network: sin red, core ni servicios externos.

Desde core/:
uv run pytest ../modules/network/autoprueba.py
"""

import importlib.util
import sys
from pathlib import Path


_especificacion = importlib.util.spec_from_file_location(
    "modulo_network",
    Path(__file__).with_name("modulo.py"),
)
modulo = importlib.util.module_from_spec(_especificacion)
sys.modules["modulo_network"] = modulo
_especificacion.loader.exec_module(modulo)


class ContextoFalso:
    def __init__(self):
        self.recuerdos = []

    def recordar(self, texto, **datos):
        recuerdo = {"texto": texto, **datos}
        self.recuerdos.append(recuerdo)
        return recuerdo


def observacion(
    agente="agente-demo",
    identificador="dispositivo-demo",
    mac="02:00:00:00:00:01",
    ip="192.0.2.10",
    puerto=22,
):
    return {
        "agente_id": agente,
        "red_id": "red-demo",
        "observado_en": "2026-11-22T10:30:00+00:00",
        "dispositivo": {
            "id_dispositivo": identificador,
            "hostname": "servidor-demo",
            "mac": mac,
            "ips": [ip],
            "sistema": "Linux",
        },
        "servicios": [
            {"puerto": puerto, "protocolo": "tcp", "nombre": "servicio-demo"}
        ],
    }


def test_analizar_observaciones_normaliza_y_rechaza():
    contexto = ContextoFalso()
    resultado = modulo.analizar_observaciones(
        contexto,
        observaciones=[
            observacion(ip="192.0.2.10"),
            {"agente_id": "incompleta"},
        ],
    )

    assert resultado["aceptadas"] == 1
    assert resultado["rechazadas"][0]["indice"] == 1
    assert resultado["observaciones"][0]["dispositivo"]["ips"] == ["192.0.2.10"]
    assert contexto.recuerdos == []


def test_analizar_observaciones_exige_zona_horaria():
    dato = observacion()
    dato["observado_en"] = "2026-11-22T10:30:00"

    resultado = modulo.analizar_observaciones(
        ContextoFalso(),
        observaciones=[dato],
    )

    assert resultado["aceptadas"] == 0
    assert "zona horaria" in resultado["rechazadas"][0]["motivo"]


def test_consolidar_usa_identificador_estable():
    contexto = ContextoFalso()
    primera = observacion(agente="agente-a", ip="192.0.2.10")
    segunda = observacion(agente="agente-b", ip="192.0.2.11")

    resultado = modulo.consolidar_servidores(
        contexto,
        observaciones=[primera, segunda],
    )

    assert resultado["cantidad"] == 1
    servidor = resultado["servidores"][0]
    assert servidor["confianza_identidad"] == "alta"
    assert servidor["ips"] == ["192.0.2.10", "192.0.2.11"]
    assert servidor["agentes"] == ["agente-a", "agente-b"]


def test_consolidar_no_fusiona_solo_por_hostname_o_ip():
    primera = observacion(identificador=None, mac=None)
    segunda = observacion(identificador=None, mac=None)

    resultado = modulo.consolidar_servidores(
        ContextoFalso(),
        observaciones=[primera, segunda],
    )

    assert resultado["cantidad"] == 2
    assert all(
        servidor["clave_correlacion"] is None
        for servidor in resultado["servidores"]
    )


def test_comparar_detecta_alta_baja_y_cambio():
    anterior = [
        observacion(identificador="equipo-a", ip="192.0.2.10", puerto=22),
        observacion(identificador="equipo-b", ip="192.0.2.20"),
    ]
    actual = [
        observacion(identificador="equipo-a", ip="192.0.2.11", puerto=443),
        observacion(identificador="equipo-c", ip="192.0.2.30"),
    ]

    resultado = modulo.comparar_observaciones(
        ContextoFalso(),
        anterior=anterior,
        actual=actual,
    )

    tipos = [evento["tipo"] for evento in resultado["eventos"]]
    assert tipos.count("alta") == 1
    assert tipos.count("baja") == 1
    assert tipos.count("cambio") == 1


def test_analizar_exposicion_no_afirma_vulnerabilidad():
    servidores = [{
        "clave_correlacion": "id:equipo-demo",
        "redes": ["red-demo"],
        "ips": ["192.0.2.10"],
        "servicios": [
            {"puerto": 23, "protocolo": "tcp", "nombre": "telnet"},
            {"puerto": 443, "protocolo": "tcp", "nombre": "https"},
        ],
    }]

    resultado = modulo.analizar_exposicion(
        ContextoFalso(),
        servidores=servidores,
    )

    assert resultado["cantidad"] == 1
    assert resultado["hallazgos"][0]["puerto"] == 23
    assert resultado["hallazgos"][0]["es_vulnerabilidad_confirmada"] is False


def test_recordar_cambios_entrega_recuerdos_al_core():
    contexto = ContextoFalso()
    eventos = [
        {
            "tipo": "alta",
            "clave_correlacion": "id:equipo-demo",
        },
        {
            "tipo": "cambio",
            "clave_correlacion": "id:equipo-demo",
            "cambios": [{"etiqueta": "servicios"}],
        },
        {"tipo": "sin_cambio"},
    ]

    resultado = modulo.recordar_cambios(contexto, eventos=eventos)

    assert resultado["recuerdos_creados"] == 2
    assert len(contexto.recuerdos) == 2
    assert all(r["sensibilidad"] == "normal" for r in contexto.recuerdos)
    assert all(r["identidades"] == [] for r in contexto.recuerdos)
    assert all(r["objetos"] == [] for r in contexto.recuerdos)
    assert all(r["opinion"] is None for r in contexto.recuerdos)


def test_recordar_cambios_respeta_limite():
    contexto = ContextoFalso()
    eventos = [
        {"tipo": "alta", "clave_correlacion": f"id:equipo-{n}"}
        for n in range(5)
    ]

    resultado = modulo.recordar_cambios(
        contexto,
        eventos=eventos,
        limite=2,
    )

    assert resultado["recuerdos_creados"] == 2
    assert len(contexto.recuerdos) == 2
