# ADR 0029: un módulo puede guardar datos propios en el core

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
Sergio pidió rehacer su centro de desarrollo (Nexo) dentro de la pestaña Workbench. Guarda proyectos, proveedores,
tareas, entregas y un servidor: registros que se crean, se editan y se borran. El contrato de módulos
(`docs/adr/0013-modulos-en-el-core.md`) solo dejaba guardar recuerdos, y una tarea que cambia de estado no es un
recuerdo.

Sergio eligió entre tres caminos: un módulo con datos propios en el core, una quinta parte del core, o datos solo en
cada dispositivo. Eligió el primero: el core sigue siendo memoria, chat, inventario e identidades, y los datos se ven
igual en todos sus equipos.

## Decisión
- **`contexto.datos`:** cada módulo recibe un almacén de registros JSON agrupados en colecciones:

  | Llamada | Qué hace |
  | --- | --- |
  | `contexto.datos.listar(coleccion)` | Los registros de la colección, del más nuevo al más viejo. |
  | `contexto.datos.leer(coleccion, id)` | Un registro, o `None`. |
  | `contexto.datos.guardar(coleccion, datos, id=None)` | Sin `id` crea el registro; con `id` lo reemplaza entero. Lanza `KeyError` si ese `id` no existe. |
  | `contexto.datos.borrar(coleccion, id)` | Lo borra. Devuelve si existía. |

  Cada registro vuelve con `id`, `creado` y `actualizado`, que pone el core.
- **Aislamiento:** un módulo solo ve sus propios registros. El almacén ya viene atado al id del módulo.
- **No son memoria de Ashur:** los datos propios no aparecen en los recuerdos, en la búsqueda ni en la masa del planeta.
  Lo que Ashur deba saber se sigue entregando con `contexto.recordar(...)`.
- **Qué acción escribe:** cambiar los datos propios no cuenta como escribir. `escribe` sigue significando que la
  acción cambia algo fuera de Ashur, y solo esas esperan la aprobación de un administrador.
- **Base:** esquema 16, con la tabla `datos_modulos` (`modulo`, `coleccion`, `id`, `datos`, `creado`, `actualizado`).

## Costos
- **Sin esquema:** el core no valida la forma de los registros; cada módulo cuida la suya.
- **Sin consultas:** solo se puede listar una colección entera. Alcanza para cientos de registros, no para miles.
- **Sin olvido automático:** el olvido y la privacidad del core (`docs/adr/0022-personas-y-roles.md`) no revisan los
  datos propios. Un módulo no debe guardar ahí lo que es de una persona.
- **Reemplazo entero:** dos cambios al mismo registro al mismo tiempo dejan solo el último.

## Pendiente
- Este ADR se escribió sin consultar al advisor, que no estaba disponible en la sesión. Queda para la revisión de
  Ashur Code.
