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
| `personas` | Cada una con `nombre` y `contacto_id`, que es `null` si la persona no está en la lista de contactos. |
| `objetos` | Cada uno con `nombre` e `inventario_id`, que es `null` si el objeto no está en el inventario. |
| `opinion` | Lo que Ashur opina del recuerdo, o `null` si todavía no tiene opinión. |

- **Ashur guarda los recuerdos directamente,** sin pedirle aprobación a Sergio (decisión 9, 2026-11-21).
- **Todo se guarda, también lo sensible.** La `sensibilidad` es solo un dato: no cambia cómo se guarda un recuerdo
  ni qué nivel de inferencia puede usarlo.

### Almacenamiento
- **Base de datos:** una tabla `recuerdos` en SQLite. `personas` y `objetos` se guardan como JSON en sus columnas.
- **Versión del esquema:** se lleva con `PRAGMA user_version`. Una base vacía se crea en la versión 1; una base con
  una versión más nueva que la que conoce el código hace que cada pedido a la memoria falle con un error, en
  lugar de adivinar.
- **Conexiones:** se abre una conexión por pedido, porque FastAPI atiende los endpoints en varios hilos.
- **Ruta:** la variable de entorno `ASHUR_DB`, que por defecto es `/datos/ashur.db`.

### Endpoints
| Método y ruta | Qué hace |
| --- | --- |
| `POST /recuerdos` | Guarda un recuerdo nuevo y lo devuelve con su `id` (201). |
| `GET /recuerdos` | Lista todos los recuerdos. |
| `DELETE /recuerdos/{id}` | Borra un recuerdo (204), o responde 404 si no existe. |

### Clave compartida
- Los endpoints de la memoria piden el encabezado `X-Ashur-Clave`, que se compara con la variable de entorno
  `ASHUR_CLAVE` mediante `secrets.compare_digest`. `/vivo` queda abierto.
- **Cerrado por defecto:** si `ASHUR_CLAVE` no está configurada, la memoria responde 503. Una clave ausente o
  equivocada responde 401.
- **Dónde vive la clave:** Sergio la crea y la pone en el panel de ZimaOS. Nunca entra al repo, que es público.
- **Dependencias:** usa `fastapi.security.APIKeyHeader`, que viene con FastAPI, así que no agrega paquetes.

## Costos
- **Los enlaces todavía no apuntan a nada:** `contacto_id` e `inventario_id` esperan a que existan la lista de
  contactos y el inventario. La lista de contactos es parte del core, como el inventario pero de personas.
- **La clave viaja sin cifrar en la red de casa:** el core habla HTTP, así que en la red local la clave va en claro.
  Por Tailscale va cifrada.
- **Una sola clave para todo:** no distingue dispositivos ni permisos, y cambiarla obliga a cambiarla en todos los
  clientes.

## Pendiente
Están en `docs/DECISIONES-ABIERTAS.md`, puntos 8, 10 y 11:
- el enlace con el inventario y con la lista de contactos;
- la búsqueda por significado;
- las reglas por nivel de sensibilidad y de consentimiento.
