import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from ashur_core.app import app


class _OllamaFalso(BaseHTTPRequestHandler):
    recibido: list = []

    def do_POST(self):
        datos = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _OllamaFalso.recibido.append(datos)
        ultimo = datos["messages"][-1]["content"]
        cuerpo = json.dumps({"message": {"role": "assistant", "content": f"Te escuché: {ultimo}"}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


@pytest.fixture
def ollama():
    servidor = HTTPServer(("127.0.0.1", 0), _OllamaFalso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    _OllamaFalso.recibido = []
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.delenv("ASHUR_OLLAMA_URL", raising=False)
    monkeypatch.delenv("ASHUR_OLLAMA_MODELO", raising=False)
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def test_ashur_responde_con_el_nodo_de_casa_y_guarda_el_historial(cliente, ollama, monkeypatch):
    monkeypatch.setenv("ASHUR_OLLAMA_URL", ollama)
    monkeypatch.setenv("ASHUR_OLLAMA_MODELO", "modelo-de-prueba")
    r = cliente.post("/chat", json={"texto": "Hola"})
    assert r.status_code == 200
    assert [(m["autor"], m["texto"]) for m in r.json()] == [("sergio", "Hola"), ("ashur", "Te escuché: Hola")]
    cliente.post("/chat", json={"texto": "¿Me recuerdas?"})
    # El modelo recibe la persona y todo el historial.
    enviados = _OllamaFalso.recibido[-1]["messages"]
    assert enviados[0]["role"] == "system" and [m["content"] for m in enviados[1:]] == [
        "Hola", "Te escuché: Hola", "¿Me recuerdas?",
    ]
    assert _OllamaFalso.recibido[-1]["model"] == "modelo-de-prueba"
    assert len(cliente.get("/chat").json()) == 4


def test_sin_modelo_el_mensaje_se_guarda_y_responde_503(cliente):
    assert cliente.post("/chat", json={"texto": "Hola"}).status_code == 503
    assert [m["autor"] for m in cliente.get("/chat").json()] == ["sergio"]


def test_si_el_nodo_no_responde_es_503(cliente, monkeypatch):
    monkeypatch.setenv("ASHUR_OLLAMA_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("ASHUR_OLLAMA_MODELO", "x")
    r = cliente.post("/chat", json={"texto": "Hola"})
    assert r.status_code == 503 and "nodo de casa" in r.json()["detail"]


def test_el_chat_pide_la_clave(cliente):
    assert TestClient(app).get("/chat").status_code == 401
