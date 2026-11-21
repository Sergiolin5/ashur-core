# ADR 0001: el cliente de Ashur es Flutter

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Ashur necesita un cliente en iOS, macOS, Windows y Android. En el repo anterior, mantener dos clientes iguales
(panel web y app nativa de iOS) obligó a llevar una lista de paridad con un chequeo en CI
(`/Users/sermolin/Developer/ashur/docs/ios/NATIVO.md`, `ios/paridad.json`). PrivateLM demuestra un cliente de chat
con IA funcionando en Flutter (`docs/REFERENCIA-PRIVATELM.md`).

## Decisión
El cliente es una sola app Flutter en `app/`, con un solo código para iOS, macOS, Windows y Android, en ese orden de
prioridad.

## Costos
### 1. Puentes nativos para HomeKit y Health
- Flutter no accede directo a HomeKit ni a HealthKit. Cada uno necesita un puente con código Swift (un plugin o un
  canal de plataforma), sus capabilities y sus entitlements en Xcode.
- Los plugins nativos en iOS y macOS se integran con CocoaPods o con Swift Package Manager. CocoaPods no está instalado
  en esta Mac; el soporte de Swift Package Manager de Flutter está activado (`flutter doctor`, 2026-11-21).
- **macOS y HomeKit:** el SDK de macOS 27.2 no trae `HomeKit.framework` para apps de macOS. Solo existe en la capa
  de Mac Catalyst (`MacOSX27.2.sdk/System/iOSSupport/System/Library/Frameworks/HomeKit.framework`), y
  `HMHome.h` declara `API_AVAILABLE(..., macCatalyst(14.0)) API_UNAVAILABLE(macos)`. La app de macOS que genera
  Flutter es una app nativa de macOS (AppKit), no de Catalyst, así que **no puede usar HomeKit**. En consecuencia,
  la pestaña Casa en la Mac tiene que leer la casa a través del core (con los datos que le pase un iPhone u otro
  equipo con acceso a HomeKit), no directamente.
- **macOS y Health:** `HKHealthStore` sí declara `macos(13.0)` en `HKHealthStore.h` del SDK de macOS; que haya datos
  de Salud útiles en la Mac está por verificar.
- **Windows y Android:** no tienen HomeKit ni HealthKit. Casa y Salud en esas plataformas tendrán que pasar por el core
  o por otra vía.
- **Cuenta gratuita de Apple:** el repo anterior anotó como probable, no comprobado, que HealthKit y HomeKit funcionan
  con un Personal Team (`/Users/sermolin/Developer/ashur/docs/ios/ETAPA3.md`, Entorno). Hay que verificarlo en
  Signing & Capabilities antes de prometerlo.

### 2. Windows no se compila desde la Mac
- `flutter build windows` solo corre en un equipo con Windows. Desde esta Mac, todo lo de Windows queda como
  "no verificado" hasta compilarlo en un equipo Windows o en CI.
- Android tampoco se compila hoy en esta Mac: falta el Android SDK (`flutter doctor`, 2026-11-21).
