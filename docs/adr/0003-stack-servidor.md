# ADR 0003: el core es Python con FastAPI y SQLite

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
El core (`core/`) es el servidor REST de Ashur: memoria, chat, inventario de objetos físicos y registro de módulos.
Por ahora corre en el servidor ZimaOS de Sergio, que ejecuta las apps como contenedores Docker. Más adelante va a
necesitar el nivel 3 de inferencia (la nube) y un conector MCP propio (`docs/REFERENCIA-ANTERIOR.md`, puntos 9 y 13).

Se compararon tres opciones:

| Opción | SDK oficial de Anthropic y de MCP | Qué había que instalar o agregar |
| --- | --- | --- |
| Python 3.13 + FastAPI + SQLite | Sí | Python 3.13, `fastapi`, `uvicorn`, `pydantic` |
| TypeScript en Node 26 + SQLite (`node:sqlite`) | Sí | Un framework REST, TypeScript y un generador de tipos |
| Dart (`shelf`) + SQLite | No, hasta donde se sabe | `shelf`, `shelf_router`, `sqlite3` |

El repo anterior usaba Python con FastAPI y SQLite (`../ashur/core/`) y solo sirve como antecedente. No se copia
código.

## Decisión
- **Lenguaje:** Python 3.13, instalado con uv. El Python de la Mac es el 3.9.6 de Xcode, que ya no tiene soporte,
  y no se usa.
- **REST:** FastAPI, servido con uvicorn.
- **Base de datos:** SQLite, con el módulo `sqlite3` de la librería estándar.
- **Pruebas:** `pytest`, y `httpx2` para el `TestClient` de FastAPI. Starlette marca `httpx` como obsoleto para su
  `TestClient` y pide `httpx2`, que mantiene Pydantic.
- **Contrato:** `contracts/galaxy-state.schema.json` sigue siendo la fuente de verdad. Los modelos de pydantic del
  core lo copian a mano y, desde el primer día, un test valida `contracts/galaxy-state.ejemplo.json` con esos
  modelos para detectar diferencias.
- **Despliegue:** un contenedor Docker en ZimaOS, construido a partir de un `Dockerfile` en `core/`. El archivo de
  SQLite vive en un volumen local montado desde el servidor, nunca dentro del contenedor (si viviera adentro, cada
  actualización de la imagen borraría la memoria de Ashur) ni en una carpeta de red.

Sergio aprobó estas dependencias: Python 3.13 (con uv), `fastapi`, `uvicorn`, `pydantic`, `httpx2` y `pytest`, más
el `Dockerfile`.

## Costos
- **Contrato copiado a mano:** los modelos de pydantic pueden quedar distintos al schema. El test con el JSON de
  ejemplo detecta parte de esas diferencias, no todas. Validar contra el propio schema necesitaría `jsonschema`, que
  no está aprobado.
- **La imagen no se construye en la Mac:** no hay Docker en la Mac, así que el `Dockerfile` solo se prueba en
  GitHub Actions y en el servidor.

## Despliegue verificado (2026-11-21)
- **Servidor:** ZimaOS 1.8 en un AMD Ryzen 5 3600 (x86_64), así que la imagen se construye para `linux/amd64`.
- **Imagen:** `.github/workflows/imagen-core.yml` la construye en cada push a `main` que toque `core/` y la publica
  como `ghcr.io/sergiolin5/ashur-nucleo` (pública), con las etiquetas `latest` y la del commit. No se llama
  `ashur-core` porque `ghcr.io/sergiolin5/ashur-core` es la imagen del repo anterior, que sigue en uso.
- **Instalación:** el panel de ZimaOS solo instala apps personalizadas desde una imagen ya publicada. La app se llama
  "Ashur Core (nuevo)", publica el puerto 8720 y monta una carpeta propia del servidor en `/datos`, separada de la
  del Ashur anterior. `/vivo` responde desde la red privada.

## Pendiente
- **Registro de módulos:** ya está, en `docs/adr/0013-modulos-en-el-core.md`.
