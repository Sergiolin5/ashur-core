import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Response, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from functools import lru_cache

from ashur_core import (
    chat, galaxia, herramientas, identidades, inventario, memoria, modulos, nodos, personas, significado,
)

app = FastAPI(title="Ashur Core")

_encabezado_clave = APIKeyHeader(name="X-Ashur-Clave", auto_error=False)


def exigir_clave(clave: str | None = Security(_encabezado_clave)) -> None:
    """Sin ASHUR_CLAVE configurada, la memoria queda cerrada (docs/adr/0004-memoria.md)."""
    esperada = os.environ.get("ASHUR_CLAVE")
    if not esperada:
        raise HTTPException(status_code=503, detail="ASHUR_CLAVE no está configurada.")
    if clave is None or not secrets.compare_digest(clave, esperada):
        raise HTTPException(status_code=401, detail="Clave inválida.")


_encabezado_admin = APIKeyHeader(name="X-Ashur-Clave-Admin", auto_error=False)


def exigir_clave_admin(clave: str | None = Security(_encabezado_admin)) -> None:
    """Solo los administradores editan y borran recuerdos. Sin ASHUR_CLAVE_ADMIN, nadie puede."""
    esperada = os.environ.get("ASHUR_CLAVE_ADMIN")
    if not esperada:
        raise HTTPException(status_code=503, detail="ASHUR_CLAVE_ADMIN no está configurada.")
    if clave is None or not secrets.compare_digest(clave, esperada):
        raise HTTPException(status_code=401, detail="Clave de administrador inválida.")


_encabezado_nodo = APIKeyHeader(name="X-Ashur-Clave-Nodo", auto_error=False)


def conexion() -> Iterator:
    con = memoria.abrir(os.environ.get("ASHUR_DB", "/datos/ashur.db"))
    try:
        yield con
    finally:
        con.close()


def _exigir_identidades_conocidas(con, lista: list[memoria.Identidad]) -> None:
    """Un recuerdo solo puede enlazar identidades que existen (docs/adr/0012-identidades.md)."""
    faltan = identidades.desconocidas(con, [i.identidad_id for i in lista if i.identidad_id is not None])
    if faltan:
        raise HTTPException(status_code=422, detail=f"No existen estas identidades: {', '.join(faltan)}")


def _exigir_objetos_conocidos(con, lista: list[memoria.Objeto]) -> None:
    """Un recuerdo solo puede enlazar objetos que existen (docs/adr/0014-inventario.md)."""
    faltan = inventario.desconocidos(con, [o.inventario_id for o in lista if o.inventario_id is not None])
    if faltan:
        raise HTTPException(status_code=422, detail=f"No existen estos objetos: {', '.join(faltan)}")


@app.get("/vivo")
def vivo() -> dict[str, bool]:
    return {"vivo": True}


@app.post("/recuerdos", status_code=201, response_model=memoria.Recuerdo, dependencies=[Depends(exigir_clave)])
def crear_recuerdo(nuevo: memoria.RecuerdoNuevo, con=Depends(conexion)) -> memoria.Recuerdo:
    return _guardar_recuerdo(con, nuevo)


def _guardar_recuerdo(con, nuevo: memoria.RecuerdoNuevo) -> memoria.Recuerdo:
    """El único camino para guardar un recuerdo, desde la API o desde un módulo."""
    _exigir_identidades_conocidas(con, nuevo.identidades)
    _exigir_objetos_conocidos(con, nuevo.objetos)
    creado = memoria.crear(con, nuevo)
    identidades.recalcular_niveles(con)
    return creado


@app.get("/recuerdos", response_model=list[memoria.Recuerdo], dependencies=[Depends(exigir_clave)])
def listar_recuerdos(buscar: str | None = None, con=Depends(conexion)) -> list[memoria.Recuerdo]:
    """Sin buscar, todos los recuerdos. Con buscar, los que tienen esas palabras, los más relevantes primero."""
    return memoria.listar(con) if buscar is None else memoria.buscar(con, buscar)


@app.patch("/recuerdos/{id_}", response_model=memoria.Recuerdo, dependencies=[Depends(exigir_clave_admin)])
def editar_recuerdo(id_: int, cambios: memoria.CambiosRecuerdo, con=Depends(conexion)) -> memoria.Recuerdo:
    if cambios.identidades is not None:
        _exigir_identidades_conocidas(con, cambios.identidades)
    if cambios.objetos is not None:
        _exigir_objetos_conocidos(con, cambios.objetos)
    editado = memoria.editar(con, id_, cambios)
    if editado is None:
        raise HTTPException(status_code=404, detail="No existe ese recuerdo.")
    identidades.recalcular_niveles(con)
    return editado


