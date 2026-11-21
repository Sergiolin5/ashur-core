# Decisiones abiertas

Cada una espera la decisión de Sergio. Cuando se cierre, se registra como ADR en `docs/adr/` y se quita de aquí.

## 1. Nombre de la tercera pestaña
Las pestañas son Estado, Casa y una tercera. En el prototipo se llama "Herramientas", de forma provisional.

## 2. Stack del servidor (`core/`)
Lenguaje, framework REST y base de datos del core. El repo anterior usaba Python con FastAPI y SQLite
(`/Users/sermolin/Developer/ashur/core/`), solo como antecedente.

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

## Nota para la fase 2: el JSON de ejemplo como asset
Flutter no puede declarar como asset un archivo fuera de la carpeta del proyecto (`app/`), así que
`contracts/galaxy-state.ejemplo.json` no se puede referenciar directo con `../contracts/`. Hay que decidir cómo
llega a `app/` (por ejemplo, una copia o un enlace simbólico) sin que deje de existir una sola fuente.
