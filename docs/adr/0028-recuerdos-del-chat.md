# ADR 0028: los mensajes son historial y un nodo decide qué se recuerda

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Reemplaza:** la parte del ADR 0016 que hacía de cada mensaje un recuerdo, y lo que de ahí heredaron los ADR 0018,
  0022 y 0024.

## Contexto
Desde el ADR 0016, cada mensaje del chat, de la persona o de Ashur, era también un recuerdo, sin filtro: en la base,
`mensajes.recuerdo_id` era obligatorio. La memoria crecía con saludos, preguntas y respuestas del modelo, y la
madurez subía dos recuerdos por intercambio (ADR 0024).

Sergio eligió el 2026-11-22 la opción A: después de cada respuesta, el nodo decide qué vale la pena recordar y se
guarda solo eso, con origen `chat`. Los mensajes se guardan aparte, como historial.

De que cada mensaje fuera un recuerdo dependían tres cosas, que este ADR rehace:
- la privacidad por conversación (ADR 0022): con otra persona, Ashur solo usa lo que salió de sus conversaciones;
- el olvido (decisión de Sergio del 2026-11-22): lo que se borra de la memoria se borra del chat;
- la búsqueda híbrida (ADR 0018), que encontraba cualquier cosa dicha en el chat porque todo era recuerdo.

## Decisión
- **Los mensajes son historial:**
  - Un mensaje nuevo no crea ningún recuerdo, y su `recuerdo_id` es `null`.
  - Ya no hay recuerdos nuevos con origen `chat-ashur`.
- **Un nodo decide qué recordar:**
  - Tras cada respuesta de Ashur, el core deja en la cola un trabajo de fondo `conversar`, con
    `proposito: "recuerdos"` y sin herramientas.
  - El nodo recibe el último intercambio (el mensaje de la persona y la respuesta) y, solo para entenderlo, los
    cuatro mensajes anteriores.
  - Se le pide guardar solo lo que la persona contó y que servirá más adelante, en tercera persona, nombrándola, y
    de modo que cada línea se entienda sola. Lo que dijo Ashur solo sirve para entender. `NADA` es ninguno.
  - Como máximo tres recuerdos por intercambio, de una línea y hasta 300 caracteres cada uno.
  - Cada uno se guarda con origen `chat`, sensibilidad `normal` y la fecha del mensaje del que salió. En la
    conversación de otra persona, el recuerdo la enlaza, como antes.
  - Es un trabajo de fondo: el chat siempre va primero, y enviar otro mensaje no espera a que termine.
- **De dónde salió cada recuerdo:**
  - `recuerdos.mensaje_id` guarda el mensaje de la persona del que salió. No es parte del contrato del recuerdo: es
    del core.
  - De ahí sale la conversación y, con ella, de quién es. `personas.recuerdos_de` y `personas.autores` ya no miran
    `mensajes.recuerdo_id`, sino ese enlace.
  - La privacidad no cambia: con otra persona, solo los recuerdos que salieron de sus conversaciones; con Sergio,
    todos, y los del chat de otra persona van marcados con su nombre.
- **El historial se sigue encontrando, por palabras:**
  - Los mensajes tienen su propio índice FTS5 (`mensajes_busqueda`), igual al de los recuerdos.
  - Además de los 5 recuerdos, al pedido entran hasta 3 mensajes de otras conversaciones, o de antes en la misma,
    que coinciden por palabras con el mensaje. Van en una lista aparte, «De conversaciones anteriores», con la fecha
    y quién lo dijo, y cortados a 300 caracteres.
  - La herramienta `buscar_recuerdos` también los trae.
  - Valen las mismas reglas de privacidad: otra persona solo encuentra los mensajes de sus conversaciones; con
    Sergio, los del chat de otra persona van marcados «(en el chat de Christian)».
  - Quedan fuera los mensajes que el modelo ya ve, los borrados y los anteriores a este ADR, que ya se encuentran
    como recuerdos. Tampoco entra como recuerdo el que salió de un mensaje que el modelo ya ve.
  - Los mensajes no reciben vector: por significado solo se buscan los recuerdos.
- **El olvido:**
  - Borrar un recuerdo que salió del chat borra del historial el intercambio del que salió: el mensaje de la persona
    y lo que Ashur respondió hasta el mensaje siguiente, que quedan como «(borrado)». La respuesta se va también
    porque puede repetir lo que se quiere olvidar.
  - Editar un recuerdo que salió del chat no cambia el historial: el recuerdo es lo que Ashur entendió, y el mensaje
    es lo que se dijo.
  - Si mientras el nodo decide se borra algo de lo que leyó, el intercambio o su contexto, lo que devuelva no se
    guarda.
