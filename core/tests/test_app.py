from fastapi.testclient import TestClient

from ashur_core.app import app


def test_vivo():
    respuesta = TestClient(app).get("/vivo")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"vivo": True}
