# ADR 0014: el inventario de objetos físicos

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
El inventario de objetos físicos es una de las cuatro partes del core (`docs/ASHUR.md`): las cosas que Sergio tiene y
dónde están. Los recuerdos ya enlazaban objetos con `inventario_id`, pero el inventario no existía. Sergio aprobó
hacerlo igual que la lista de identidades (`docs/adr/0012-identidades.md`), sin la parte de niveles.

## Decisión
- **Contrato:** `contracts/objeto.schema.json`, con un ejemplo inventado. Cada objeto tiene `id` (lo pone el core,
  `obj-N`, nunca se reusa), `nombre`, `lugar`, `archivado` y `menciones`.
- **Lugar:** texto libre, o `null` si no se sabe. No hay una lista de lugares.
- **Base:** esquema 7, con la tabla `objetos`. Una base de la versión 6 la recibe sola al abrirse.
- **Endpoints:**

  | Método y ruta | Clave | Qué hace |
  | --- | --- | --- |
  | `POST /objetos` | normal | Crea un objeto. |
  | `GET /objetos` | normal | Lista los no archivados; con `?archivados=true`, todos. |
  | `PATCH /objetos/{id}` | administrador | Edita, mueve, archiva o restaura. |

  No hay `DELETE`: un objeto se archiva (decisión 8). Archivado, sale de la lista y deja de pesar en la galaxia, y
  los recuerdos conservan su enlace.
- **Enlaces:** un recuerdo no puede enlazar un objeto que no existe; el core responde 422. Vale también para los
  recuerdos que guarda un módulo con `contexto.recordar`.
- **Menciones:** la cantidad de recuerdos distintos que enlazan el objeto.
- **En la galaxia:** los objetos no son cuerpos (decisión 12, abierta). Solo cambia la masa del planeta Objetos: 1 más
  la cantidad de objetos sin archivar. El contrato de la galaxia no cambia.

- **Enlaces anteriores al inventario:** antes de la versión 7 se aceptaba cualquier `inventario_id`. Para que un
  recuerdo viejo con `obj-3` no quede enlazado a un objeto nuevo que no tiene que ver, la migración a la versión 7 hace
  que la numeración empiece después del mayor `obj-N` que ya usan los recuerdos. Los recuerdos no se tocan.

## Costos
- **Recuerdos anteriores:** un recuerdo guardado antes de este cambio puede traer un `inventario_id` que no existe y
  que ya no existirá. El core no lo toca, pero editar los `objetos` de ese recuerdo exige que sus enlaces existan.
- **Mover un objeto necesita la clave de administrador,** igual que cualquier otra edición.
- **El lugar no se valida:** «garaje» y «Garaje» son dos lugares distintos.

## Revisión
- El borrador se escribió cuando la herramienta `advisor` no estaba disponible en la sesión. Un subagente
  independiente de Claude Code revisó el cambio y encontró que un enlace viejo a `obj-N` lo heredaba el primer objeto
  nuevo con ese número.
- Después apareció el `advisor`, se le consultó y propuso el arreglo que no toca los recuerdos (ver «Enlaces
  anteriores al inventario»). Por la revisión también se pusieron al día los ADR 0004, `docs/MODULOS.md` y
  `docs/PROMPT-MODULOS.md`.

## Verificado (2026-11-22)
- `uv run pytest` (57 pruebas): contrato, crear, listar, mover, archivar y restaurar, enlaces rotos rechazados al crear
  y al editar un recuerdo, menciones, masa del planeta Objetos, migración desde la versión 6 y enlaces viejos que no
  hereda un objeto nuevo.

## Pendiente
- Cómo se ven los objetos en la galaxia (decisión 12).
- Qué más guarda un objeto y si los lugares pasan a ser una lista.
- El mismo problema de enlaces viejos existe con `ide-N` desde la migración a la versión 5; no se arregló aquí.
- La misma validación laxa que usan las identidades: un `lugar` de solo espacios se acepta, y las menciones se cuentan
  recorriendo todos los recuerdos.
