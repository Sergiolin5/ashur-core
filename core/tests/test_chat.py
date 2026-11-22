import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from ashur_core.app import app

ADMIN = {"X-Ashur-Clave-Admin": "a"}


def nodo_falso(prefijo: str, clave: str | None = None):
    """Un servidor compatible con OpenAI que contesta '<prefijo>: <último mensaje>'."""
    recibidos = []

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self):
            datos = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            recibidos.append((self.path, self.headers.get("Authorization"), datos))
            if clave and self.headers.get("Authorization") != f"Bearer {clave}":
                self.send_response(401)
                self.end_headers()
                return
            cuerpo = json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": f"{prefijo}: {datos['messages'][-1]['content']}"}}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *args):
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Manejador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_port}", recibidos


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def test_ashur_responde_con_el_nodo_y_guarda_el_historial(cliente):
    servidor, url, recibidos = nodo_falso("zima", clave="secreta")
    try:
        nodo = cliente.post("/nodos", json={"nombre": "Zima", "url": url + "/", "modelo": "m", "clave": "secreta"},
                            headers=ADMIN)
        assert nodo.status_code == 201 and nodo.json()["tiene_clave"] is True and "clave" not in nodo.json()
        r = cliente.post("/chat", json={"texto": "Hola"})
        assert [(m["autor"], m["texto"]) for m in r.json()] == [("sergio", "Hola"), ("ashur", "zima: Hola")]
        ruta, autorizacion, datos = recibidos[-1]
        assert ruta == "/v1/chat/completions" and autorizacion == "Bearer secreta"
        assert datos["messages"][0]["role"] == "system" and datos["model"] == "m"
        assert len(cliente.get("/chat").json()) == 2
    finally:
        servidor.shutdown()


def test_si_el_nodo_de_casa_no_responde_usa_el_siguiente_nivel(cliente):
    servidor, url, _ = nodo_falso("telefono")
    try:
        cliente.post("/nodos", json={"nombre": "Caído", "url": "http://127.0.0.1:9", "modelo": "m", "nivel": 1}, headers=ADMIN)
        cliente.post("/nodos", json={"nombre": "Teléfono", "url": url, "modelo": "m", "nivel": 2}, headers=ADMIN)
        r = cliente.post("/chat", json={"texto": "Hola"})
        assert r.status_code == 200 and r.json()[1]["texto"] == "telefono: Hola"
        # Un nodo desactivado no se usa.
        cliente.patch("/nodos/2", json={"activo": False}, headers=ADMIN)
        assert cliente.post("/chat", json={"texto": "Otra"}).status_code == 503
    finally:
        servidor.shutdown()


def test_sin_nodos_el_mensaje_se_guarda_y_responde_503(cliente):
    r = cliente.post("/chat", json={"texto": "Hola"})
    assert r.status_code == 503 and "No hay nodos" in r.json()["detail"]
    assert [m["autor"] for m in cliente.get("/chat").json()] == ["sergio"]


def test_los_nodos_se_configuran_con_la_clave_de_administrador(cliente):
    datos = {"nombre": "Zima", "url": "http://x", "modelo": "m"}
    assert cliente.post("/nodos", json=datos).status_code == 401
    assert cliente.post("/nodos", json=datos | {"nivel": 4}, headers=ADMIN).status_code == 422
    assert cliente.patch("/nodos/9", json={"activo": False}, headers=ADMIN).status_code == 404
    assert TestClient(app).get("/chat").status_code == 401
