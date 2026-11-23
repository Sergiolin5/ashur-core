"""Workbench: centro de desarrollo. Guarda proyectos, proveedores, tareas, entregas y servidores como datos propios
(docs/adr/0029-datos-propios-de-los-modulos.md), reparte la cola y manda las tareas al modelo de cada proveedor.

Las llamadas a las APIs de los modelos van con urllib: el core no tiene aprobado ningún paquete de esos proveedores.
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

TIPOS = {
    "proyectos": {"obligatorio": "nombre", "por_defecto": {"estado": "activo", "plataformas": []}},
    "proveedores": {
        "obligatorio": "nombre",
        "por_defecto": {"familia": "propio", "plan": "libre", "cuota": 100, "usadas": 0, "estado": "activo",
                        "fortalezas": []},
    },
    "tareas": {
        "obligatorio": "titulo",
        "por_defecto": {"tipo": "funcion", "prioridad": "media", "estado": "cola", "ejecuciones": 0,
                        "proyecto_id": None, "proveedor_id": None},
    },
    "entregas": {
        "obligatorio": "version",
        "por_defecto": {"canal": "interno", "estado": "borrador", "guardada": False, "compilada": False,
                        "firmada": False, "publicada": False, "proyecto_id": None},
    },
    "servidores": {
        "obligatorio": "nombre",
        "por_defecto": {"ruta_salud": "/", "servicios": [], "estado": "sin_probar"},
    },
    # Los equipos que corren ejecutor.py. Se anotan solos al pedir trabajo.
    "equipos": {"obligatorio": "nombre", "por_defecto": {"familias": []}},
}

# Familias que no se llaman por API: las resuelve un equipo de Sergio con el programa oficial de cada una, ya con su
# sesión iniciada (ejecutor.py). Ashur nunca ve esas credenciales.
FAMILIAS_DE_EQUIPO = ("claude_code", "codex", "gemini_cli")

# Si un equipo toma una tarea y no la entrega en este tiempo, se le ofrece a otro (o al mismo, cuando vuelva).
PLAZO_EQUIPO_S = 45 * 60

# Modelo que se usa cuando el proveedor no nombra uno.
MODELOS = {"claude": "claude-opus-5-5"}

ESPERA_MODELO_S = 180
ESPERA_SERVIDOR_S = 8


def _tipo(tipo: str) -> dict:
    if tipo not in TIPOS:
        raise ValueError(f"No existe el tipo {tipo}. Los tipos son: {', '.join(TIPOS)}.")
    return TIPOS[tipo]


def _leer(contexto, tipo: str, id_: str) -> dict:
    registro = contexto.datos.leer(tipo, id_)
    if registro is None:
        raise ValueError(f"No hay un registro {id_} en {tipo}.")
    return registro


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def listar(contexto, tipo: str) -> dict:
    _tipo(tipo)
    return {"registros": contexto.datos.listar(tipo)}


def crear(contexto, tipo: str, datos: dict) -> dict:
    definicion = _tipo(tipo)
    obligatorio = definicion["obligatorio"]
    if not str(datos.get(obligatorio) or "").strip():
        raise ValueError(f"Falta {obligatorio}.")
    return {"registro": contexto.datos.guardar(tipo, {**definicion["por_defecto"], **datos})}


def editar(contexto, tipo: str, id: str, cambios: dict) -> dict:
    _tipo(tipo)
    return {"registro": contexto.datos.guardar(tipo, {**_leer(contexto, tipo, id), **cambios}, id)}


def borrar(contexto, tipo: str, id: str) -> dict:
    _tipo(tipo)
    return {"borrado": contexto.datos.borrar(tipo, id)}


def _libre(proveedor: dict) -> int:
    return max(0, int(proveedor.get("cuota") or 0) - int(proveedor.get("usadas") or 0))


def repartir_cola(contexto) -> dict:
    """Cada tarea en cola va al proveedor activo con más cuota libre, contando las que ya recibió en este reparto.
    Las más viejas primero."""
    libre = {p["id"]: _libre(p) for p in contexto.datos.listar("proveedores") if p.get("estado") == "activo"}
    libre = {id_: n for id_, n in libre.items() if n > 0}
    asignadas = 0
    for tarea in reversed(contexto.datos.listar("tareas")):
        if tarea.get("estado") != "cola":
            continue
        if not libre:
            break
        mejor = max(libre, key=libre.get)
        contexto.datos.guardar("tareas", {**tarea, "proveedor_id": mejor, "estado": "asignada"}, tarea["id"])
        libre[mejor] -= 1
        if libre[mejor] == 0:
            del libre[mejor]
        asignadas += 1
    return {"asignadas": asignadas}


def _pedir_http(url: str, cuerpo: dict | None, cabeceras: dict, espera: float, metodo: str | None = None):
    """Hace el pedido y devuelve (código, texto). Un error HTTP no lanza: vuelve con su código."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    if datos is not None:
        cabeceras = {"Content-Type": "application/json", **cabeceras}
    pedido = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=espera) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def probar_servidor(contexto, id: str) -> dict:
    servidor = _leer(contexto, "servidores", id)
    url = str(servidor.get("url") or "").rstrip("/")
    cambios = {"ultima_prueba": _ahora(), "latencia_ms": None}
    if not url.startswith(("http://", "https://")):
        cambios.update(estado="sin_conexion", detalle="La URL tiene que empezar con http:// o https://.")
    else:
        inicio = time.monotonic()
        try:
            codigo, _ = _pedir_http(url + (servidor.get("ruta_salud") or "/"), None, {}, ESPERA_SERVIDOR_S)
            cambios.update(
                estado="en_linea" if codigo < 500 else "sin_conexion",
                detalle=f"HTTP {codigo}",
                latencia_ms=round((time.monotonic() - inicio) * 1000),
            )
        except OSError as e:  # sin red, DNS, tiempo agotado
            cambios.update(estado="sin_conexion", detalle=str(getattr(e, "reason", e)))
    return {"registro": contexto.datos.guardar("servidores", {**servidor, **cambios}, id)}


