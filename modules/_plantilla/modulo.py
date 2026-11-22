"""Módulo de ejemplo. Cada acción del manifiesto es una función con este mismo nombre.

Firma de una acción: def <accion>(contexto, **parametros) -> dict
- contexto.recordar(texto, ...) guarda un recuerdo en el core con origen igual al id del módulo.
- Los parámetros llegan del JSON del pedido. Lo que devuelve tiene que ser un dict, que se manda tal cual.
- Un módulo no importa nada del core ni de otro módulo, y no guarda memoria propia.
"""


def saludar(contexto, nombre: str = "mundo") -> dict:
    saludo = f"Hola, {nombre}."
    contexto.recordar(f"La plantilla saludó a {nombre}.")
    return {"saludo": saludo}
