# ADR 0009: zoom de la galaxia con una cámara propia

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Sergio pidió escalas como las reales: todo está lejos y se ve más al acercarse. Los personajes de Identidades solo
se ven de cerca (`docs/adr/0008-cuerpos-reales-de-la-galaxia.md`).

## Decisión
- **Cámara propia:** `app/lib/galaxia/camara.dart` guarda el zoom y el desplazamiento, y el pintor lleva cada punto a
  la pantalla con las fórmulas de `docs/GALAXIA.md`. No se usa `InteractiveViewer`, porque escala todo el lienzo: el
  polvo y las líneas crecerían y no habría nivel de detalle.
- **Gestos:** un solo `GestureDetector` con toque y escala, que cubre acercar con dos dedos, mover con uno y el pellizco
  del trackpad. La rueda del mouse acerca con un `Listener`. No hay doble toque, porque haría esperar cada toque
  sencillo y retrasaría el que abre el chat.
- **Volver:** al alejarse hasta $z = 1$ la galaxia regresa sola al centro.
- **Seguir un cuerpo** (decisión 16, elegida por Sergio): al acercar, la cámara sigue al cuerpo que quedó bajo los
  dedos y la galaxia sigue girando. Moverla con un dedo lo suelta. El cuerpo se elige en el primer cuadro con dos
  dedos, con un margen de 48 px porque el foco queda entre los dedos y el cuerpo se mueve.
- **Repintado:** la cámara vive en un `ValueNotifier`, y el pintor se repinta cuando cambian la cámara o el tiempo,
  sin `setState` en cada gesto.
- **Sin paquetes:** todo viene con Flutter.

## Verificado (2026-11-21)
- `flutter test` (11 pruebas) cubre ida y vuelta entre pantalla y mundo, el foco quieto al acercar, el regreso en
  $z = 1$, el límite del desplazamiento, la opacidad, el toque del núcleo con zoom, el dibujo de cerca sobre
  Identidades y, con gestos simulados de dos dedos, que la cámara siga a Identidades mientras gira y que un dedo la
  suelte.
- En el simulador de iPhone: acercar con dos dedos, ver los personajes dentro de Identidades y abrir el chat tocando
  el núcleo con zoom.

## Pendiente
- **Seguir un cuerpo en el simulador:** el pellizco automático no alcanzó a caer sobre el planeta en movimiento, así
  que esa parte se probó con gestos simulados, no a mano.
- **Trackpad y rueda en macOS:** sin probar en la Mac.
- Los valores de la cámara son provisionales.
