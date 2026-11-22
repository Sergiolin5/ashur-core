import 'dart:convert';
import 'dart:io';

import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un core falso en localhost: responde /galaxia con el ejemplo del contrato si la clave es "buena".
Future<HttpServer> coreFalso({int? siempre}) async {
  final ejemplo = await File('../contracts/galaxy-state.ejemplo.json').readAsString();
  final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  servidor.listen((pedido) {
    final r = pedido.response;
    if (siempre != null) {
      r.statusCode = siempre;
    } else if (pedido.headers.value('X-Ashur-Clave') != 'buena') {
      r.statusCode = 401;
    } else if (pedido.uri.path == '/galaxia') {
      r.headers.contentType = ContentType.json;
      r.write(ejemplo);
    } else {
      r.statusCode = 404;
    }
    r.close();
  });
  return servidor;
}

Uri direccionDe(HttpServer s) => Uri.parse('http://127.0.0.1:${s.port}');

void main() {
  // Sin binding de pruebas en este archivo: así HttpClient habla de verdad con el servidor local.
  setUpAll(() => HttpOverrides.global = null);

  test('pide la galaxia con la clave y la interpreta', () async {
    final s = await coreFalso();
    addTearDown(s.close);
    final g = await ClienteCore(direccion: direccionDe(s), clave: 'buena').galaxia();
    expect(g.aprendizaje.recuerdos, 120);
  });

  test('distingue clave equivocada, core sin clave y core inalcanzable', () async {
    final s = await coreFalso();
    addTearDown(s.close);
    await expectLater(ClienteCore(direccion: direccionDe(s), clave: 'mala').galaxia(),
        throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.claveInvalida)));

    final sinClave = await coreFalso(siempre: 503);
    addTearDown(sinClave.close);
    await expectLater(ClienteCore(direccion: direccionDe(sinClave), clave: 'x').galaxia(),
        throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.coreSinClave)));

    final cerrado = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final puerto = cerrado.port;
    await cerrado.close();
    await expectLater(
        ClienteCore(direccion: Uri.parse('http://127.0.0.1:$puerto'), clave: 'x', espera: const Duration(seconds: 2))
            .galaxia(),
        throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.inalcanzable)));
  });

  test('sin core configurado se ve el ejemplo; con core, lo del core; y si se cae, lo guardado', () async {
    final ejemplo = EstadoGalaxia.fromJson(
        jsonDecode(await File('../contracts/galaxy-state.ejemplo.json').readAsString()) as Map<String, dynamic>);
    final fuente = FuenteGalaxia(almacen: AlmacenEnMemoria(), cache: CacheEnMemoria(), cargarEjemplo: () async => ejemplo);

    await fuente.actualizar();
    expect(fuente.estado, EstadoConexion.sinConfigurar);
    expect(fuente.esEjemplo, isTrue);

    final s = await coreFalso();
    await fuente.guardarAjustes('${direccionDe(s)}/', 'buena');
    expect(fuente.estado, EstadoConexion.conectado);
    expect(fuente.esEjemplo, isFalse);
    expect(fuente.galaxia, isNotNull);

    await s.close(force: true);
    await fuente.actualizar();
    expect(fuente.estado, EstadoConexion.sinConexion);
    expect(fuente.galaxia, isNotNull, reason: 'se queda con lo último guardado');
    expect(fuente.esEjemplo, isFalse);
  });

  test('con un core configurado que nunca respondió, no se muestra el ejemplo', () async {
    final ejemplo = EstadoGalaxia.fromJson(
        jsonDecode(await File('../contracts/galaxy-state.ejemplo.json').readAsString()) as Map<String, dynamic>);
    final fuente = FuenteGalaxia(almacen: AlmacenEnMemoria(), cache: CacheEnMemoria(), cargarEjemplo: () async => ejemplo);
    await fuente.actualizar(); // sin configurar: ejemplo
    final cerrado = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final puerto = cerrado.port;
    await cerrado.close();
    await fuente.guardarAjustes('http://127.0.0.1:$puerto', 'x');
    expect(fuente.estado, EstadoConexion.sinConexion);
    expect(fuente.galaxia, isNull);
  });
}
