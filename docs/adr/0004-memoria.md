# ADR 0004: primera versión de la memoria del core

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
La memoria es la primera de las tres partes del core (`docs/ASHUR.md`) y lo primero que el core guarda de verdad.
Vive en SQLite sobre el volumen `/datos` (`docs/adr/0003-stack-servidor.md`), así que sobrevive a las
actualizaciones de la imagen. Esta primera versión es una prueba: Ashur todavía no tiene chat ni modelo, y las reglas
de consentimiento y tratamiento de datos se definen antes de usarla en serio.

## Decisión
### Qué es un recuerdo
El contrato es `contracts/recuerdo.schema.json`, con un ejemplo inventado en `contracts/recuerdo.ejemplo.json`.

| Campo | Qué es |
| --- | --- |
| `id` | Número que pone el core al guardarlo. |
| `texto` | El recuerdo, en palabras. |
| `origen` | De dónde vino: chat, diario o el id de un módulo. |
| `fecha` | Cuándo pasó, en ISO 8601 con zona horaria. La envía el cliente, porque un recuerdo del diario de ayer lleva la fecha de ayer. |
| `sensibilidad` | `normal`, `privado` o `sensible`. |
| `identidades` | Las personas y mascotas involucradas, cada una con `nombre` e `identidad_id`, que es `null` si no está en la lista de identidades. |
| `objetos` | Cada uno con `nombre` e `inventario_id`, que es `null` si el objeto no está en el inventario. |
| `opinion` | Lo que Ashur opina del recuerdo, o `null` si todavía no tiene opinión. |

- **Inicio del aprendizaje:** es el momento en que el core creó su base de memoria (decisión 15). Una base que ya
  existía antes de la versión 3 toma el momento de su migración. Los administradores pueden cambiarlo.
- **Búsqueda por palabras** (decisión 10, 2026-11-21): un índice FTS5 de SQLite sobre `texto` y `opinion`, que no
  agrega paquetes. Usa el tokenizador `unicode61` con `remove_diacritics`, así que "medico" encuentra "médico", y cada
  palabra se busca también como prefijo ("bici" encuentra "bicicleta"). Unos disparadores mantienen el índice al crear,
  editar y borrar. La búsqueda por significado llegó con el ADR 0018, con embeddings que calculan los nodos de casa,
  guardados en la misma base.
- **Archivar en vez de borrar** (decisión 8, 2026-11-21): un objeto del inventario o una identidad que ya no se
  quiere ver se archiva, no se borra (ADR 0012 y 0014). Desaparece de la galaxia y de las listas,
  los recuerdos conservan su enlace, y un administrador puede restaurarlo.
- **Ashur guarda los recuerdos directamente,** sin pedirle aprobación a Sergio (decisión 9, 2026-11-21).
- **Todo se guarda, también lo sensible.** La `sensibilidad` es solo un dato: no cambia cómo se guarda un recuerdo
  ni qué nivel de inferencia puede usarlo.

### Almacenamiento
- **Base de datos:** una tabla `recuerdos` en SQLite. `identidades` y `objetos` se guardan como JSON en sus columnas.
- **Versión del esquema:** se lleva con `PRAGMA user_version` (la versión actual es `VERSION_ESQUEMA` en
  `core/ashur_core/memoria.py`; las versiones 5 a 8 están en los ADR 0012, 0013 y 0014). Una base vacía se crea en la
  versión actual.
  Una de la versión 1 (con `personas` y `contacto_id`) se migra sola a `identidades` e `identidad_id`, y la versión 3
  agrega la tabla `meta` con la fecha en que Ashur empezó a aprender. La versión 4 agrega el índice de búsqueda. La
  migración corre dentro de `BEGIN IMMEDIATE`, así que dos pedidos a la vez no la repiten; una base con
  una versión más nueva que la que conoce el código hace que cada pedido a la memoria falle con un error, en
  lugar de adivinar.
- **Conexiones:** se abre una conexión por pedido, porque FastAPI atiende los endpoints en varios hilos.
- **Ruta:** la variable de entorno `ASHUR_DB`, que por defecto es `/datos/ashur.db`.

