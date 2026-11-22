// Caché de lo último que mandó el core, en un archivo JSON (docs/adr/0010-cache-en-el-dispositivo.md).
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'fuente.dart';

class CacheArchivo implements Cache {
  Future<File> _archivo() async => File('${(await getApplicationSupportDirectory()).path}/galaxia.json');

  @override
  Future<String?> leer() async {
    final archivo = await _archivo();
    return await archivo.exists() ? archivo.readAsString() : null;
  }

  @override
  Future<void> escribir(String json) async {
    final archivo = await _archivo();
    await archivo.parent.create(recursive: true);
    await archivo.writeAsString(json);
  }
}