@app.delete("/recuerdos/{id_}", status_code=204, dependencies=[Depends(exigir_clave_admin)])
def borrar_recuerdo(id_: int, con=Depends(conexion)) -> Response:
    if not memoria.borrar(con, id_):
        raise HTTPException(status_code=404, detail="No existe ese recuerdo.")
    identidades.recalcular_niveles(con)
    return Response(status_code=204)


@app.get("/aprendizaje", response_model=memoria.Aprendizaje, dependencies=[Depends(exigir_clave)])
def ver_aprendizaje(con=Depends(conexion)) -> memoria.Aprendizaje:
    return memoria.aprendizaje(con)


@app.patch("/aprendizaje", response_model=memoria.Aprendizaje, dependencies=[Depends(exigir_clave_admin)])
def cambiar_inicio(cambio: memoria.CambioInicio, con=Depends(conexion)) -> memoria.Aprendizaje:
    return memoria.cambiar_inicio(con, cambio.inicio)


@app.get("/galaxia", response_model=galaxia.EstadoGalaxia, dependencies=[Depends(exigir_clave)])
def ver_galaxia(con=Depends(conexion)) -> galaxia.EstadoGalaxia:
    planetas = [
        (m.manifiesto, memoria.contar_por_origen(con, id_)) for id_, m in registro_de_modulos().modulos.items()
    ]
    return galaxia.estado_actual(memoria.aprendizaje(con), identidades.listar(con), planetas, inventario.contar(con))


@app.post("/identidades", status_code=201, response_model=identidades.Identidad, dependencies=[Depends(exigir_clave)])
def crear_identidad(nueva: identidades.IdentidadNueva, con=Depends(conexion)) -> identidades.Identidad:
    return identidades.crear(con, nueva)


@app.get("/identidades", response_model=list[identidades.Identidad], dependencies=[Depends(exigir_clave)])
def listar_identidades(archivadas: bool = False, con=Depends(conexion)) -> list[identidades.Identidad]:
    """Sin archivadas, salvo que se pidan."""
    return identidades.listar(con, archivadas)


@app.patch(
    "/identidades/{id_}", response_model=identidades.Identidad, dependencies=[Depends(exigir_clave_admin)]
)
def editar_identidad(id_: str, cambios: identidades.CambiosIdentidad, con=Depends(conexion)) -> identidades.Identidad:
    """Editar, archivar o restaurar, y ponerle o quitarle un rol. No hay DELETE: se archiva (decisión 8). Archivada,
    su clave deja de abrir el chat."""
    if cambios.rol is not None and personas.obtener_rol(con, cambios.rol) is None:
        raise HTTPException(status_code=422, detail=f"No existe el rol {cambios.rol}.")
    editada = identidades.editar(con, id_, cambios)
    if editada is None:
        raise HTTPException(status_code=404, detail="No existe esa identidad.")
    return editada


class ClaveCreada(BaseModel):
    identidad: identidades.Identidad
    clave: str  # se muestra una sola vez; el core solo guarda su hash


@app.post("/identidades/{id_}/clave", status_code=201, response_model=ClaveCreada, dependencies=[Depends(exigir_clave_admin)])
def crear_clave(id_: str, con=Depends(conexion)) -> ClaveCreada:
    """Crea o reemplaza la clave con la que esa persona entra a su chat (docs/adr/0022-personas-y-roles.md)."""
    identidad = identidades.obtener(con, id_)
    if identidad is None:
        raise HTTPException(status_code=404, detail="No existe esa identidad.")
    if identidad.archivada:
        raise HTTPException(status_code=409, detail="Esa identidad está archivada.")
    clave = personas.nueva_clave(con, id_)
    return ClaveCreada(identidad=identidades.obtener(con, id_), clave=clave)


@app.post("/roles", status_code=201, response_model=personas.Rol, dependencies=[Depends(exigir_clave_admin)])
def crear_rol(nuevo: personas.RolNuevo, con=Depends(conexion)) -> personas.Rol:
    return personas.crear_rol(con, nuevo)


@app.get("/roles", response_model=list[personas.Rol], dependencies=[Depends(exigir_clave)])
def listar_roles(con=Depends(conexion)) -> list[personas.Rol]:
    return personas.listar_roles(con)


