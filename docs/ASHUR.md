# Ashur: documento maestro

## Qué es
Ashur es una IA personal que aprende de Sergio a partir de sus chats, su diario, su uso del tiempo y sus hábitos.
Es un solo asistente, con una sola memoria, que Sergio usa desde todos sus dispositivos.

## El core
El core es lo mínimo que Ashur necesita para existir, y tiene cuatro partes:

1. **Memoria:** lo que Ashur aprende y recuerda.
2. **Chat:** la conversación con Ashur, al estilo de WhatsApp.
3. **Inventario de objetos físicos:** las cosas que Sergio tiene y dónde están.
4. **Identidades:** las personas y las mascotas que conoce Ashur, como un inventario pero de seres.

Todo lo demás (casa, salud, tiempo, hábitos, herramientas, WhatsApp) es un módulo independiente que se integra al core
siguiendo el contrato de `docs/MODULOS.md`. El core vive en `core/` como servidor REST, y el cliente es la app
Flutter de `app/` (ver `docs/adr/0001-cliente-flutter.md`).

## La app
- **Inicio:** la galaxia, descrita en `docs/GALAXIA.md`. Tocar el núcleo abre el chat.
- **Pestañas:**
  - **Estado:** cómo están Ashur, sus agentes y sus módulos.
  - **Casa:** la casa y sus dispositivos.
  - **Workbench:** la tercera pestaña (`docs/adr/0005-workbench-y-whatsapp.md`).
- La app no tiene temas ni ajustes de apariencia.

## Tres niveles de inferencia
Ashur piensa siempre en el primer nivel disponible, en este orden:

| Nivel | Dónde corre | Papel |
| --- | --- | --- |
| 1 | **Nodos de casa:** los equipos de Sergio en su red, con modelos locales. | La base. |
| 2 | **Modelo en el dispositivo:** un modelo pequeño en el teléfono o la computadora que se está usando. | Cuando no hay nodos de casa a la mano. |
| 3 | **Nube:** un proveedor externo. | Solo como respaldo. |

Si $D_k$ indica que el nivel $k$ está disponible en este momento, el nivel elegido es

$$
k^{*} = \min\{\, k \in \{1, 2, 3\} : D_k \,\}
$$

Este esquema todavía no está implementado.

## Filosofía anti e-waste
Ashur aprovecha el hardware que Sergio ya tiene en lugar de pedirle hardware nuevo. Un equipo viejo sigue siendo
útil como nodo de casa y presta su procesador y su memoria. Por eso la nube es el respaldo, no la base.

## Flujo multi-IA
Varias IA pueden proponer, escribir o investigar, pero **Claude es el revisor final**: ningún cambio entra al repo
sin pasar por su revisión. En Claude Code, esa revisión incluye consultar al advisor antes de cerrar una tarea
(ver `CLAUDE.md` y `docs/HERRAMIENTAS.md`).

## Mapa de la documentación
| Documento | Contenido |
| --- | --- |
| `CLAUDE.md` | Reglas del repo para cualquier sesión de IA. |
| `docs/GALAXIA.md` | Glosario visual y modelo matemático de la galaxia. |
| `docs/MODULOS.md` | Contrato que cumple todo módulo. |
| `docs/HERRAMIENTAS.md` | REA y el advisor de Claude Code. |
| `docs/DECISIONES-ABIERTAS.md` | Lo que falta decidir. |
| `docs/REFERENCIA-PRIVATELM.md` | Qué tomamos de PrivateLM. |
| `docs/REFERENCIA-ANTERIOR.md` | Aprendizajes del repo anterior. |
| `docs/adr/` | Decisiones de arquitectura ya tomadas. |
| `contracts/` | Contratos de datos entre el core y la app. |
