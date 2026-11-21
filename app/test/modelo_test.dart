import 'package:ashur/galaxia/modelo.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('el JSON de ejemplo se carga en el modelo Dart', () async {
    final estado = await EstadoGalaxia.cargar(rootBundle);

    int cuantos(TipoCuerpo t) => estado.cuerpos.where((c) => c.tipo == t).length;
    expect(cuantos(TipoCuerpo.nucleo), 1);
    expect(cuantos(TipoCuerpo.agente), 3);
    expect(cuantos(TipoCuerpo.planeta), 5);
    expect(cuantos(TipoCuerpo.asteroide), 2);
    expect(estado.eventos.length, 3);

    // Lo que el esquema JSON no puede comprobar: que cada referencia apunte a un cuerpo que existe.
    final ids = {for (final c in estado.cuerpos) c.id};
    expect(ids.length, estado.cuerpos.length, reason: 'ids repetidos');
    for (final c in estado.cuerpos) {
      if (c.tipo == TipoCuerpo.nucleo) {
        expect(c.orbita, isNull);
      } else {
        expect(ids, contains(c.orbita!.centro));
      }
    }
    for (final e in estado.eventos) {
      expect(ids, contains(e.origen));
      expect(ids, contains(e.destino));
    }
  });
}
