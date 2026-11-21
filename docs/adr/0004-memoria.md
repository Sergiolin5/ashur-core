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
- **Archivar en vez de borrar** (decisión 8, 2026-11-21): cuando existan el inventario y la lista de identidades, un
  objeto o una identidad que ya no se quiere ver se archiva, no se borra. Desaparece de la galaxia y de las listas,
  los recuerdos conservan su enlace, y un administrador puede restaurarlo.
- **Ashur guarda los recuerdos directamente,** sin pedirle aprobación a Sergio (decisión 9, 2026-11-21).
- **Todo se guarda, también lo sensible.** La `sensibilidad` es solo un dato: no cambia cómo se guarda un recuerdo
  ni qué nivel de inferencia puede usarlo.

### Almacenamiento
- **Base de datos:** una tabla `recuerdos` en SQLite. `identidades` y `objetos` se guardan como JSON en sus columnas.
- **Versión del esquema:** se lleva con `PRAGMA user_version` y va en la 3. Una base vacía se crea en la versión 3.
  Una de la versión 1 (con `personas` y `contacto_id`) se migra sola a `identidades` e `identidad_id`, y la versión 3
  agrega la tabla `meta` con la fecha en que Ashur empezó a aprender. La
  migración corre dentro de `BEGIN IMMEDIATE`, así que dos pedidos a la vez no la repiten; una base con
  una versión más nueva que la que conoce el código hace que cada pedido a la memoria falle con un error, en
  lugar de adivinar.
- **Conexiones:** se abre una conexión por pedido, porque FastAPI atiende los endpoints en varios hilos.
- **Ruta:** la variable de entorno `ASHUR_DB`, que por defecto es `/datos/ashur.db`.

### Endpoints
| Método y ruta | Qué hace |
| --- | --- |
| `POST /recuerdos` | Guarda un recuerdo nuevo y lo devuelve con su `id` (201). |
| `GET /recuerdos` | Lista todos los recuerdos. |
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
- **Los enlaces todavía no apuntan a nada:** `identidad_id` e `inventario_id` esperan a que existan la lista de
  identidades y el inventario. Las identidades son parte del core: personas y mascotas, como un inventario de seres.
- **La clave viaja sin cifrar en la red de casa:** el core habla HTTP, así que en la red local la clave va en claro.
  Por Tailscale va cifrada.
- **Dos claves fijas:** no distinguen dispositivos ni personas, y cambiar una obliga a cambiarla en todos los
  clientes que la usan.

## Pendiente
Están en `docs/DECISIONES-ABIERTAS.md`, puntos 10 y 11:
- la búsqueda por significado;
- las reglas por nivel de sensibilidad y de consentimiento.
