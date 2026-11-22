// Dónde guarda la app la dirección del core y sus claves (docs/adr/0007-clave-en-el-dispositivo.md, 0025).
import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// No se pudo leer un secreto protegido: Face ID falló o se canceló.
class SecretoBloqueado implements Exception {
  const SecretoBloqueado(this.motivo);

  final String motivo;

  @override
  String toString() => 'SecretoBloqueado: $motivo';
}

/// Un lugar para guardar textos. Los protegidos piden Face ID (o el código del teléfono) para leerse.
/// En las pruebas se usa la versión en memoria.
abstract class AlmacenSecreto {
  /// Lanza [SecretoBloqueado] si el texto es protegido y Face ID falla.
  Future<String?> leer(String clave, {bool protegido = false});
  Future<void> escribir(String clave, String valor, {bool protegido = false});
  Future<void> borrar(String clave);
}

/// El Llavero en iOS y macOS. En macOS no usa el Llavero de protección de datos, para no necesitar Keychain Sharing,
/// y por eso allí lo protegido no pide Touch ID.
class AlmacenLlavero implements AlmacenSecreto {
  static const _comun = FlutterSecureStorage(
    mOptions: MacOsOptions(usesDataProtectionKeychain: false),
  );

  /// En iOS, leer un secreto protegido pide Face ID, Touch ID o el código del teléfono.
  static const _protegido = FlutterSecureStorage(
    iOptions: IOSOptions(accountName: 'ashur.protegido', accessControlFlags: [AccessControlFlag.userPresence]),
    mOptions: MacOsOptions(usesDataProtectionKeychain: false),
  );

  @override
  Future<String?> leer(String clave, {bool protegido = false}) async {
    if (!protegido) return _comun.read(key: clave);
    try {
      return await _protegido.read(key: clave);
    } on PlatformException catch (e) {
      throw SecretoBloqueado(e.message ?? e.code);
    }
  }

  @override
  Future<void> escribir(String clave, String valor, {bool protegido = false}) =>
      (protegido ? _protegido : _comun).write(key: clave, value: valor);

  @override
  Future<void> borrar(String clave) => _comun.delete(key: clave);
}

class AlmacenEnMemoria implements AlmacenSecreto {
  final _comunes = <String, String>{};
  final _protegidos = <String, String>{};

  /// En las pruebas, simula que Face ID falla.
  bool bloqueado = false;

  /// Cuántas veces se pidió Face ID.
  int pedidosFaceId = 0;

  @override
  Future<String?> leer(String clave, {bool protegido = false}) async {
    if (!protegido) return _comunes[clave];
    if (!_protegidos.containsKey(clave)) return null; // el Llavero no pide Face ID si no hay nada guardado
    pedidosFaceId++;
    if (bloqueado) throw const SecretoBloqueado('Face ID cancelado');
    return _protegidos[clave];
  }

  @override
  Future<void> escribir(String clave, String valor, {bool protegido = false}) async =>
      (protegido ? _protegidos : _comunes)[clave] = valor;

  @override
  Future<void> borrar(String clave) async => _comunes.remove(clave);
}
