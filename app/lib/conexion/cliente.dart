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

class ClienteCore {
  ClienteCore({required this.direccion, required this.clave, this.espera = const Duration(seconds: 8)});

  /// Por ejemplo http://servidor:8720, sin la barra final.
  final Uri direccion;
  final String clave;
  final Duration espera;

  Future<EstadoGalaxia> galaxia() async => EstadoGalaxia.fromJson(await _pedir('/galaxia'));

  Future<Map<String, dynamic>> _pedir(String ruta) async {
    final cliente = HttpClient()..connectionTimeout = espera;
    try {
      final pedido = await cliente.getUrl(direccion.resolve(ruta)).timeout(espera);
      pedido.headers.set('X-Ashur-Clave', clave);
      final respuesta = await pedido.close().timeout(espera);
      final cuerpo = await respuesta.transform(utf8.decoder).join().timeout(espera);
      switch (respuesta.statusCode) {
        case 200:
          return jsonDecode(cuerpo) as Map<String, dynamic>;
        case 401:
          throw const ErrorCore(FalloCore.claveInvalida);
        case 503:
          throw const ErrorCore(FalloCore.coreSinClave);
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
