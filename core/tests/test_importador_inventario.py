import json

import pytest

from ashur_core import importador_inventario


def lote_de_prueba():
    return {
        "items": [
            {
                "id": "lote-raiz",
                "name": "equipo inventado",
                "slots": ["pci-1"],
                "identifiers": {"serial": "SERIAL-FALSO"},
                "specs": {"ram_gb": 16},
                "evidence": {"source_files": ["foto-falsa.jpg"], "confidence": {"model": "inferido"}},
            },
            {
                "id": "lote-hijo",
                "name": "placa inventada",
                "place": "lugar-falso",
                "parent_id": "lote-raiz",
                "slot": "pci-1",
                "slots": [],
                "identifiers": {"model": "MODELO-FALSO"},
                "specs": {"cores": 8},
                "evidence": {"source_files": ["video-falso.mov"], "confidence": {"model": "visto"}},
                "status": "Estado inventado sin confirmar",
            },
        ],
        "shipments": [{"id": "envio-falso"}],
    }


def test_simulacion_ordena_padres_antes_de_hijos_y_no_escribe(tmp_path, monkeypatch):
    ruta = tmp_path / "lote.json"
    ruta.write_text(json.dumps(lote_de_prueba()), encoding="utf-8")
    monkeypatch.setattr(importador_inventario, "_solicitar", lambda *args, **kwargs: pytest.fail("simulación hizo una petición"))

    resultado = importador_inventario.simular(ruta)

    assert resultado["orden"] == ["lote-raiz", "lote-hijo"]
    assert (resultado["objetos"], resultado["raices"], resultado["con_padre"]) == (2, 1, 1)
    assert (resultado["envios_importados"], resultado["evidencias_cambiadas"], resultado["estados_cambiados"]) == (
        0, 0, 0
    )


@pytest.mark.parametrize(
    "cambio",
    [
        lambda l: l["items"][0].update(slots=[]),
        lambda l: l["items"][0].update(parent_id="lote-hijo", slot="pci-1"),
        lambda l: l["items"][1].update(parent_id="desconocido"),
    ],
    ids=["ranura-fuera-del-padre", "ciclo", "padre-inexistente"],
)
def test_simulacion_rechaza_jerarquia_invalida(tmp_path, cambio):
    lote = lote_de_prueba()
    cambio(lote)
    ruta = tmp_path / "lote.json"
    ruta.write_text(json.dumps(lote), encoding="utf-8")

    with pytest.raises(ValueError):
        importador_inventario.simular(ruta)


def test_importacion_envia_evidencia_estado_y_relacion_sin_cambiarlos(tmp_path, monkeypatch):
    lote = lote_de_prueba()
    ruta = tmp_path / "lote.json"
    ruta.write_text(json.dumps(lote), encoding="utf-8")
    llamadas = []

    def responder(metodo, url, payload, encabezados):
        llamadas.append((metodo, url, payload, encabezados))
        if metodo == "POST":
            return {"id": "obj-1" if payload["nombre"] == "equipo inventado" else "obj-2"}
        return {"id": "obj-2"}

    monkeypatch.setattr(importador_inventario, "_solicitar", responder)
    mapa = importador_inventario.importar(ruta, "http://core.test", "clave", "admin")

    assert mapa == {"lote-raiz": "obj-1", "lote-hijo": "obj-2"}
    assert [llamada[0] for llamada in llamadas] == ["POST", "POST", "PATCH"]
    assert llamadas[1][2]["evidencia"] == lote["items"][1]["evidence"]
    assert llamadas[1][2]["estado"] == lote["items"][1]["status"]
    assert llamadas[1][2]["lugar"] is None
    assert llamadas[2][2] == {"padre_id": "obj-1", "ranura": "pci-1"}
    assert llamadas[0][3] == {"X-Ashur-Clave": "clave"}
    assert llamadas[2][3] == {"X-Ashur-Clave-Admin": "admin"}
    correspondencia = json.loads((tmp_path / "lote_correspondencia.json").read_text(encoding="utf-8"))
    assert correspondencia == [{"id_lote": "lote-raiz", "obj_id": "obj-1"}, {"id_lote": "lote-hijo", "obj_id": "obj-2"}]
