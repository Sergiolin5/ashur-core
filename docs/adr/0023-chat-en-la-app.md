# ADR 0023: el chat en la app

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
El core ya tiene el chat y la cola de trabajos que responden los nodos de casa (ADR 0016, 0017). En la app, tocar el
núcleo abría una pantalla «Chats» vacía. Sergio quiere hacer las primeras pruebas del chat en sus iPhones, el iPad M1 y
el iPhone Duo. Es el primer paso: los teléfonos chatean con Ashur y el modelo corre en un nodo de casa. Que los
teléfonos también presten su modelo (como PrivateLM, `docs/REFERENCIA-PRIVATELM.md`) es un paso aparte.

## Decisión
- **Pantalla Chats** (`app/lib/chat/pantalla_chats.dart`): se abre tocando el núcleo. Lista las conversaciones
  (`GET /conversaciones`) y tiene «Nueva conversación» (`POST /conversaciones`). Una conversación sin mensajes se llama
  «Conversación nueva».
- **Pantalla de una conversación** (`app/lib/chat/pantalla_conversacion.dart`):
  - muestra los mensajes, los de Sergio a la derecha y los de Ashur a la izquierda;
  - enviar usa `POST /conversaciones/{id}/mensajes`, que responde 202;
  - **sin streaming:** mientras la respuesta está abierta (`espera` con estado `pendiente` o `tomado`), la pantalla
    vuelve a pedir la conversación cada 2 s y muestra en qué va. Una respuesta puede pasar por más de un trabajo
    (primero la búsqueda por significado, ADR 0018), así que solo se mira `espera`;
  - deja de preguntar cuando `espera` es `null` o `fallido`. Si falló, muestra el error y se puede escribir de nuevo;
  - mientras la respuesta está abierta, el campo y «Enviar» quedan desactivados. Si aun así el core responde 409, se
    muestra su detalle;
  - al salir de la pantalla se cancela el reloj;
  - con el teclado abierto, el campo y «Enviar» suben por encima de él (la pantalla no usa `CupertinoPageScaffold`).
- **Cliente:** `listarConversaciones`, `crearConversacion`, `verConversacion` y `enviarMensaje`, con JSON crudo como
  `contracts/conversacion.schema.json`. `_enviar` acepta 202.
- **Sin core o con las claves bloqueadas** (ADR 0025), Chats lo explica igual que Inventario.
- **Sin paquetes nuevos.** No incluye cerrar la conversación ni las correcciones (ADR 0024).

## Costos
- **Cada mensaje es un recuerdo para siempre** (ADR 0016) y no hay `DELETE`. Por eso las pruebas se hacen con un core
  de prueba y una base temporal, con textos inventados.
- **Preguntar cada 2 s** gasta algo de red y batería mientras Ashur responde.
- **Sin nodos en línea, el mensaje espera** y la conversación no acepta otro hasta que alguno lo tome.

## Verificado (2026-11-22)
- `flutter analyze` sin avisos y `flutter test` con 46 pruebas. Las nuevas:
  - el cliente contra un core falso: listar, crear, ver, enviar (202) y el 409 con su detalle;
  - la conversación pregunta hasta que llega la respuesta y después no pregunta más;
  - si falla, deja de preguntar, muestra el error y deja escribir;
  - salir mientras espera no lanza errores ni deja el reloj andando;
  - Chats con conversaciones, y con las claves bloqueadas.
- Quitar la parada en `fallido` o la cancelación del reloj hace fallar su prueba.
- De punta a punta por la API, con un core de prueba, el programa `nodo/` en la Mac y `qwen2.5:3b` en Ollama: un
  mensaje recibió respuesta en 10,3 s.

## Sin verificar
- La app en los iPhones, el iPad M1 y el iPhone Duo.
