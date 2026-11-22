import os
import secrets
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Response, Security
from fastapi.security import APIKeyHeader

from ashur_core import memoria

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


def conexion() -> Iterator:
    con = memoria.abrir(os.environ.get("ASHUR_DB", "/datos/ashur.db"))
    try:
        yield con
    finally:
        con.close()


@app.get("/vivo")
def vivo() -> dict[str, bool]:
    return {"vivo": True}


@app.post("/recuerdos", status_code=201, response_model=memoria.Recuerdo, dependencies=[Depends(exigir_clave)])
def crear_recuerdo(nuevo: memoria.RecuerdoNuevo, con=Depends(conexion)) -> memoria.Recuerdo:
    return memoria.crear(con, nuevo)


@app.get("/recuerdos", response_model=list[memoria.Recuerdo], dependencies=[Depends(exigir_clave)])
def listar_recuerdos(buscar: str | None = None, con=Depends(conexion)) -> list[memoria.Recuerdo]:
    """Sin buscar, todos los recuerdos. Con buscar, los que tienen esas palabras, los más relevantes primero."""
    return memoria.listar(con) if buscar is None else memoria.buscar(con, buscar)


@app.patch("/recuerdos/{id_}", response_model=memoria.Recuerdo, dependencies=[Depends(exigir_clave_admin)])
def editar_recuerdo(id_: int, cambios: memoria.CambiosRecuerdo, con=Depends(conexion)) -> memoria.Recuerdo:
    editado = memoria.editar(con, id_, cambios)
    if editado is None:
        raise HTTPException(status_code=404, detail="No existe ese recuerdo.")
    return editado


@app.delete("/recuerdos/{id_}", status_code=204, dependencies=[Depends(exigir_clave_admin)])
def borrar_recuerdo(id_: int, con=Depends(conexion)) -> Response:
    if not memoria.borrar(con, id_):
        raise HTTPException(status_code=404, detail="No existe ese recuerdo.")
    return Response(status_code=204)


@app.get("/aprendizaje", response_model=memoria.Aprendizaje, dependencies=[Depends(exigir_clave)])
def ver_aprendizaje(con=Depends(conexion)) -> memoria.Aprendizaje:
    return memoria.aprendizaje(con)


@app.patch("/aprendizaje", response_model=memoria.Aprendizaje, dependencies=[Depends(exigir_clave_admin)])
def cambiar_inicio(cambio: memoria.CambioInicio, con=Depends(conexion)) -> memoria.Aprendizaje:
    return memoria.cambiar_inicio(con, cambio.inicio)
