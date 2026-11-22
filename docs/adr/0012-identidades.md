# ADR 0012: la lista de identidades del core

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Las identidades (personas y mascotas) son la cuarta parte del core (`docs/ASHUR.md`). Los recuerdos ya las enlazaban
con `identidad_id`, pero la lista no existía, así que la galaxia no tenía personajes reales.

## Decisión
- **Contrato:** `contracts/identidad.schema.json`, con un ejemplo inventado. Cada identidad tiene `id` (lo pone el core,
  `ide-N`, nunca se reusa), `nombre`, `clase` (`persona` o `mascota`, provisional), `archivada`, `menciones` y `nivel`.
- **Base:** esquema 5, con la tabla `identidades`. Una base de la versión 4 la recibe sola al abrirse.
- **Endpoints:**

  | Método y ruta | Clave | Qué hace |
  | --- | --- | --- |
  | `POST /identidades` | normal | Crea una identidad. |
  | `GET /identidades` | normal | Lista las no archivadas; con `?archivadas=true`, todas. |
  | `PATCH /identidades/{id}` | administrador | Edita, archiva o restaura. |

  No hay `DELETE`: una identidad se archiva (decisión 8). Archivada, sale de la galaxia y de la lista, y los recuerdos
  conservan su enlace.
- **Enlaces:** un recuerdo no puede enlazar una identidad que no existe; el core responde 422.
- **Enlaces anteriores a la lista** (2026-11-22, esquema 8): antes de la versión 5 se aceptaba cualquier
  `identidad_id`. La migración a la versión 8 hace que la numeración siga después del mayor `ide-N` que ya usan los
  recuerdos, para que una identidad nueva no herede un enlace viejo que hablaba de otra persona. Nunca retrocede la
  numeración ni toca los recuerdos. Una identidad creada antes de la versión 8 que ya heredó un enlace así lo conserva:
  solo un administrador puede corregir ese recuerdo.
- **Masa:** la cantidad de recuerdos distintos que mencionan a la identidad. Es provisional: hoy es la única señal real
  de importancia.
- **Nivel:** con los umbrales y el margen de `docs/GALAXIA.md` («Evolución de una identidad»), $\theta = (1, 5, 20)$ y
  $\eta = 0.2$, provisionales. El nivel se guarda y se recalcula al escribir (crear, editar o borrar un recuerdo, o
  editar una identidad), así que leer la galaxia no escribe nada.
- **En la galaxia:** nivel 1 es un `personaje` sobre Identidades, nivel 2 una `luna` alrededor de Identidades y nivel 3
  un `planeta` propio alrededor del núcleo, todos con `ref: {"tipo": "identidad"}`. El id del cuerpo
  (`identidad-<id>`) y su `fase` (un hash del id) no cambian al subir o bajar, para que nada salte y la cámara pueda
  seguirlo. La masa de Identidades crece con la de sus miembros.
- **App:** el contrato de la galaxia no cambia. De cerca, cada planeta muestra su nombre (decisión 18).

## Verificado (2026-11-21)
- `uv run pytest` (39 pruebas): contrato, niveles con margen, archivar y restaurar, enlaces rotos rechazados, aparición
  en la galaxia y migración desde la versión 4.
- Servidor real con 40 pedidos simultáneos sobre una base de la versión 4, sin errores.

## Pendiente
- Qué más guarda una identidad (por ejemplo, contacto o fecha de nacimiento) y si `clase` crece.
- Una señal de importancia mejor que las menciones, cuando Ashur aprenda de verdad.