@app.patch("/roles/{id_}", response_model=personas.Rol, dependencies=[Depends(exigir_clave_admin)])
def cambiar_rol(id_: str, cambios: personas.CambiosRol, con=Depends(conexion)) -> personas.Rol:
    """Cambia en la ronda siguiente de cada conversación: la puerta lee el rol actual."""
    rol = personas.cambiar_rol(con, id_, cambios)
    if rol is None:
        raise HTTPException(status_code=404, detail="No existe ese rol.")
    return rol


@app.post("/objetos", status_code=201, response_model=inventario.Objeto, dependencies=[Depends(exigir_clave)])
def crear_objeto(nuevo: inventario.ObjetoNuevo, con=Depends(conexion)) -> inventario.Objeto:
    return inventario.crear(con, nuevo)


@app.get("/objetos", response_model=list[inventario.Objeto], dependencies=[Depends(exigir_clave)])
def listar_objetos(archivados: bool = False, con=Depends(conexion)) -> list[inventario.Objeto]:
    """Sin archivados, salvo que se pidan."""
    return inventario.listar(con, archivados)


@app.patch("/objetos/{id_}", response_model=inventario.Objeto, dependencies=[Depends(exigir_clave_admin)])
def editar_objeto(id_: str, cambios: inventario.CambiosObjeto, con=Depends(conexion)) -> inventario.Objeto:
    """Editar, mover, archivar o restaurar. No hay DELETE: se archiva (decisión 8)."""
    editado = inventario.editar(con, id_, cambios)
    if editado is None:
        raise HTTPException(status_code=404, detail="No existe ese objeto.")
    return editado


# ── Chat y nodos (docs/adr/0016-chat-y-nodos.md) ──


def nodo_autenticado(clave: str | None = Security(_encabezado_nodo), con=Depends(conexion)) -> str:
    """Una clave de nodo solo abre la cola de trabajos."""
    id_nodo = nodos.autenticar(con, clave) if clave else None
    if id_nodo is None:
        raise HTTPException(status_code=401, detail="Clave de nodo inválida.")
    return id_nodo


class Quien:
    """Quién habla en el chat: Sergio (identidad None) o una persona con su clave."""

    def __init__(self, identidad_id: str | None):
        self.identidad_id = identidad_id


def quien_habla(clave: str | None = Security(_encabezado_clave), con=Depends(conexion)) -> Quien:
    """Para las rutas del chat, las únicas que abre la clave de una persona. Las demás siguen con exigir_clave, que
    solo acepta la de Sergio. Sin ASHUR_CLAVE, todo queda cerrado, también para las personas."""
    esperada = os.environ.get("ASHUR_CLAVE")
    if not esperada:
        raise HTTPException(status_code=503, detail="ASHUR_CLAVE no está configurada.")
    if clave is not None and secrets.compare_digest(clave, esperada):
        return Quien(None)
    identidad = personas.autenticar(con, clave) if clave else None
    if identidad is None:
        raise HTTPException(status_code=401, detail="Clave inválida.")
    return Quien(identidad)


def _suya(con, id_conversacion: str, quien: Quien) -> chat.Conversacion:
    """Una conversación ajena responde igual que una que no existe: los ids se pueden adivinar."""
    existe, duenio = chat.duenio(con, id_conversacion)
    if not existe or duenio != quien.identidad_id:
        raise HTTPException(status_code=404, detail="No existe esa conversación.")
    return chat.obtener(con, id_conversacion)


def _completa(con, conversacion: chat.Conversacion) -> chat.ConversacionCompleta:
    trabajo = chat.trabajo_actual(con, conversacion.id)
    estado = nodos.estado_de(con, trabajo) if trabajo is not None else None
    espera = chat.Espera(**estado) if estado and estado["estado"] != "hecho" else None
    return chat.ConversacionCompleta(conversacion=conversacion, mensajes=chat.mensajes(con, conversacion.id), espera=espera)


def _decir(con, id_conversacion: str, rol: str, origen: str, texto: str) -> chat.Mensaje:
    """Todo mensaje del chat también es un recuerdo, por el mismo camino que POST /recuerdos. En la conversación de
    otra persona, el recuerdo la enlaza: así crece en la galaxia mientras habla con Ashur."""
    fecha = chat.ahora()
    _, duenio = chat.duenio(con, id_conversacion)
    persona = identidades.obtener(con, duenio) if duenio else None
    enlaces = [memoria.Identidad(nombre=persona.nombre, identidad_id=persona.id)] if persona else []
    recuerdo = _guardar_recuerdo(
        con,
        memoria.RecuerdoNuevo(
            texto=texto, origen=origen, fecha=fecha, sensibilidad="normal", identidades=enlaces, objetos=[], opinion=None
        ),
    )
    return chat.agregar(con, id_conversacion, rol, texto, fecha, recuerdo.id)


