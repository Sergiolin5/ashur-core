import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ashur_core import modulos
from ashur_core.app import app

PLANTILLA = Path(__file__).resolve().parents[2] / "modules" / "_plantilla"
ADMIN = {"X-Ashur-Clave-Admin": "a"}


def escribir_modulo(carpeta: Path, id_: str, acciones: list[dict], codigo: str) -> None:
    (carpeta / id_).mkdir(parents=True)
    manifiesto = {"id": id_, "nombre": id_.title(), "version": "0.1.0", "descripcion": "De prueba.", "acciones": acciones}
    (carpeta / id_ / "modulo.json").write_text(json.dumps(manifiesto), encoding="utf-8")
    (carpeta / id_ / "modulo.py").write_text(codigo, encoding="utf-8")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    carpeta = tmp_path / "modules"
    carpeta.mkdir()
    escribir_modulo(
        carpeta, "eco",
        [{"id": "repetir", "descripcion": "Lee.", "escribe": False},
         {"id": "enviar", "descripcion": "Escribe.", "escribe": True},
         {"id": "romper", "descripcion": "Falla.", "escribe": False}],
        "def repetir(contexto, texto='x'):\n    contexto.recordar('eco: ' + texto)\n    return {'texto': texto}\n"
        "def enviar(contexto, a=''):\n    return {'enviado_a': a}\n"
        "def romper(contexto):\n    raise RuntimeError('se rompió')\n",
    )
    escribir_modulo(carpeta, "roto", [{"id": "falta", "descripcion": "x", "escribe": False}], "")
    shutil.copytree(PLANTILLA, carpeta / "_plantilla")  # empieza con _: no se registra
    monkeypatch.setenv("ASHUR_MODULOS", str(carpeta))
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def test_la_plantilla_cumple_el_contrato_y_su_accion_corre():
    modulo = modulos.cargar_uno(PLANTILLA)
    guardados = []
    por_defecto = {a.id: a.por_defecto for a in modulo.manifiesto.ajustes}
    contexto = modulos.Contexto("plantilla", lambda r: guardados.append(r) or r, por_defecto.get)
    assert modulos.ejecutar(modulo, "saludar", {"nombre": "Ana"}, contexto) == {"saludo": "Hola, Ana."}
    assert guardados[0]["origen"] == "plantilla"


def test_lista_los_modulos_y_muestra_el_error_de_un_modulo_roto(cliente):
    estados = {e["id"]: e for e in cliente.get("/modulos").json()}
    assert set(estados) == {"eco", "roto"}
    assert estados["eco"]["error"] is None
    assert "falta()" in estados["roto"]["error"]
    assert TestClient(app).get("/modulos").status_code == 401


def test_una_accion_que_lee_corre_y_guarda_su_recuerdo(cliente):
    r = cliente.post("/modulos/eco/acciones/repetir", json={"texto": "hola"})
    assert r.status_code == 200 and r.json() == {"resultado": {"texto": "hola"}}
    [recuerdo] = cliente.get("/recuerdos").json()
    assert recuerdo["origen"] == "eco" and recuerdo["texto"] == "eco: hola"
    planeta = next(c for c in cliente.get("/galaxia").json()["cuerpos"] if c["id"] == "modulo-eco")
    assert planeta["ref"] == {"tipo": "modulo", "id": "eco"} and planeta["masa"] == 2
    assert cliente.post("/modulos/eco/acciones/nada").status_code == 404
    assert cliente.post("/modulos/nadie/acciones/repetir").status_code == 404


def test_si_el_modulo_falla_responde_502(cliente):
    r = cliente.post("/modulos/eco/acciones/romper")
    assert r.status_code == 502 and "se rompió" in r.json()["detail"]


def test_una_accion_que_escribe_espera_aprobacion_y_corre_una_sola_vez(cliente):
    r = cliente.post("/modulos/eco/acciones/enviar", json={"a": "Bruno"})
    assert r.status_code == 202 and r.json()["estado"] == "pendiente"
    id_ = r.json()["id"]
    assert [p["id"] for p in cliente.get("/pedidos", params={"estado": "pendiente"}).json()] == [id_]
    assert cliente.post(f"/pedidos/{id_}/aprobar").status_code == 401  # pide la clave de administrador
    hecho = cliente.post(f"/pedidos/{id_}/aprobar", headers=ADMIN)
    assert hecho.status_code == 200 and hecho.json()["estado"] == "hecho"
    assert hecho.json()["resultado"] == {"enviado_a": "Bruno"}
    assert cliente.post(f"/pedidos/{id_}/aprobar", headers=ADMIN).status_code == 409  # no corre dos veces

    otro = cliente.post("/modulos/eco/acciones/enviar", json={"a": "Ana"}).json()["id"]
    assert cliente.post(f"/pedidos/{otro}/rechazar", headers=ADMIN).json()["estado"] == "rechazado"
    assert cliente.post(f"/pedidos/{otro}/aprobar", headers=ADMIN).status_code == 409
    assert cliente.post("/pedidos/99/aprobar", headers=ADMIN).status_code == 404


