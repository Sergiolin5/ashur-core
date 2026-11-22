# Prompt para construir módulos con otras IA

Este prompt sirve para construir módulos, herramientas y habilidades de Ashur en un Proyecto de Claude.ai o en otra
IA. Está escrito para Claude, con etiquetas XML; otras IA lo entienden igual. Claude Code, con el advisor, es siempre
el último paso: revisa e integra lo que se construya afuera (`docs/ASHUR.md`, «Flujo multi-IA»).

**Antes de pegarlo:**
1. Sube al Proyecto (o pega en la conversación) estos archivos del repo, tal como están en `main`: `CLAUDE.md`,
   `docs/ASHUR.md`, `docs/MODULOS.md`, `docs/DECISIONES-ABIERTAS.md` y `modules/_plantilla/modulo.json`.
2. Reemplaza `[MÓDULO]` por lo que quieres construir, en una o dos frases.

```xml
<contexto>
Ashur es una IA personal de Sergio. El repo público ashur-core tiene un core (servidor Python 3.13 con FastAPI y
SQLite: memoria, chat, inventario de objetos físicos e identidades), una app Flutter y módulos independientes en
modules/<id>/. Los archivos adjuntos son la fuente de verdad: CLAUDE.md (reglas), docs/ASHUR.md, docs/MODULOS.md
(contrato de módulos), docs/DECISIONES-ABIERTAS.md y modules/_plantilla/modulo.json. Si algo de este prompt choca con
esos archivos, ganan los archivos.

Todavía no está decidido cómo se registra un módulo en el core (docs/MODULOS.md, sección 2). Por eso cada módulo se
construye autocontenido, y la integración con el core la hace después Claude Code.
</contexto>

<tarea>
Construye un solo módulo: [MÓDULO].
</tarea>

<reglas>
- Escribe todo en español: código comentado, documentación y mensajes.
- Un módulo por tarea. Trabaja solo dentro de modules/<id>/. No toques core/, app/, contracts/ ni otro módulo.
- El módulo no depende de otro módulo y no guarda memoria propia: lo que aprende se lo entrega al core.
- Cumple el contrato de docs/MODULOS.md: un modulo.json con id, nombre, version, descripcion y acciones; cada acción
  dice si escribe (cambia algo fuera de Ashur) o solo lee.
- No agregues ninguna dependencia (paquete, librería o herramienta) sin listarla como propuesta para que Sergio la
  apruebe. Si el módulo no puede hacerse sin una, dilo y detente.
- El repo es público: no escribas IPs, rutas del servidor, claves, tokens ni nombres reales de personas o mascotas.
  Usa ejemplos inventados.
- Nunca hagas push a main ni lo integres tú: entrega una rama, un pull request o un parche para revisión.
- Cambios mínimos: solo lo pedido, sin funciones, abstracciones ni configuraciones extra.
- Si una decisión abierta de docs/DECISIONES-ABIERTAS.md afecta al módulo, no la resuelvas: nómbrala y sigue con la
  opción más simple, marcada como provisional.
</reglas>

<entrega>
1. La carpeta modules/<id>/ completa:
   - modulo.json según el contrato;
   - el código del módulo;
   - una autoprueba que corra sin red ni servicios externos, con datos inventados;
   - un README.md breve: qué hace, qué acciones tiene, cómo correr la autoprueba.
2. Un resumen de no más de 15 líneas con:
   - los archivos creados;
   - las dependencias propuestas, si hay;
   - las decisiones abiertas que tocó y qué supuso;
   - lo que falta para integrarlo al core.
3. El resultado real de correr la autoprueba, copiado tal cual. Si no pudiste correrla, dilo.
</entrega>

<cierre>
El trabajo no está terminado hasta que Claude Code lo revise con el advisor y lo integre. Termina tu respuesta con la
lista de lo que Claude Code debe revisar primero.
</cierre>
```

**Después:** pasa la rama, el pull request o el parche a Claude Code en este repo para que lo revise e integre.