RUTAS_DE_PERSONAS = {"/conversaciones", "/conversaciones/{id_}", "/conversaciones/{id_}/mensajes"}


@app.post("/conversaciones", status_code=201, response_model=chat.Conversacion)
def crear_conversacion(quien: Quien = Depends(quien_habla), con=Depends(conexion)) -> chat.Conversacion:
    return chat.crear(con, quien.identidad_id)


@app.get("/conversaciones", response_model=list[chat.Conversacion])
def listar_conversaciones(quien: Quien = Depends(quien_habla), con=Depends(conexion)) -> list[chat.Conversacion]:
    """Las de quien pregunta. Sergio ve lo que dicen los demás en sus recuerdos, no en esta lista."""
    return chat.listar(con, quien.identidad_id)


@app.get("/conversaciones/{id_}", response_model=chat.ConversacionCompleta)
def ver_conversacion(id_: str, quien: Quien = Depends(quien_habla), con=Depends(conexion)) -> chat.ConversacionCompleta:
    return _completa(con, _suya(con, id_, quien))


@app.post("/conversaciones/{id_}/mensajes", status_code=202, response_model=chat.ConversacionCompleta)
def enviar_mensaje(
    id_: str, nuevo: chat.MensajeNuevo, quien: Quien = Depends(quien_habla), con=Depends(conexion)
) -> chat.ConversacionCompleta:
    """Guarda el mensaje y deja en la cola el primer paso de la respuesta, que llega cuando un nodo la entregue. Si hay
    un nodo con el modelo de embeddings, el primer paso es buscar por significado; si no, Ashur responde con lo que
    encuentra por palabras (docs/adr/0018-busqueda-hibrida.md)."""
    _suya(con, id_, quien)
    buscar_primero = nodos.hay_quien(con, "embedding")
    trabajo = nodos.encolar(con, "embedding" if buscar_primero else "conversar", {}, id_, estado="preparando")
    if not chat.reservar(con, id_, trabajo):
        nodos.descartar(con, trabajo)
        raise HTTPException(status_code=409, detail="Ashur todavía está respondiendo el mensaje anterior.")
    _decir(con, id_, "user", chat.ORIGEN_SERGIO, nuevo.texto)
    if buscar_primero:
        nodos.preparar(con, trabajo, {"input": [nuevo.texto]})
    else:
        nodos.preparar(con, trabajo, _pedido(con, id_, None))
    return _completa(con, chat.obtener(con, id_))


RECUERDOS_EN_EL_PEDIDO = 5
# Si nadie toma la búsqueda por significado en este tiempo, Ashur responde solo con la búsqueda por palabras.
ESPERA_SIGNIFICADO_S = 15


def _recordar(con, id_conversacion: str, vector: list[float] | None) -> list[memoria.Recuerdo]:
    """Búsqueda híbrida: los recuerdos que mejor combinan la búsqueda por palabras y, si hay vector, la búsqueda por
    significado. Sin los que ya están en el historial que ve el modelo."""
    historial = chat.historial(con, id_conversacion)
    ultimo = next((m.texto for m in reversed(historial) if m.rol == "user"), "")
    vistos = {m.recuerdo_id for m in historial}
    permitidos = _permitidos(con, id_conversacion)
    listas = [[i for i in memoria.buscar_alguna(con, ultimo, permitidos=permitidos) if i not in vistos]]
    if vector is not None:
        listas.append([i for i in significado.cercanos(con, vector, permitidos) if i not in vistos])
    ids = significado.combinar(*listas, cuantos=RECUERDOS_EN_EL_PEDIDO)
    return [r for r in (memoria.obtener(con, i) for i in ids) if r is not None]


def _permitidos(con, id_conversacion: str) -> set[int] | None:
    """Con Sergio, toda la memoria (None). Con otra persona, solo lo que salió de sus mensajes (docs/adr/0022)."""
    _, duenio = chat.duenio(con, id_conversacion)
    return None if duenio is None else personas.recuerdos_de(con, duenio)


