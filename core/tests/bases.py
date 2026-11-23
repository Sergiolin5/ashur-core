"""Para las pruebas de migraciones: deja una base nueva como estaba en una versión anterior del esquema."""

import sqlite3

# Lo que agregó cada versión desde la 9, de la más nueva a la más vieja.
_AGREGADO = {
    15: ["TRIGGER mensajes_ai", "TRIGGER mensajes_ad", "TRIGGER mensajes_au", "TABLE mensajes_busqueda",
         "COLUMN recuerdos.mensaje_id"],
    14: ["COLUMN objetos.estado", "COLUMN objetos.evidencia", "COLUMN objetos.especificaciones",
         "COLUMN objetos.identificadores", "COLUMN objetos.ranuras", "COLUMN objetos.ranura", "COLUMN objetos.padre_id"],
    13: ["COLUMN conversaciones.corregida"],
    12: ["TABLE roles", "COLUMN identidades.clave_hash", "COLUMN identidades.rol",
         "COLUMN conversaciones.identidad_id", "COLUMN pedidos.pedido_por"],
    11: ["TABLE ajustes_modulos", "COLUMN nodos.ajustes"],
    10: ["TABLE embeddings"],
    9: ["TABLE conversaciones", "TABLE mensajes", "TABLE nodos", "TABLE trabajos"],
}


def recordar_del_chat(cliente, nodo, lineas="NADA") -> dict:
    """El nodo falso atiende el trabajo de fondo que sale tras cada respuesta de Ashur, en el que decide qué vale la
    pena recordar (docs/adr/0028-recuerdos-del-chat.md). Devuelve el trabajo."""
    tomado = cliente.post("/nodo/trabajos/tomar", headers=nodo)
    assert tomado.status_code == 200 and tomado.json()["entrada"]["proposito"] == "recuerdos"
    salida = {"mensaje": {"role": "assistant", "content": lineas}}
    assert cliente.post(f"/nodo/trabajos/{tomado.json()['id']}", json={"salida": salida}, headers=nodo).status_code == 204
    return tomado.json()


def _existe(con: sqlite3.Connection, tabla: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)).fetchone() is not None


def quitar_desde(con: sqlite3.Connection, version: int) -> None:
    """Borra lo que agregaron las versiones de [version] en adelante. No toca user_version."""
    for v in sorted(_AGREGADO, reverse=True):
        if v < version:
            break
        for cosa in _AGREGADO[v]:
            tipo, nombre = cosa.split(" ")
            if tipo == "COLUMN":
                tabla, columna = nombre.split(".")
                if _existe(con, tabla):
                    con.execute(f"ALTER TABLE {tabla} DROP COLUMN {columna}")
            else:
                con.execute(f"DROP {tipo} IF EXISTS {nombre}")
