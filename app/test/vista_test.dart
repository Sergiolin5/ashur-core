import 'package:ashur/galaxia/camara.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:ashur/galaxia/pintor.dart';
import 'package:ashur/galaxia/vista.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // rootBundle guarda en caché la carga de una prueba anterior, que no termina en la siguiente.
  setUp(() => rootBundle.clear());

  testWidgets('al acercar con dos dedos sobre un planeta, la cámara lo sigue mientras gira', (tester) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    const tamano = Size(400, 800);

    final camara = ValueNotifier(Camara.inicial);
    addTearDown(camara.dispose);
    await tester.pumpWidget(Directionality(
      textDirection: TextDirection.ltr,
      child: VistaGalaxia(alTocarNucleo: (_, __) {}, camara: camara),
    ));
    final estado = (await tester.runAsync(() => EstadoGalaxia.cargar(rootBundle)))!;
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
    await tester.pump();

    // Con el tiempo detenido entre cuadros, el planeta está donde lo dice la geometría del último cuadro.
    await tester.pump(const Duration(seconds: 1));
    const t = 1.0;
    final planeta = Camara.inicial.aPantalla(Geometria(estado, tamano, t).posicion('identidades', t),
        tamano.center(Offset.zero));

    final a = await tester.startGesture(planeta + const Offset(-6, 0), pointer: 1);
    final b = await tester.startGesture(planeta + const Offset(6, 0), pointer: 2);
    for (var i = 1; i <= 5; i++) {
      await a.moveTo(planeta + Offset(-6.0 - 10 * i, 0));
      await b.moveTo(planeta + Offset(6.0 + 10 * i, 0));
      await tester.pump();
    }
    expect(camara.value.sigue, 'identidades');
    expect(camara.value.zoom, greaterThan(2));
    await a.up();
    await b.up();

    // Pasan varios segundos: el planeta gira, pero sigue en el ancla de la pantalla.
    for (final pasos in [1, 3, 5]) {
      await tester.pump(Duration(seconds: pasos));
      final t2 = camara.value; // la cámara del último cuadro
      expect(t2.sigue, 'identidades');
    }
    final ancla = camara.value.ancla;
    expect((ancla - planeta).distance, lessThan(1.0));

    // Mover con un dedo suelta el planeta.
    final c = await tester.startGesture(const Offset(200, 600), pointer: 3);
    await c.moveBy(const Offset(40, 0));
    await tester.pump();
    await c.moveBy(const Offset(40, 0));
    await tester.pump();
    await c.up();
    expect(camara.value.sigue, isNull);
  });

  testWidgets('sigue al planeta aunque el primer cuadro del pellizco no cambie la distancia entre los dedos',
      (tester) async {
    final (camara, planeta) = await _prepararVista(tester);
    final a = await tester.startGesture(planeta + const Offset(-20, 0), pointer: 1);
    final b = await tester.startGesture(planeta + const Offset(20, 0), pointer: 2);
    // Los dos dedos se mueven juntos primero (escala 1), como pasa en un teléfono real.
    for (var i = 1; i <= 3; i++) {
      await a.moveBy(const Offset(0, 4));
      await b.moveBy(const Offset(0, 4));
      await tester.pump();
    }
    for (var i = 1; i <= 5; i++) {
      await a.moveBy(const Offset(-12, 0));
      await b.moveBy(const Offset(12, 0));
      await tester.pump();
    }
    expect(camara.value.sigue, 'identidades');
    expect(camara.value.zoom, greaterThan(1.5));

    // Al levantar un dedo, el otro tiembla un poco: eso no suelta al planeta.
    await a.up();
    await tester.pump();
    await b.moveBy(const Offset(3, 2));
    await tester.pump();
    await b.moveBy(const Offset(-2, 3));
    await tester.pump();
    await b.up();
    await tester.pump(const Duration(seconds: 2));
    expect(camara.value.sigue, 'identidades');
  });

  testWidgets('al alejar, la galaxia vuelve al centro de a poco y no de golpe al final', (tester) async {
    final (camara, _) = await _prepararVista(tester);
    camara.value = const Camara(zoom: 3, desplazamiento: Offset(240, 0));
    const centro = Offset(200, 400);
    final a = await tester.startGesture(centro + const Offset(-100, 0), pointer: 1);
    final b = await tester.startGesture(centro + const Offset(100, 0), pointer: 2);
    final distancias = <double>[];
    for (var i = 1; i <= 8; i++) {
      await a.moveBy(const Offset(10, 0));
      await b.moveBy(const Offset(-10, 0));
      await tester.pump();
      if (camara.value.zoom < 1.3 && camara.value.zoom > 1) distancias.add(camara.value.desplazamiento.distance);
    }
    await a.up();
    await b.up();
    // Cerca de z = 1 el desplazamiento ya es pequeño.
    expect(distancias, isNotEmpty);
    expect(distancias.last, lessThan(240 * 0.3));
  });
}

Future<(ValueNotifier<Camara>, Offset)> _prepararVista(WidgetTester tester) async {
  tester.view.physicalSize = const Size(400, 800);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  const tamano = Size(400, 800);
  final camara = ValueNotifier(Camara.inicial);
  addTearDown(camara.dispose);
  await tester.pumpWidget(Directionality(
    textDirection: TextDirection.ltr,
    child: VistaGalaxia(alTocarNucleo: (_, __) {}, camara: camara),
  ));
  final estado = (await tester.runAsync(() => EstadoGalaxia.cargar(rootBundle)))!;
  await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
  await tester.pump();
  await tester.pump(const Duration(seconds: 1));
  const t = 1.0;
  final planeta = Camara.inicial
      .aPantalla(Geometria(estado, tamano, t).posicion('identidades', t), tamano.center(Offset.zero));
  return (camara, planeta);
}
