// Dónde guarda la app la dirección del core y su clave (docs/adr/0007-clave-en-el-dispositivo.md).
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Un lugar para guardar textos secretos. En las pruebas se usa la versión en memoria.
abstract class AlmacenSecreto {
  Future<String?> leer(String clave);
  Future<void> escribir(String clave, String valor);
}

/// El Llavero en iOS y macOS. En macOS no usa el Llavero de protección de datos, para no necesitar Keychain Sharing.
class AlmacenLlavero implements AlmacenSecreto {
  static const _almacen = FlutterSecureStorage(
    mOptions: MacOsOptions(usesDataProtectionKeychain: false),
  );

  @override
  Future<String?> leer(String clave) => _almacen.read(key: clave);

  @override
  Future<void> escribir(String clave, String valor) => _almacen.write(key: clave, value: valor);
}

class AlmacenEnMemoria implements AlmacenSecreto {
  final _valores = <String, String>{};

  @override
  Future<String?> leer(String clave) async => _valores[clave];

  @override
  Future<void> escribir(String clave, String valor) async => _valores[clave] = valor;
}