def _pedido(con, id_conversacion: str, vector: list[float] | None) -> dict:
    """El pedido al modelo, con lo que encontró la búsqueda y, si hay un nodo que sepa usarlas, las herramientas que
    se ofrecen en esta conversación (docs/adr/0021-herramientas-del-chat.md)."""
    recuerdos = _recordar(con, id_conversacion, vector)
    pedido = chat.pedido_al_modelo(
        con, id_conversacion, recuerdos, autores=personas.autores(con, [r.id for r in recuerdos])
    )
    _, duenio = chat.duenio(con, id_conversacion)
    ofrecidas = herramientas.herramientas_para(con, duenio, registro_de_modulos())
    if ofrecidas and nodos.hay_quien(con, "conversar", requiere="tools"):
        pedido.update(tools=[h.definicion() for h in ofrecidas], rondas=0)
        pedido["messages"][0]["content"] += "\n\n" + herramientas.AVISO
    return pedido


def _seguir(con, id_conversacion: str, pedido: dict) -> int:
    """Deja el paso siguiente en la cola y la conversación apuntando a él, antes de cerrar el anterior: entre los dos
    nunca queda un hueco en el que se cuele otro mensaje."""
    siguiente = nodos.encolar(con, "conversar", pedido, id_conversacion)
    chat.poner_trabajo(con, id_conversacion, siguiente)
    return siguiente


def _responder(con, id_conversacion: str, vector: list[float] | None) -> None:
    _seguir(con, id_conversacion, _pedido(con, id_conversacion, vector))


def _rescatar_busquedas(con) -> None:
    """Una búsqueda por significado que nadie tomó a tiempo no frena la respuesta: se responde solo por palabras."""
    limite = datetime.now(timezone.utc) - timedelta(seconds=ESPERA_SIGNIFICADO_S)
    for id_, creado, conversacion in nodos.pendientes(con, "embedding", con_conversacion=True):
        if datetime.fromisoformat(creado) < limite and nodos.abandonar(con, id_):
            _responder(con, conversacion, None)


def _repartir_embeddings(con) -> None:
    """Los recuerdos sin vector, nuevos o de antes, salen en lotes mientras haya un nodo que pueda calcularlos."""
    while len(nodos.pendientes(con, "embedding", con_conversacion=False)) < 2:
        faltan = significado.faltantes(con)
        if not faltan:
            return
        trabajo = nodos.encolar(con, "embedding", {"input": [t for _, t in faltan], "recuerdos": [i for i, _ in faltan]})
        significado.apartar(con, [i for i, _ in faltan], trabajo)


@app.post("/nodos", status_code=201, response_model=nodos.NodoCreado, dependencies=[Depends(exigir_clave_admin)])
def crear_nodo(nuevo: nodos.NodoNuevo, con=Depends(conexion)) -> nodos.NodoCreado:
    """Solo para los equipos de Sergio: un nodo ve todo lo que viaja en sus trabajos."""
    return nodos.crear(con, nuevo)


@app.get("/nodos", response_model=list[nodos.Nodo], dependencies=[Depends(exigir_clave)])
def listar_nodos(con=Depends(conexion)) -> list[nodos.Nodo]:
    return nodos.listar(con)


@app.patch("/nodos/{id_}", response_model=nodos.Nodo, dependencies=[Depends(exigir_clave_admin)])
def cambiar_nodo(id_: str, cambios: nodos.CambiosNodo, con=Depends(conexion)) -> nodos.Nodo:
    """Archiva o restaura (archivado, el nodo pierde su clave; no hay DELETE, decisión 8) y cambia sus ajustes."""
    nodo = nodos.cambiar(con, id_, cambios)
    if nodo is None:
        raise HTTPException(status_code=404, detail="No existe ese nodo.")
    return nodo


@app.post("/nodo/latido", response_model=nodos.Nodo)
def latir(latido: nodos.Latido, id_nodo: str = Depends(nodo_autenticado), con=Depends(conexion)) -> nodos.Nodo:
    nodo = nodos.latir(con, id_nodo, latido)
    if nodos.mejor_modelo("embedding", nodo.modo, nodo.prestados()):
        _repartir_embeddings(con)
    return nodo


@app.post("/nodo/trabajos/tomar", response_model=nodos.Trabajo | None)
def tomar_trabajo(response: Response, id_nodo: str = Depends(nodo_autenticado), con=Depends(conexion)):
    """Un trabajo para este nodo, o 204 si no hay ninguno que pueda o le toque atender."""
    _rescatar_busquedas(con)
    trabajo = nodos.tomar(con, id_nodo)
    if trabajo is None:
        return Response(status_code=204)
    return trabajo


