# ADR 0010: la app guarda un caché de lo último que mandó el core

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Quedaba abierto qué guarda la app en el dispositivo además de la clave, que ya va en el Llavero
(`docs/adr/0007-clave-en-el-dispositivo.md`). La memoria de Ashur vive en el core, no en la app.

## Decisión
- **Caché sin conexión:** la app guarda lo último que recibió del core (la galaxia y los recuerdos) para mostrar algo
  cuando no hay conexión.
- **Formato:** archivos JSON sin cifrar, en la carpeta de soporte de la app.
- **Paquete:** `path_provider`, para saber cuál es esa carpeta en cada plataforma. Sergio lo aprobó el 2026-11-21. Se
  agrega junto con el código que lo use, cuando la app se conecte al core.
- **Borradores del chat:** quedan para cuando exista el chat.

## Costos
- El caché no está cifrado: quien tenga acceso a los archivos de la app en el dispositivo puede leer los recuerdos
  guardados.
