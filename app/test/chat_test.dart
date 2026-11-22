import 'package:ashur/chat/pantalla_chats.dart';
import 'package:ashur/chat/pantalla_conversacion.dart';
import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> _conversacion(String id, String? titulo) => {
  'id': id,
  'titulo': titulo,
  'creada': '2026-11-22T00:00:00Z',
  'actualizada': '2026-11-22T00:00:00Z',
  'archivada': false,
};

Map<String, dynamic> _mensaje(int id, String rol, String texto) => {
  'id': id,
  'rol': rol,
  'texto': texto,
  'fecha': '2026-11-22T00:00:00Z',
  'recuerdo_id': id,
};

Map<String, dynamic> _espera(String estado, {String? error}) => {
  'estado': estado,
  'desde': '2026-11-22T00:00:00Z',
  'nodo': null,
  'modelo': null,
  'error': error,
};

/// Un cliente falso para las pantallas: cada vez que se pregunta, devuelve la siguiente respuesta de [respuestas].
class _ClienteGuionado extends ClienteCore {
  _ClienteGuionado(this.respuestas) : super(direccion: Uri.parse('http://127.0.0.1'), clave: 'buena');

  final List<Map<String, dynamic>> respuestas;
  int preguntas = 0;

  @override
  Future<Map<String, dynamic>> verConversacion(String id) async {
    final i = preguntas < respuestas.length ? preguntas : respuestas.length - 1;
    preguntas++;
    return respuestas[i];
  }

  @override
  Future<List<Map<String, dynamic>>> listarConversaciones() async => [_conversacion('con-1', null)];
}

Map<String, dynamic> _completa(List<Map<String, dynamic>> mensajes, Map<String, dynamic>? espera) => {
  'conversacion': _conversacion('con-1', 'Hola'),
  'mensajes': mensajes,
  'espera': espera,
};

Widget _app(Widget pantalla) => CupertinoApp(home: pantalla);

void main() {
  testWidgets('la conversación pregunta hasta que llega la respuesta, y entonces deja de preguntar', (tester) async {
    final cliente = _ClienteGuionado([
      _completa([_mensaje(1, 'user', 'Hola')], _espera('pendiente')),
      _completa([_mensaje(1, 'user', 'Hola')], _espera('tomado')),
      _completa([_mensaje(1, 'user', 'Hola'), _mensaje(2, 'assistant', 'Hola, Sergio')], null),
    ]);
    await tester.pumpWidget(
      _app(PantallaConversacion(cliente: cliente, id: 'con-1', intervalo: const Duration(milliseconds: 100))),
    );
    await tester.pump();
    expect(find.text('Esperando a que un equipo tome el mensaje…'), findsOneWidget);
    // Mientras espera, no se puede escribir.
    expect(tester.widget<CupertinoTextField>(find.byType(CupertinoTextField)).enabled, isFalse);

    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Ashur está respondiendo…'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Hola, Sergio'), findsOneWidget);
    expect(tester.widget<CupertinoTextField>(find.byType(CupertinoTextField)).enabled, isTrue);

    final hechas = cliente.preguntas;
    await tester.pump(const Duration(seconds: 1));
    expect(cliente.preguntas, hechas, reason: 'sin respuesta abierta no se vuelve a preguntar');
  });

  testWidgets('si la respuesta falla, deja de preguntar, muestra el error y se puede escribir', (tester) async {
    final cliente = _ClienteGuionado([
      _completa([_mensaje(1, 'user', 'Hola')], _espera('fallido', error: 'sin nodos')),
    ]);
    await tester.pumpWidget(
      _app(PantallaConversacion(cliente: cliente, id: 'con-1', intervalo: const Duration(milliseconds: 100))),
    );
    await tester.pump();
    expect(find.text('Ashur no pudo responder: sin nodos. Puedes escribir de nuevo.'), findsOneWidget);
    expect(tester.widget<CupertinoTextField>(find.byType(CupertinoTextField)).enabled, isTrue);

    await tester.pump(const Duration(seconds: 1));
    expect(cliente.preguntas, 1, reason: 'un trabajo fallido no avanza: no se pregunta más');
  });

  testWidgets('salir de la conversación mientras espera no lanza errores ni deja el reloj andando', (tester) async {
    final cliente = _ClienteGuionado([
      _completa([_mensaje(1, 'user', 'Hola')], _espera('pendiente')),
    ]);
    await tester.pumpWidget(
      _app(PantallaConversacion(cliente: cliente, id: 'con-1', intervalo: const Duration(milliseconds: 100))),
    );
    await tester.pump();
    await tester.pumpWidget(_app(const SizedBox()));
    final hechas = cliente.preguntas;
    await tester.pump(const Duration(seconds: 1));
    expect(cliente.preguntas, hechas);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Chats lista las conversaciones, o explica que las claves están bloqueadas', (tester) async {
    final fuente = FuenteGalaxia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () async => throw 'no',
    );
    await tester.pumpWidget(_app(PantallaChats(fuente: fuente, cliente: _ClienteGuionado([]))));
    await tester.pump();
    expect(find.text('Conversación nueva'), findsOneWidget);
    expect(find.text('Nueva conversación'), findsOneWidget);

    fuente.estado = EstadoConexion.bloqueada;
    await tester.pumpWidget(_app(PantallaChats(key: UniqueKey(), fuente: fuente)));
    await tester.pump();
    expect(find.text('Las claves están bloqueadas: desbloquéalas con Face ID en la pestaña Estado.'), findsOneWidget);
  });

  testWidgets('con el teclado abierto, el campo y Enviar quedan por encima del teclado', (tester) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1;
    tester.view.viewInsets = const FakeViewPadding(bottom: 300);
    addTearDown(tester.view.reset);
    final cliente = _ClienteGuionado([_completa([], null)]);
    await tester.pumpWidget(_app(PantallaConversacion(cliente: cliente, id: 'con-1')));
    await tester.pump();
    expect(tester.getRect(find.byType(CupertinoTextField)).bottom, lessThanOrEqualTo(500));
    expect(tester.getRect(find.text('Enviar')).bottom, lessThanOrEqualTo(500));
  });
}