### Endpoints
| Método y ruta | Qué hace |
| --- | --- |
| `POST /recuerdos` | Guarda un recuerdo nuevo y lo devuelve con su `id` (201). |
| `GET /recuerdos` | Lista todos los recuerdos. Con `?buscar=...`, solo los que tienen esas palabras, los más relevantes primero. |
| `PATCH /recuerdos/{id}` | Edita un recuerdo: solo cambia los campos enviados (solo administradores). |
| `DELETE /recuerdos/{id}` | Borra un recuerdo (204), o responde 404 si no existe (solo administradores). |
| `GET /aprendizaje` | Devuelve `{inicio, recuerdos}`: desde cuándo aprende Ashur y cuántos recuerdos tiene. |
| `PATCH /aprendizaje` | Cambia `inicio` (solo administradores). |

### Clave compartida
- Los endpoints de la memoria piden el encabezado `X-Ashur-Clave`, que se compara con la variable de entorno
  `ASHUR_CLAVE` mediante `secrets.compare_digest`. `/vivo` queda abierto.
- **Administradores:** editar y borrar piden el encabezado `X-Ashur-Clave-Admin`, que se compara con
  `ASHUR_CLAVE_ADMIN`. Esa clave alcanza sola: no hace falta enviar también `X-Ashur-Clave`. Así los dueños del sistema son los únicos que cambian la memoria.
- **Cerrado por defecto:** si `ASHUR_CLAVE` no está configurada, la memoria responde 503, y si
  `ASHUR_CLAVE_ADMIN` no está configurada, nadie puede editar ni borrar. Una clave ausente o
  equivocada responde 401.
- **Dónde vive la clave:** Sergio la crea y la pone en el panel de ZimaOS. Nunca entra al repo, que es público.
- **Dependencias:** usa `fastapi.security.APIKeyHeader`, que viene con FastAPI, así que no agrega paquetes.

## Costos
- **Enlaces:** `identidad_id` e `inventario_id` apuntan a la lista de identidades (ADR 0012) y al inventario
  (ADR 0014). Un recuerdo nuevo no puede enlazar algo que no existe.
- **La clave viaja sin cifrar en la red de casa:** el core habla HTTP, así que en la red local la clave va en claro.
  Por Tailscale va cifrada.
- **FTS5 no entiende el español:** no reduce las palabras a su raíz, así que "perros" no encuentra "perro" salvo
  por el prefijo, y "fui" no encuentra "ir". La búsqueda por significado lo resuelve más adelante.
- **Dos claves fijas:** no distinguen dispositivos ni personas, y cambiar una obliga a cambiarla en todos los
  clientes que la usan.

## Decisiones de Sergio (2026-11-22)
- **Lo que se olvida se olvida en el chat:** si se borra el recuerdo de un mensaje, el mensaje queda como
  «(borrado)»; si se edita su texto, el mensaje cambia igual. En los dos casos el título de la conversación se vuelve
  a sacar del primer mensaje. Va en la misma transacción que el cambio del recuerdo. Costo: el texto viejo sigue en
  la entrada de los trabajos ya hechos de la cola y en las correcciones que ya se sacaron de esa conversación; no se
  purgan.
- **WAL:** la base se abre en modo WAL, para que leer no espere a que termine una escritura. Pide un disco local (no
  NFS ni SMB) para `/datos` en ZimaOS. Un respaldo tiene que copiar también `ashur.db-wal` y `ashur.db-shm`, o usar
  la API de respaldo de SQLite.
- **Fechas en la zona de Sergio:** se siguen guardando en UTC. `ASHUR_ZONA` (un nombre IANA) solo cambia el día con
  que el modelo ve cada recuerdo, en el pedido y en `buscar_recuerdos`. Sin ella, o si el equipo no conoce esa zona,
  queda UTC. Sin verificar: si la imagen `python:3.13-slim` trae la base de zonas; si no, haría falta el paquete
  `tzdata`, que es una dependencia nueva.

## Pendiente
Están en `docs/DECISIONES-ABIERTAS.md`, puntos 10 y 11:
- la búsqueda por significado, con embeddings de los nodos de casa;
- las reglas por nivel de sensibilidad y de consentimiento.
