# Borrador ADR 0025: jerarquía, identificadores y evidencia del inventario

- **Estado:** Propuesto; pendiente de decisiones de Sergio y revisión de Ashur Code.
- **Fecha:** 2026-11-22

## Contexto

[Seguro] El ADR 0014 define objetos planos con `id`, `nombre`, `lugar`, `archivado` y `menciones`, y dejó pendiente qué más guarda un objeto. [Seguro] El contrato rechaza campos adicionales. [Seguro] La base vigente usa el esquema 13 y las bases anteriores se migran al abrirse.

[Seguro] El lote descrito por Sergio contiene relaciones padre-hijo por `parent_id` y `slot`, ranuras declaradas por el padre, identificadores y especificaciones, evidencia por campo, y en algunos casos un estado de presencia sin confirmar. Los envíos no son objetos. [Seguro] La jerarquía no afecta la representación gráfica, que continúa fuera del alcance por la decisión abierta 12.

## Propuesta

Todos los campos de esta propuesta son opcionales: un objeto guardado antes de este cambio sigue siendo válido. [Probable] Se usarían nombres en español, coherentes con el contrato actual:

| Campo | Tipo propuesto | Uso |
| --- | --- | --- |
| `padre_id` | texto | Id del objeto padre; ausente para una raíz. |
| `ranura` | texto | Ranura del padre donde está instalado este componente; ausente para una raíz. |
| `ranuras` | lista de textos | Ranuras que ofrece el objeto para instalar componentes. |
| `identificadores` | objeto libre | Identificadores con las claves tal como vienen en el lote; no se limita a un catálogo fijo. |
| `especificaciones` | objeto libre | Especificaciones propias del objeto, sin imponer un catálogo global de atributos. |
| `evidencia` | objeto libre | Evidencia por campo y fuentes asociadas; se conserva como JSON sin normalizar sus claves ni valores. |
| `estado` | texto | Valor opcional recibido en `status`; se conserva literalmente, sin enumerar valores que el lote no define como catálogo. |

[Seguro] El lote usa claves variables dentro de `identifiers`, `specs` y `evidence`; la evidencia incluye fuentes y estados de confianza por campo, y `status` aparece como texto. [Probable] `estado` conserva ese `status` sin reemplazar `archivado`; `archivado` sigue controlando si el objeto aparece en listas activas. [Adivinando] `especificaciones` permitirá valores JSON libres, incluidos texto, número, booleano, lista u objeto, para no inventar una taxonomía que el lote no define.

## Validación de la jerarquía

- [Probable] Una raíz no lleva `padre_id` ni `ranura`. Un componente debe llevar `padre_id`; `ranura` puede ser `null` cuando no se conoce, y si trae un valor debe aparecer entre las ranuras declaradas por el padre.
- [Probable] Al crear o mover un componente, el core comprueba que `padre_id` exista, que padre e hijo sean objetos distintos y que no se forme un ciclo al recorrer la cadena de ancestros.
- [Probable] Toda ranura no nula debe aparecer en `ranuras` del padre. Se recomienda comparación exacta, sensible a mayúsculas y acentos, porque el contrato actual trata el texto libre literalmente.
- [Probable] La jerarquía se valida en el core, no solo en el schema: el schema valida formas y tipos, pero no puede comprobar referencias entre filas.

## Lugar de un componente

[Adivinando] `lugar` se reserva para la ubicación física de una raíz o conjunto. Los componentes heredan conceptualmente el lugar del ancestro raíz y guardan su ubicación interna mediante `ranura`; su `lugar` propio debe ser `null`. Al mover un componente, solo cambian `padre_id` y `ranura`. Esta regla evita que el mismo objeto aparente estar en lugares distintos de su padre.

## Archivo de un padre

[Adivinando] Se propone rechazar el archivo de un padre que tenga hijos activos (422); primero habría que mover o archivar cada hijo. Así no quedan componentes activos debajo de un objeto excluido de las listas normales. Archivar un hijo no afecta a su padre. Restaurar un objeto requiere que su padre, si tiene uno, esté activo.

## Base de datos y migración

[Probable] La próxima versión del esquema sería la 14. Al abrir una base 13, una migración transaccional agregaría las columnas opcionales de jerarquía y guardaría los campos estructurados (`identificadores`, `especificaciones`, `evidencia`) como JSON; los objetos anteriores recibirían valores ausentes o `NULL`, sin alterar ids, recuerdos, `menciones` ni orden. La lógica existente de apertura ya ejecuta migraciones de forma serializada y revierte la transacción ante un error.

[Adivinando] Se mantendrían los datos agrupados en columnas por campo, no en una única bolsa JSON, para que las relaciones se puedan validar y consultar sin deserializar todos los objetos. La decisión final sobre columnas frente a JSON debe seguir el formato exacto que Sergio apruebe.

## API

[Probable] Los endpoints existentes de `/objetos` conservarían sus rutas, claves y códigos base. `POST` aceptaría los campos opcionales; `GET` los devolvería; `PATCH` permitiría cambiar padre y ranura juntos para mover un componente y validaría la relación resultante. La respuesta mantendría todos los campos antiguos. No se agregan endpoints para envíos.

## Costos

- [Seguro] El lote real contiene seriales y otros datos privados, por lo que no se copia al repositorio público; el ejemplo del contrato usará datos inventados.
- [Probable] Cada creación o movimiento de un componente requiere consultas adicionales para comprobar padre, ranura y ciclos.
- [Probable] La evidencia describe lo que se sabe de cada campo, pero no vuelve verdadera una inferencia ni confirma presencia; clientes e importadores deben conservarla sin elevar su nivel.
- [Probable] Campos de especificaciones libres son flexibles, pero dificultan búsquedas uniformes y consistencia entre objetos.
- [Probable] Los clientes que no usan campos nuevos pueden seguir creando y leyendo objetos antiguos; los modelos de respuesta que rechazan claves nuevas deberán actualizarse antes de que reciban objetos con esas claves.

## Decisiones pendientes de Sergio

1. **Forma y nombres de los datos:** ¿aprobar los nombres propuestos (`padre_id`, `ranura`, `ranuras`, `identificadores`, `especificaciones`, `evidencia`, `estado`) y mantener libres las claves internas de identificadores/especificaciones, o preferir un esquema alternativo? [Probable]
2. **Semántica de lugar y archivo:** ¿un componente debe tener `lugar: null` y heredar la ubicación de su raíz, como se propone, y se rechaza archivar un padre con hijos activos? [Adivinando]
3. **Ranura, evidencia y estado:** ¿aprobar permitir `ranura: null` cuando el lote no la confirma, exigir que toda ranura indicada esté declarada por el padre, y conservar `evidencia`/`status` exactamente como llegan (traduciendo solo el nombre externo `status` a `estado`)? [Probable]

## Revisión

[Seguro] No se consultó al advisor de Claude Code: no está disponible entre las herramientas de esta sesión. Este archivo es solo un borrador de propuesta; no registra una decisión aceptada. Ashur Code debe revisar la propuesta antes de que se considere cerrada.
