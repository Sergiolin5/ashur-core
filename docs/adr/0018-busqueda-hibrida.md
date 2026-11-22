# ADR 0018: búsqueda híbrida, por palabras y por significado

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Cierra:** la decisión 10 (búsqueda por significado).

## Contexto
Antes de responder, Ashur tiene que traer los recuerdos que vienen al caso. Sergio pidió una búsqueda híbrida, por
palabras y por significado. Es la fase 3 del chat (`docs/adr/0016-chat-y-nodos.md`). La búsqueda por palabras ya
existía (`docs/adr/0004-memoria.md`).

## Decisión
- **Modelo:** siempre `bge-m3`, en los nodos con Ollama.
  - Cada vector guarda el modelo que lo calculó, y nunca se comparan vectores de modelos distintos.
  - Un nodo sin `bge-m3` nunca toma trabajos de embeddings, aunque tenga otro modelo de embeddings. Eso incluye a los teléfonos y al iPad.
- **Vectores de los recuerdos:**
  - Se guardan normalizados, como `float32`, en la tabla `embeddings` (esquema 10), con `array` de la librería estándar.
  - En cada latido de un nodo con `bge-m3`, el core reparte en lotes de 32 los recuerdos sin vector, nuevos o de antes, con dos lotes en la cola como máximo.
  - Cambiar el texto de un recuerdo o borrarlo borra su vector; el siguiente latido lo vuelve a calcular.
- **Dos pasos por mensaje:**
  1. Si hay un nodo en línea con `bge-m3`, el primer trabajo calcula el vector del mensaje.
  2. Con ese vector, el core busca y deja en la cola el pedido al modelo.

  Sin ese nodo, se responde directamente con la búsqueda por palabras.
- **Sin frenar la respuesta:** si nadie toma el primer paso en 15 s, o si falla tres veces, Ashur responde solo con lo
  que encuentra por palabras.
- **Búsqueda híbrida:**
  - **Palabras:** FTS5 con cualquiera de las palabras del mensaje que tengan tres letras o más.
  - **Significado:** coseno contra todos los vectores, con un parecido mínimo de 0,45.
  - **Combinación:** las dos listas, de hasta 20 cada una, se unen por rangos recíprocos ($\sum 1/(60 + \text{rango})$).
  - Entran al pedido los 5 mejores, sin los que ya están en el historial que ve el modelo, como una lista con fecha al final de la personalidad.
- **Prioridad:** un nodo toma primero los trabajos de una conversación y después los de fondo, para que el reparto de
  vectores nunca frene el chat.
- **Un recuerdo que siempre falla:** si un lote falla tres veces, sus recuerdos se reparten de a uno. Un recuerdo que
  falla solo se queda sin vector, y se encuentra únicamente por palabras.

## Costos
- **El coseno es Python puro:** con 20 000 recuerdos de 1024 dimensiones tarda unos segundos por mensaje. Si crece,
  hará falta un índice o un paquete, con la aprobación de Sergio.
- **Un paso más por mensaje,** con su ida y vuelta al nodo.
- **Un nodo ve todos los recuerdos,** porque calcula sus vectores (ver «Costos» del ADR 0016).
- **El texto del mensaje queda dos veces en la cola:** como entrada del vector y dentro del pedido al modelo.

## Verificado (2026-11-22)
- `uv run pytest` (82 pruebas). Las de este ADR, con un nodo falso que calcula vectores de juguete:
  - Un recuerdo llega por significado aunque no comparta palabras con el mensaje («llavecitas» trae «llaves»), y lo que no se parece no entra.
  - Sin nodo de embeddings, se responde con las palabras.
  - Una búsqueda que nadie toma a tiempo, o que falla, no frena la respuesta.
  - Se rechazan los vectores mal formados.
  - Editar o borrar un recuerdo olvida su vector.
  - Un recuerdo que siempre falla no deja sin vector a los demás.
  - Se migra desde la versión 9.

## Sin verificar
- **El parecido mínimo de 0,45 es una suposición.** Falta calibrarlo con `bge-m3` sobre recuerdos reales. Esa prueba
  se corre solo cuando el equipo Windows informe `full` por sí mismo.
- **El tiempo real** del primer paso con `bge-m3`, y si cambiar entre `bge-m3` y `qwen2.5` en una tarjeta de 4 GB
  agrega segundos.

## Pendiente
- La privacidad por persona (fase 5): cada persona solo con sus recuerdos.
