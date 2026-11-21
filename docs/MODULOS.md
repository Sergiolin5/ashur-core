# Contrato de módulos

Todo lo que no es core (memoria, chat, inventario de objetos físicos e identidades) es un módulo. Cada módulo vive en su propia
carpeta `modules/<id>/`, no depende de otro módulo y cumple este contrato. `modules/_plantilla/` es el punto de partida.
Las carpetas que empiezan con `_` no se registran.

## 1. Qué expone
Cada módulo tiene un manifiesto `modulo.json` en su raíz con:

| Campo | Qué es |
| --- | --- |
| `id` | Identificador único, en minúsculas y sin espacios. Es también el id de su planeta en la galaxia. |
| `nombre` | Nombre visible para Sergio. |
| `version` | Versión del módulo. |
| `descripcion` | Una frase sobre lo que hace. |
| `acciones` | Lista de lo que el módulo sabe hacer. Cada acción tiene `id`, `descripcion` y si `escribe` (cambia algo fuera de Ashur) o solo lee. |

El módulo no guarda memoria propia: lo que aprende se lo entrega al core, que es la única memoria de Ashur.

## 2. Cómo se registra en el core
- El core descubre cada módulo leyendo su `modulo.json`.
- Al registrarlo, el core guarda el manifiesto y empieza a ofrecer sus acciones a Ashur.
- Una acción que `escribe` necesita la aprobación de Sergio antes de ejecutarse.
- El mecanismo concreto (endpoint REST, carpeta compartida u otro) está por definir sobre el stack del servidor
  (`docs/adr/0003-stack-servidor.md`).

## 3. Cómo aparece en la galaxia
- Cada módulo registrado es un **planeta** con `id` igual al `id` del módulo y `nombre` igual al del manifiesto.
- La **masa** la calcula el core según la importancia que aprendió; el módulo no la declara.
- Si el módulo está bloqueado (le falta un permiso, no responde, espera una respuesta), el core publica un
  **asteroide** que orbita su planeta.
- Lo que el módulo entrega al core aparece como una **estrella fugaz** con destino a su planeta.

Formato exacto: `contracts/galaxy-state.schema.json`.
