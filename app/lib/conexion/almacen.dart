// Dónde guarda la app la dirección del core y su clave (docs/adr/0007-clave-en-el-dispositivo.md, 0015).
import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// No se pudo leer un secreto protegido: Face ID falló o se canceló.
class SecretoBloqueado implements Exception {
  const SecretoBloqueado(this.motivo);

  final String motivo;
}

/// Un lugar para guardar textos. Los protegidos piden Face ID (o el código del teléfono) para leerse.
/// En las pruebas se usa la versión en memoria.
abstract class AlmacenSecreto {
  Future<String?> leer(String clave, {bool protegido = false});
  Future<void> escribir(String clave, String valor, {bool protegido = false});
}

/// El Llavero en iOS y macOS. En macOS no usa el Llavero de protección de datos, para no necesitar Keychain Sharing.
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
      final valor = await _protegido.read(key: clave);
      if (valor != null) return valor;
    } on PlatformException catch (e) {
      throw SecretoBloqueado(e.message ?? e.code);
    }
    // La clave se guardó sin protección antes de Face ID: se mueve a la protegida.
    final vieja = await _comun.read(key: clave);
    if (vieja != null) {
      await _protegido.write(key: clave, value: vieja);
      await _comun.delete(key: clave);
    }
    return vieja;
  }

  @override
  Future<void> escribir(String clave, String valor, {bool protegido = false}) =>
      (protegido ? _protegido : _comun).write(key: clave, value: valor);
}

class AlmacenEnMemoria implements AlmacenSecreto {
  final _valores = <String, String>{};

  /// En las pruebas, simula que Face ID falla.
  bool bloqueado = false;

  @override
  Future<String?> leer(String clave, {bool protegido = false}) async {
    if (protegido && bloqueado) throw const SecretoBloqueado('Face ID cancelado');
    return _valores[clave];
  }

  @override
  Future<void> escribir(String clave, String valor, {bool protegido = false}) async => _valores[clave] = valor;
}
