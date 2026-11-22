# ADR 0025: las claves del core se desbloquean con Face ID

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
Desde el ADR 0015 el teléfono guarda dos claves en el Llavero: `ASHUR_CLAVE` y `ASHUR_CLAVE_ADMIN`. La de administrador
tiene privilegios totales en el core. Hasta ahora las dos se leían sin pedir nada, así que quien tuviera el teléfono
desbloqueado podía usarlas. Sergio pidió protegerlas con Face ID.

## Decisión
- **Una sola entrada protegida:** las dos claves van juntas en `ashur.claves` (JSON `{"clave": ..., "admin": ...}`),
  guardada con `flutter_secure_storage` y `AccessControlFlag.userPresence`. Leerla pide Face ID, Touch ID o el
  código del teléfono. Al estar juntas, Face ID se pide una vez y no una por clave.
- **Una vez por sesión:** después de desbloquear, las claves quedan en memoria hasta cerrar la app. Si dos partes de la
  app las piden a la vez, comparten la misma lectura y Face ID se pide una sola vez.
- **Si Face ID falla o se cancela:** la conexión queda `bloqueada`. La galaxia muestra lo último guardado (nunca el
  ejemplo). La pestaña Estado lo explica y ofrece «Desbloquear con Face ID», o volver a pegar las claves. Inventario
  indica que hay que desbloquearlas en Estado.
- **Migración:** si no existe `ashur.claves`, se leen las claves viejas sin protección (`ashur.clave`,
  `ashur.clave_admin`), se guardan en la entrada protegida y se borran. La dirección del core sigue sin protección.
- **Info.plist:** `NSFaceIDUsageDescription` explica para qué se usa Face ID.
- **Sin paquetes nuevos:** usa el `flutter_secure_storage` 11.2.0 aprobado en el ADR 0007; `pubspec.yaml` y
  `pubspec.lock` no cambiaron.

## Costos
- Cada vez que se abre la app aparece Face ID.
- **macOS:** la app usa el Llavero sin protección de datos (ADR 0007), así que allí las claves no piden Touch ID.
- **Teléfono sin código:** con `userPresence`, iOS no deja guardar la entrada si el teléfono no tiene código; guardar
  las claves fallaría. No se maneja.

## Verificado (2026-11-22)
- `flutter analyze` sin avisos y `flutter test` con 33 pruebas, todas bien. Las nuevas: las claves viejas se mueven y
  se borran; Face ID se pide una vez por sesión; cancelado, queda bloqueada con lo guardado y se puede volver a
  intentar; cancelado sin nada guardado, no hay galaxia ni ejemplo.
- Quitar el reinicio tras un fallo hace fallar la prueba de volver a intentar; quitar la lectura compartida hace
  fallar la de una vez por sesión.

## Sin verificar
- **En el iPhone real:** que Face ID aparezca al abrir la app y que la migración conserve las claves que ya estaban.
  `main.dart` llama a `actualizar()` justo después de `runApp`, antes del primer cuadro: si iOS no muestra Face ID
  tan pronto y la app arranca siempre bloqueada, hay que mover esa llamada a después del primer cuadro.
- Guardar encima de una entrada protegida que ya existe podría pedir Face ID otra vez.