@app.post("/nodo/trabajos/{id_}", status_code=204)
def entregar_trabajo(
    id_: int, resultado: nodos.Resultado, id_nodo: str = Depends(nodo_autenticado), con=Depends(conexion)
) -> Response:
    if (resultado.salida is None) == (resultado.error is None):
        raise HTTPException(status_code=422, detail="Manda salida o error, uno de los dos.")
    tomado = nodos.tomado_por(con, id_, id_nodo)
    if tomado is None:
        raise HTTPException(status_code=409, detail="Ese trabajo no está tomado por este nodo.")
    if resultado.salida is not None:
        if tomado["necesidad"] == "conversar":
            respuesta = _respuesta_de(resultado.salida)
            if respuesta is None:
                raise HTTPException(status_code=422, detail="La salida no trae mensaje.content ni tool_calls válidas.")
            if respuesta[2] and not tomado["entrada"].get("tools"):
                # Llamadas sin herramientas ofrecidas (pasado el límite de rondas): no abren otra ronda. Con texto, es la
                # respuesta; sin texto, es un error que se reintenta, así que la conversación siempre termina.
                if respuesta[0]:
                    respuesta = (respuesta[0], respuesta[1], [])
                else:
                    resultado = nodos.Resultado(error="El modelo pidió herramientas sin que se le ofrecieran.")
        else:
            vectores = _vectores_de(resultado.salida, len(tomado["entrada"]["input"]))
            if vectores is None:
                raise HTTPException(status_code=422, detail="La salida no trae un vector por cada texto.")

    # Lo que sigue en la conversación se deja listo antes de cerrar este trabajo (ver _seguir).
    conversacion = tomado["conversacion_id"]
    falla = resultado.error is not None
    ultimo_intento = falla and tomado["intentos"] + 1 >= nodos.INTENTOS
    if conversacion and (not falla or ultimo_intento):
        if tomado["necesidad"] == "embedding":  # la búsqueda por significado del mensaje
            _responder(con, conversacion, None if falla else vectores[0])
        elif not falla:
            texto, mensaje, llamadas = respuesta
            if llamadas:
                _ronda_de_herramientas(con, conversacion, tomado["entrada"], mensaje, llamadas)
            else:
                _decir(con, conversacion, "assistant", chat.ORIGEN_ASHUR, texto)
    try:
        estado, fila = nodos.entregar(con, id_nodo, id_, resultado)
    except nodos.TrabajoAjeno:
        raise HTTPException(status_code=409, detail="Ese trabajo no está tomado por este nodo.") from None
    if not conversacion:  # un lote de recuerdos
        if estado == "hecho":
            significado.guardar(con, fila["entrada"]["recuerdos"], vectores, fila["modelo"])
        elif estado == "fallido":
            _lote_fallido(con, id_, fila["entrada"])
    return Response(status_code=204)


def _lote_fallido(con, trabajo: int, entrada: dict) -> None:
    """Un lote que falló tres veces se reparte de a uno, para que un recuerdo que siempre falla no deje sin vector a
    los demás. Si falla uno solo, se queda sin vector: solo se encuentra por palabras."""
    if len(entrada["recuerdos"]) == 1:
        significado.abandonar(con, trabajo)
        return
    for recuerdo, texto in zip(entrada["recuerdos"], entrada["input"]):
        uno = nodos.encolar(con, "embedding", {"input": [texto], "recuerdos": [recuerdo]})
        significado.apartar(con, [recuerdo], uno)


def _vectores_de(salida: dict, cuantos: int) -> list[list[float]] | None:
    """Los embeddings: {"vectores": [[...], ...]}, uno por cada texto de la entrada, todos del mismo largo."""
    vectores = salida.get("vectores")
    if not isinstance(vectores, list) or len(vectores) != cuantos or not vectores:
        return None
    largo = len(vectores[0]) if isinstance(vectores[0], list) else 0
    for v in vectores:
        if not isinstance(v, list) or len(v) != largo or largo == 0:
            return None
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
            return None
    return vectores


def _respuesta_de(salida: dict) -> tuple[str, dict, list] | None:
    """La respuesta del modelo, en el formato de OpenAI: {"mensaje": {"role": "assistant", "content": "...",
    "tool_calls": [...]}}. Vale con texto, con llamadas a herramientas, o con las dos; vacía no vale."""
    mensaje = salida.get("mensaje")
    if not isinstance(mensaje, dict):
        return None
    contenido = mensaje.get("content") or ""
    llamadas = herramientas.llamadas_de(mensaje)
    if not isinstance(contenido, str) or llamadas is None or (not contenido.strip() and not llamadas):
        return None
    return contenido.strip(), mensaje, llamadas


