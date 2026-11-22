"""El nodo de casa: avisa al core que sigue vivo y le atiende trabajos con su Ollama (docs/adr/0017-programa-del-nodo.md).

    python -m ashur_nodo

Siempre llama al core; el core nunca lo llama (docs/REFERENCIA-ANTERIOR.md, punto 2).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

from ashur_nodo import ollama, politica, senales

LATIDO_S = 15  # el mismo del core: tres latidos perdidos lo dejan fuera de línea
SIN_TRABAJO_S = 2


class Core:
    def __init__(self, base: str, clave: str):
        self.base = base.rstrip("/")
        self.clave = clave

    def pedir(self, ruta: str, cuerpo: dict | None) -> tuple[int, dict | None]:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode() if cuerpo is not None else b""
        pedido = urllib.request.Request(
            self.base + ruta, data=datos, method="POST",
            headers={"Content-Type": "application/json", "X-Ashur-Clave-Nodo": self.clave},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=30) as respuesta:
                cuerpo = respuesta.read()
                return respuesta.status, json.loads(cuerpo) if cuerpo else None
        except urllib.error.HTTPError as e:
            return e.code, None


class Nodo:
    def __init__(self, core: Core, ollama_base: str, ofrecidos: list[str] | None, num_ctx: int, espera_s: float):
        self.core = core
        self.ollama = ollama_base
        self.ofrecidos = ofrecidos
        self.num_ctx = num_ctx
        self.espera_s = espera_s
        self.trabajando = threading.Event()
        self.carga_ajena: float | None = None
        self.modo_fijo = os.environ.get("ASHUR_MODO")  # para probar o forzar un modo

    def latido(self) -> dict:
        if not self.trabajando.is_set():  # entre trabajos, para no contar el propio modelo
            self.carga_ajena = senales.carga()
        modo = self.modo_fijo or politica.modo(senales.leer(self.carga_ajena))
        try:
            modelos = ollama.modelos(self.ollama, self.ofrecidos)
        except OSError:
            modelos, modo = [], "off"  # sin Ollama no hay nada que prestar
        estado, _ = self.core.pedir("/nodo/latido", {"modo": modo, "modelos": modelos})
        return {"estado": estado, "modo": modo, "modelos": [m["nombre"] for m in modelos]}

    def latir_siempre(self) -> None:
        """En su propio hilo: mientras el modelo piensa, el nodo sigue en línea."""
        while True:
            try:
                print("latido", self.latido(), flush=True)
            except OSError as e:
                print("latido sin core:", e, flush=True)
            time.sleep(LATIDO_S)

    def atender_uno(self) -> bool:
        estado, trabajo = self.core.pedir("/nodo/trabajos/tomar", None)
        if estado != 200 or not trabajo:
            return False
        self.trabajando.set()
        inicio = time.monotonic()
        try:
            if trabajo["necesidad"] == "conversar":
                resultado = {"salida": ollama.conversar(self.ollama, trabajo["modelo"], trabajo["entrada"], self.num_ctx, self.espera_s)}
            else:
                resultado = {"salida": ollama.vectores(self.ollama, trabajo["modelo"], trabajo["entrada"], self.espera_s)}
        except (OSError, ValueError, KeyError) as e:
            resultado = {"error": f"{type(e).__name__}: {e}"}
        finally:
            self.trabajando.clear()
        estado, _ = self.core.pedir(f"/nodo/trabajos/{trabajo['id']}", resultado)
        print(f"trabajo {trabajo['id']} con {trabajo['modelo']}: {time.monotonic() - inicio:.1f} s, core {estado}", flush=True)
        return True


def principal() -> None:
    faltan = [v for v in ("ASHUR_CORE", "ASHUR_CLAVE_NODO") if not os.environ.get(v)]
    if faltan:
        sys.exit(f"Faltan las variables {', '.join(faltan)}. Ver nodo/README.md.")
    ofrecidos = os.environ.get("ASHUR_MODELOS")
    nodo = Nodo(
        Core(os.environ["ASHUR_CORE"], os.environ["ASHUR_CLAVE_NODO"]),
        os.environ.get("ASHUR_OLLAMA", "http://127.0.0.1:11434"),
        [m.strip() for m in ofrecidos.split(",") if m.strip()] if ofrecidos else None,
        int(os.environ.get("ASHUR_NUM_CTX", "8192")),
        float(os.environ.get("ASHUR_ESPERA_S", "280")),  # menos que el plazo del core (300 s)
    )
    threading.Thread(target=nodo.latir_siempre, daemon=True).start()
    time.sleep(1)  # que el primer latido llegue antes de pedir trabajo
    while True:
        try:
            if not nodo.atender_uno():
                time.sleep(SIN_TRABAJO_S)
        except OSError as e:
            print("sin core:", e, flush=True)
            time.sleep(LATIDO_S)


if __name__ == "__main__":
    principal()
