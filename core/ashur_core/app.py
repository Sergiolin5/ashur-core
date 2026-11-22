import os
import secrets
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Response, Security
from fastapi.security import APIKeyHeader

from functools import lru_cache

from ashur_core import chat, galaxia, identidades, inventario, memoria, modulos, nodos

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
    """Editar, archivar o restaurar. No hay DELETE: se archiva (decisión 8)."""
    editada = identidades.editar(con, id_, cambios)
    if editada is None:
        raise HTTPException(status_code=404, detail="No existe esa identidad.")
    return editada


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


def _completa(con, conversacion: chat.Conversacion) -> chat.ConversacionCompleta:
    trabajo = chat.trabajo_actual(con, conversacion.id)
    estado = nodos.estado_de(con, trabajo) if trabajo is not None else None
    espera = chat.Espera(**estado) if estado and estado["estado"] != "hecho" else None
    return chat.ConversacionCompleta(conversacion=conversacion, mensajes=chat.mensajes(con, conversacion.id), espera=espera)


def _decir(con, id_conversacion: str, rol: str, origen: str, texto: str) -> chat.Mensaje:
    """Todo mensaje del chat también es un recuerdo, por el mismo camino que POST /recuerdos."""
    fecha = chat.ahora()
    recuerdo = _guardar_recuerdo(
        con,
        memoria.RecuerdoNuevo(
            texto=texto, origen=origen, fecha=fecha, sensibilidad="normal", identidades=[], objetos=[], opinion=None
        ),
    )
    return chat.agregar(con, id_conversacion, rol, texto, fecha, recuerdo.id)


@app.post("/conversaciones", status_code=201, response_model=chat.Conversacion, dependencies=[Depends(exigir_clave)])
def crear_conversacion(con=Depends(conexion)) -> chat.Conversacion:
    return chat.crear(con)


@app.get("/conversaciones", response_model=list[chat.Conversacion], dependencies=[Depends(exigir_clave)])
def listar_conversaciones(con=Depends(conexion)) -> list[chat.Conversacion]:
    return chat.listar(con)


@app.get(
    "/conversaciones/{id_}", response_model=chat.ConversacionCompleta, dependencies=[Depends(exigir_clave)]
)
def ver_conversacion(id_: str, con=Depends(conexion)) -> chat.ConversacionCompleta:
    conversacion = chat.obtener(con, id_)
    if conversacion is None:
        raise HTTPException(status_code=404, detail="No existe esa conversación.")
    return _completa(con, conversacion)


@app.post(
    "/conversaciones/{id_}/mensajes", status_code=202, response_model=chat.ConversacionCompleta,
    dependencies=[Depends(exigir_clave)],
)
def enviar_mensaje(id_: str, nuevo: chat.MensajeNuevo, con=Depends(conexion)) -> chat.ConversacionCompleta:
    """Guarda el mensaje y deja en la cola el pedido al modelo. La respuesta llega cuando un nodo la entregue."""
    conversacion = chat.obtener(con, id_)
    if conversacion is None:
        raise HTTPException(status_code=404, detail="No existe esa conversación.")
    trabajo = nodos.encolar(con, "conversar", {}, id_, estado="preparando")
    if not chat.reservar(con, id_, trabajo):
        nodos.descartar(con, trabajo)
        raise HTTPException(status_code=409, detail="Ashur todavía está respondiendo el mensaje anterior.")
    _decir(con, id_, "user", chat.ORIGEN_SERGIO, nuevo.texto)
    nodos.preparar(con, trabajo, chat.pedido_al_modelo(con, id_))
    return _completa(con, chat.obtener(con, id_))


@app.post("/nodos", status_code=201, response_model=nodos.NodoCreado, dependencies=[Depends(exigir_clave_admin)])
def crear_nodo(nuevo: nodos.NodoNuevo, con=Depends(conexion)) -> nodos.NodoCreado:
    """Solo para los equipos de Sergio: un nodo ve todo lo que viaja en sus trabajos."""
    return nodos.crear(con, nuevo)


@app.get("/nodos", response_model=list[nodos.Nodo], dependencies=[Depends(exigir_clave)])
def listar_nodos(con=Depends(conexion)) -> list[nodos.Nodo]:
    return nodos.listar(con)


@app.patch("/nodos/{id_}", response_model=nodos.Nodo, dependencies=[Depends(exigir_clave_admin)])
def archivar_nodo(id_: str, cambios: nodos.CambiosNodo, con=Depends(conexion)) -> nodos.Nodo:
    """Archivado, el nodo pierde su clave. No hay DELETE (decisión 8)."""
    nodo = nodos.archivar(con, id_, cambios.archivado)
    if nodo is None:
        raise HTTPException(status_code=404, detail="No existe ese nodo.")
    return nodo


@app.post("/nodo/latido", response_model=nodos.Nodo)
def latir(latido: nodos.Latido, id_nodo: str = Depends(nodo_autenticado), con=Depends(conexion)) -> nodos.Nodo:
    return nodos.latir(con, id_nodo, latido)


@app.post("/nodo/trabajos/tomar", response_model=nodos.Trabajo | None)
def tomar_trabajo(response: Response, id_nodo: str = Depends(nodo_autenticado), con=Depends(conexion)):
    """Un trabajo para este nodo, o 204 si no hay ninguno que pueda o le toque atender."""
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
    if resultado.salida is not None:
        texto = _texto_de(resultado.salida)
        if texto is None:
            raise HTTPException(status_code=422, detail="La salida no trae mensaje.content.")
    try:
        estado, fila = nodos.entregar(con, id_nodo, id_, resultado)
    except nodos.TrabajoAjeno:
        raise HTTPException(status_code=409, detail="Ese trabajo no está tomado por este nodo.") from None
    if estado == "hecho" and fila["necesidad"] == "conversar" and fila["conversacion_id"]:
        _decir(con, fila["conversacion_id"], "assistant", chat.ORIGEN_ASHUR, texto)
    return Response(status_code=204)


def _texto_de(salida: dict) -> str | None:
    """La respuesta del modelo, en el formato de OpenAI: {"mensaje": {"role": "assistant", "content": "..."}}."""
    mensaje = salida.get("mensaje")
    contenido = mensaje.get("content") if isinstance(mensaje, dict) else None
    return contenido.strip() if isinstance(contenido, str) and contenido.strip() else None


# ── Módulos (docs/adr/0013-modulos-en-el-core.md) ──


@lru_cache
def _registro(carpeta: str) -> modulos.Registro:
    return modulos.descubrir(modulos.Path(carpeta))


def registro_de_modulos() -> modulos.Registro:
    """Los módulos se descubren una vez por carpeta, al primer pedido."""
    return _registro(str(modulos.carpeta_por_defecto()))


def _contexto(con, id_modulo: str) -> modulos.Contexto:
    def guardar(datos: dict) -> dict:
        try:
            nuevo = memoria.RecuerdoNuevo.model_validate(datos)
        except ValueError as e:
            raise ValueError(f"El recuerdo del módulo no cumple el contrato: {e}") from None
        return _guardar_recuerdo(con, nuevo).model_dump(mode="json")

    return modulos.Contexto(id_modulo, guardar)


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