- **Lo de antes se queda como está:**
  - Los recuerdos que ya salieron de mensajes, con origen `chat` o `chat-ashur`, no se borran ni se revisan.
  - Sus mensajes conservan su `recuerdo_id` y siguen a su recuerdo como hasta ahora: editarlo cambia el mensaje, y
    borrarlo lo deja como «(borrado)».
  - Un mensaje de antes cuya respuesta llega después de actualizar el core no deja el trabajo: ya es un recuerdo.
    Borrar ese recuerdo borra también la respuesta.
- **Contrato:** en `contracts/conversacion.schema.json`, `recuerdo_id` puede ser `null`.
- **Base:** esquema 15.
  - `mensajes.recuerdo_id` deja de ser obligatorio. SQLite no permite quitar un `NOT NULL`, así que la tabla se
    rehace conservando los ids.
  - `recuerdos.mensaje_id`, que en los recuerdos de antes se llena con su propio mensaje.
  - El índice `mensajes_busqueda` y sus tres disparadores.

## Costos
- **Lo que el nodo no guarda no es memoria.** Sigue en el historial y se encuentra por palabras, pero no por
  significado, no cuenta para la madurez y no enlaza a nadie en la galaxia.
- **El recuerdo es lo que el modelo entendió,** no lo que se dijo: puede resumir mal o inventar. Sergio lo corrige o
  lo borra en `/recuerdos`, y el mensaje original sigue en el historial.
- **Un pedido más al modelo por cada respuesta.** Mientras corre, ocupa el nodo: un mensaje que llega en ese
  momento espera a que termine.
- **Si falla tres veces,** de ese intercambio no queda ningún recuerdo, y no se vuelve a intentar.
- **La madurez sube más despacio:** ya no son dos recuerdos por intercambio, sino los que el nodo decida. Los
  umbrales (2000 y 20 000) se pensaron con la cuenta anterior.
- **Un mensaje que no dejó recuerdo no se puede borrar del historial:** no hay ruta para borrar un mensaje. Hoy
  solo se olvida del chat lo que tiene un recuerdo que borrar.
- **Borrar un recuerdo equivocado también borra su intercambio,** aunque lo dicho fuera inofensivo, y los otros
  recuerdos que salieron de ese intercambio se quedan.
- **Otra puerta para darle órdenes al modelo:** los recuerdos los escribe un modelo leyendo lo que escribió una
  persona, y los mensajes de otras personas llegan al pedido de Sergio por la búsqueda en el historial. Los dos van
  marcados con el nombre de quien habló, como en el ADR 0022.
- **El historial de antes pesa dos veces:** los mensajes viejos siguen siendo también recuerdos.

## Verificado (2026-11-22)
- `uv run pytest` (192 pruebas del core). Las de este ADR, con un nodo falso:
  - tras cada respuesta sale el trabajo, sin herramientas, con el intercambio y el contexto; como máximo tres
    recuerdos, cortos, con origen `chat` y la fecha del mensaje;
  - `NADA`, también como viñeta, y un texto sin líneas no dejan nada;
  - el chat va antes que decidir qué recordar;
  - si falla tres veces no queda nada y la conversación sigue;
  - un intercambio borrado mientras el nodo pensaba no deja recuerdos, y tampoco si se borró su contexto;
  - la persona sube de nivel con los recuerdos de su chat;
  - `buscar_recuerdos` no devuelve lo que el modelo ya ve;
  - lo que se dijo y no quedó como recuerdo se encuentra desde otra conversación, sin repetir lo que el modelo ya
    ve, con el límite de tres y cortado;
  - otra persona no encuentra el historial de Sergio ni el de otra, ni en el pedido ni con `buscar_recuerdos`, y a
    Sergio lo de los demás le llega marcado;
  - borrar un recuerdo del chat borra su intercambio del historial, del título y de la búsqueda; editarlo no toca
    el mensaje; un mensaje de antes sigue a su recuerdo;
  - la migración desde la versión 14 conserva los mensajes y sus ids, y sabe de dónde salió cada recuerdo.

- **Revisión independiente** antes de subir: encontró cinco defectos (un recuerdo borrado que podía volver por el
  contexto de un trabajo ya en la cola, el nivel de la persona que no subía, la herramienta que devolvía la propia
  pregunta, una respuesta en vuelo al actualizar y «Nadar…» leído como `NADA`). Los cinco quedaron arreglados y con
  prueba.

## Sin verificar
- **Con un modelo real.** Qué decide guardar `qwen2.5:7b` con estas instrucciones, y si respeta el formato, solo
  se sabrá con el chat de Sergio. Las instrucciones están en `core/ashur_core/memoria.py` (`INSTRUCCIONES`).

## Pendiente
- Una ruta para borrar un mensaje del historial, si Sergio la quiere.
- Decidir si el historial también se busca por significado. Costaría un vector por mensaje, y el coseno ya es el
  costo que nombra el ADR 0018.
- Revisar los umbrales de la madurez con la cuenta nueva.
