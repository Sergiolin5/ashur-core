# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 4. Almacenamiento en Flutter
La clave del core ya se guarda con `flutter_secure_storage` (`docs/adr/0007-clave-en-el-dispositivo.md`). Falta
decidir qué más guarda la app en el dispositivo (caché, borradores) y con qué. PrivateLM usa Hive. La memoria de
Ashur vive en el core, no en la app.

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

## 15. De dónde sale la fecha en que Ashur empezó a aprender
El contrato trae `aprendizaje.inicio`, pero el core todavía no publica la galaxia. Falta decidir de dónde sale esa
fecha (por ejemplo, el momento en que se creó la base de la memoria).

## 16. Seguir un cuerpo con la cámara
Con zoom, los planetas siguen girando y salen de la pantalla en pocos segundos. Falta decidir si la cámara sigue al
cuerpo que se está mirando, o si la galaxia se detiene mientras uno se acerca.
