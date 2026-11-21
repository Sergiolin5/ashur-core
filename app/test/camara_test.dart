import 'package:ashur/galaxia/camara.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:ashur/galaxia/pintor.dart';
import 'package:ashur/galaxia/vista.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const tamano = Size(400, 800);
final centro = tamano.center(Offset.zero);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('ir de pantalla a mundo y volver deja el mismo punto', () {
    const camara = Camara(zoom: 7, desplazamiento: Offset(30, -12));
    const punto = Offset(123, 456);
    final ida = camara.aPantalla(camara.aMundo(punto, centro), centro);
    expect((ida - punto).distance, lessThan(1e-9));
  });

  test('acercar alrededor de un foco deja quieto lo que está bajo el foco', () {
    const foco = Offset(150, 300);
    final antes = Camara.inicial.aMundo(foco, centro);
    final despues = Camara.inicial.acercar(8, foco, tamano);
    expect((despues.aPantalla(antes, centro) - foco).distance, lessThan(1e-9));
    expect(despues.zoom, 8);
  });

  test('al volver a z = 1 la galaxia regresa al centro, y el zoom no pasa del máximo', () {
    final lejos = Camara.inicial.acercar(5, const Offset(10, 10), tamano).mover(const Offset(90, 40), tamano);
    final deVuelta = lejos.acercar(0.5, const Offset(300, 700), tamano);
    expect(deVuelta.zoom, 1);
    expect(deVuelta.desplazamiento, Offset.zero);
    expect(Camara.inicial.acercar(1000, centro, tamano).zoom, zoomMaximo);
  });

  test('un movimiento muy largo no pierde la galaxia', () {
    final camara = const Camara(zoom: 2).mover(const Offset(1e6, 0), tamano);
    expect(camara.desplazamiento.distance, lessThanOrEqualTo(desplazamientoMaximo * 200 * 2 + 1e-9));
  });

  test('la opacidad va de 0 a 1 según el tamaño en pantalla', () {
    expect(opacidadPorTamano(0), 0);
    expect(opacidadPorTamano(radioVisibleMin), 0);
    expect(opacidadPorTamano(radioVisibleTotal), 1);
    expect(opacidadPorTamano(100), 1);
  });

  test('tocar el núcleo funciona con zoom, y fuera de la pantalla no hace nada', () async {
    final estado = await EstadoGalaxia.cargar(rootBundle);
    final g = Geometria(estado, tamano, 0);
    final nucleo = g.posicion('ashur', 0);

    const cerca = Camara(zoom: 6);
    expect(tocaNucleo(estado, tamano, 0, cerca, cerca.aPantalla(nucleo, g.centro)), isTrue);

    final corrida = const Camara(zoom: 6).mover(const Offset(900, 0), tamano);
    final dondeQuedo = corrida.aPantalla(nucleo, g.centro);
    expect(dondeQuedo.dx, greaterThan(tamano.width));
    expect(tocaNucleo(estado, tamano, 0, corrida, centro), isFalse);
  });
}
