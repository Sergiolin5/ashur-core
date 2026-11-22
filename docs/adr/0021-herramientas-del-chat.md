# ADR 0021: las herramientas del chat las corre el core

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
Sergio pidió que Ashur pueda usar herramientas en el chat: el inventario, las identidades y los módulos. Las acciones
que escriben siguen pidiendo su aprobación. Es la fase 4 del chat (ADR 0016). El número 0020 está reservado para la
configuración avanzada de la app.

## Decisión
- **El core corre todo y el nodo solo pasa el pedido:**
  - El pedido lleva `tools` en el formato de OpenAI. El nodo se las pasa a Ollama y devuelve lo que responda el modelo, con `tool_calls` si pidió alguna.
  - El core corre cada llamada y deja en la cola la ronda siguiente, con los resultados como mensajes `role: "tool"`.
- **Una sola puerta:** `herramientas_para(conversacion)` decide qué se ofrece. Hoy ofrece todo, porque el chat es solo
  de Sergio; la fase 5 decide ahí según el rol de quien habla.
  - Una llamada solo corre si su herramienta se ofreció en ese mismo trabajo: el modelo puede inventar nombres.
- **Herramientas:**

  | Nombre | Qué hace |
  | --- | --- |
  | `buscar_objetos` | Busca en el inventario por nombre o lugar. |
  | `listar_identidades` | Lista las personas y mascotas. |
  | `buscar_recuerdos` | Busca en la memoria por palabras. |
  | `modulo-<id>-<accion>` | Una por cada acción de cada módulo registrado. |

  El guion separa porque no puede ir dentro de un id, y así dos módulos nunca dan el mismo nombre. Los nombres se
  buscan en una lista, nunca se desarman. Si dos nombres quedan iguales al cortarlos a 64 caracteres, el segundo no se
  ofrece.
- **Argumentos:**
  - Los de las herramientas del core se validan con `extra="forbid"`.
  - Los de los módulos se pasan tal cual, porque los manifiestos no traen su esquema.
  - Se aceptan como objeto (Ollama) o como texto JSON (OpenAI), y vuelven a la ronda siguiente siempre como objeto.
- **Todo error es texto para el modelo:** una herramienta que no existe, argumentos inválidos, un módulo que falla o
  devuelve fechas, o cualquier otra excepción vuelven como resultado, nunca como un 4xx, un 500 ni un trabajo fallido.
  Si una ronda fallara, se repetiría entera, y con ella las acciones y los pedidos.
  - Cada resultado se corta a 20 elementos y a unos 2000 caracteres.
- **Las acciones que escriben siguen siendo pedidos,** también en el chat de Sergio. El modelo recibe «Quedó pendiente
  de la aprobación de Sergio (pedido N)».
- **Rondas:**
  - Hay como máximo 3 rondas de herramientas por mensaje.
  - Después, el modelo responde sin herramientas.
  - Si igual pide alguna, no se abre otra ronda: con texto, ese texto es la respuesta; sin texto, es un error que se
    reintenta y, a la tercera, deja la conversación en `fallido`. Así la conversación siempre termina.
  - Solo la respuesta final es mensaje y recuerdo; las rondas quedan en los trabajos.
- **Capacidad `tools`:**
  - El core manda herramientas solo si hay un nodo en línea con un modelo que sepa usarlas.
  - Un pedido con herramientas solo lo toma un modelo con esa capacidad.
  - Esto importa para los teléfonos y el iPad.
- **Aviso en la personalidad:** cuando hay herramientas, se agrega una línea que le pide al modelo usarlas antes de decir
  que no sabe. Sin ella, `qwen2.5:7b` contestaba sin buscar.
- **Sin hueco entre pasos:** el paso siguiente queda en la cola, y la conversación apunta a él, antes de cerrar el
  anterior. Así no se cuela otro mensaje entre la búsqueda, las rondas y la respuesta. Esto también corrige la
  fase 3.
- **Protocolo:** `contracts/nodo.schema.json` documenta `tools` en la entrada, `tool_calls` en la salida y los mensajes
  `role: "tool"`.

## Costos
- **Lo que el modelo lee puede traer instrucciones:** los resultados de las herramientas y los recuerdos son datos
  que el modelo lee, y un texto puede intentar darle órdenes.
  - Lo que escribe está protegido por la aprobación de los pedidos.
  - Una acción de módulo que «solo lee» corre en cuanto el modelo la pide, con todos los privilegios del módulo (ADR 0013). Su única protección es que el módulo la declare bien como `escribe: false`.
- **El resultado de un pedido aprobado no vuelve al chat:** Ashur no se entera de que se hizo.
- **El modelo no siempre usa las herramientas:** en la prueba real, `qwen2.5:7b` inventó una mascota en lugar de llamar
  a `listar_identidades`, aunque en otra corrida la misma pregunta salió bien.
- **Cada ronda es otro viaje al nodo,** de unos 5 a 15 s con el 7B.
- **Si se va el nodo que sabe usar herramientas,** el pedido que ya las lleva espera, aunque haya en línea un nodo sin
  esa capacidad.
- **Un pedido se puede duplicar si el core se cae** justo después de crearlo y antes de cerrar el trabajo: el trabajo
  vuelve a la cola y la ronda se repite. Es raro.

## Verificado (2026-11-22)
- `uv run pytest` (12 pruebas de herramientas):
  - el inventario de punta a punta;
  - argumentos como texto JSON;
  - herramientas inventadas y argumentos inválidos devueltos como texto;
  - acciones que escriben, que quedan como pedidos;
  - un módulo que falla;
  - el límite de rondas, también con un modelo que igual pide herramientas sin texto, o con texto;
  - una herramienta no ofrecida que no se corre;
  - un resultado con fechas que no tumba la ronda;
  - los argumentos en texto, que vuelven como objeto;
  - los nodos sin la capacidad `tools`;
  - las respuestas vacías;
  - que no se cuela otro mensaje entre pasos.
- `uv run pytest ../nodo/tests`: las herramientas viajan a Ollama y las llamadas vuelven sin texto.
- **De punta a punta con `qwen2.5:7b` real,** en el equipo Windows en `full` por sí mismo:
  - Sin el aviso, a «¿Dónde está mi bicicleta roja?» respondió que no sabía, sin buscar.
  - Con el aviso, llamó a `buscar_objetos` y respondió «en el garaje, detrás de la puerta», en 15 s.
  - «¿A quiénes conoces?» llamó a `listar_identidades` en una corrida e inventó en la otra.
  - Los pedidos pesaron entre 1000 y 1600 caracteres, lejos del contexto de 8192.

## Decisión de Sergio (2026-11-22)
- **El aviso nombra solo lo que se ofrece:** se arma con las herramientas de esa conversación. A una persona cuyo rol
  solo tiene `buscar_objetos`, el aviso le habla del inventario y nada más; si prometía la memoria, el modelo podía
  decir que buscó sin haber buscado. Con todas las herramientas, el texto es el mismo que se probó con `qwen2.5:7b`.

## Pendiente
- Qué herramientas puede usar cada rol (fase 5).
- Que el resultado de un pedido aprobado vuelva a la conversación.
