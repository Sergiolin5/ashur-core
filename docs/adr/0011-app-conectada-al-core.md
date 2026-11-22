# ADR 0011: la app pide la galaxia al core

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
La app dibujaba la galaxia de ejemplo de `contracts/`. Sergio pidió que muestre lo que de verdad sabe el core.

## Decisión
- **Core:** `GET /galaxia`, con la clave normal, devuelve el estado de la galaxia según `contracts/galaxy-state.schema.json`.
  Hoy trae el núcleo, los planetas Identidades y Objetos (colecciones del core, con `ref: null`) y el `aprendizaje`
  real de la base. No inventa agentes, módulos ni eventos: todavía no existen en el core.
- **Cliente:** `HttpClient` de `dart:io`, sin paquetes, con espera máxima de 8 s. La pestaña Estado distingue
  core inalcanzable, clave rechazada (401) y core sin clave (503).
- **Dirección y clave:** se pegan en la pestaña Estado y se guardan en el Llavero con `flutter_secure_storage`
  (`docs/adr/0007-clave-en-el-dispositivo.md`), con `usesDataProtectionKeychain: false` en macOS. Nunca entran al repo.
  Cada campo tiene un botón «Pegar», porque la clave tiene 64 caracteres.
- **Caché:** lo último que mandó el core se guarda en `galaxia.json`, en la carpeta de soporte de la app, con
  `path_provider` (aprobado por Sergio, `docs/adr/0010-cache-en-el-dispositivo.md`).
- **Qué se muestra:** lo que acaba de mandar el core; si no responde, lo último guardado; y la galaxia de ejemplo solo
  cuando todavía no hay un core configurado, para que los datos inventados nunca parezcan reales.
- **macOS:** la app tiene el permiso `com.apple.security.network.client` para poder salir a la red.
- **Campos de texto:** usan `CupertinoTextField`. Flutter marca `package:flutter/cupertino.dart` como obsoleto en favor
  del paquete `cupertino_ui`, que no está aprobado; el import lleva una excepción comentada.

## Verificado (2026-11-21)
- `uv run pytest`: `GET /galaxia` cumple el contrato y pide la clave.
- `flutter test`: el cliente contra un core falso en localhost (clave buena, 401, 503 e inalcanzable) y el orden de lo
  que se muestra (ejemplo sin configurar, core, lo guardado si se cae, nada si nunca respondió).

## Sin verificar
- **Escribir en los campos desde el simulador:** la automatización perdía caracteres y el botón «Pegar» no recibió el
  portapapeles del simulador. Se prueba a mano en el iPhone.
- **HTTP sin cifrar a una IP en iOS** (App Transport Security): si iOS lo bloquea, la pestaña Estado lo dirá como
  «No se pudo llegar al core», y habrá que agregar una excepción mínima en `Info.plist`.
- **Leer y escribir el Llavero en el dispositivo.**

## Pendiente
- **Identidades, agentes y módulos reales** en la galaxia, cuando existan en el core.
