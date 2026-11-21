# ADR 0002: cómo se dibuja la galaxia

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
La pantalla de inicio dibuja la galaxia de `docs/GALAXIA.md` a partir del contrato
`contracts/galaxy-state.schema.json`, en movimiento continuo y sin paquetes de terceros. Lo de no usar paquetes
fue solo para este prototipo: la regla del repo es pedir aprobación antes de agregar uno (`CLAUDE.md`).

## Decisión
- **Dibujo:** un solo `CustomPainter` (`app/lib/galaxia/pintor.dart`) que se repinta cada cuadro. Lo mueve un
  `Ticker` que actualiza un `ValueNotifier<double>` con el tiempo; el pintor escucha ese notificador (`repaint:`),
  así que no hay `setState` en cada cuadro (`app/lib/galaxia/vista.dart`).
- **Sin Flame y sin shaders propios.** Con círculos, líneas y caminos del `Canvas` alcanza. Los únicos `createShader`
  del código son los degradados que trae `Canvas` (`RadialGradient` del halo del núcleo y `LinearGradient` de la cola
  de las estrellas), no programas de fragmentos.
- **Solo `package:flutter/widgets.dart`.** `flutter create` (Flutter 3.50.1) añadió `material_ui` y `flutter_lints`
  al `pubspec.yaml`; se quitaron porque la fase pedía cero paquetes de terceros. `package:flutter/material.dart`
  está marcado `@Deprecated` en esta versión, así que la app usa `WidgetsApp` y no usa Material.
- **El JSON de ejemplo se lee directo de `contracts/`:** `pubspec.yaml` declara
  `../contracts/galaxy-state.ejemplo.json` como asset, así que hay una sola fuente. Funciona en `flutter test` y en
  el simulador de iOS, donde el archivo queda en `App.framework/contracts/`, fuera de `flutter_assets`, y aun así
  carga. En macOS solo se comprobó que queda empaquetado (no se abrió la app). En Windows y Android no se verificó.
  Si alguna plataforma falla, la alternativa es una copia en `app/assets/` con un test que compare los bytes con
  `contracts/`.

## Fórmulas y parámetros
Las fórmulas son las de `docs/GALAXIA.md`. Las distancias y radios son fracciones de la mitad del lado corto de la
pantalla.

| Parámetro | Valor | Constante en `pintor.dart` |
| --- | --- | --- |
| Radio del núcleo | 0.09 | `radioNucleo` |
| $R_{\min}$, $R_{\max}$ (planetas) | 0.025, 0.06 | `radioPlanetaMin`, `radioPlanetaMax` |
| $d_{\min}$, $d_{\max}$ (órbitas de planetas) | 0.34, 0.88 | `distanciaMin`, `distanciaMax` |
| Órbita y radio de los agentes | 0.17, 0.012 | `distanciaAgente`, `radioAgente` |
| Órbita y radio de los asteroides | radio del planeta + 0.035, 0.009 | `distanciaAsteroide`, `radioAsteroide` |
| $T_0$ (periodo de todos los planetas) | 24 s | `periodoBase` |
| Periodo de agentes y asteroides | 7 s, 5 s | `periodoAgente`, `periodoAsteroide` |
| $\tau$ (viaje de una estrella) | 2.4 s | `duracionEstrella` |
| Ciclo y desfase de las estrellas | 7 s, 2.3 s | `cicloEstrellas`, `desfaseEstrellas` |
| $N$, $a$, $b$ (brazos de polvo) | 2, 0.06, 0.28 | `brazos`, `espiralA`, `espiralB` |
| $\omega$ (giro del polvo) | 0.03 rad/s | `omegaPolvo` |
| $\rho$ (granos de polvo) | 700 | `densidadPolvo` |

Las dos reglas que eligió Sergio son un interruptor cada una:
- `pesadosCerca = true`: los planetas más pesados orbitan más cerca del núcleo.
- `periodoKepler = false`: todos los planetas giran a la misma velocidad angular.

## Lo que el cliente supone porque el contrato no lo trae
- **Instantes de los eventos:** los eventos no tienen hora, así que cada estrella fugaz se repite en bucle,
  desfasada de las demás.
- **Tiempo de aprendizaje $t_A$:** no está en el contrato, así que la densidad del polvo es fija
  (ver `docs/DECISIONES-ABIERTAS.md`).
- **Toque del núcleo:** se acepta un toque dentro de su radio, con un mínimo de 22 px para que sea fácil de tocar.

## Navegación
- Tocar el núcleo abre "Chats" con un zoom hacia adentro centrado en el punto tocado (`rutaZoom` en
  `app/lib/pantallas.dart`).
- La barra de abajo tiene exactamente tres pestañas: Estado, Casa y Workbench (el nombre se decidió en
  `docs/adr/0005-workbench-y-whatsapp.md`). Cada una abre su
  pantalla vacía encima de la galaxia, con una flecha para volver. La galaxia sigue siendo la pantalla de inicio.
