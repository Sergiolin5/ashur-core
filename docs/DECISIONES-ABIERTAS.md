# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 11. Consentimiento y sensibilidad
El acceso de otras personas al chat y su privacidad ya están decididos (`docs/adr/0022-personas-y-roles.md`). Quedan
dos partes:
- **Consentimiento:** si Sergio les avisa a los demás, antes de darles su clave, que lo que le digan a Ashur queda en
  su memoria.
- **Sensibilidad:** `sensibilidad` sigue siendo solo un dato (decisión de Sergio, 2026-11-21). Hay que decidir qué puede
  usar cada nivel de inferencia antes de que exista el nivel 3, la nube.

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
