# ADR 0009: zoom de la galaxia con una cámara propia

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Sergio pidió escalas como las reales: todo está lejos y se ve más al acercarse. Los personajes de Identidades solo
se ven de cerca (`docs/adr/0008-cuerpos-reales-de-la-galaxia.md`).

## Decisión
- **Zoom máximo:** 200×, para que de cerca se sienta lo lejos que está todo.
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

## Lo que falló en el iPhone y cómo se arregló (2026-11-21)
- **La cámara no seguía al planeta.** En un teléfono real, el primer cuadro con dos dedos llega con escala 1. Eso
  dejaba el zoom en 1, y el límite del desplazamiento devolvía la cámara inicial y perdía el cuerpo seguido. Ahora el
  límite conserva el cuerpo seguido, y el cuerpo se vuelve a buscar en cada cuadro con dos dedos hasta encontrarlo.
- **Lo soltaba al levantar los dedos.** El dedo que queda al final del pellizco movía la vista. Ahora un `Listener`
  cuenta los dedos, y ese último dedo no mueve nada; solo un gesto nuevo de un dedo suelta el cuerpo.
- **Volvía al centro solo al final.** El límite del desplazamiento ahora se achica de a poco al alejar
  (`docs/GALAXIA.md`).
- **Los planetas iban muy rápido y los personajes no se distinguían.** Órbitas más lentas, personajes con figura y
  nombres desde que Identidades mide 48 px en pantalla.

## Verificado (2026-11-21)
- `flutter test` (13 pruebas) cubre ida y vuelta entre pantalla y mundo, el foco quieto al acercar, el regreso en
  $z = 1$, el límite del desplazamiento, la opacidad, el toque del núcleo con zoom, el dibujo de cerca sobre
  Identidades y, con gestos simulados de dos dedos, que la cámara siga a Identidades mientras gira, también cuando el
  primer cuadro llega con escala 1, que el último dedo de un pellizco no la suelte, y que al alejar vuelva al centro
  de a poco.
- En el simulador de iPhone: acercar con dos dedos, que la cámara siga al planeta varios segundos, que un dedo lo
  suelte, y abrir el chat tocando el núcleo con zoom.

## Pendiente
- **Trackpad y rueda en macOS:** sin probar en la Mac.
- Los valores de la cámara son provisionales.