def test_un_manifiesto_con_id_distinto_a_la_carpeta_no_se_registra(tmp_path):
    escribir_modulo(tmp_path, "uno", [], "")
    (tmp_path / "uno" / "modulo.json").write_text(
        json.dumps({"id": "otro", "nombre": "x", "version": "1", "descripcion": "x", "acciones": []}), encoding="utf-8"
    )
    registro = modulos.descubrir(tmp_path)
    assert "uno" in registro.errores and "nombre de la carpeta" in registro.errores["uno"]


def test_carga_un_modulo_con_dataclass_y_anotaciones_diferidas(tmp_path):
    escribir_modulo(
        tmp_path, "dc", [{"id": "a", "descripcion": "x", "escribe": False}],
        "from __future__ import annotations\nfrom dataclasses import dataclass\n\n@dataclass\nclass P:\n    x: int\n\n"
        "def a(contexto):\n    return {'x': P(1).x}\n",
    )
    registro = modulos.descubrir(tmp_path)
    assert registro.errores == {}
    assert modulos.ejecutar(registro.modulos["dc"], "a", {}, modulos.Contexto("dc", lambda r: r)) == {"x": 1}


def test_un_modulo_guarda_sus_datos_propios_y_no_ve_los_de_otro(tmp_path):
    from ashur_core import memoria

    con = memoria.abrir(str(tmp_path / "ashur.db"))
    datos = modulos.Datos(con, "uno")
    nuevo = datos.guardar("tareas", {"titulo": "Probar", "id": "ignorado"})
    assert nuevo["titulo"] == "Probar" and nuevo["id"] != "ignorado" and nuevo["creado"] == nuevo["actualizado"]
    cambiado = datos.guardar("tareas", {"titulo": "Otra"}, nuevo["id"])
    assert cambiado["titulo"] == "Otra" and cambiado["creado"] == nuevo["creado"]
    assert [r["id"] for r in datos.listar("tareas")] == [nuevo["id"]]
    assert datos.listar("proyectos") == []

    otro = modulos.Datos(con, "dos")
    assert otro.listar("tareas") == [] and otro.leer("tareas", nuevo["id"]) is None
    assert otro.borrar("tareas", nuevo["id"]) is False
    with pytest.raises(KeyError):
        otro.guardar("tareas", {"titulo": "x"}, nuevo["id"])

    assert datos.borrar("tareas", nuevo["id"]) is True and datos.leer("tareas", nuevo["id"]) is None


def test_una_accion_usa_contexto_datos_desde_la_api(tmp_path, monkeypatch):
    carpeta = tmp_path / "modules"
    escribir_modulo(
        carpeta, "notas", [{"id": "anotar", "descripcion": "Guarda una nota propia.", "escribe": False}],
        "def anotar(contexto, texto=''):\n"
        "    contexto.datos.guardar('notas', {'texto': texto})\n"
        "    return {'notas': [n['texto'] for n in contexto.datos.listar('notas')]}\n",
    )
    monkeypatch.setenv("ASHUR_MODULOS", str(carpeta))
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    cliente = TestClient(app, headers={"X-Ashur-Clave": "c"})
    assert cliente.post("/modulos/notas/acciones/anotar", json={"texto": "a"}).json() == {"resultado": {"notas": ["a"]}}
    assert cliente.post("/modulos/notas/acciones/anotar", json={"texto": "b"}).json() == {"resultado": {"notas": ["b", "a"]}}
    assert cliente.get("/recuerdos").json() == []  # los datos propios no son recuerdos


def test_una_base_del_esquema_15_gana_la_tabla_de_datos(tmp_path):
    from ashur_core import memoria
    from bases import quitar_desde

    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    quitar_desde(con, 16)
    con.execute("PRAGMA user_version = 15")
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA
    assert modulos.Datos(con, "uno").listar("x") == []
