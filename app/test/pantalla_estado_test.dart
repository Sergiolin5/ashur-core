import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
import 'package:ashur/conexion/pantalla_estado.dart';
import 'package:ashur/galaxia/modelo.dart';
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un core sin nodos ni módulos. Lo de Ashur recibe un error: basta con que deje de pedir conectarse.
class _ClienteVacio extends ClienteCore {
  _ClienteVacio() : super(direccion: Uri.parse('http://127.0.0.1'), clave: 'normal');

  @override
  Future<List<Map<String, dynamic>>> listarNodos() async => [];

  @override
  Future<List<Map<String, dynamic>>> listarModulos() async => [];

  @override
  Future<Map<String, dynamic>> verPersonalidad() async => throw const FormatException('sin personalidad');
}

/// Una fuente que se conecta cuando la prueba lo decide.
class _FuenteManual extends FuenteGalaxia {
  _FuenteManual()
      : super(almacen: AlmacenEnMemoria(), cache: CacheEnMemoria(), cargarEjemplo: () async => throw 'no');

  ClienteCore? _cliente;

  void bloquear() {
    estado = EstadoConexion.bloqueada;
    notifyListeners();
  }

  void conectar() {
    _cliente = _ClienteVacio();
    estado = EstadoConexion.conectado;
    notifyListeners();
  }

  @override
  Future<(String?, String?, String?)> ajustes() async => (null, null, null);

  @override
  Future<ClienteCore?> cliente() async => _cliente;

  @override
  Future<void> actualizar() async {}

  @override
  EstadoGalaxia? get galaxia => null;
}

void main() {
  testWidgets('al conectarse con Estado abierto, la configuración avanzada y Lo de Ashur cargan solas', (tester) async {
    tester.view.physicalSize = const Size(800, 4000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final fuente = _FuenteManual();
    await tester.pumpWidget(CupertinoApp(home: PantallaEstado(fuente: fuente)));
    await tester.pumpAndSettle();
    expect(find.text('Conecta con el core para ver los nodos y módulos.'), findsOneWidget);
    expect(find.text('Conecta con el core para ver la configuración avanzada.'), findsOneWidget);

    fuente.conectar();
    await tester.pumpAndSettle();
    expect(find.text('Conecta con el core para ver los nodos y módulos.'), findsNothing);
    expect(find.text('No hay nodos registrados.'), findsOneWidget);
    expect(find.text('Conecta con el core para ver la configuración avanzada.'), findsNothing);
  });

  testWidgets('al desbloquear con Face ID, la configuración avanzada y Lo de Ashur cargan solas', (tester) async {
    tester.view.physicalSize = const Size(800, 4000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final fuente = _FuenteManual()..bloquear();
    await tester.pumpWidget(CupertinoApp(home: PantallaEstado(fuente: fuente)));
    await tester.pumpAndSettle();
    expect(find.text('Desbloquear con Face ID'), findsOneWidget);
    expect(find.text('Conecta con el core para ver los nodos y módulos.'), findsOneWidget);

    fuente.conectar(); // lo que deja actualizar() cuando Face ID acepta
    await tester.pumpAndSettle();
    expect(find.text('Desbloquear con Face ID'), findsNothing);
    expect(find.text('No hay nodos registrados.'), findsOneWidget);
    expect(find.text('Conecta con el core para ver la configuración avanzada.'), findsNothing);
  });
}
