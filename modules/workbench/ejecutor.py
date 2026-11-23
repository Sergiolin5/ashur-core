"""Ejecutor de Workbench: corre en un equipo de Sergio (por ejemplo su Mac), le pide tareas al core y las resuelve con
el programa oficial de cada familia, ya con su sesión iniciada. Ashur nunca ve esas credenciales.

    ASHUR_CORE=http://servidor:8720 ASHUR_CLAVE=... python3 modules/workbench/ejecutor.py

Variables:
- ASHUR_CORE: dirección del core. Obligatoria.
- ASHUR_CLAVE: la clave normal del core (no la de administrador). Obligatoria.
- ASHUR_EQUIPO: nombre con el que aparece este equipo en Workbench. Por defecto, el nombre de la máquina.
- ASHUR_EJECUTOR_FAMILIAS: familias que atiende, separadas por comas. Por defecto, solo claude_code.

Es el equipo el que llama al core, nunca al revés: no hay que abrirle puertos ni saber su dirección. Si el equipo se
apaga, las tareas esperan; una tarea tomada y no entregada se vuelve a ofrecer (PLAZO_EQUIPO_S en modulo.py).

Solo usa la biblioteca estándar de Python, desde la versión 3.9 (la que trae macOS).
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# Por familia: el programa y sus argumentos. El encargo siempre entra por la entrada estándar.
# claude: sin herramientas y sin servidores MCP, así solo devuelve texto y no toca el equipo.
# codex y gemini quedan listos, pero sin probar: no estaban instalados cuando se escribió esto.
PROGRAMAS = {
    "claude_code": ["claude", "-p", "--output-format", "json", "--tools", "", "--strict-mcp-config",
                    "--no-session-persistence"],
    "codex": ["codex", "exec", "--skip-git-repo-check", "-"],
    "gemini_cli": ["gemini", "-p", ""],
}

PAUSA_S = 10
LIMITE_TAREA_S = 30 * 60


def comando(familia: str, modelo: str | None) -> list[str]:
    """El comando para una familia. El modelo del proveedor, si lo dice, se pasa con --model."""
    partes = list(PROGRAMAS[familia])
    if modelo:
        partes += ["--model", modelo]
    return partes


def leer_respuesta(familia: str, salida: str) -> str:
    """El texto de la respuesta. claude devuelve JSON con `result`; lanza RuntimeError si vino un error."""
    if familia != "claude_code":
        return salida.strip()
    try:
        datos = json.loads(salida)
    except ValueError:
        raise RuntimeError(f"claude no devolvió JSON: {salida[:300]}") from None
    if datos.get("is_error"):
        raise RuntimeError(str(datos.get("result") or datos.get("subtype") or "claude devolvió un error"))
    return str(datos.get("result") or "").strip()


def resolver(familia: str, modelo: str | None, encargo: str) -> str:
    """Corre el programa en una carpeta vacía y devuelve su respuesta. Lanza RuntimeError con el motivo si falla."""
    with tempfile.TemporaryDirectory(prefix="ashur-workbench-") as carpeta:
        try:
            proceso = subprocess.run(
                comando(familia, modelo), input=encargo, capture_output=True, text=True, cwd=carpeta,
                timeout=LIMITE_TAREA_S,
            )
        except FileNotFoundError:
            raise RuntimeError(f"Este equipo no tiene instalado {PROGRAMAS[familia][0]}.") from None
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{PROGRAMAS[familia][0]} tardó más de {LIMITE_TAREA_S // 60} minutos.") from None
    if proceso.returncode != 0 and not proceso.stdout.strip():
        raise RuntimeError(f"{PROGRAMAS[familia][0]} terminó con error: {proceso.stderr.strip()[-500:]}")
    respuesta = leer_respuesta(familia, proceso.stdout)
    if not respuesta:
        raise RuntimeError(f"{PROGRAMAS[familia][0]} no devolvió texto. {proceso.stderr.strip()[-300:]}")
    return respuesta


def accion(core: str, clave: str, nombre: str, parametros: dict) -> dict:
    """Corre una acción del módulo workbench en el core y devuelve su resultado."""
    pedido = urllib.request.Request(
        f"{core.rstrip('/')}/modulos/workbench/acciones/{nombre}",
        data=json.dumps(parametros).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Ashur-Clave": clave},
    )
    with urllib.request.urlopen(pedido, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))["resultado"]


def atender_una(core: str, clave: str, equipo: str, familias: list[str], resolver_=resolver, accion_=accion) -> bool:
    """Pide una tarea y, si hay, la resuelve y la entrega. Devuelve si hubo tarea."""
    tarea = accion_(core, clave, "tomar_tarea", {"equipo": equipo, "familias": familias})["tarea"]
    if tarea is None:
        return False
    entrega = {"id": tarea["id"], "equipo": equipo}
    try:
        entrega["resultado"] = resolver_(tarea["familia"], tarea.get("modelo"), tarea["encargo"])
        entrega["modelo"] = tarea.get("modelo") or PROGRAMAS[tarea["familia"]][0]
    except RuntimeError as e:
        entrega["error"] = str(e)
    accion_(core, clave, "entregar_tarea", entrega)
    return True


def main() -> int:
    core, clave = os.environ.get("ASHUR_CORE"), os.environ.get("ASHUR_CLAVE")
    if not core or not clave:
        print("Faltan ASHUR_CORE y ASHUR_CLAVE.", file=sys.stderr)
        return 2
    equipo = os.environ.get("ASHUR_EQUIPO") or socket.gethostname().split(".")[0]
    pedidas = [f.strip() for f in os.environ.get("ASHUR_EJECUTOR_FAMILIAS", "claude_code").split(",") if f.strip()]
    familias = [f for f in pedidas if f in PROGRAMAS and shutil.which(PROGRAMAS[f][0])]
    for f in pedidas:
        if f not in familias:
            print(f"No atiendo {f}: no existe esa familia o falta su programa en este equipo.", file=sys.stderr)
    if not familias:
        return 2
    print(f"{equipo} atiende {', '.join(familias)} para {core}. Ctrl+C para salir.")
    while True:
        try:
            if atender_una(core, clave, equipo, familias):
                print(time.strftime("%H:%M:%S"), "tarea entregada")
                continue  # puede haber otra esperando
        except urllib.error.HTTPError as e:
            print(time.strftime("%H:%M:%S"), f"el core respondió HTTP {e.code}", file=sys.stderr)
        except OSError as e:  # sin red o core apagado: se reintenta
            print(time.strftime("%H:%M:%S"), f"sin core: {getattr(e, 'reason', e)}", file=sys.stderr)
        except KeyboardInterrupt:
            return 0
        try:
            time.sleep(PAUSA_S)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
