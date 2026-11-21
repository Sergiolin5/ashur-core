# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 1. Nombre de la tercera pestaña
Las pestañas son Estado, Casa y una tercera. En el prototipo se llama "Herramientas", de forma provisional.

## 3. Manejo de estado en Flutter
Qué patrón o paquete maneja el estado de la app. PrivateLM usa GetX. Cualquier paquete necesita aprobación.

## 4. Almacenamiento en Flutter
Qué guarda la app en el dispositivo (caché, borradores, claves) y con qué. PrivateLM usa Hive. La memoria de Ashur
vive en el core, no en la app.

## 5. Vínculo con WhatsApp
Si el chat de Ashur se conecta con WhatsApp real o solo se parece a WhatsApp, y por qué vía.

## 6. Tiempo de aprendizaje en el contrato de la galaxia
La densidad del polvo crece con el tiempo que Ashur lleva aprendiendo, $t_A$ (ver `docs/GALAXIA.md`), pero el
contrato todavía no trae ese dato. Hay que decidir si se agrega un campo al esquema (por ejemplo, la fecha en que
Ashur empezó a aprender) o si el cliente lo deja fijo mientras tanto.
## 7. Personas en la memoria
Hoy un recuerdo guarda solo los nombres de las personas (`docs/adr/0004-memoria.md`). Falta decidir si las personas
son entidades propias, con su id, para reconocer a la misma persona en varios recuerdos.

## 8. Enlace de la memoria con el inventario
Cada objeto de un recuerdo trae un `inventario_id`, pero el inventario todavía no existe. Falta decidir cómo se
enlazan los dos cuando exista, y qué pasa con un recuerdo si se borra un objeto del inventario.

## 9. Quién decide qué se recuerda
Si Ashur guarda un recuerdo apenas lo aprende o se lo propone primero a Sergio para que lo apruebe.

## 10. Búsqueda por significado
Cómo encuentra Ashur los recuerdos relacionados con lo que se habla (por ejemplo, con embeddings). Cualquier
paquete o modelo nuevo necesita aprobación.

## 11. Reglas por sensibilidad y consentimiento
Hoy `sensibilidad` es solo un dato. Falta decidir, antes de usar Ashur en serio, qué nivel de inferencia puede
usar cada nivel de sensibilidad y qué consentimiento hace falta.