def _ronda_de_herramientas(con, id_conversacion: str, entrada: dict, mensaje: dict, llamadas: list) -> None:
    """Corre lo que pidió el modelo, solo entre lo que se le ofreció en este trabajo, y deja la ronda siguiente. Tras
    herramientas.RONDAS rondas, el modelo responde sin herramientas: la conversación siempre termina en texto."""
    _, duenio = chat.duenio(con, id_conversacion)
    # Lo que se ofreció en este trabajo y que el rol actual todavía permite: quitar un rol corta en la ronda siguiente.
    ofrecidas = herramientas.herramientas_para(con, duenio, registro_de_modulos())
    nombres = {t["function"]["name"] for t in entrada.get("tools", [])}
    ofrecidas = [h for h in ofrecidas if h.nombre in nombres]
    permitidos = _permitidos(con, id_conversacion)
    resultados = []
    for nombre, argumentos in llamadas:
        try:
            texto = herramientas.correr(
                con, nombre, argumentos, ofrecidas, lambda m, a, p: _modulo_desde_el_chat(con, m, a, p, duenio),
                permitidos,
            )
        except Exception as e:  # todo error es texto para el modelo; si la ronda fallara, se repetiría entera
            texto = f"La herramienta {nombre} falló: {type(e).__name__}: {e}"
        resultados.append((nombre, texto))
    rondas = entrada.get("rondas", 0) + 1
    siguientes = entrada.get("tools") if rondas < herramientas.RONDAS else None
    mensaje = {**mensaje, "tool_calls": herramientas.normalizar(mensaje.get("tool_calls") or [])}
    _seguir(con, id_conversacion, chat.otra_ronda(entrada, mensaje, resultados, siguientes))


def _modulo_desde_el_chat(con, id_modulo: str, accion: str, parametros: dict, pedido_por: str | None = None) -> str:
    """Una acción que solo lee corre ya; una que escribe queda como pedido, igual que desde POST /modulos/... ."""
    modulo = registro_de_modulos().modulos.get(id_modulo)
    definicion = modulo.accion(accion) if modulo else None
    if definicion is None:
        return f"El módulo {id_modulo} ya no tiene la acción {accion}."
    if definicion.escribe:
        pedido = modulos.pedir(con, id_modulo, accion, parametros, pedido_por)
        return f"Quedó pendiente de la aprobación de Sergio (pedido {pedido.id}). Todavía no se hizo."
    try:
        resultado = modulos.ejecutar(modulo, accion, parametros, _contexto(con, id_modulo))
    except modulos.ErrorDeModulo as e:
        return f"El módulo {id_modulo} falló: {e.mensaje}"
    return json.dumps(resultado, ensure_ascii=False, default=str)  # fechas o conjuntos no tumban la ronda


# ── Módulos (docs/adr/0013-modulos-en-el-core.md) ──


@lru_cache
def _registro(carpeta: str) -> modulos.Registro:
    return modulos.descubrir(modulos.Path(carpeta))


def registro_de_modulos() -> modulos.Registro:
    """Los módulos se descubren una vez por carpeta, al primer pedido."""
    return _registro(str(modulos.carpeta_por_defecto()))


@app.get(
    "/modulos/{id_}/ajustes", response_model=list[modulos.EstadoAjuste], dependencies=[Depends(exigir_clave)]
)
def ver_ajustes_de_modulo(id_: str, con=Depends(conexion)) -> list[modulos.EstadoAjuste]:
    modulo = registro_de_modulos().modulos.get(id_)
    if modulo is None:
        raise HTTPException(status_code=404, detail="No hay un módulo registrado con ese id.")
    return modulos.ajustes_de(con, modulo.manifiesto)


@app.patch(
    "/modulos/{id_}/ajustes", response_model=list[modulos.EstadoAjuste], dependencies=[Depends(exigir_clave_admin)]
)
def cambiar_ajustes_de_modulo(id_: str, cambios: dict, con=Depends(conexion)) -> list[modulos.EstadoAjuste]:
    """Solo los ajustes enviados; null vuelve al por_defecto."""
    modulo = registro_de_modulos().modulos.get(id_)
    if modulo is None:
        raise HTTPException(status_code=404, detail="No hay un módulo registrado con ese id.")
    try:
        return modulos.cambiar_ajustes(con, modulo.manifiesto, cambios)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


