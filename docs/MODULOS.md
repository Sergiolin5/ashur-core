# Contrato de módulos

Todo lo que no es core (memoria, chat, inventario de objetos físicos e identidades) es un módulo. Cada módulo vive en su propia
carpeta `modules/<id>/`, no depende de otro módulo y cumple este contrato. `modules/_plantilla/` es el punto de partida.
Las carpetas que empiezan con `_` no se registran.

## 1. Qué expone
Cada módulo tiene un manifiesto `modulo.json` en su raíz con:

| Campo | Qué es |
| --- | --- |
| `id` | Identificador único, en minúsculas y sin espacios. Su planeta en la galaxia lo nombra en `ref` (`{"tipo": "modulo", "id": ...}`). |
| `nombre` | Nombre visible para Sergio. |
| `version` | Versión del módulo. |
| `descripcion` | Una frase sobre lo que hace. |
| `acciones` | Lista de lo que el módulo sabe hacer. Cada acción tiene `id`, `descripcion` y si `escribe` (cambia algo fuera de Ashur) o solo lee. |

El módulo no guarda memoria propia: lo que aprende se lo entrega al core, que es la única memoria de Ashur. Sí puede
guardar datos propios de trabajo (sección 2).

## 2. Cómo se registra y corre en el core
Ver `docs/adr/0013-modulos-en-el-core.md`.

- **Archivos:** además de `modulo.json` (formato exacto en `contracts/modulo.schema.json`), cada módulo trae:
  - `modulo.py`, con una función por acción, con el mismo nombre que su `id`:
    `def <accion>(contexto, **parametros) -> dict`;
  - `autoprueba.py`, que corre sin red ni core, con un contexto falso. Desde `core/`:
    `uv run pytest ../modules/<id>/autoprueba.py`.
- **Contexto:** `contexto.recordar(texto, fecha=None, sensibilidad="normal", identidades=None, objetos=None,
  opinion=None)` guarda un recuerdo en el core con `origen` igual al id del módulo. Con `contexto.datos` y `contexto.ajuste(id)` (abajo),
  es todo lo que el módulo recibe.
  Como no puede consultar las identidades ni el inventario, usa `identidad_id: null` e `inventario_id: null`: un id
  que no existe hace fallar la acción.
- **Datos propios:** `contexto.datos` guarda registros JSON del módulo, agrupados en colecciones:
  `listar(coleccion)`, `leer(coleccion, id)`, `guardar(coleccion, datos, id=None)` y `borrar(coleccion, id)`. Un módulo
  solo ve los suyos, y no son recuerdos: lo que Ashur deba saber se entrega con `contexto.recordar(...)`. Cambiar los
  datos propios no cuenta como escribir (`docs/adr/0029-datos-propios-de-los-modulos.md`).
- **Ajustes:** el manifiesto puede declarar `ajustes`, cada uno con `id`, `tipo` (`texto`, `numero` o `booleano`),
  `descripcion`, `por_defecto` y `secreto` (solo texto). Sergio los cambia desde la app, y el módulo los lee con
  `contexto.ajuste(id)`, que devuelve lo que puso Sergio o el `por_defecto`. Un secreto nunca se vuelve a mostrar
  (`docs/adr/0019-ajustes-de-modulos-y-nodos.md`). Es opcional: un manifiesto sin `ajustes` sigue valiendo.
- **Registro:** el core descubre los módulos de `modules/` solo. Uno roto aparece en `GET /modulos` con su error.
- **Acciones que escriben:** `POST /modulos/<id>/acciones/<accion>` crea un pedido pendiente, y la acción corre recién
  cuando un administrador lo aprueba en `POST /pedidos/<id>/aprobar`.
- **Sin paquetes nuevos** salvo aprobación de Sergio; si hace falta uno, se agrega al core en una tarea aparte.
- **Ejemplo:** `modules/_plantilla/`.

## 3. Cómo aparece en la galaxia
- Cada módulo registrado es un **planeta** con `ref: {"tipo": "modulo", "id": <id del módulo>}` y `nombre` igual al
  del manifiesto. El `id` del planeta es propio de la galaxia (`docs/adr/0008-cuerpos-reales-de-la-galaxia.md`).
- La **masa** la calcula el core según la importancia que aprendió; el módulo no la declara.
- La masa es 1 más la cantidad de recuerdos con su `origen`.
- **Pendiente** (`docs/adr/0013-modulos-en-el-core.md`): si el módulo está bloqueado (le falta un permiso, no
  responde, espera una respuesta), el core publicará un **asteroide** que orbita su planeta, y lo que entrega
  aparecerá como una **estrella fugaz** con destino a su planeta.

Formato exacto: `contracts/galaxy-state.schema.json`.
