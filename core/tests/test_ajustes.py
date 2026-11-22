import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ashur_core import modulos
from ashur_core.app import app

ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
QWEN3 = {"nombre": "qwen2.5:3b", "tamano": int(1.9 * GB), "capacidades": ["completion", "tools"]}
PLANTILLA = Path(__file__).resolve().parents[2] / "modules" / "_plantilla"

AJUSTES = [
    {"id": "direccion", "tipo": "texto", "descripcion": "Dirección del dispositivo.", "por_defecto": "192.168.1.10"},
    {"id": "clave", "tipo": "texto", "descripcion": "Clave del dispositivo.", "secreto": True},
    {"id": "intervalo", "tipo": "numero", "descripcion": "Segundos entre lecturas.", "por_defecto": 60},
    {"id": "activo", "tipo": "booleano", "descripcion": "Si lee o no.", "por_defecto": True},
]


def escribir_modulo(carpeta: Path, id_: str, ajustes: list[dict] | None, codigo: str) -> None:
    (carpeta / id_).mkdir(parents=True)
    manifiesto = {"id": id_, "nombre": id_.title(), "version": "0.1.0", "descripcion": "De prueba.",
                  "acciones": [{"id": "leer", "descripcion": "Lee.", "escribe": False}]}
    if ajustes is not None:
        manifiesto["ajustes"] = ajustes
    (carpeta / id_ / "modulo.json").write_text(json.dumps(manifiesto), encoding="utf-8")
    (carpeta / id_ / "modulo.py").write_text(codigo, encoding="utf-8")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    carpeta = tmp_path / "modules"
    carpeta.mkdir()
    escribir_modulo(carpeta, "sensor", AJUSTES,
                    "def leer(contexto):\n    return {'direccion': contexto.ajuste('direccion'),"
                    " 'clave': contexto.ajuste('clave'), 'otro': contexto.ajuste('no_existe')}\n")
    escribir_modulo(carpeta, "viejo", None, "def leer(contexto):\n    return {}\n")
    escribir_modulo(carpeta, "malo", [{"id": "n", "tipo": "numero", "descripcion": "x", "por_defecto": "diez"}],
                    "def leer(contexto):\n    return {}\n")
    monkeypatch.setenv("ASHUR_MODULOS", str(carpeta))
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


# ── Módulos ──


def test_los_ajustes_son_opcionales_y_se_validan_al_cargar(cliente):
    estados = {e["id"]: e for e in cliente.get("/modulos").json()}
    assert estados["viejo"]["error"] is None and estados["viejo"]["manifiesto"]["ajustes"] == []
    assert estados["sensor"]["error"] is None
    assert "no es de tipo numero" in estados["malo"]["error"]
    assert modulos.cargar_uno(PLANTILLA).manifiesto.ajustes  # la plantilla trae un ejemplo


def test_ver_y_cambiar_los_ajustes_de_un_modulo(cliente):
    ajustes = {a["id"]: a for a in cliente.get("/modulos/sensor/ajustes").json()}
    assert ajustes["direccion"]["valor"] == "192.168.1.10" and ajustes["direccion"]["configurado"]
    assert ajustes["clave"] == {"id": "clave", "tipo": "texto", "descripcion": "Clave del dispositivo.", "secreto": True,
                                "por_defecto": None, "valor": None, "configurado": False}

    assert cliente.patch("/modulos/sensor/ajustes", json={"direccion": "10.0.0.5"}).status_code == 401  # pide admin
    cambiados = cliente.patch("/modulos/sensor/ajustes", json={"direccion": "10.0.0.5", "clave": "s3creta"}, headers=ADMIN)
    ajustes = {a["id"]: a for a in cambiados.json()}
    assert ajustes["direccion"]["valor"] == "10.0.0.5"
    assert ajustes["clave"]["valor"] is None and ajustes["clave"]["configurado"]  # el secreto nunca vuelve
    assert "s3creta" not in cliente.get("/modulos/sensor/ajustes").text

    # El módulo lee lo que puso Sergio, y el secreto también.
    resultado = cliente.post("/modulos/sensor/acciones/leer").json()["resultado"]
    assert resultado == {"direccion": "10.0.0.5", "clave": "s3creta", "otro": None}

    # null vuelve al por_defecto.
    cliente.patch("/modulos/sensor/ajustes", json={"direccion": None}, headers=ADMIN)
    assert cliente.post("/modulos/sensor/acciones/leer").json()["resultado"]["direccion"] == "192.168.1.10"


