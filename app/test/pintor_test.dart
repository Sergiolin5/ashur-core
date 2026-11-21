import 'dart:ui' as ui;

import 'package:ashur/galaxia/camara.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:ashur/galaxia/pintor.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('el pintor dibuja el ejemplo sin fallar, con lunas y personajes', () async {
    final estado = await EstadoGalaxia.cargar(rootBundle);
    final grabadora = ui.PictureRecorder();
    final tiempo = ValueNotifier<double>(3.0);
    final camara = ValueNotifier(Camara.inicial);
    final pintor = PintorGalaxia(estado: estado, tiempo: tiempo, camara: camara);
    const tamano = Size(400, 800);
    final lienzo = ui.Canvas(grabadora);
    pintor.paint(lienzo, tamano);

    // De cerca sobre Identidades, para que se dibujen los personajes con su nombre.
    final g = Geometria(estado, tamano, 3.0);
    final identidades = g.posicion('identidades', 3.0);
    camara.value = Camara(zoom: 20, desplazamiento: -(identidades - g.centro) * 20);
    expect(g.radio(g.cuerpo('identidades')!) * 20, greaterThan(radioPlanetaConPersonajes * 2));
    pintor.paint(lienzo, tamano);
    grabadora.endRecording();
    tiempo.dispose();
    camara.dispose();
  });

  test('el polvo del primer día es solo la base, y crece con los recuerdos', () async {
    final inicio = DateTime.utc(2026, 11, 1, 14);
    expect(densidadPolvo(Aprendizaje(inicio: inicio, recuerdos: 0), inicio), polvoBase);

    final estado = await EstadoGalaxia.cargar(rootBundle);
    final veinteDias = estado.aprendizaje.inicio.add(const Duration(days: 20));
    expect(densidadPolvo(estado.aprendizaje, veinteDias), 258);
  });
}
