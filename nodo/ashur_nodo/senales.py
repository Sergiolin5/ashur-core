"""Lectores de señales de cada sistema. Si algo no se puede leer, la señal queda en None y la política decide sin ella.

Windows: ctypes de la librería estándar. macOS: ioreg y pmset, que vienen con el sistema (sin probar todavía, ver
docs/adr/0017-programa-del-nodo.md).
"""

from __future__ import annotations

import re
import subprocess
import sys
import time

from ashur_nodo.politica import Senales


def leer(carga_ajena: float | None) -> Senales:
    """[carga_ajena] la mide el nodo entre trabajos, para no contar su propio modelo."""
    if sys.platform == "win32":
        inactivo, enchufado, bateria = _windows()
    elif sys.platform == "darwin":
        inactivo, enchufado, bateria = _mac()
    else:
        inactivo, enchufado, bateria = None, None, None
    return Senales(inactivo_s=inactivo, carga_ajena=carga_ajena, enchufado=enchufado, bateria=bateria)


def carga(muestra_s: float = 1.0) -> float | None:
    """La carga total del procesador durante [muestra_s] segundos, de 0 a 1."""
    if sys.platform == "win32":
        return _carga_windows(muestra_s)
    if sys.platform == "darwin":
        return _carga_mac()
    return None


# ── Windows ──


def _windows() -> tuple[float | None, bool | None, int | None]:
    import ctypes
    from ctypes import wintypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte), ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte), ("BatteryLifeTime", wintypes.DWORD),
            ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    inactivo = None
    info = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        inactivo = ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000

    enchufado = bateria = None
    estado = SYSTEM_POWER_STATUS()
    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(estado)):
        sin_bateria = estado.BatteryFlag == 128
        if estado.ACLineStatus in (0, 1):
            enchufado = None if sin_bateria else estado.ACLineStatus == 1
        if not sin_bateria and estado.BatteryLifePercent <= 100:
            bateria = estado.BatteryLifePercent
    return inactivo, enchufado, bateria


def _carga_windows(muestra_s: float) -> float | None:
    import ctypes
    from ctypes import wintypes

    def tiempos():
        inactivo, nucleo, usuario = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(inactivo), ctypes.byref(nucleo), ctypes.byref(usuario)):
            return None
        valor = lambda f: (f.dwHighDateTime << 32) | f.dwLowDateTime  # noqa: E731
        return valor(inactivo), valor(nucleo) + valor(usuario)  # el tiempo de núcleo incluye el inactivo

    antes = tiempos()
    time.sleep(muestra_s)
    despues = tiempos()
    if antes is None or despues is None or despues[1] == antes[1]:
        return None
    return max(0.0, min(1.0, 1 - (despues[0] - antes[0]) / (despues[1] - antes[1])))


# ── macOS (sin probar) ──


def _mac() -> tuple[float | None, bool | None, int | None]:
    inactivo = enchufado = bateria = None
    try:
        salida = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True, timeout=5).stdout
        encontrado = re.search(r'"HIDIdleTime" = (\d+)', salida)
        if encontrado:
            inactivo = int(encontrado.group(1)) / 1e9
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        salida = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
        if "InternalBattery" in salida:
            enchufado = "AC Power" in salida
            encontrado = re.search(r"(\d+)%", salida)
            bateria = int(encontrado.group(1)) if encontrado else None
    except (OSError, subprocess.SubprocessError):
        pass
    return inactivo, enchufado, bateria


def _carga_mac() -> float | None:
    import os

    try:
        return min(1.0, os.getloadavg()[0] / (os.cpu_count() or 1))
    except OSError:
        return None
