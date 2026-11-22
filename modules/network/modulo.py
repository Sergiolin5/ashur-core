"""Ashur Network: análisis de observaciones de redes y dispositivos.

Las acciones procesan datos recibidos como parámetros. No escanean redes,
no abren conexiones, no ejecutan comandos y no guardan estado propio.

Firma de cada acción: def <accion>(contexto, **parametros) -> dict
"""

from datetime import datetime
import ipaddress
import re


_PATRON_MAC = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
# Los identificadores terminan en recuerdos que lee el modelo: sin espacios, no caben frases ni instrucciones.
_PATRON_IDENTIFICADOR = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_PATRON_CLAVE = re.compile(r"^(?:id|mac):[A-Za-z0-9._:-]{1,140}$")
_PROTOCOLOS = {"tcp", "udp"}

_REGLAS_PUERTOS = {
    (21, "tcp"): ("advertencia", "FTP puede transmitir credenciales o datos sin cifrar."),
    (22, "tcp"): ("atencion", "SSH debe estar restringido y protegido."),
    (23, "tcp"): ("advertencia", "Telnet transmite información sin cifrado."),
    (445, "tcp"): ("atencion", "SMB merece revisión de exposición y segmentación."),
    (3389, "tcp"): ("advertencia", "RDP merece revisión de exposición y controles de acceso."),
    (5900, "tcp"): ("advertencia", "VNC merece revisión de exposición y autenticación."),
}

_CAMPOS = (
    ("ips", "direcciones IP"),
    ("hostnames", "hostnames"),
    ("sistemas", "sistemas informados"),
    ("servicios", "servicios"),
    ("macs", "direcciones MAC"),
    ("redes", "redes"),
)
_ETIQUETAS = dict(_CAMPOS)


def _identificador(valor, campo, obligatorio=False):
    valor = _texto(valor, campo, obligatorio)
    if valor is not None and not _PATRON_IDENTIFICADOR.fullmatch(valor):
        raise ValueError(f"{campo} solo admite letras, números, «.», «_», «:» y «-», hasta 64.")
    return valor


def _ordenar_ips(ips):
    return sorted(ips, key=lambda ip: (ipaddress.ip_address(ip).version, ipaddress.ip_address(ip)))


def _texto(valor, campo, obligatorio=False):
    if valor is None and not obligatorio:
        return None
    if not isinstance(valor, str):
        raise ValueError(f"{campo} debe ser texto.")
    valor = valor.strip()
    if obligatorio and not valor:
        raise ValueError(f"{campo} no puede estar vacío.")
    return valor or None


def _normalizar_ip(valor):
    if not isinstance(valor, str):
        raise ValueError("Cada dirección IP debe ser texto.")
    try:
        return str(ipaddress.ip_address(valor.strip()))
    except ValueError:
        raise ValueError(f"Dirección IP no válida: {valor!r}.") from None


