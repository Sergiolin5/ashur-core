// De dónde sale la galaxia que se dibuja (docs/adr/0011-app-conectada-al-core.md, docs/adr/0015-inventario-en-la-app.md,
// docs/adr/0025-claves-con-face-id.md).
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../galaxia/modelo.dart';
import 'almacen.dart';
import 'cliente.dart';

const claveDireccion = 'ashur.direccion';

/// Las dos claves juntas, en una sola entrada protegida con Face ID: {"clave": ..., "admin": ...}.
const claveClaves = 'ashur.claves';

/// Dónde estaban las claves, sin protección, antes del ADR 0025. Se leen una vez para moverlas y se borran.
const claveClave = 'ashur.clave';
const claveClaveAdmin = 'ashur.clave_admin';
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

  /// Las claves ya desbloqueadas. Face ID se pide una vez y quedan en memoria hasta cerrar la app.
  Future<(String?, String?)>? _claves;

  /// La clave y la de administrador. Lanza [SecretoBloqueado] si Face ID falla; se puede volver a intentar.
  Future<(String?, String?)> _leerClaves() async {
    final lectura = _claves ??= _leerDelLlavero();
    try {
      return await lectura;
    } on SecretoBloqueado {
      if (identical(_claves, lectura)) _claves = null;
      rethrow;
    }
  }

  Future<(String?, String?)> _leerDelLlavero() async {
    final json = await almacen.leer(claveClaves, protegido: true);
    if (json != null) {
      final m = jsonDecode(json) as Map<String, dynamic>;
      return (m['clave'] as String?, m['admin'] as String?);
    }
    // Claves guardadas sin protección antes del ADR 0025: se mueven a la entrada protegida.
    final clave = await almacen.leer(claveClave);
    final admin = await almacen.leer(claveClaveAdmin);
    if (clave != null || admin != null) {
      await _escribirClaves(clave, admin);
      await almacen.borrar(claveClave);
      await almacen.borrar(claveClaveAdmin);
    }
    return (clave, admin);
  }

  Future<void> _escribirClaves(String? clave, String? admin) =>
      almacen.escribir(claveClaves, jsonEncode({'clave': clave, 'admin': admin}), protegido: true);

  /// Dirección, clave y clave de administrador. Lanza [SecretoBloqueado] si Face ID falla.
  Future<(String?, String?, String?)> ajustes() async {
    final direccion = await almacen.leer(claveDireccion);
    final (clave, admin) = await _leerClaves();
    return (direccion, clave, admin);
  }

  /// Sin [claveAdmin], se conserva la que ya estaba guardada.
  Future<void> guardarAjustes(String direccion, String clave, [String? claveAdmin]) async {
    await almacen.escribir(claveDireccion, direccion.trim().replaceAll(RegExp(r'/+$'), ''));
    final admin = claveAdmin?.trim() ?? (await _leerClaves()).$2;
    await _escribirClaves(clave.trim(), admin);
    _claves = Future.value((clave.trim(), admin));
    await actualizar();
  }

  /// Un cliente con lo guardado, o null si falta algo o Face ID falla (entonces [estado] queda en bloqueada).
  Future<ClienteCore?> cliente() async {
    final String? direccion, clave, claveAdmin;
    try {
      (direccion, clave, claveAdmin) = await ajustes();
    } on SecretoBloqueado catch (e) {
      estado = EstadoConexion.bloqueada;
      detalle = e.motivo;
      notifyListeners();
      return null;
    }
    if (direccion == null || direccion.isEmpty || clave == null || clave.isEmpty) return null;
    return ClienteCore(
      direccion: Uri.parse(direccion),
      clave: clave,
      claveAdmin: claveAdmin,
    );
  }

  Future<void> actualizar() async {
    final String? direccion, clave;
    try {
      (direccion, clave, _) = await ajustes();
    } on SecretoBloqueado catch (e) {
      // Face ID falló: se muestra lo último guardado, y la pestaña Estado ofrece desbloquear o volver a pegar la clave.
      estado = EstadoConexion.bloqueada;
      detalle = e.motivo;
      final guardada = await cache.leer();
      if (guardada != null) {
        galaxia = EstadoGalaxia.fromJson(jsonDecode(guardada) as Map<String, dynamic>);
      } else {
        galaxia = null;
      }
      esEjemplo = false;
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
        _ => EstadoConexion.error,
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
