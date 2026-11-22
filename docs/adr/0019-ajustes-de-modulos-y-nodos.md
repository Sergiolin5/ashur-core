# ADR 0019: los ajustes de cada módulo y de cada nodo viven en el core

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
Sergio pidió una configuración avanzada desde la app para lo de Ashur, lo de cada módulo y lo de cada nodo. No puede
ser un módulo:
- el contrato de `docs/MODULOS.md` solo corre acciones y guarda recuerdos;
- ningún módulo puede cambiar el core.

Así que se reparte:
- **El core** guarda los ajustes y los hace cumplir (este ADR).
- **Otra IA** hace la pantalla, una sección «Configuración avanzada» en la pestaña Estado (decisión de Sergio). Desde la Mac, porque esa pantalla se compila allá.

Lo de Ashur (personalidad, madurez, roles) se suma cuando existan sus rutas, en las fases 5 y 6 del chat
(ADR 0016).

## Decisión
- **Ajustes de un módulo:**
  - El manifiesto puede declarar `ajustes` (`contracts/modulo.schema.json`). Cada uno trae:
    - `id`;
    - `tipo`: `texto`, `numero` o `booleano`;
    - `descripcion`;
    - `por_defecto`, del mismo tipo o `null`;
    - `secreto`, solo para texto.
  - Es opcional: los manifiestos de antes, sin `ajustes`, siguen cargando. Un `por_defecto` de otro tipo deja el módulo con su error, sin tumbar el core.
  - El módulo los lee con `contexto.ajuste(id)`: lo que puso Sergio, o el `por_defecto`.
  - `GET /modulos/{id}/ajustes` (clave normal) devuelve cada ajuste con su valor y si está configurado. Un secreto nunca vuelve: su valor sale como `null`.
  - `PATCH /modulos/{id}/ajustes` (clave de administrador) cambia solo los enviados. `null` vuelve al `por_defecto`.
  - Si un ajuste no existe o es de otro tipo, responde 422 sin cambiar nada.
  - Se guardan en la tabla `ajustes_modulos` (esquema 11), como JSON.
- **Ajustes de un nodo**, en `PATCH /nodos/{id}` (clave de administrador), junto con `archivado`:
  - **`modelos_ofrecidos`:** los únicos modelos que el core le asigna. El core lo hace cumplir, diga lo que diga el nodo, también para decidir qué nodo es el mejor.
  - **`num_ctx`:** el contexto que el nodo le pide a su modelo, entre 512 y 131 072.
  - **`horario`:** `{desde, hasta}` en la hora local del equipo; si `hasta` es menor que `desde`, cruza la medianoche. Fuera del horario, el nodo se ofrece en `off`.

  `null` en cualquiera vuelve a lo que el nodo decida por su cuenta. Los ajustes vuelven en la respuesta de cada
  latido (`contracts/nodo.schema.json`), y el nodo los aplica. Las variables de entorno del nodo quedan como respaldo.
- **Umbrales:** los demás números (latido, plazo, búsqueda) siguen siendo constantes del código. Solo los umbrales de
  madurez serán ajustables, en la fase 6.

## Costos
- **Los secretos de los módulos se guardan en claro en la base,** igual que el resto de la memoria. La app nunca los
  vuelve a ver, pero quien tenga la base sí.
- **El horario depende del reloj del equipo:** el core no sabe en qué zona horaria está cada nodo.
- **Un nodo de antes** (fase 2) no aplica `num_ctx` ni el horario. `modelos_ofrecidos` sí se cumple, porque lo hace
  cumplir el core.

## Verificado (2026-11-22)
- `uv run pytest`:
  - **Ajustes de módulos:**
    - un manifiesto sin ajustes sigue valiendo, y uno con un `por_defecto` de otro tipo queda con su error;
    - el secreto nunca vuelve, pero el módulo lo lee;
    - `null` vuelve al `por_defecto`;
    - tipos equivocados o ajustes desconocidos dan 422 sin cambios a medias;
    - cambiar pide la clave de administrador.
  - **Ajustes de nodos:**
    - viajan en el latido;
    - el core asigna solo los modelos ofrecidos;
    - `null` vuelve a lo del nodo;
    - los valores inválidos dan 422.
  - La plantilla trae un ajuste de ejemplo (`saludo`) y su autoprueba lo cubre.

## Pendiente
- La sección «Configuración avanzada» de la app, con su ADR 0020.
- Lo de Ashur en la misma pantalla, cuando existan sus rutas (fases 5 y 6).
