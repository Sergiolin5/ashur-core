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
- **Pruebas:** `pytest`, y `httpx` para el `TestClient` de FastAPI.
- **Contrato:** `contracts/galaxy-state.schema.json` sigue siendo la fuente de verdad. Los modelos de pydantic del
  core lo copian a mano y, desde el primer día, un test valida `contracts/galaxy-state.ejemplo.json` con esos
  modelos para detectar diferencias.
- **Despliegue:** un contenedor Docker en ZimaOS, construido a partir de un `Dockerfile` en `core/`. El archivo de
  SQLite vive en un volumen local montado desde el servidor, nunca dentro del contenedor (si viviera adentro, cada
  actualización de la imagen borraría la memoria de Ashur) ni en una carpeta de red.

Sergio aprobó estas dependencias: Python 3.13 (con uv), `fastapi`, `uvicorn`, `pydantic`, `httpx` y `pytest`, más
el `Dockerfile`.

## Costos
- **Contrato copiado a mano:** los modelos de pydantic pueden quedar distintos al schema. El test con el JSON de
  ejemplo detecta parte de esas diferencias, no todas. Validar contra el propio schema necesitaría `jsonschema`, que
  no está aprobado.
- **La imagen no se verifica en la Mac:** no hay Docker en la Mac, así que el `Dockerfile` solo se prueba en el
  servidor.

## Pendiente
- **Arquitectura del servidor ZimaOS** (x86_64 o ARM). Las imágenes oficiales de Python existen para las dos, así
  que no cambia esta decisión.
- **Cómo se construye y se instala la imagen en ZimaOS:** si se construye en el servidor o se instala desde un
  archivo compose. Está sin verificar.
- **Registro de módulos:** el mecanismo concreto sigue sin definir (`docs/MODULOS.md`, sección 2).
