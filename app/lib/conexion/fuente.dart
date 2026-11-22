// De dónde sale la galaxia que se dibuja (docs/adr/0011-app-conectada-al-core.md).
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../galaxia/modelo.dart';
import 'almacen.dart';
import 'cliente.dart';

const claveDireccion = 'ashur.direccion';
const claveClave = 'ashur.clave';
const claveCache = 'ashur.cache.galaxia';

/// Cómo está la conexión con el core, para la pestaña Estado.
enum EstadoConexion { sinConfigurar, bloqueada, conectando, conectado, sinConexion, claveInvalida, coreSinClave, error }

/// Guarda lo último que mandó el core. En la app es un archivo JSON (cache_archivo.dart); en las pruebas, memoria.
abstract class Cache {
  Future<String?> leer();
  Future<void> escribir(String json);
}

class CacheEnMemoria implements Cache {
  String? _json;

  @override
  Future<String?> leer() async => _json;

  @override
  Future<void> escribir(String json) async => _json = json;
}

/// La galaxia que ve la app. Orden: lo que acaba de mandar el core; si no responde, lo último guardado; y el ejemplo
/// solo si todavía no hay un core configurado, para que los datos inventados nunca parezcan reales.
class FuenteGalaxia extends ChangeNotifier {
  FuenteGalaxia({required this.almacen, required this.cache, required this.cargarEjemplo});

  final AlmacenSecreto almacen;
  final Cache cache;
  final Future<EstadoGalaxia> Function() cargarEjemplo;

  EstadoGalaxia? galaxia;
  EstadoConexion estado = EstadoConexion.sinConfigurar;
  bool esEjemplo = false;
  String detalle = '';

  /// Un cliente con la dirección y la clave guardadas, o null si falta alguna.
  Future<ClienteCore?> cliente() async {
    final String? direccion, clave;
    try {
      (direccion, clave) = await ajustes();
    } on SecretoBloqueado {
      return null;
    }
    if (direccion == null || direccion.isEmpty || clave == null || clave.isEmpty) return null;
    return ClienteCore(direccion: Uri.parse(direccion), clave: clave);
  }

  /// La clave se lee una vez por sesión, con Face ID, y queda en memoria hasta cerrar la app.
  String? _claveDesbloqueada;

  /// Lee la dirección y la clave. Lanza SecretoBloqueado si Face ID falla.
  Future<(String?, String?)> ajustes() async {
    final direccion = await almacen.leer(claveDireccion);
    _claveDesbloqueada ??= await almacen.leer(claveClave, protegido: true);
    return (direccion, _claveDesbloqueada);
  }

  Future<void> guardarAjustes(String direccion, String clave) async {
    await almacen.escribir(claveDireccion, direccion.trim().replaceAll(RegExp(r'/+$'), ''));
    await almacen.escribir(claveClave, clave.trim(), protegido: true);
    _claveDesbloqueada = clave.trim();
    await actualizar();
  }

  Future<void> actualizar() async {
    final String? direccion, clave;
    try {
      (direccion, clave) = await ajustes();
    } on SecretoBloqueado catch (e) {
      // Face ID falló: se muestra lo último guardado y se ofrece desbloquear o volver a pegar la clave.
      estado = EstadoConexion.bloqueada;
      detalle = e.motivo;
      final guardada = await cache.leer();
      if (guardada != null) {
        galaxia = EstadoGalaxia.fromJson(jsonDecode(guardada) as Map<String, dynamic>);
        esEjemplo = false;
      }
      notifyListeners();
      return;
    }
    if (direccion == null || direccion.isEmpty || clave == null || clave.isEmpty) {
      galaxia = await cargarEjemplo();
      esEjemplo = true;
      estado = EstadoConexion.sinConfigurar;
      notifyListeners();
      return;
    }
    estado = EstadoConexion.conectando;
    notifyListeners();
    try {
      final nueva = await ClienteCore(direccion: Uri.parse(direccion), clave: clave).galaxia();
      galaxia = nueva;
      esEjemplo = false;
      estado = EstadoConexion.conectado;
      detalle = '';
      await cache.escribir(jsonEncode(nueva.aJson()));
    } on ErrorCore catch (e) {
      estado = switch (e.fallo) {
        FalloCore.inalcanzable => EstadoConexion.sinConexion,
        FalloCore.claveInvalida => EstadoConexion.claveInvalida,
        FalloCore.coreSinClave => EstadoConexion.coreSinClave,
        FalloCore.otro => EstadoConexion.error,
      };
      detalle = e.detalle;
      final guardada = await cache.leer();
      if (guardada != null) {
        galaxia = EstadoGalaxia.fromJson(jsonDecode(guardada) as Map<String, dynamic>);
        esEjemplo = false;
      } else if (esEjemplo) {
        galaxia = null; // con un core configurado, el ejemplo no se muestra
        esEjemplo = false;
      }
    } on FormatException catch (e) {
      estado = EstadoConexion.error;
      detalle = e.message;
    }
    notifyListeners();
  }
}
