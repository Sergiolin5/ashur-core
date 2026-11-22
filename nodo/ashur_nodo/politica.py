"""Cuánto se ofrece el equipo a Ashur: full, light, busy u off (docs/adr/0017-programa-del-nodo.md).

Sergio siempre gana en sus máquinas (docs/REFERENCIA-ANTERIOR.md, punto 4). Es una función pura: se prueba en
cualquier sistema, y solo los lectores de señales dependen del sistema (punto 5).
"""

from __future__ import annotations

from dataclasses import dataclass

# Sin tocar el equipo por este tiempo, Sergio no lo está usando.
INACTIVO_S = 300
# Con esta carga de otros programas, el equipo está ocupado.
CARGA_OCUPADO = 0.7
# Con batería por debajo de este porcentaje y sin cargador, el equipo no presta nada.
BATERIA_MINIMA = 30


@dataclass(frozen=True)
class Senales:
    inactivo_s: float | None  # None: el sistema no lo informa
    carga_ajena: float | None  # 0 a 1, de otros programas; None si no se pudo medir
    enchufado: bool | None  # None: sin batería o no se sabe
    bateria: int | None  # porcentaje


def modo(s: Senales) -> str:
    """off: batería baja sin cargador. busy: otros programas cargan el equipo. light: Sergio lo está usando, o va con
    batería. full: el equipo está libre y enchufado."""
    if s.enchufado is False and s.bateria is not None and s.bateria < BATERIA_MINIMA:
        return "off"
    if s.carga_ajena is not None and s.carga_ajena >= CARGA_OCUPADO:
        return "busy"
    if s.enchufado is False:
        return "light"
    if s.inactivo_s is not None and s.inactivo_s < INACTIVO_S:
        return "light"
    return "full"


def en_horario(horario: dict | None, hora: str) -> bool:
    """Si la hora local ("HH:MM") cae dentro del horario que Sergio le puso al nodo en el core. Sin horario, siempre.
    Si hasta < desde, el horario cruza la medianoche (docs/adr/0019-ajustes-de-modulos-y-nodos.md)."""
    if not horario:
        return True
    desde, hasta = horario["desde"], horario["hasta"]
    if desde <= hasta:
        return desde <= hora < hasta
    return hora >= desde or hora < hasta
