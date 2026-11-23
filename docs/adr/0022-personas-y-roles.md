# ADR 0022: otras personas en el chat, con su clave y su rol

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Cierra:** la parte de la decisión 11 que toca al acceso y la privacidad del chat. El consentimiento quedó en
  que Sergio avisa en persona; la sensibilidad sigue abierta.

## Contexto
Sergio quiere que otras personas, como Christian o Erick, hablen con Ashur. Es la fase 5 del chat (ADR 0016).
Sus decisiones del 2026-11-22:
- **Acceso:** una clave por persona.
- **Recuerdos:** con otra persona, Ashur usa solo los suyos.
- **Datos de Sergio:** esa persona no ve la parte de la personalidad que habla de Sergio (fase 6).
- **Herramientas:** dependen de roles con reglas de acceso.

## Decisión
- **Claves:**
  - Cada identidad puede tener su propia clave, que crea o reemplaza `POST /identidades/{id}/clave` (administrador). Igual que la de un nodo, se muestra una sola vez y se guarda su sha256.
  - Va en el mismo encabezado `X-Ashur-Clave` que la de Sergio, así que la app no cambia.
  - Archivar la identidad revoca la clave en el acto, y restaurarla no la devuelve: hay que crearle otra (revisión
    del 2026-11-22). Reemplazarla invalida la anterior.
  - Sin `ASHUR_CLAVE` configurada, todo queda cerrado, también para las personas (503).
- **Cerrado por defecto:**
  - Una clave de persona solo abre las rutas del chat: `POST/GET /conversaciones`, `GET /conversaciones/{id}` y `POST /conversaciones/{id}/mensajes`, listadas en `RUTAS_DE_PERSONAS`.
  - Todas las demás siguen con `exigir_clave`, que solo acepta la de Sergio.
  - Una prueba recorre todas las rutas de la app, así que una ruta nueva queda cerrada salvo que se agregue a la lista a propósito.
  - Por eso la app de otra persona no puede ver la galaxia, que muestra los nombres de las identidades.
- **Dueño de cada conversación:**
  - Cada conversación es de quien la creó; `NULL` es Sergio.
  - Cada uno lista solo las suyas.
  - Una conversación ajena responde 404, igual que una que no existe, porque los ids `con-N` se pueden adivinar.
  - Sergio ve lo que dicen los demás en sus recuerdos, no en su lista de conversaciones.
- **Solo los suyos:**
  - Con otra persona, Ashur solo usa los recuerdos de los mensajes de sus conversaciones.
  - No usa los que la mencionan: esos son las notas de Sergio sobre ella.
  - El filtro está en la búsqueda misma (`buscar_alguna`, `cercanos` y la herramienta `buscar_recuerdos`). El rol decide qué herramientas hay, pero la privacidad vale dentro de cada una.
- **Lo que dice otra persona también es memoria de Sergio:**
  - Cada mensaje, suyo o de Ashur, es un recuerdo que la enlaza (`identidad_id`).
  - Por eso crece en la galaxia mientras habla con Ashur.
- **Roles** (`contracts/rol.schema.json`):
  - Los crea y cambia el administrador con `POST` y `PATCH /roles`; `GET /roles` usa la clave normal.
  - Se asignan con `PATCH /identidades/{id}` y `rol` (`null` lo quita). Un rol que no existe da 422.
  - Cada rol lista herramientas por nombre exacto o por prefijo con un solo `*` al final (`modulo-luces-*`). Se distinguen mayúsculas.
  - No se usa `fnmatch`: en Windows ignora las mayúsculas y le da sentido a `?` y `[`.
  - Una persona sin rol solo conversa.
- **La puerta** sigue siendo `herramientas_para`:
  - A Sergio le da todas; a otra persona, las de su rol actual.
  - Cada ronda vuelve a preguntar, así que quitar un rol corta en la ronda siguiente.
- **Pedidos:** cada pedido guarda quién lo pidió (`pedido_por`; `null` es Sergio). Así Sergio sabe que fue Christian
  antes de aprobarlo.
- **Contratos:** `contracts/identidad.schema.json` suma `rol` y `con_clave`, y aparece `contracts/rol.schema.json`.
- **Base:** esquema 12, con la tabla `roles`, la clave y el rol de cada identidad, el dueño de cada conversación y quién
  pidió cada pedido.

## Costos
- **Sin aviso a los demás:** todo lo que una persona le dice a Ashur queda en la memoria de Sergio. Aparece en
  `/recuerdos` y en lo que Ashur recuerda con Sergio. Sergio decidió avisarles en persona antes de darles su clave (2026-11-22);
  el core no les muestra ningún aviso.
- **Otra persona puede intentar mandar sobre Ashur en el chat de Sergio:** lo que escribe queda en la memoria de
  Sergio, y la búsqueda de Sergio busca en toda su memoria. Un mensaje plantado puede llegar al pedido de Sergio, que
  tiene todas las herramientas, y las acciones de módulos que solo leen corren en el acto.
  - Para que el modelo no lo tome como una orden, ese recuerdo llega marcado: «(lo dijo Christian en su chat)».
  - Lo que escribe sigue esperando a Sergio.
- **La privacidad solo filtra recuerdos:** un rol con `buscar_objetos` o `listar_identidades` (o `buscar_*`) le
  muestra a esa persona todo el inventario de Sergio y el nombre de todas las identidades.
- **Un rol con `modulo-*`:** le da a esa persona todo lo que el módulo puede leer, con los privilegios del módulo
  (ADR 0013). Lo que escribe sigue esperando a Sergio.
- **Sin límite de carga:** una clave de persona puede llenar la cola de los nodos de Sergio de mensajes. «Sergio siempre
  gana» protege el equipo que él está usando, nada más.
- **Las correcciones de la fase 6** que salgan de otras conversaciones entran en la personalidad de todos.
- **La galaxia queda cerrada para los demás:** su app no la puede dibujar.

## Verificado (2026-11-22)
- `uv run pytest` (11 pruebas de este ADR):
  - una clave de persona da 401 en todas las rutas que no son del chat, recorridas una por una;
  - sin `ASHUR_CLAVE`, 503;
  - cada uno ve solo sus conversaciones, y las ajenas dan 404;
  - archivar revoca la clave y reemplazarla invalida la anterior;
  - con otra persona, Ashur no usa las notas de Sergio sobre ella, pero sí lo que ella le contó;
  - con Sergio, lo que dijo otra persona llega marcado con su nombre;
  - sus mensajes la enlazan;
  - los patrones de rol distinguen mayúsculas y no aceptan `[` ni un `*` en medio;
  - sin rol no hay herramientas; con rol, solo las suyas;
  - el pedido guarda quién lo pidió;
  - quitar el rol corta en la ronda siguiente;
  - `buscar_recuerdos` respeta la privacidad aunque el rol la permita;
  - la migración desde la versión 11.

## Revisión del 2026-11-22
- Los mensajes ya no son recuerdos (ADR 0028). «Solo los suyos» ahora son los recuerdos que un nodo sacó de sus
  conversaciones y, del historial, los mensajes de sus conversaciones. Lo que enlaza a la persona es cada uno de
  esos recuerdos, no cada mensaje.

## Pendiente
- La personalidad sin «Lo que sabes de Sergio» para los demás (fase 6).
- Una galaxia propia para otra persona, si Sergio la quiere.
- Las claves y los roles en la configuración avanzada de la app.
