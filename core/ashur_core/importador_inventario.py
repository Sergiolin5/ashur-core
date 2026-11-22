"""Importa un lote de objetos con simulación segura por defecto."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _leer_lote(ruta: str | Path) -> dict[str, Any]:
    with Path(ruta).open(encoding="utf-8") as archivo:
        lote = json.load(archivo)
    if not isinstance(lote, dict) or not isinstance(lote.get("items"), list):
        raise ValueError("El lote debe ser un objeto JSON con una lista 'items'.")
    return lote


def _ordenar(lote: dict[str, Any]) -> list[dict[str, Any]]:
    items = lote["items"]
    por_id: dict[str, dict[str, Any]] = {}
    for item in items:
        id_lote = item.get("id")
        if not isinstance(id_lote, str) or not id_lote:
            raise ValueError("Cada objeto del lote debe tener un id de texto.")
        if id_lote in por_id:
            raise ValueError("El lote contiene ids de objeto repetidos.")
        por_id[id_lote] = item
        if not isinstance(item.get("slots", []), list) or any(not isinstance(x, str) or not x for x in item.get("slots", [])):
            raise ValueError(f"El objeto {id_lote} declara una lista de ranuras inválida.")

    orden: list[dict[str, Any]] = []
    hechos: set[str] = set()
    pendientes = list(items)
    while pendientes:
        progreso = False
        for item in pendientes[:]:
            id_lote = item["id"]
            padre_id = item.get("parent_id")
            ranura = item.get("slot")
            if padre_id is None:
                if ranura is not None:
                    raise ValueError(f"La raíz {id_lote} declara una ranura sin padre.")
                orden.append(item)
                hechos.add(id_lote)
                pendientes.remove(item)
                progreso = True
                continue
            if not isinstance(padre_id, str) or not padre_id:
                raise ValueError(f"El componente {id_lote} necesita un parent_id válido.")
            if ranura is not None and (not isinstance(ranura, str) or not ranura):
                raise ValueError(f"El componente {id_lote} trae un slot inválido.")
            if padre_id not in por_id:
                raise ValueError(f"No existe el padre {padre_id} del objeto {id_lote} en el lote.")
            if padre_id in hechos:
                if ranura is not None and ranura not in por_id[padre_id].get("slots", []):
                    raise ValueError(f"El padre {padre_id} no declara la ranura {ranura}.")
                orden.append(item)
                hechos.add(id_lote)
                pendientes.remove(item)
                progreso = True
        if not progreso:
            raise ValueError("La jerarquía contiene un ciclo o una referencia circular.")
    return orden


def _payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "nombre": item["name"],
        "lugar": None if item.get("parent_id") is not None else item.get("place"),
        "padre_id": None,
        "ranura": None,
        "ranuras": item.get("slots", []),
        "identificadores": item.get("identifiers"),
        "especificaciones": item.get("specs"),
        "evidencia": item.get("evidence"),
        "estado": item.get("status"),
    }


def simular(ruta: str | Path) -> dict[str, Any]:
    """Valida el lote y calcula el orden sin llamar al core ni escribir archivos."""
    lote = _leer_lote(ruta)
    orden = _ordenar(lote)
    return {
        "objetos": len(orden),
        "raices": sum(item.get("parent_id") is None for item in orden),
        "con_padre": sum(item.get("parent_id") is not None for item in orden),
        "envios_importados": 0,
        "evidencias_cambiadas": sum(_payload(item)["evidencia"] != item.get("evidence") for item in orden),
        "estados_cambiados": sum(_payload(item)["estado"] != item.get("status") for item in orden),
        "orden": [item["id"] for item in orden],
    }


def _solicitar(metodo: str, url: str, payload: dict[str, Any], encabezados: dict[str, str]) -> dict[str, Any]:
    datos = json.dumps(payload, ensure_ascii=False).encode("utf-8") if metodo != "GET" else None
    solicitud = urllib.request.Request(
        url,
        data=datos,
        headers={"Content-Type": "application/json", **encabezados},
        method=metodo,
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"El core respondió HTTP {error.code} durante la importación.") from error


def importar(ruta: str | Path, core: str, clave: str, clave_admin: str) -> dict[str, str]:
    lote = _leer_lote(ruta)
    orden = _ordenar(lote)
    base = core.rstrip("/")
    correspondencia: dict[str, str] = {}
    for item in orden:
        payload = _payload(item)
        padre_id = item.get("parent_id")
        if padre_id is None:
            respuesta = _solicitar("POST", f"{base}/objetos", payload, {"X-Ashur-Clave": clave})
        else:
            # Se crea después del padre y se enlaza con PATCH, usando la clave de administrador.
            respuesta = _solicitar("POST", f"{base}/objetos", payload, {"X-Ashur-Clave": clave})
            payload_enlace = {"padre_id": correspondencia[padre_id], "ranura": item.get("slot")}
            _solicitar(
                "PATCH",
                f"{base}/objetos/{respuesta['id']}",
                payload_enlace,
                {"X-Ashur-Clave-Admin": clave_admin},
            )
        correspondencia[item["id"]] = respuesta["id"]

    ruta_mapa = Path(ruta).with_name(f"{Path(ruta).stem}_correspondencia.json")
    filas = [{"id_lote": id_lote, "obj_id": obj_id} for id_lote, obj_id in correspondencia.items()]
    ruta_mapa.write_text(json.dumps(filas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return correspondencia


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importa objetos al core de Ashur; por defecto solo simula.")
    parser.add_argument("--lote", required=True, help="Ruta del lote JSON")
    parser.add_argument("--core", required=True, help="Dirección base del core, por ejemplo http://localhost:8720")
    parser.add_argument("--escribir", action="store_true", help="Escribe en el core y guarda la correspondencia junto al lote")
    argumentos = parser.parse_args(argv)
    if not argumentos.escribir:
        resultado = simular(argumentos.lote)
        print("Modo: simulación (no escribe en el core)")
        print(f"Objetos: {resultado['objetos']}; raíces: {resultado['raices']}; con padre: {resultado['con_padre']}")
        print(f"Envíos importados: {resultado['envios_importados']}")
        print(f"Registros de evidencia cambiados: {resultado['evidencias_cambiadas']}; estados cambiados: {resultado['estados_cambiados']}")
        return 0

    clave = os.environ.get("ASHUR_CLAVE")
    clave_admin = os.environ.get("ASHUR_CLAVE_ADMIN")
    if not clave or not clave_admin:
        parser.error("ASHUR_CLAVE y ASHUR_CLAVE_ADMIN deben estar configuradas para escribir.")
    try:
        correspondencia = importar(argumentos.lote, argumentos.core, clave, clave_admin)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"No se completó la importación: {error}", file=sys.stderr)
        return 1
    print(f"Importados {len(correspondencia)} objetos. La correspondencia quedó junto al lote.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