def _contexto(con, id_modulo: str) -> modulos.Contexto:
    def guardar(datos: dict) -> dict:
        try:
            nuevo = memoria.RecuerdoNuevo.model_validate(datos)
        except ValueError as e:
            raise ValueError(f"El recuerdo del módulo no cumple el contrato: {e}") from None
        return _guardar_recuerdo(con, nuevo).model_dump(mode="json")

    def ajuste(id_ajuste: str):
        modulo = registro_de_modulos().modulos.get(id_modulo)
        return modulos.valor_de(con, modulo.manifiesto, id_ajuste) if modulo else None

    return modulos.Contexto(id_modulo, guardar, ajuste)


def _correr(con, modulo: modulos.ModuloCargado, accion: str, parametros: dict) -> dict:
    try:
        return modulos.ejecutar(modulo, accion, parametros, _contexto(con, modulo.manifiesto.id))
    except modulos.ErrorDeModulo as e:
        raise HTTPException(status_code=502, detail=f"El módulo {modulo.manifiesto.id} falló: {e.mensaje}") from None


@app.get("/modulos", response_model=list[modulos.EstadoModulo], dependencies=[Depends(exigir_clave)])
def listar_modulos() -> list[modulos.EstadoModulo]:
    return registro_de_modulos().estados()


@app.post("/modulos/{id_}/acciones/{accion}", dependencies=[Depends(exigir_clave)])
def correr_accion(id_: str, accion: str, response: Response, parametros: dict | None = None, con=Depends(conexion)):
    """Una acción que solo lee corre ya. Una que escribe queda como pedido pendiente (202) hasta que un administrador
    la apruebe."""
    modulo = registro_de_modulos().modulos.get(id_)
    if modulo is None:
        raise HTTPException(status_code=404, detail="No hay un módulo registrado con ese id.")
    definicion = modulo.accion(accion)
    if definicion is None:
        raise HTTPException(status_code=404, detail="Ese módulo no tiene esa acción.")
    if definicion.escribe:
        response.status_code = 202
        return modulos.pedir(con, id_, accion, parametros or {}).model_dump()
    return {"resultado": _correr(con, modulo, accion, parametros or {})}


@app.get("/pedidos", response_model=list[modulos.Pedido], dependencies=[Depends(exigir_clave)])
def listar_pedidos(estado: str | None = None, con=Depends(conexion)) -> list[modulos.Pedido]:
    return modulos.listar_pedidos(con, estado)


@app.post("/pedidos/{id_}/aprobar", response_model=modulos.Pedido, dependencies=[Depends(exigir_clave_admin)])
def aprobar_pedido(id_: int, con=Depends(conexion)) -> modulos.Pedido:
    pedido = modulos.obtener_pedido(con, id_)
    if pedido is None:
        raise HTTPException(status_code=404, detail="No existe ese pedido.")
    modulo = registro_de_modulos().modulos.get(pedido.modulo)
    if modulo is None or modulo.accion(pedido.accion) is None:
        raise HTTPException(status_code=409, detail="El módulo o la acción de ese pedido ya no están registrados.")
    if not modulos.tomar_pendiente(con, id_, "corriendo"):
        raise HTTPException(status_code=409, detail="Ese pedido ya no está pendiente.")
    try:
        resultado = modulos.ejecutar(modulo, pedido.accion, pedido.parametros, _contexto(con, pedido.modulo))
    except modulos.ErrorDeModulo as e:
        modulos.cerrar_pedido(con, id_, "fallido", None, e.mensaje)
        raise HTTPException(status_code=502, detail=f"El módulo {pedido.modulo} falló: {e.mensaje}") from None
    modulos.cerrar_pedido(con, id_, "hecho", resultado, None)
    return modulos.obtener_pedido(con, id_)


@app.post("/pedidos/{id_}/rechazar", response_model=modulos.Pedido, dependencies=[Depends(exigir_clave_admin)])
def rechazar_pedido(id_: int, con=Depends(conexion)) -> modulos.Pedido:
    if modulos.obtener_pedido(con, id_) is None:
        raise HTTPException(status_code=404, detail="No existe ese pedido.")
    if not modulos.tomar_pendiente(con, id_, "rechazado"):
        raise HTTPException(status_code=409, detail="Ese pedido ya no está pendiente.")
    return modulos.obtener_pedido(con, id_)