@pytest.mark.parametrize(
    "cambio", [{"intervalo": "sesenta"}, {"activo": 1}, {"intervalo": True}, {"direccion": ""}, {"no_existe": 1}],
    ids=["numero-con-texto", "booleano-con-numero", "numero-con-booleano", "texto-vacio", "ajuste-desconocido"],
)
def test_un_ajuste_del_tipo_equivocado_se_rechaza_sin_cambiar_nada(cliente, cambio):
    respuesta = cliente.patch("/modulos/sensor/ajustes", json={"direccion": "10.0.0.5", **cambio}, headers=ADMIN)
    assert respuesta.status_code == 422
    ajustes = {a["id"]: a for a in cliente.get("/modulos/sensor/ajustes").json()}
    assert ajustes["direccion"]["valor"] == "192.168.1.10"  # nada a medias


def test_un_modulo_que_no_existe_da_404(cliente):
    assert cliente.get("/modulos/nada/ajustes").status_code == 404
    assert cliente.patch("/modulos/nada/ajustes", json={}, headers=ADMIN).status_code == 404


# ── Nodos ──


def test_los_ajustes_de_un_nodo_viajan_en_su_latido_y_el_core_los_hace_cumplir(cliente):
    creado = cliente.post("/nodos", json={"nombre": "windows"}, headers=ADMIN).json()
    id_, nodo = creado["nodo"]["id"], {"X-Ashur-Clave-Nodo": creado["clave"]}
    assert creado["nodo"]["ajustes"] == {"modelos_ofrecidos": None, "num_ctx": None, "horario": None}

    cambios = {"modelos_ofrecidos": ["qwen2.5:3b"], "num_ctx": 4096, "horario": {"desde": "22:00", "hasta": "07:00"}}
    assert cliente.patch(f"/nodos/{id_}", json=cambios).status_code == 401  # pide admin
    assert cliente.patch(f"/nodos/{id_}", json=cambios, headers=ADMIN).json()["ajustes"] == cambios

    latido = cliente.post("/nodo/latido", json={"modo": "full", "modelos": [QWEN7, QWEN3]}, headers=nodo).json()
    assert latido["ajustes"] == cambios  # el nodo se entera en la respuesta
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    assert cliente.post("/nodo/trabajos/tomar", headers=nodo).json()["modelo"] == "qwen2.5:3b"  # aunque tenga el 7B

    # null vuelve a lo que el nodo decida; los demás ajustes no se tocan.
    ajustes = cliente.patch(f"/nodos/{id_}", json={"modelos_ofrecidos": None}, headers=ADMIN).json()["ajustes"]
    assert ajustes == {**cambios, "modelos_ofrecidos": None}


@pytest.mark.parametrize(
    "cambio", [{"archivado": None}, {"num_ctx": 100}, {"horario": {"desde": "25:00", "hasta": "07:00"}}, {"otro": 1}],
    ids=["archivado-null", "contexto-chico", "hora-invalida", "campo-extra"],
)
def test_ajustes_de_nodo_invalidos(cliente, cambio):
    id_ = cliente.post("/nodos", json={"nombre": "x"}, headers=ADMIN).json()["nodo"]["id"]
    assert cliente.patch(f"/nodos/{id_}", json=cambio, headers=ADMIN).status_code == 422
