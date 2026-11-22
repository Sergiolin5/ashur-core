// Cliente HTTP del core, con lo que trae Dart (docs/adr/0011-app-conectada-al-core.md).
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../galaxia/modelo.dart';

/// Por qué no se pudo hablar con el core.
enum FalloCore {
  /// No hay red, la dirección está mal o el core no responde.
  inalcanzable,

  /// El core respondió 401: la clave no es la correcta.
  claveInvalida,

  /// El core respondió 503: no tiene ASHUR_CLAVE configurada.
  coreSinClave,

  /// Otra respuesta inesperada.
  otro,
}

class ErrorCore implements Exception {
  const ErrorCore(this.fallo, [this.detalle = '']);

  final FalloCore fallo;
  final String detalle;

  @override
  String toString() => 'ErrorCore($fallo, $detalle)';
}

String _detalle(String cuerpo) {
  try {
    return (jsonDecode(cuerpo) as Map<String, dynamic>)['detail']?.toString() ?? '';
  } on FormatException {
    return '';
  }
}

/// Un mensaje del chat (core/ashur_core/chat.py).
class MensajeChat {
  const MensajeChat({required this.id, required this.deAshur, required this.texto});

  final int id;
  final bool deAshur;
  final String texto;

  factory MensajeChat.fromJson(Map<String, dynamic> j) =>
      MensajeChat(id: j['id'] as int, deAshur: j['autor'] == 'ashur', texto: j['texto'] as String);
}

class ClienteCore {
  ClienteCore({required this.direccion, required this.clave, this.espera = const Duration(seconds: 8)});

  /// Por ejemplo http://servidor:8720, sin la barra final.
  final Uri direccion;
  final String clave;
  final Duration espera;

  Future<EstadoGalaxia> galaxia() async =>
      EstadoGalaxia.fromJson(await _pedir('/galaxia') as Map<String, dynamic>);

  /// El historial del chat.
  Future<List<MensajeChat>> chat() async =>
      [for (final m in await _pedir('/chat') as List) MensajeChat.fromJson(m as Map<String, dynamic>)];

  /// Manda un mensaje y devuelve el mensaje guardado y la respuesta de Ashur. El modelo puede tardar.
  Future<List<MensajeChat>> hablar(String texto) async => [
        for (final m in await _pedir('/chat', cuerpo: {'texto': texto}, esperaMax: const Duration(minutes: 3)) as List)
          MensajeChat.fromJson(m as Map<String, dynamic>)
      ];

  Future<Object?> _pedir(String ruta, {Map<String, dynamic>? cuerpo, Duration? esperaMax}) async {
    final limite = esperaMax ?? espera;
    final cliente = HttpClient()..connectionTimeout = espera;
    try {
      final destino = direccion.resolve(ruta);
      final pedido = await (cuerpo == null ? cliente.getUrl(destino) : cliente.postUrl(destino)).timeout(espera);
      pedido.headers.set('X-Ashur-Clave', clave);
      if (cuerpo != null) {
        pedido.headers.contentType = ContentType.json;
        pedido.write(jsonEncode(cuerpo));
      }
      final respuesta = await pedido.close().timeout(limite);
      final texto = await respuesta.transform(utf8.decoder).join().timeout(limite);
      switch (respuesta.statusCode) {
        case 200:
          return jsonDecode(texto);
        case 401:
          throw const ErrorCore(FalloCore.claveInvalida);
        case 503:
          // Sin ASHUR_CLAVE, o, en el chat, sin un nodo que responda: el detalle lo dice.
          throw ErrorCore(FalloCore.coreSinClave, _detalle(texto));
        default:
          throw ErrorCore(FalloCore.otro, 'HTTP ${respuesta.statusCode}');
      }
    } on SocketException catch (e) {
      throw ErrorCore(FalloCore.inalcanzable, e.message);
    } on TimeoutException {
      throw const ErrorCore(FalloCore.inalcanzable, 'sin respuesta');
    } on HandshakeException catch (e) {
      throw ErrorCore(FalloCore.inalcanzable, e.message);
    } finally {
      cliente.close(force: true);
    }
  }
}
