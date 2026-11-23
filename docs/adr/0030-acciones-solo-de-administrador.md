# ADR 0030: una acción de un módulo puede ser solo de administrador

- **Estado:** Aceptada
- **Fecha:** 2026-11-23

## Contexto
El ejecutor de Workbench (`modules/workbench/ejecutor.py`) corre en un equipo de Sergio, toma tareas y entrega sus
resultados con las acciones `tomar_tarea` y `entregar_tarea`. Como solo cambian datos propios del módulo, corrían con
la clave normal: cualquiera con esa clave podía entregar un resultado. Sergio pidió que eso se maneje siempre como
administrador.

El contrato solo distinguía acciones que leen y acciones que escriben fuera de Ashur, y las segundas pasan por un
pedido que un administrador aprueba después. Eso no sirve para un programa que trabaja solo.

## Decisión
- **Campo `admin`:** una acción del manifiesto puede declarar `"admin": true` (`contracts/modulo.schema.json`). Por
  defecto es `false`, así que los manifiestos de antes siguen valiendo.
- **Cómo corre:** `POST /modulos/{id}/acciones/{accion}` acepta la clave normal (`X-Ashur-Clave`) o la de administrador
  (`X-Ashur-Clave-Admin`). Una acción con `admin: true` responde 401 sin la clave de administrador, y con ella corre
  ya, sin pedido: quien llama ya es el administrador.
- **El resto no cambia:** con la clave de administrador, una acción que escribe sigue quedando como pedido, y una que
  solo lee corre igual que antes.
- **Chat:** una acción solo de administrador no se le ofrece a Ashur como herramienta, y si se pide desde el chat no
  corre.

## Costos
- **La clave de administrador sale del core:** el equipo que corre el ejecutor la guarda (en la Mac, en el Llavero).
  Quien entre a ese equipo con la sesión de Sergio puede leerla.
- **Sin rastro:** una acción solo de administrador no deja pedido, así que no queda registro de quién la corrió.

## Pendiente
- Este ADR se escribió sin consultar al advisor, que no estaba disponible en la sesión. Queda para la revisión de
  Ashur Code.
