// Separado de chat_test.dart: en un archivo con testWidgets, Flutter cambia el HttpClient y todo responde 400.
import 'dart:convert';
import 'dart:io';

import 'package:ashur/conexion/cliente.dart';
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

/// Un core falso del chat en localhost: una conversación, y un 409 si se escribe con la respuesta abierta.
Future<HttpServer> _coreDelChat() async {
  final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  final mensajes = <Map<String, dynamic>>[];
  var abierta = false;
  servidor.listen((pedido) async {
    final r = pedido.response;
    final ruta = pedido.uri.path;
    Map<String, dynamic> completa() => {
      'conversacion': _conversacion('con-1', mensajes.isEmpty ? null : mensajes.first['texto'] as String),
      'mensajes': mensajes,
      'espera': abierta ? _espera('pendiente') : null,
    };
    r.headers.contentType = ContentType.json;
    if (pedido.headers.value('X-Ashur-Clave') != 'buena') {
      r.statusCode = 401;
    } else if (pedido.method == 'GET' && ruta == '/conversaciones') {
      r.write(jsonEncode([_conversacion('con-1', null)]));
    } else if (pedido.method == 'POST' && ruta == '/conversaciones') {
      r.statusCode = 201;
      r.write(jsonEncode(_conversacion('con-1', null)));
    } else if (pedido.method == 'GET' && ruta == '/conversaciones/con-1') {
      r.write(jsonEncode(completa()));
    } else if (pedido.method == 'POST' && ruta == '/conversaciones/con-1/mensajes') {
      final cuerpo = jsonDecode(await utf8.decodeStream(pedido)) as Map<String, dynamic>;
      if (abierta) {
        r.statusCode = 409;
        r.write(jsonEncode({'detail': 'Ashur todavía está respondiendo el mensaje anterior.'}));
      } else {
        mensajes.add(_mensaje(mensajes.length + 1, 'user', cuerpo['texto'] as String));
        abierta = true;
        r.statusCode = 202;
        r.write(jsonEncode(completa()));
      }
    } else {
      r.statusCode = 404;
    }
    await r.close();
  });
  return servidor;
}

void main() {
  test('cliente del chat: listar, crear, ver, enviar (202) y el 409 con su detalle', () async {
    final s = await _coreDelChat();
    addTearDown(() => s.close(force: true));
    final c = ClienteCore(direccion: Uri.parse('http://127.0.0.1:${s.port}'), clave: 'buena');

    expect((await c.listarConversaciones()).single['id'], 'con-1');
    expect((await c.crearConversacion())['id'], 'con-1');
    expect((await c.verConversacion('con-1'))['espera'], isNull);

    final enviada = await c.enviarMensaje('con-1', 'Hola');
    expect((enviada['mensajes'] as List).single['texto'], 'Hola');
    expect((enviada['espera'] as Map)['estado'], 'pendiente');

    await expectLater(
      c.enviarMensaje('con-1', 'Otra'),
      throwsA(
        isA<ErrorCore>()
            .having((e) => e.fallo, 'fallo', FalloCore.conflicto)
            .having((e) => e.detalle, 'detalle', contains('todavía está respondiendo')),
      ),
    );
  });
}
