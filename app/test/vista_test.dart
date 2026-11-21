import 'package:ashur/galaxia/camara.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:ashur/galaxia/pintor.dart';
import 'package:ashur/galaxia/vista.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
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
}
