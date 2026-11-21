# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 3. Manejo de estado en Flutter
Qué patrón o paquete maneja el estado de la app. PrivateLM usa GetX. Cualquier paquete necesita aprobación.

## 4. Almacenamiento en Flutter
Qué guarda la app en el dispositivo (caché, borradores, claves) y con qué. PrivateLM usa Hive. La memoria de Ashur
vive en el core, no en la app.

## 6. Tiempo de aprendizaje en el contrato de la galaxia
La densidad del polvo crece con el tiempo que Ashur lleva aprendiendo, $t_A$ (ver `docs/GALAXIA.md`), pero el
contrato todavía no trae ese dato. Hay que decidir si se agrega un campo al esquema (por ejemplo, la fecha en que
Ashur empezó a aprender) o si el cliente lo deja fijo mientras tanto.

## 8. Enlace de la memoria con el inventario y los contactos
Cada objeto de un recuerdo trae un `inventario_id`, y cada persona un `contacto_id`, pero ni el inventario ni la
lista de contactos existen todavía. Falta decidir cómo se enlazan cuando existan, y qué pasa con un recuerdo si se
borra un objeto o un contacto.

## 9. Quién decide qué se recuerda
Si Ashur guarda un recuerdo apenas lo aprende o se lo propone primero a Sergio para que lo apruebe.

## 10. Búsqueda por significado
Cómo encuentra Ashur los recuerdos relacionados con lo que se habla (por ejemplo, con embeddings). Cualquier
paquete o modelo nuevo necesita aprobación.

## 11. Reglas por sensibilidad y consentimiento
Hoy `sensibilidad` es solo un dato. Falta decidir, antes de usar Ashur en serio, qué nivel de inferencia puede
usar cada nivel de sensibilidad y qué consentimiento hace falta.
