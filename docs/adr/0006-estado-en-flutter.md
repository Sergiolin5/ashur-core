# ADR 0006: el estado de la app usa lo que trae Flutter

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Faltaba decidir cómo maneja la app su estado (decisión 3). Sergio no tenía preferencia, así que se registra la opción
por defecto: la que no agrega paquetes y la que la app ya usa.

## Decisión
- El estado vive en `ChangeNotifier` y `ValueNotifier`, y las pantallas lo leen con `ListenableBuilder` o
  `ValueListenableBuilder`.
- El ejemplo existente es la galaxia: un `ValueNotifier<double>` con el tiempo mueve el dibujo
  (`app/lib/galaxia/vista.dart`, ver `docs/adr/0002-render-galaxia.md`).
- No hay paquetes de manejo de estado.

## Cuándo revisarla
Si pasar el estado compartido entre varias pantallas se vuelve difícil, se puede cambiar a Riverpod, con aprobación
de Sergio.
