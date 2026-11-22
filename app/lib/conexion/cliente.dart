// Cliente HTTP del core, con lo que trae Dart (docs/adr/0011-app-conectada-al-core.md, docs/adr/0015-inventario-en-la-app.md).
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../galaxia/modelo.dart';
import '../inventario/objeto.dart';

/// Por qué no se pudo hablar con el core.
enum FalloCore {
  /// No hay red, la dirección está mal o el core no responde.
  inalcanzable,

  /// El core respondió 401: la clave no es la correcta.
  claveInvalida,

  /// El core respondió 404: el recurso no existe.
  noExiste,

  /// El core respondió 422: los datos son inválidos.
  datosInvalidos,

  /// El core respondió 503: no tiene la clave configurada.
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
  ClienteCore({
    required this.direccion,
    required this.clave,
    this.claveAdmin,
    this.espera = const Duration(seconds: 8),
  });

  /// Por ejemplo http://servidor:8720, sin la barra final.
  final Uri direccion;
  final String clave;
  final String? claveAdmin;
  final Duration espera;

  Future<EstadoGalaxia> galaxia() async => EstadoGalaxia.fromJson(await _pedir('/galaxia'));

  Future<List<Objeto>> listarObjetos({bool archivados = false}) async {
    final ruta = archivados ? '/objetos?archivados=true' : '/objetos';
    final respuesta = await _enviar('GET', ruta);
    return (respuesta as List<dynamic>)
        .map((e) => Objeto.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Objeto> crearObjeto(String nombre, String? lugar) async {
    final lugarLimpio = lugar?.trim();
    final respuesta = await _enviar(
      'POST',
      '/objetos',
      cuerpo: {
        'nombre': nombre.trim(),
        'lugar': (lugarLimpio == null || lugarLimpio.isEmpty) ? null : lugarLimpio,
      },
    );
    return Objeto.fromJson(respuesta as Map<String, dynamic>);
  }

  Future<Objeto> editarObjeto(String id, Map<String, dynamic> cambios) async {
    final respuesta = await _enviar(
      'PATCH',
      '/objetos/$id',
      cuerpo: cambios,
      admin: true,
    );
    return Objeto.fromJson(respuesta as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> _pedir(String ruta) async {
    final respuesta = await _enviar('GET', ruta);
    return respuesta as Map<String, dynamic>;
  }

  Future<dynamic> _enviar(
    String metodo,
    String ruta, {
    Object? cuerpo,
    bool admin = false,
  }) async {
    final cliente = HttpClient()..connectionTimeout = espera;
    try {
      final pedido = await cliente.openUrl(metodo, direccion.resolve(ruta)).timeout(espera);
      if (admin) {
        if (claveAdmin != null) {
          pedido.headers.set('X-Ashur-Clave-Admin', claveAdmin!);
        }
      } else {
        pedido.headers.set('X-Ashur-Clave', clave);
      }
      if (cuerpo != null) {
        pedido.headers.contentType = ContentType.json;
        final bytes = utf8.encode(jsonEncode(cuerpo));
        pedido.contentLength = bytes.length;
        pedido.add(bytes);
      }
      final respuesta = await pedido.close().timeout(espera);
      final texto = await respuesta.transform(utf8.decoder).join().timeout(espera);
      switch (respuesta.statusCode) {
        case 200:
        case 201:
          if (texto.isEmpty) return null;
          return jsonDecode(texto);
        case 401:
          throw const ErrorCore(FalloCore.claveInvalida);
        case 404:
          throw const ErrorCore(FalloCore.noExiste);
        case 422:
          throw ErrorCore(FalloCore.datosInvalidos, texto);
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
