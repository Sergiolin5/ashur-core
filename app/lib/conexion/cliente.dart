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

  /// El core respondió 409: la identidad está archivada, o Ashur todavía está respondiendo en el chat.
  conflicto,

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

  Future<EstadoGalaxia> galaxia() async =>
      EstadoGalaxia.fromJson(await _pedir('/galaxia'));

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
        'lugar': (lugarLimpio == null || lugarLimpio.isEmpty)
            ? null
            : lugarLimpio,
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

  Future<Map<String, dynamic>> crearNodo(String nombre) async => await _enviar(
    'POST',
    '/nodos',
    cuerpo: {'nombre': nombre.trim()},
    admin: true,
  ) as Map<String, dynamic>;

  Future<Map<String, dynamic>> verPersonalidad() async {
    return await _enviar('GET', '/personalidad') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> guardarPersonalidad(
    Map<String, dynamic> personalidad,
  ) async {
    return await _enviar(
      'PUT',
      '/personalidad',
      cuerpo: personalidad,
      admin: true,
    ) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> reemplazarCorrecciones(
    List<Map<String, dynamic>> correcciones,
  ) async {
    return await _enviar(
      'PUT',
      '/personalidad/correcciones',
      cuerpo: correcciones,
      admin: true,
    ) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listarRoles() async {
    final respuesta = await _enviar('GET', '/roles') as List<dynamic>;
    return respuesta.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> crearRol(
    String nombre,
    List<String> herramientas,
  ) async {
    return await _enviar(
      'POST',
      '/roles',
      cuerpo: {'nombre': nombre, 'herramientas': herramientas},
      admin: true,
    ) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> editarRol(
    String id,
    String nombre,
    List<String> herramientas,
  ) async {
    return await _enviar(
      'PATCH',
      '/roles/${Uri.encodeComponent(id)}',
      cuerpo: {'nombre': nombre, 'herramientas': herramientas},
      admin: true,
    ) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listarIdentidades() async {
    final respuesta = await _enviar('GET', '/identidades') as List<dynamic>;
    return respuesta.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> asignarRol(String id, String? rol) async {
    return await _enviar(
      'PATCH',
      '/identidades/${Uri.encodeComponent(id)}',
      cuerpo: {'rol': rol},
      admin: true,
    ) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> crearClaveIdentidad(String id) async {
    return await _enviar(
      'POST',
      '/identidades/${Uri.encodeComponent(id)}/clave',
      admin: true,
    ) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listarModulos() async {
    final respuesta = await _enviar('GET', '/modulos') as List<dynamic>;
    return respuesta.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> verAjustesModulo(String id) async {
    final respuesta = await _enviar(
      'GET',
      '/modulos/${Uri.encodeComponent(id)}/ajustes',
    ) as List<dynamic>;
    return respuesta.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> cambiarAjustesModulo(
    String id,
    Map<String, dynamic> cambios,
  ) async {
    final respuesta = await _enviar(
      'PATCH',
      '/modulos/${Uri.encodeComponent(id)}/ajustes',
      cuerpo: cambios,
      admin: true,
    ) as List<dynamic>;
    return respuesta.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> listarNodos() async {
    final respuesta = await _enviar('GET', '/nodos') as List<dynamic>;
    return respuesta.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> editarNodo(
    String id,
    Map<String, dynamic> cambios,
  ) async {
    return await _enviar(
      'PATCH',
      '/nodos/${Uri.encodeComponent(id)}',
      cuerpo: cambios,
      admin: true,
    ) as Map<String, dynamic>;
  }

  // Chat (docs/adr/0016-chat-y-nodos.md, docs/adr/0023-chat-en-la-app.md). Las conversaciones y los mensajes van
  // como JSON crudo, igual que contracts/conversacion.schema.json.

  Future<List<Map<String, dynamic>>> listarConversaciones() async =>
      ((await _enviar('GET', '/conversaciones')) as List).cast<Map<String, dynamic>>();

  Future<Map<String, dynamic>> crearConversacion() async =>
      await _enviar('POST', '/conversaciones') as Map<String, dynamic>;

  /// La conversación completa: {conversacion, mensajes, espera}.
  Future<Map<String, dynamic>> verConversacion(String id) => _pedir('/conversaciones/${Uri.encodeComponent(id)}');

  /// Guarda el mensaje y deja la respuesta en la cola (202). Con un trabajo abierto, el core responde 409.
  Future<Map<String, dynamic>> enviarMensaje(String id, String texto) async => await _enviar(
        'POST',
        '/conversaciones/${Uri.encodeComponent(id)}/mensajes',
        cuerpo: {'texto': texto},
      ) as Map<String, dynamic>;

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
      final pedido = await cliente
          .openUrl(metodo, direccion.resolve(ruta))
          .timeout(espera);
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
      final texto = await respuesta
          .transform(utf8.decoder)
          .join()
          .timeout(espera);
      switch (respuesta.statusCode) {
        case 200:
        case 201:
        case 202:
          if (texto.isEmpty) return null;
          return jsonDecode(texto);
        case 401:
          throw const ErrorCore(FalloCore.claveInvalida);
        case 404:
          throw const ErrorCore(FalloCore.noExiste);
        case 409:
          throw ErrorCore(FalloCore.conflicto, _detalle(texto));
        case 422:
          throw ErrorCore(FalloCore.datosInvalidos, _detalle(texto));
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

  String _detalle(String texto) {
    try {
      final datos = jsonDecode(texto);
      if (datos is Map<String, dynamic> && datos['detail'] != null) {
        return datos['detail'].toString();
      }
    } on FormatException {
      // Algunos cores pueden devolver texto sin un cuerpo JSON.
    }
    return texto;
  }
}
