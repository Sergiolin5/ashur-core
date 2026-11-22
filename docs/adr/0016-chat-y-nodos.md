# ADR 0016: el chat vive en el core y los nodos de casa lo responden

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
El chat es la parte del core que faltaba (`docs/ASHUR.md`). Sergio quiere que Ashur piense en sus propios equipos:
- una Mac, un Windows, un iPhone adicional y un iPad Pro como nodos de casa;
- un modelo dentro del teléfono, como PrivateLM (`docs/REFERENCIA-PRIVATELM.md`).

Del repo anterior vienen tres aprendizajes (`docs/REFERENCIA-ANTERIOR.md`):
- los nodos van y vienen y siempre llaman al core, nunca al revés (puntos 1 y 2);
- Sergio siempre gana en sus máquinas (punto 4);
- las decisiones son funciones puras (punto 5).

Sergio aprobó el diseño el 2026-11-22. Esta es la primera de seis fases.

## Decisión
- **El core piensa y los nodos solo ejecutan:**
  - El core arma cada pedido al modelo en el formato de OpenAI: la personalidad y el historial; en fases siguientes, también los recuerdos y las herramientas.
  - Un nodo solo lo pasa a su modelo y devuelve la respuesta cruda.
  - Así un iPhone o un iPad pueden ser nodos sin lógica propia, igual que un Ollama.
- **Chat:**
  - Conversaciones `con-N` con título (el comienzo del primer mensaje) y mensajes `user` o `assistant`.
  - Cada mensaje, de Sergio o de Ashur, también es un recuerdo, sin filtro (decisión de Sergio): con origen `chat` los de Sergio y `chat-ashur` los de Ashur.
  - El modelo ve los últimos 20 mensajes.
- **Cola de trabajos:**
  - Cada mensaje deja un trabajo `conversar`.
  - Un nodo lo toma de forma atómica y tiene 300 s para devolverlo; si no, el trabajo vuelve a la cola.
  - Si el nodo devuelve un error, se reintenta hasta tres veces y después queda `fallido`.
  - Desde la revisión del 2026-11-22, también gastan un intento un plazo vencido y una salida que el core rechaza
    (422). Antes un nodo caído o un modelo que respondía mal dejaban la conversación trabada para siempre.
  - Al entregar, el nodo reclama el trabajo de forma atómica (estado interno `entregando`, que la API muestra como
    `tomado`) antes de que el core aplique sus efectos: una entrega doble o tardía responde 409 y no duplica nada.
  - Mientras hay un trabajo abierto, la conversación no acepta otro mensaje (409). La reserva es atómica: dos
    mensajes enviados a la vez nunca dejan dos respuestas.
- **Nodos:**
  - Cada nodo `nod-N` manda un latido cada 15 s con su modo y sus modelos. Tres latidos perdidos (45 s) lo dejan fuera de línea.
  - Modos: `full` toma cualquier trabajo, `light` solo modelos de hasta 2,5 GB, y `busy` u `off` nada.
- **Ashur decide:**
  - Al entregar un trabajo, el core elige el modelo más grande que el nodo ofrece para esa necesidad y que su modo le deja correr.
  - Durante los primeros 10 s, un trabajo solo lo toma el nodo en línea con el mejor modelo; después, cualquiera que pueda.
  - Todo esto son funciones puras en `core/ashur_core/nodos.py`.
- **Claves:**
  - El administrador crea cada nodo con `POST /nodos` y recibe su clave una sola vez. El core guarda solo su sha256.
  - La clave va en `X-Ashur-Clave-Nodo` y solo abre `/nodo/...`.
  - Archivar un nodo le quita la clave para siempre: restaurarlo no se la devuelve, así que un nodo restaurado no se
    puede usar y hay que crear uno nuevo (revisión del 2026-11-22). No hay `DELETE` (decisión 8).
- **Endpoints:**

  | Método y ruta | Clave | Qué hace |
  | --- | --- | --- |
  | `POST /conversaciones` | normal | Crea una conversación. |
  | `GET /conversaciones` | normal | Lista las no archivadas, las más recientes primero. |
  | `GET /conversaciones/{id}` | normal | La conversación, sus mensajes y, si Ashur no respondió, en qué va (`espera`). |
  | `POST /conversaciones/{id}/mensajes` | normal | Guarda el mensaje y deja el trabajo en la cola (202). |
  | `POST /nodos` | administrador | Crea un nodo y devuelve su clave. |
  | `GET /nodos` | normal | Lista los nodos, su modo, sus modelos y si están en línea. |
  | `PATCH /nodos/{id}` | administrador | Archiva o restaura un nodo. |
  | `POST /nodo/latido` | nodo | Informa el modo y los modelos. |
  | `POST /nodo/trabajos/tomar` | nodo | Entrega un trabajo, o 204. |
  | `POST /nodo/trabajos/{id}` | nodo | Devuelve la salida o el error. |

- **Contratos:** `contracts/nodo.schema.json` (el protocolo, compartido por core y nodos, punto 3) y `contracts/conversacion.schema.json`.
- **Base:** esquema 9, con las tablas `conversaciones`, `mensajes`, `nodos` y `trabajos`.
- **Personalidad:** por ahora una genérica, en el código. La de Sergio llega en la fase 6, y vive solo en su base, nunca en el repo, que es público (punto 8).

## Costos
- **Un nodo ve todo lo que viaja en sus trabajos.** Por eso solo el administrador crea claves de nodo, y solo para los equipos de Sergio.
- **La respuesta no es inmediata:** la app pregunta por la conversación hasta que llega. Sin nodos en línea, el mensaje espera.
- **Todo el chat es memoria:** la memoria crece con cada mensaje, también con las respuestas del modelo, sin filtro.
- **Una conversación a la vez por trabajo:** no se puede escribir de nuevo hasta que Ashur responda o falle.
- **Sin nodos, la conversación queda esperando:** un trabajo pendiente no vence, así que si todos los equipos están
  apagados esa conversación no acepta otro mensaje hasta que aparezca un nodo. Mientras tanto se puede abrir otra; el
  modelo del teléfono (nivel 2) lo resolverá.

## Verificado (2026-11-22)
- `uv run pytest` (72 pruebas):
  - política de modos y elección de modelo;
  - chat de punta a punta con un nodo falso y todo el chat como recuerdo;
  - reintentos y fallo;
  - plazo vencido y nodo fuera de línea;
  - preferencia por el mejor nodo;
  - claves de nodo que solo abren la cola, y la clave guardada como hash;
  - dos mensajes a la vez dejan un solo trabajo;
  - migración desde la versión 8.

## Hecho después, en el mismo diseño
- **Fase 2:** el programa `nodo/` (ADR 0017).
- **Fase 3:** la búsqueda híbrida con `bge-m3` (ADR 0018).
- **Ajustes de módulos y nodos** (ADR 0019).
- **Fase 4:** las herramientas del chat (ADR 0021).
- **Fase 5:** otras personas con su clave y su rol (ADR 0022).
- **Fase 6:** la personalidad, la madurez y las correcciones (ADR 0024).

## Pendiente
- **App:** la pantalla de chat (ADR 0023, reservado) y el modelo dentro del iPhone y del iPad, desde la Mac.
- **Galaxia:** los nodos todavía no son cuerpos.