def _normalizar_observacion(observacion):
    if not isinstance(observacion, dict):
        raise ValueError("La observación debe ser un objeto.")

    agente_id = _texto(observacion.get("agente_id"), "agente_id", True)
    red_id = _identificador(observacion.get("red_id"), "red_id", True)
    observado_en = _texto(observacion.get("observado_en"), "observado_en", True)

    try:
        fecha = datetime.fromisoformat(observado_en.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("observado_en debe ser una fecha ISO 8601.") from None

    if fecha.tzinfo is None or fecha.utcoffset() is None:
        raise ValueError("observado_en debe incluir zona horaria.")

    dispositivo = observacion.get("dispositivo")
    if not isinstance(dispositivo, dict):
        raise ValueError("dispositivo debe ser un objeto.")

    id_dispositivo = _identificador(
        dispositivo.get("id_dispositivo"), "dispositivo.id_dispositivo"
    )
    hostname = _texto(dispositivo.get("hostname"), "dispositivo.hostname")
    sistema = _texto(dispositivo.get("sistema"), "dispositivo.sistema")

    mac = dispositivo.get("mac")
    if mac is not None:
        mac = _texto(mac, "dispositivo.mac", True)
        if not _PATRON_MAC.fullmatch(mac):
            raise ValueError("dispositivo.mac no tiene un formato MAC válido.")
        mac = mac.lower()

    ips = dispositivo.get("ips", [])
    if not isinstance(ips, list):
        raise ValueError("dispositivo.ips debe ser una lista.")
    ips_normalizadas = _ordenar_ips({_normalizar_ip(ip) for ip in ips})

    servicios = observacion.get("servicios", [])
    if not isinstance(servicios, list):
        raise ValueError("servicios debe ser una lista.")

    servicios_normalizados = {}
    for servicio in servicios:
        if not isinstance(servicio, dict):
            raise ValueError("Cada servicio debe ser un objeto.")

        puerto = servicio.get("puerto")
        if isinstance(puerto, bool) or not isinstance(puerto, int):
            raise ValueError("El puerto debe ser un entero.")
        if not 1 <= puerto <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535.")

        protocolo = _texto(servicio.get("protocolo"), "servicio.protocolo", True)
        protocolo = protocolo.lower()
        if protocolo not in _PROTOCOLOS:
            raise ValueError("El protocolo debe ser tcp o udp.")

        nombre = _texto(servicio.get("nombre"), "servicio.nombre")
        clave = (puerto, protocolo)
        servicios_normalizados[clave] = {
            "puerto": puerto,
            "protocolo": protocolo,
            "nombre": nombre,
        }

    return {
        "agente_id": agente_id,
        "red_id": red_id,
        "observado_en": fecha.isoformat(),
        "dispositivo": {
            "id_dispositivo": id_dispositivo,
            "hostname": hostname,
            "mac": mac,
            "ips": ips_normalizadas,
            "sistema": sistema,
        },
        "servicios": [
            servicios_normalizados[clave]
            for clave in sorted(servicios_normalizados)
        ],
    }


def _procesar_lista(observaciones):
    if not isinstance(observaciones, list):
        raise ValueError("observaciones debe ser una lista.")

    aceptadas = []
    rechazadas = []

    for indice, observacion in enumerate(observaciones):
        try:
            aceptadas.append(_normalizar_observacion(observacion))
        except (ValueError, TypeError) as error:
            rechazadas.append({
                "indice": indice,
                "motivo": str(error),
            })

    return aceptadas, rechazadas


def _clave_identidad(observacion):
    dispositivo = observacion["dispositivo"]
    id_dispositivo = dispositivo["id_dispositivo"]

    if id_dispositivo:
        return f"id:{id_dispositivo}", "alta"

    mac = dispositivo["mac"]
    if mac:
        return f"mac:{observacion['red_id']}:{mac}", "media"

    return None, "insuficiente"


def _consolidar(observaciones):
    aceptadas, rechazadas = _procesar_lista(observaciones)
    grupos = {}

    for indice, observacion in enumerate(aceptadas):
        clave, confianza = _clave_identidad(observacion)

        # Sin identidad suficientemente fuerte, no se fusionan observaciones.
        if clave is None:
            clave = f"sin_correlacion:{indice}"

        if clave not in grupos:
            grupos[clave] = {
                "clave_correlacion": (
                    None if confianza == "insuficiente" else clave
                ),
                "confianza_identidad": confianza,
                "redes": set(),
                "agentes": set(),
                "hostname": set(),
                "sistemas": set(),
                "macs": set(),
                "ips": set(),
                "servicios": {},
                "observaciones": 0,
            }

        grupo = grupos[clave]
        dispositivo = observacion["dispositivo"]

        grupo["redes"].add(observacion["red_id"])
        grupo["agentes"].add(observacion["agente_id"])
        grupo["observaciones"] += 1

        if dispositivo["hostname"]:
            grupo["hostname"].add(dispositivo["hostname"])
        if dispositivo["sistema"]:
            grupo["sistemas"].add(dispositivo["sistema"])
        if dispositivo["mac"]:
            grupo["macs"].add(dispositivo["mac"])

        grupo["ips"].update(dispositivo["ips"])

        for servicio in observacion["servicios"]:
            clave_servicio = (servicio["puerto"], servicio["protocolo"])
            grupo["servicios"][clave_servicio] = servicio

    servidores = []
    for clave in sorted(grupos):
        grupo = grupos[clave]
        servidores.append({
            "clave_correlacion": grupo["clave_correlacion"],
            "confianza_identidad": grupo["confianza_identidad"],
            "redes": sorted(grupo["redes"]),
            "agentes": sorted(grupo["agentes"]),
            "hostnames": sorted(grupo["hostname"]),
            "sistemas": sorted(grupo["sistemas"]),
            "macs": sorted(grupo["macs"]),
            "ips": _ordenar_ips(grupo["ips"]),
            "servicios": [
                grupo["servicios"][k]
                for k in sorted(grupo["servicios"])
            ],
            "cantidad_observaciones": grupo["observaciones"],
        })

    return servidores, rechazadas


def analizar_observaciones(contexto, observaciones=None, **parametros) -> dict:
    """Valida y normaliza una lista de observaciones."""
    observaciones = [] if observaciones is None else observaciones
    aceptadas, rechazadas = _procesar_lista(observaciones)

    return {
        "observaciones": aceptadas,
        "aceptadas": len(aceptadas),
        "rechazadas": rechazadas,
        "total": len(observaciones),
    }


def consolidar_servidores(contexto, observaciones=None, **parametros) -> dict:
    """Agrupa observaciones sin fusionar identidades ambiguas."""
    servidores, rechazadas = _consolidar([] if observaciones is None else observaciones)

    return {
        "servidores": servidores,
        "cantidad": len(servidores),
        "rechazadas": rechazadas,
    }


def comparar_observaciones(
    contexto,
    anterior=None,
    actual=None,
    **parametros,
) -> dict:
    """Compara dos instantáneas y devuelve altas, bajas y cambios."""
    servidores_anteriores, rechazadas_anteriores = _consolidar([] if anterior is None else anterior)
    servidores_actuales, rechazadas_actuales = _consolidar([] if actual is None else actual)

    mapa_anterior = {
        servidor["clave_correlacion"]: servidor
        for servidor in servidores_anteriores
        if servidor["clave_correlacion"] is not None
    }
    mapa_actual = {
        servidor["clave_correlacion"]: servidor
        for servidor in servidores_actuales
        if servidor["clave_correlacion"] is not None
    }

    eventos = []

    for clave in sorted(mapa_actual.keys() - mapa_anterior.keys()):
        eventos.append({
            "tipo": "alta",
            "clave_correlacion": clave,
            "servidor": mapa_actual[clave],
            "detalle": "Dispositivo observado en la instantánea actual, no en la anterior.",
        })

    for clave in sorted(mapa_anterior.keys() - mapa_actual.keys()):
        eventos.append({
            "tipo": "baja",
            "clave_correlacion": clave,
            "servidor": mapa_anterior[clave],
            "detalle": "Dispositivo presente en la instantánea anterior y ausente en la actual.",
        })

    for clave in sorted(mapa_actual.keys() & mapa_anterior.keys()):
        antes = mapa_anterior[clave]
        despues = mapa_actual[clave]
        cambios = []

        for campo, etiqueta in _CAMPOS:
            if antes[campo] != despues[campo]:
                cambios.append({
                    "campo": campo,
                    "etiqueta": etiqueta,
                    "anterior": antes[campo],
                    "actual": despues[campo],
                })

        if cambios:
            eventos.append({
                "tipo": "cambio",
                "clave_correlacion": clave,
                "cambios": cambios,
                "servidor": despues,
                "detalle": "Se detectaron diferencias entre las instantáneas.",
            })

    no_correlacionables = (
        sum(s["clave_correlacion"] is None for s in servidores_anteriores)
        + sum(s["clave_correlacion"] is None for s in servidores_actuales)
    )

    return {
        "eventos": eventos,
        "resumen": {
            "altas": sum(e["tipo"] == "alta" for e in eventos),
            "bajas": sum(e["tipo"] == "baja" for e in eventos),
            "cambios": sum(e["tipo"] == "cambio" for e in eventos),
            "no_correlacionables": no_correlacionables,
        },
        "rechazadas": {
            "anterior": rechazadas_anteriores,
            "actual": rechazadas_actuales,
        },
    }


def analizar_exposicion(contexto, servidores=None, **parametros) -> dict:
    """Señala servicios que merecen revisión; no determina vulnerabilidades."""
    servidores = [] if servidores is None else servidores
    if not isinstance(servidores, list):
        raise ValueError("servidores debe ser una lista.")

    hallazgos = []

    for servidor in servidores:
        if not isinstance(servidor, dict):
            continue
        servicios = servidor.get("servicios", [])
        if not isinstance(servicios, list):
            continue

        for servicio in servicios:
            if not isinstance(servicio, dict):
                continue

            puerto = servicio.get("puerto")
            protocolo = servicio.get("protocolo")

            if isinstance(puerto, bool) or not isinstance(puerto, int):
                continue
            if not isinstance(protocolo, str):
                continue
            protocolo = protocolo.strip().lower()  # «TCP» también cuenta
            if protocolo not in _PROTOCOLOS:
                continue

            regla = _REGLAS_PUERTOS.get((puerto, protocolo))
            if regla is None:
                continue

            severidad, motivo = regla
            hallazgos.append({
                "clave_correlacion": servidor.get("clave_correlacion"),
                "redes": servidor.get("redes", []),
                "ips": servidor.get("ips", []),
                "puerto": puerto,
                "protocolo": protocolo,
                "servicio": servicio.get("nombre"),
                "severidad_sugerida": severidad,
                "motivo": motivo,
                "es_vulnerabilidad_confirmada": False,
            })

    orden = {"advertencia": 0, "atencion": 1}
    hallazgos.sort(
        key=lambda h: (
            orden.get(h["severidad_sugerida"], 9),
            h["puerto"],
            h["protocolo"],
        )
    )

    return {
        "hallazgos": hallazgos,
        "cantidad": len(hallazgos),
        "nota": (
            "Son indicadores heurísticos para revisión. "
            "No confirman vulnerabilidades ni implican que un servicio sea accesible desde Internet."
        ),
    }


def _texto_del_evento(evento, indice):
    """El texto del recuerdo, None si el tipo no es de los que se recuerdan, o ValueError si el evento no sirve."""
    tipo = evento.get("tipo")
    if tipo not in {"alta", "baja", "cambio"}:
        return None

    clave = evento.get("clave_correlacion")
    if clave is None:
        clave = "identidad no correlacionada"
    elif not isinstance(clave, str) or not _PATRON_CLAVE.fullmatch(clave):
        raise ValueError(f"El evento {indice} trae una clave_correlacion que no armó este módulo.")

    if tipo == "alta":
        return (
            f"Ashur Network detectó un dispositivo nuevo: {clave}. "
            "El hallazgo procede de una comparación de observaciones."
        )
    if tipo == "baja":
        return (
            f"Ashur Network dejó de observar un dispositivo previamente conocido: {clave}. "
            "La ausencia en una instantánea no demuestra que el dispositivo haya sido retirado."
        )

    cambios = evento.get("cambios")
    if not isinstance(cambios, list) or not cambios:
        raise ValueError(f"El evento {indice} es un cambio sin una lista de cambios.")
    etiquetas = set()
    for cambio in cambios:
        campo = cambio.get("campo") if isinstance(cambio, dict) else None
        if not isinstance(campo, str) or campo not in _ETIQUETAS:
            raise ValueError(f"El evento {indice} trae un cambio de un campo que este módulo no compara.")
        etiquetas.add(_ETIQUETAS[campo])
    return f"Ashur Network detectó cambios en {clave}: {', '.join(sorted(etiquetas))}."


def recordar_cambios(
    contexto,
    eventos=None,
    limite=20,
    **parametros,
) -> dict:
    """Entrega recuerdos concisos sobre cambios relevantes al core.

    Los recuerdos llegan después al modelo, así que no llevan texto libre del cliente: la clave tiene que ser una de
    las que arma este módulo y las etiquetas salen de su propia lista. Todos los eventos se validan antes de guardar
    el primero: un evento malo no deja recuerdos a medias."""
    eventos = [] if eventos is None else eventos
    if not isinstance(eventos, list):
        raise ValueError("eventos debe ser una lista.")
    if isinstance(limite, bool) or not isinstance(limite, int):
        raise ValueError("limite debe ser un entero.")
    if not 1 <= limite <= 50:
        raise ValueError("limite debe estar entre 1 y 50.")

    textos = []
    for indice, evento in enumerate(eventos):
        if not isinstance(evento, dict):
            raise ValueError(f"El evento {indice} debe ser un objeto.")
        texto = _texto_del_evento(evento, indice)
        if texto is not None and texto not in textos:
            textos.append(texto)

    recuerdos = []
    for texto in textos[:limite]:
        contexto.recordar(
            texto,
            sensibilidad="normal",
            identidades=[],
            objetos=[],
            opinion=None,
        )
        recuerdos.append(texto)

    return {
        "recuerdos_creados": len(recuerdos),
        "recuerdos": recuerdos,
    }
