# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 4. Almacenamiento en Flutter
La clave del core ya se guarda con `flutter_secure_storage` (`docs/adr/0007-clave-en-el-dispositivo.md`). Falta
decidir qué más guarda la app en el dispositivo (caché, borradores) y con qué. PrivateLM usa Hive. La memoria de
Ashur vive en el core, no en la app.

## 6. Tiempo de aprendizaje en el contrato de la galaxia
La fórmula ya está decidida (`docs/GALAXIA.md`): el polvo crece un poco con el tiempo y sobre todo con los
recuerdos. Falta agregar al contrato la fecha en que Ashur empezó a aprender y la cantidad de recuerdos, y decidir de
dónde sale esa fecha. Se hace junto con la definición de qué otras cosas son cuerpos de la galaxia.

## 8. Enlace de la memoria con el inventario y los contactos
Cada objeto de un recuerdo trae un `inventario_id`, y cada persona un `contacto_id`, pero ni el inventario ni la
lista de contactos existen todavía. Falta decidir cómo se enlazan cuando existan, y qué pasa con un recuerdo si se
borra un objeto o un contacto.

## 10. Búsqueda por significado
Cómo encuentra Ashur los recuerdos relacionados con lo que se habla (por ejemplo, con embeddings). Cualquier
paquete o modelo nuevo necesita aprobación.

## 11. Reglas por sensibilidad y consentimiento
Hoy `sensibilidad` es solo un dato. Falta decidir, antes de usar Ashur en serio, qué nivel de inferencia puede
usar cada nivel de sensibilidad y qué consentimiento hace falta.
