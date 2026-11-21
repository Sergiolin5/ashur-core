# ADR 0007: la app guarda la clave del core con flutter_secure_storage

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Para hablar con la memoria del core, la app tiene que enviar `ASHUR_CLAVE` en el encabezado `X-Ashur-Clave`
(`docs/adr/0004-memoria.md`). Es un secreto, así que no puede guardarse en un archivo común. Es la primera parte de
la decisión 4 (almacenamiento en Flutter).

## Decisión
- **Paquete:** `flutter_secure_storage` 11.2.0, de un publicador verificado (steenbakker.dev). Sergio lo aprobó el
  2026-11-21. Usa el Llavero en iOS y macOS.
- **Paquetes nuevos:** agregó 33 paquetes al `pubspec.lock` (el paquete y sus implementaciones por plataforma). No
  cambió la versión de ningún paquete que ya estaba.
- **macOS:** se va a llamar con `MacOsOptions(usesDataProtectionKeychain: false)`. Así no hace falta la capacidad
  Keychain Sharing, que con la cuenta gratuita de Apple solo deja abrir la app en la Mac que la compiló.

## Verificado (2026-11-21)
- `flutter build macos --debug` y `flutter build ios --simulator --debug` compilan con Swift Package Manager, sin
  CocoaPods.
- `flutter test` y `flutter analyze` pasan.

## Sin verificar
- **Leer y escribir el Llavero:** ningún código usa el paquete todavía. Se usa cuando la app se conecte al core, y
  ahí se prueba también la opción de macOS.
- **Windows:** no se compila desde la Mac (`docs/adr/0001-cliente-flutter.md`).
- **Android:** el paquete pide el SDK mínimo 23, y `app/android/app/build.gradle.kts` usa `flutter.minSdkVersion`.
  Hay que fijarlo antes de la primera compilación de Android. Además, el Android SDK no está instalado en la Mac.
