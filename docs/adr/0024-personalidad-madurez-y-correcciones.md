# ADR 0024: la personalidad, la madurez y las correcciones

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
Sergio escribió la personalidad de Ashur: tono, lo que sabe de él, tres niveles de madurez, trato y correcciones. Sus
decisiones del 2026-11-22:
- **Madurez:** una sola para todos, que sube sola, inicial hasta 2000 recuerdos, intermedio hasta 20 000 y pleno después.
- **Correcciones:** salen solas al terminar cada conversación.
- **Otras personas:** no ven lo que Ashur sabe de Sergio.

Es la fase 6 del chat (ADR 0016). El número 0023 está reservado para el chat en la app.

## Decisión
- **Personalidad** (`contracts/personalidad.schema.json`):
  - Se guarda en la tabla `meta`, validada y sin campos extra. Tiene:
    - `base`;
    - `sobre_sergio`;
    - `madurez`, con `inicial`, `intermedio` y `pleno`;
    - `trato`;
    - `umbrales`, con `intermedio` y `pleno`.
  - `PUT /personalidad` pide la clave de administrador. `GET /personalidad` (solo Sergio) devuelve además las correcciones con su fuente y la madurez de hoy.
  - Nunca entra al repo, que es público (`docs/REFERENCIA-ANTERIOR.md`, punto 8). Sin personalidad cargada, Ashur usa una genérica.
- **El pedido arma, en este orden:**
  1. `base`;
  2. con Sergio, «Lo que sabes de Sergio»; con otra persona, «Estás hablando con {nombre}, no con Sergio»;
  3. solo la sección de la madurez actual;
  4. el trato;
  5. las correcciones, solo su texto;
  6. los recuerdos y el aviso de herramientas.
- **Madurez:** se cuenta con todos los recuerdos.
  - Cada mensaje y su respuesta son dos recuerdos, y las conversaciones de los demás también cuentan.
  - Los umbrales los cambia el administrador en la personalidad (2000 y 20 000 por defecto), como prometía el ADR 0019. Se valida que `intermedio < pleno`.
- **Correcciones:**
  - **Cuándo:** una conversación termina tras 30 minutos sin mensajes, o con `POST /conversaciones/{id}/cerrar`. Esa ruta es del chat, así que también la usan las personas con su clave: si la conversación no es suya, 404; si Ashur está respondiendo, 409.
  - **El trabajo:** al terminar, el core deja en la cola un trabajo de fondo `conversar`, con `proposito: "correcciones"` y sin herramientas. El modelo lee la conversación y escribe hasta dos líneas sobre cómo debe comportarse Ashur, nunca sobre la persona ni con nombres. `NADA` es ninguna.
  - **Una sola vez:** cada conversación se marca de forma atómica la primera vez, así que sus correcciones salen una sola vez aunque dos nodos pregunten a la vez. Se revisa una conversación inactiva por cada pedido de trabajo de un nodo.
  - **Límites:** cada corrección es una línea de hasta 200 caracteres, y se guardan solo las últimas 20.
  - **La fuente** (quién y qué conversación) se guarda para Sergio, pero al pedido solo llega el texto.
  - **Corregir una corrección:** `PUT /personalidad/correcciones` (administrador) reemplaza la lista, para borrar o arreglar una mala.
- **Base:** esquema 13, con `corregida` en cada conversación. Las conversaciones que ya existían quedan como corregidas,
  así que la primera vez no sale un trabajo por cada una.
- **La entrega de trabajos de fondo** distingue por necesidad y propósito: un lote de embeddings y un trabajo de
  correcciones nunca se confunden.

## Costos
- **Las correcciones son otra puerta para darle órdenes al modelo:** las escribe el modelo leyendo una conversación, y
  entran al pedido de todos, también las que salen del chat de otra persona. Sergio las revisa en `GET /personalidad` y
  las borra con `PUT /personalidad/correcciones`.
- **La madurez sube más rápido de lo que parece,** porque cada intercambio son dos recuerdos y cuentan los chats de todos.
- **Un trabajo de correcciones que falla tres veces** no se repite: esa conversación queda sin correcciones.
- **El modelo puede escribir un nombre en una corrección** aunque se le pida que no. Sergio las revisa en
  `GET /personalidad`.
- **Mientras corre un trabajo de correcciones, ocupa el nodo:** un mensaje que llega en ese momento espera.

## Verificado (2026-11-22)
- `uv run pytest` (9 pruebas de este ADR):
  - cargar la personalidad pide administrador y se valida;
  - la madurez sube con los umbrales y solo entra la actual;
  - con otra persona no entra lo de Sergio, y el modelo sabe con quién habla;
  - cerrar saca las correcciones una vez, como máximo dos, con su fuente guardada y fuera del pedido;
  - cerrar una conversación ajena da 404, y una ocupada 409;
  - tras 30 minutos salen solas, y `NADA`, también como viñeta, no deja nada;
  - se guardan solo las últimas 20, y Sergio puede reemplazarlas;
  - la migración desde la versión 12 marca las conversaciones viejas.
- La prueba que recorre todas las rutas confirma que `/personalidad` sigue cerrada para las personas.
- Con un core local y una base temporal, la personalidad de Sergio se cargó con `Invoke-RestMethod -InFile` y volvió
  idéntica, con los acentos bien.
- **De punta a punta con `qwen2.5:7b` real** y esa personalidad, en el equipo Windows en `full` por sí mismo:
  - «¿Dónde puse las llavecitas?»: respondió con el recuerdo del cajón azul, que en el ADR 0018 había ignorado. Tardó
    44 s, porque además buscó en la memoria y en el inventario.
  - «¿En qué trabajo yo?»: respondió con lo que sabe de Sergio, en 14 s.
  - El pedido más grande pesó unos 3400 caracteres (el sistema, unos 2000), lejos del contexto de 8192.

## Decisión de Sergio (2026-11-22)
- **Las correcciones siguen siendo una sola lista:** una corrección que salió del chat de Sergio también cambia cómo
  Ashur le habla a otra persona. Se queda así mientras casi solo habla Sergio; se separan por persona cuando otros
  usen el chat.

## Revisión del 2026-11-22
- Los mensajes ya no son recuerdos (ADR 0028): la madurez cuenta lo que un nodo decide recordar de cada
  intercambio, no dos recuerdos por cada uno, así que sube más despacio.

## Pendiente
- Lo de Ashur (personalidad, correcciones, roles y claves) en la configuración avanzada de la app.
