"""Lo que el nodo le pide a su Ollama, que escucha solo en el propio equipo."""

from __future__ import annotations

import json
import urllib.request


def _pedir(base: str, ruta: str, cuerpo: dict | None, espera_s: float) -> dict:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(base + ruta, data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=espera_s) as respuesta:
        return json.loads(respuesta.read())


def modelos_de(etiquetas: dict, ofrecidos: list[str] | None) -> list[dict]:
    """Los modelos de GET /api/tags en el formato del protocolo (contracts/nodo.schema.json). Con [ofrecidos], solo
    esos: Sergio elige qué presta cada equipo."""
    modelos = []
    for m in etiquetas.get("models") or []:
        if not isinstance(m, dict) or not isinstance(m.get("name"), str):
            continue  # una entrada rara no deja al nodo sin latido
        if ofrecidos is not None and m["name"] not in ofrecidos:
            continue
        familias = (m.get("details") or {}).get("families") or []
        capacidades = m.get("capabilities") or (["embedding"] if "bert" in familias else ["completion"])
        modelos.append({"nombre": m["name"], "tamano": int(m.get("size", 0)), "capacidades": list(capacidades)})
    return modelos


def modelos(base: str, ofrecidos: list[str] | None) -> list[dict]:
    return modelos_de(_pedir(base, "/api/tags", None, 10), ofrecidos)


def vectores(base: str, modelo: str, entrada: dict, espera_s: float) -> dict:
    """Los embeddings de cada texto de la entrada, como salida del protocolo: {"vectores": [[...], ...]}."""
    respuesta = _pedir(base, "/api/embed", {"model": modelo, "input": entrada["input"]}, espera_s)
    lista = respuesta.get("embeddings") or []
    if len(lista) != len(entrada["input"]):
        raise ValueError(f"{modelo} devolvió {len(lista)} vectores para {len(entrada['input'])} textos.")
    return {"vectores": lista}


def conversar(base: str, modelo: str, entrada: dict, num_ctx: int, espera_s: float) -> dict:
    """El pedido del core a /api/chat, y su respuesta como salida del protocolo: {"mensaje": {...}}."""
    pedido = {"model": modelo, "messages": entrada["messages"], "stream": False, "options": {"num_ctx": num_ctx}}
    if entrada.get("tools"):
        pedido["tools"] = entrada["tools"]  # las corre el core; el modelo solo las pide (ADR 0021)
    mensaje = _pedir(base, "/api/chat", pedido, espera_s).get("message") or {}
    if not isinstance(mensaje, dict):
        raise ValueError(f"{modelo} devolvió un mensaje que no es un objeto.")
    contenido = mensaje.get("content") or ""
    llamadas = mensaje.get("tool_calls") or []
    if not isinstance(contenido, str) or not isinstance(llamadas, list):
        raise ValueError(f"{modelo} devolvió un mensaje con un formato que el nodo no conoce.")
    if not contenido.strip() and not llamadas:
        # Como error, el core lo reintenta; una salida vacía la rechazaría y el trabajo quedaría tomado hasta vencer.
        raise ValueError(f"{modelo} devolvió una respuesta vacía.")
    salida = {"role": "assistant", "content": contenido}
    if llamadas:
        salida["tool_calls"] = llamadas
    return {"mensaje": salida}
