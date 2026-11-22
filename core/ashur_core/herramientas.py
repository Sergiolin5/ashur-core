"""Herramientas que Ashur puede usar en el chat (docs/adr/0021-herramientas-del-chat.md).

El modelo solo pide: el core revisa que la herramienta se haya ofrecido en ese trabajo, valida los argumentos y la
corre. Lo que falla vuelve como texto para el modelo, nunca como un error del pedido. Las acciones de módulos que
escriben quedan como pedidos pendientes de la aprobación de Sergio.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ashur_core import identidades, inventario, memoria, personas

# Va al final de la personalidad cuando el pedido lleva herramientas. Sin esto, qwen2.5:7b decía que no sabía dónde
# estaba un objeto sin buscarlo en el inventario (docs/adr/0021-herramientas-del-chat.md).
AVISO = (
    "Tienes herramientas para consultar el inventario de objetos, las personas y mascotas que conoces, tu memoria y "
    "los módulos. Si la pregunta es sobre algo de eso, úsalas antes de responder, y nunca digas que no sabes sin "
    "haber buscado."
)
# Rondas de herramientas por mensaje; después, el modelo responde sin herramientas.
RONDAS = 3
LARGO_RESULTADO = 2000
ELEMENTOS = 20


class ArgsBuscarObjetos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str | None = None


class ArgsSinNada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArgsBuscarRecuerdos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1)


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    descripcion: str
    parametros: dict
    # Para las del core, el modelo de sus argumentos; para las de módulos, None (los manifiestos no traen esquema).
    argumentos: type[BaseModel] | None = None
    modulo: str | None = None
    accion: str | None = None

    def definicion(self) -> dict:
        """En el formato de OpenAI, que Ollama entiende."""
        return {"type": "function", "function": {
            "name": self.nombre, "description": self.descripcion, "parameters": self.parametros}}


DEL_CORE = (
    Herramienta(
        "buscar_objetos", "Busca en el inventario de objetos de Sergio por nombre o lugar. Sin texto, los lista.",
        {"type": "object", "properties": {"texto": {"type": "string"}}}, ArgsBuscarObjetos,
    ),
    Herramienta("listar_identidades", "Lista las personas y mascotas que Ashur conoce.",
                {"type": "object", "properties": {}}, ArgsSinNada),
    Herramienta(
        "buscar_recuerdos", "Busca en la memoria de Ashur los recuerdos con esas palabras.",
        {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}, ArgsBuscarRecuerdos,
    ),
)


def de_modulos(registro) -> list[Herramienta]:
    """Una herramienta por acción de cada módulo registrado, llamada modulo-<id>-<accion>: el guion no puede ir dentro
    de un id, así que dos módulos nunca dan el mismo nombre."""
    lista, usados = [], set()
    for id_, modulo in sorted(registro.modulos.items()):
        for accion in modulo.manifiesto.acciones:
            nombre = f"modulo-{id_}-{accion.id}"[:64]
            if nombre in usados:  # al cortarlo chocó con otro: nunca se corre una acción equivocada
                continue
            usados.add(nombre)
            aviso = " Escribe: queda pendiente de la aprobación de Sergio." if accion.escribe else ""
            lista.append(Herramienta(
                nombre, f"{modulo.manifiesto.nombre}: {accion.descripcion}{aviso}", {"type": "object"},
                modulo=id_, accion=accion.id,
            ))
    return lista


def herramientas_para(con, identidad_id: str | None, registro) -> list[Herramienta]:
    """La única puerta: qué herramientas se ofrecen a quien habla. Sergio, todas; otra persona, las de su rol actual,
    y ninguna si no tiene rol (docs/adr/0022-personas-y-roles.md)."""
    todas = list(DEL_CORE) + de_modulos(registro)
    if identidad_id is None:
        return todas
    patrones = personas.patrones_de(con, identidad_id)
    return [h for h in todas if personas.permite(patrones, h.nombre)]


def _recortar(texto: str) -> str:
    return texto if len(texto) <= LARGO_RESULTADO else texto[:LARGO_RESULTADO] + " […]"


def _lineas(lineas: list[str], vacio: str) -> str:
    if not lineas:
        return vacio
    extra = f"\n(y {len(lineas) - ELEMENTOS} más)" if len(lineas) > ELEMENTOS else ""
    return "\n".join(lineas[:ELEMENTOS]) + extra


def correr(
    con, nombre: str, argumentos, ofrecidas: list[Herramienta], correr_modulo: Callable[[str, str, dict], str],
    permitidos: set[int] | None = None,
) -> str:
    """El resultado de una llamada, siempre como texto para el modelo. Con [permitidos], buscar_recuerdos solo ve esos:
    el rol decide qué herramientas hay, pero la privacidad vale dentro de cada una."""
    herramienta = next((h for h in ofrecidas if h.nombre == nombre), None)
    if herramienta is None:
        return f"No existe la herramienta {nombre}."
    if isinstance(argumentos, str):  # el formato de OpenAI manda los argumentos como texto JSON
        try:
            argumentos = json.loads(argumentos) if argumentos.strip() else {}
        except json.JSONDecodeError:
            return "Los argumentos no son JSON válido."
    if not isinstance(argumentos, dict):
        return "Los argumentos tienen que ser un objeto."
    if herramienta.modulo is not None:
        return _recortar(correr_modulo(herramienta.modulo, herramienta.accion, argumentos))
    try:
        args = herramienta.argumentos.model_validate(argumentos)
    except ValidationError as e:
        return f"Argumentos inválidos: {e.errors()[0]['msg']}."
    if nombre == "buscar_objetos":
        texto = (args.texto or "").lower()
        objetos = [o for o in inventario.listar(con) if texto in o.nombre.lower() or texto in (o.lugar or "").lower()]
        resultado = _lineas([f"{o.nombre}: {o.lugar or 'sin lugar'}" for o in objetos], "No hay objetos con eso.")
    elif nombre == "listar_identidades":
        resultado = _lineas([f"{i.nombre} ({i.clase})" for i in identidades.listar(con)], "Ashur no conoce a nadie todavía.")
    else:
        ids = memoria.buscar_alguna(con, args.texto, limite=ELEMENTOS, permitidos=permitidos)
        recuerdos = [memoria.obtener(con, i) for i in ids]
        resultado = _lineas(
            [f"{r.fecha.date().isoformat()}: {r.texto}" for r in recuerdos if r is not None], "No hay recuerdos con eso."
        )
    return _recortar(resultado)


def llamadas_de(mensaje: dict) -> list[tuple[str, object]] | None:
    """Las llamadas a herramientas de la respuesta del modelo, como (nombre, argumentos). None si vienen mal."""
    llamadas = mensaje.get("tool_calls") or []
    if not isinstance(llamadas, list):
        return None
    resultado = []
    for llamada in llamadas:
        funcion = llamada.get("function") if isinstance(llamada, dict) else None
        if not isinstance(funcion, dict) or not isinstance(funcion.get("name"), str):
            return None
        resultado.append((funcion["name"], funcion.get("arguments", {})))
    return resultado


def normalizar(llamadas: list) -> list:
    """Las llamadas con los argumentos como objeto: el formato de OpenAI los trae como texto JSON, y Ollama los espera
    como objeto cuando vuelven en el historial."""
    normalizadas = []
    for llamada in llamadas:
        funcion = dict(llamada.get("function") or {})
        argumentos = funcion.get("arguments", {})
        if isinstance(argumentos, str):
            try:
                argumentos = json.loads(argumentos) if argumentos.strip() else {}
            except json.JSONDecodeError:
                argumentos = {}
        funcion["arguments"] = argumentos if isinstance(argumentos, dict) else {}
        normalizadas.append({**llamada, "function": funcion})
    return normalizadas