def _encargo(tarea: dict, proyecto: dict | None) -> str:
    partes = [f"Tarea: {tarea['titulo']}"]
    if proyecto:
        partes.append(
            f"Proyecto: {proyecto['nombre']}. {proyecto.get('descripcion') or ''} Stack: {proyecto.get('stack') or 'sin definir'}."
        )
    partes.append(f"Tipo: {tarea.get('tipo')}. Prioridad: {tarea.get('prioridad')}.")
    if tarea.get("contexto"):
        partes.append(f"Contexto y criterios:\n{tarea['contexto']}")
    partes.append("Resuelve la tarea. Entrega el resultado listo para revisar, en español.")
    return "\n\n".join(partes)


def _json(texto: str, que: str) -> dict:
    try:
        return json.loads(texto)
    except ValueError:
        raise RuntimeError(f"{que} respondió algo que no es JSON.") from None


def _preguntar(contexto, proveedor: dict, encargo: str) -> tuple[str, str]:
    """Manda el encargo al modelo del proveedor. Devuelve (respuesta, modelo usado)."""
    familia = proveedor.get("familia")
    modelo = str(proveedor.get("modelo") or MODELOS.get(familia) or "").strip()
    if familia == "copilot":
        raise RuntimeError("Copilot no tiene una API para ejecutar tareas desde Ashur. Asigna la tarea a otro proveedor.")
    if not modelo:
        raise RuntimeError(f"El proveedor {proveedor['nombre']} no dice qué modelo usar.")
    clave = contexto.ajuste(f"clave_{familia}") if familia in ("claude", "gpt", "gemini", "propio") else None
    if familia in ("claude", "gpt", "gemini") and not clave:
        raise RuntimeError(f"Falta la clave de {familia} en los ajustes del módulo Workbench.")

    if familia == "claude":
        codigo, texto = _pedir_http(
            "https://api.anthropic.com/v1/messages",
            {"model": modelo, "max_tokens": 16000, "messages": [{"role": "user", "content": encargo}]},
            {"x-api-key": clave, "anthropic-version": "2026-10-21"},
            ESPERA_MODELO_S,
        )
        datos = _json(texto, "Claude")
        if codigo != 200:
            raise RuntimeError(f"Claude respondió HTTP {codigo}: {(datos.get('error') or {}).get('message', texto[:200])}")
        if datos.get("stop_reason") == "refusal":
            raise RuntimeError("Claude declinó esta tarea.")
        respuesta = "".join(b.get("text", "") for b in datos.get("content", []) if b.get("type") == "text")
    elif familia == "gemini":
        codigo, texto = _pedir_http(
            f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
            {"contents": [{"parts": [{"text": encargo}]}]},
            {"x-goog-api-key": clave},
            ESPERA_MODELO_S,
        )
        datos = _json(texto, "Gemini")
        if codigo != 200:
            raise RuntimeError(f"Gemini respondió HTTP {codigo}: {(datos.get('error') or {}).get('message', texto[:200])}")
        candidatos = datos.get("candidates") or [{}]
        respuesta = "".join(p.get("text", "") for p in (candidatos[0].get("content") or {}).get("parts", []))
    elif familia in ("gpt", "propio"):
        base = "https://api.openai.com/v1" if familia == "gpt" else str(contexto.ajuste("url_propio") or "").rstrip("/")
        if not base:
            raise RuntimeError("Falta la dirección del servidor propio en los ajustes del módulo Workbench.")
        codigo, texto = _pedir_http(
            base + "/chat/completions",
            {"model": modelo, "messages": [{"role": "user", "content": encargo}]},
            {"Authorization": f"Bearer {clave}"} if clave else {},
            ESPERA_MODELO_S,
        )
        datos = _json(texto, proveedor["nombre"])
        if codigo != 200:
            error = datos.get("error")
            detalle = error.get("message") if isinstance(error, dict) else error
            raise RuntimeError(f"{proveedor['nombre']} respondió HTTP {codigo}: {detalle or texto[:200]}")
        respuesta = ((datos.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    else:
        raise RuntimeError(f"No sé ejecutar tareas con la familia {familia}.")
    if not respuesta.strip():
        raise RuntimeError("El modelo no devolvió texto.")
    return respuesta, modelo


def ejecutar_tarea(contexto, id: str) -> dict:
    """Si el modelo falla, la tarea queda con error y el motivo: la acción no lanza por eso. Una tarea de una familia
    de equipo no se resuelve aquí: queda esperando a que un equipo la tome."""
    tarea = _leer(contexto, "tareas", id)
    proveedor = contexto.datos.leer("proveedores", tarea.get("proveedor_id") or "")
    if proveedor is None:
        raise ValueError("La tarea no está asignada a un proveedor.")
    if proveedor.get("familia") in FAMILIAS_DE_EQUIPO:
        espera = {"estado": "ejecutando", "espera_equipo": True, "pedida": _ahora(), "tomada": None, "equipo": None,
                  "error": None}
        return {"registro": contexto.datos.guardar("tareas", {**tarea, **espera}, id)}
    proyecto = contexto.datos.leer("proyectos", tarea.get("proyecto_id") or "")
    cambios = {"ejecuciones": int(tarea.get("ejecuciones") or 0) + 1, "ultima_ejecucion": _ahora()}
    try:
        respuesta, modelo = _preguntar(contexto, proveedor, _encargo(tarea, proyecto))
    except (RuntimeError, OSError) as e:
        cambios.update(estado="error", error=str(getattr(e, "reason", e)))
    else:
        cambios.update(estado="revision", resultado=respuesta, modelo_usado=modelo, error=None)
        contexto.datos.guardar(
            "proveedores", {**proveedor, "usadas": int(proveedor.get("usadas") or 0) + 1}, proveedor["id"]
        )
    return {"registro": contexto.datos.guardar("tareas", {**tarea, **cambios}, id)}


def _vencida(tarea: dict) -> bool:
    tomada = tarea.get("tomada")
    if not tomada:
        return True
    return (datetime.now(timezone.utc) - datetime.fromisoformat(tomada)).total_seconds() > PLAZO_EQUIPO_S


def tomar_tarea(contexto, equipo: str, familias: list) -> dict:
    """Lo llama ejecutor.py desde un equipo. Anota que el equipo está vivo y le da la tarea más vieja que espera a una
    de sus familias, o ninguna. Una tarea tomada hace más de PLAZO_EQUIPO_S se vuelve a ofrecer."""
    equipo = str(equipo or "").strip()
    if not equipo:
        raise ValueError("Falta el nombre del equipo.")
    familias = [f for f in familias if f in FAMILIAS_DE_EQUIPO]
    conocido = next((e for e in contexto.datos.listar("equipos") if e.get("nombre") == equipo), None)
    ficha = {"nombre": equipo, "familias": familias, "visto": _ahora()}
    contexto.datos.guardar("equipos", ficha, conocido["id"] if conocido else None)
    for tarea in reversed(contexto.datos.listar("tareas")):
        if not tarea.get("espera_equipo") or not _vencida(tarea):
            continue
        proveedor = contexto.datos.leer("proveedores", tarea.get("proveedor_id") or "")
        if proveedor is None or proveedor.get("familia") not in familias:
            continue
        contexto.datos.guardar("tareas", {**tarea, "tomada": _ahora(), "equipo": equipo}, tarea["id"])
        proyecto = contexto.datos.leer("proyectos", tarea.get("proyecto_id") or "")
        return {
            "tarea": {
                "id": tarea["id"],
                "familia": proveedor["familia"],
                "modelo": str(proveedor.get("modelo") or "").strip() or None,
                "encargo": _encargo(tarea, proyecto),
            }
        }
    return {"tarea": None}


def entregar_tarea(contexto, id: str, equipo: str, resultado: str | None = None, error: str | None = None,
                   modelo: str | None = None) -> dict:
    """Lo llama ejecutor.py con la respuesta del programa, o con el motivo si falló. Solo vale la entrega del equipo
    que tiene tomada la tarea."""
    tarea = _leer(contexto, "tareas", id)
    if not tarea.get("espera_equipo") or tarea.get("equipo") != equipo:
        raise ValueError("Esta tarea ya no está tomada por este equipo.")
    cambios = {"espera_equipo": False, "tomada": None, "ejecuciones": int(tarea.get("ejecuciones") or 0) + 1,
               "ultima_ejecucion": _ahora()}
    if str(resultado or "").strip():
        cambios.update(estado="revision", resultado=resultado, modelo_usado=modelo or equipo, error=None)
        proveedor = contexto.datos.leer("proveedores", tarea.get("proveedor_id") or "")
        if proveedor is not None:
            contexto.datos.guardar(
                "proveedores", {**proveedor, "usadas": int(proveedor.get("usadas") or 0) + 1}, proveedor["id"]
            )
    else:
        cambios.update(estado="error", error=str(error or "El equipo no devolvió texto."))
    return {"registro": contexto.datos.guardar("tareas", {**tarea, **cambios}, id)}


def compilar_entrega(contexto, id: str) -> dict:
    """Manda la entrega a la ruta de compilación del primer servidor. Si el servidor falla, la entrega queda fallida
    con el motivo en su registro."""
    entrega = _leer(contexto, "entregas", id)
    servidores = contexto.datos.listar("servidores")
    servidor = servidores[-1] if servidores else None
    if servidor is None or not servidor.get("url") or not servidor.get("ruta_compilacion"):
        raise ValueError("Configura la URL y la ruta de compilación del servidor antes de compilar.")
    proyecto = contexto.datos.leer("proyectos", entrega.get("proyecto_id") or "")
    try:
        codigo, texto = _pedir_http(
            str(servidor["url"]).rstrip("/") + servidor["ruta_compilacion"],
            {"version": entrega["version"], "canal": entrega.get("canal"), "proyecto": (proyecto or {}).get("nombre")},
            {},
            ESPERA_SERVIDOR_S,
        )
        bien, registro = codigo < 300, f"HTTP {codigo}\n{texto[:4000]}"
    except OSError as e:
        bien, registro = False, str(getattr(e, "reason", e))
    cambios = {"estado": "compilando" if bien else "fallida", "registro": f"{_ahora()}\n{registro}"}
    return {"registro": contexto.datos.guardar("entregas", {**entrega, **cambios}, id), "aceptada": bien}
