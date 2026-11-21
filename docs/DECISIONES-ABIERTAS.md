# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 8. Enlace de la memoria con el inventario y las identidades
Cada objeto de un recuerdo trae un `inventario_id`, y cada identidad un `identidad_id`, pero ni el inventario ni la
lista de identidades existen todavía. Falta decidir cómo se enlazan cuando existan, qué pasa con un recuerdo si se
borra un objeto o una identidad, y qué guarda cada identidad (por ejemplo, su clase: persona, mascota).

## 10. Búsqueda por significado
Cómo encuentra Ashur los recuerdos relacionados con lo que se habla (por ejemplo, con embeddings). Cualquier
paquete o modelo nuevo necesita aprobación.

## 11. Reglas por sensibilidad y consentimiento
Hoy `sensibilidad` es solo un dato. Falta decidir, antes de usar Ashur en serio, qué nivel de inferencia puede
usar cada nivel de sensibilidad y qué consentimiento hace falta.

## 12. Cómo se ven los objetos del inventario
Los objetos no son cuerpos de la galaxia todavía. Sergio quiere decidir su forma según el objeto, cuidando que el
planeta Objetos no se llene.

## 13. Qué es una luna, además de una identidad
Hoy una luna es una identidad que se volvió importante (`docs/GALAXIA.md`). Sergio quiere que las lunas sean algo
representativo o grande; falta decidir si otras cosas también pueden serlo.
