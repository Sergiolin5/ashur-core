# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 10. Búsqueda por significado
La búsqueda por palabras ya existe (`docs/adr/0004-memoria.md`). Falta la búsqueda por significado, con embeddings que
calcule el modelo de los nodos de casa: qué modelo, dónde se guardan y cuándo se calculan. Cualquier paquete o modelo
nuevo necesita aprobación.

## 11. Reglas por sensibilidad y consentimiento
Por ahora `sensibilidad` es solo un dato y no cambia nada (decisión de Sergio, 2026-11-21, mientras Ashur es una
prueba). Las reglas de qué puede usar cada nivel y qué consentimiento hace falta se deciden antes de que alguien más
que Sergio use Ashur.

## 12. Cómo se ven los objetos del inventario
Los objetos no son cuerpos de la galaxia todavía. Sergio quiere decidir su forma según el objeto, cuidando que el
planeta Objetos no se llene.

## 13. Qué es una luna, además de una identidad
Hoy una luna es una identidad que se volvió importante (`docs/GALAXIA.md`). Sergio quiere que las lunas sean algo
representativo o grande; falta decidir si otras cosas también pueden serlo.

## 17. La galaxia en el Duo abierto
Con el iPhone Duo abierto, la galaxia debería correrse a la mitad derecha, como se ve con el teléfono cerrado. El
código lo hace si Flutter informa un pliegue vertical, pero en el teléfono de Sergio no se corre: lo más probable es
que iOS no le pase el pliegue a Flutter. Sergio lo dejó así mientras la app es un boceto. Falta averiguar cómo se
entera la app del pliegue en iOS (por ejemplo, con un canal de plataforma en Swift).
