import 'dart:convert';
import 'dart:io';

import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un core falso en localhost: responde /galaxia y /objetos según las claves.
Future<HttpServer> coreFalso({int? siempre, bool tieneAdmin = true}) async {
  final ejemplo = await File('../contracts/galaxy-state.ejemplo.json').readAsString();
  final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  final objetos = <Map<String, dynamic>>[
    {'id': 'obj-1', 'nombre': 'Cuaderno', 'lugar': 'Escritorio', 'archivado': false, 'menciones': 2},
    {'id': 'obj-2', 'nombre': 'Lápiz', 'lugar': null, 'archivado': true, 'menciones': 0},
  ];
  servidor.listen((pedido) async {
    final r = pedido.response;
    if (siempre != null) {
      r.statusCode = siempre;
      await r.close();
      return;
    }
    final path = pedido.uri.path;
    final claveNormal = pedido.headers.value('X-Ashur-Clave');
    final claveAdmin = pedido.headers.value('X-Ashur-Clave-Admin');

    if (pedido.method == 'GET' && path == '/galaxia') {
      if (claveNormal != 'buena') {
        r.statusCode = 401;
      } else {
        r.headers.contentType = ContentType.json;
        r.write(ejemplo);
      }
    } else if (pedido.method == 'GET' && path == '/objetos') {
      if (claveNormal != 'buena') {
        r.statusCode = 401;
      } else {
        final conArchivados = pedido.uri.queryParameters['archivados'] == 'true';
        final filtrados = conArchivados ? objetos : objetos.where((o) => !(o['archivado'] as bool)).toList();
        r.headers.contentType = ContentType.json;
        r.write(jsonEncode(filtrados));
      }
    } else if (pedido.method == 'POST' && path == '/objetos') {
      if (claveNormal != 'buena') {
        r.statusCode = 401;
      } else {
        final texto = await utf8.decodeStream(pedido);
        final Map<String, dynamic> cuerpo = jsonDecode(texto);
        final nombre = cuerpo['nombre'] as String?;
        if (nombre == null || nombre.trim().isEmpty) {
          r.statusCode = 422;
          r.write('Nombre inválido');
        } else {
          final nuevo = {
            'id': 'obj-${objetos.length + 1}',
            'nombre': nombre,
            'lugar': cuerpo['lugar'],
            'archivado': false,
            'menciones': 0,
          };
          objetos.add(nuevo);
          r.statusCode = 201;
          r.headers.contentType = ContentType.json;
          r.write(jsonEncode(nuevo));
        }
      }
    } else if (pedido.method == 'PATCH' && path.startsWith('/objetos/')) {
      if (!tieneAdmin) {
        r.statusCode = 503;
      } else if (claveAdmin != 'admin-buena') {
        r.statusCode = 401;
      } else {
        final id = path.substring('/objetos/'.length);
        final idx = objetos.indexWhere((o) => o['id'] == id);
        if (idx == -1) {
          r.statusCode = 404;
        } else {
          final texto = await utf8.decodeStream(pedido);
          final Map<String, dynamic> cambios = jsonDecode(texto);
          if (cambios.containsKey('nombre') &&
              (cambios['nombre'] == null || (cambios['nombre'] as String).trim().isEmpty)) {
            r.statusCode = 422;
            r.write('Nombre inválido');
          } else {
            final obj = Map<String, dynamic>.from(objetos[idx]);
            for (final entrada in cambios.entries) {
              obj[entrada.key] = entrada.value;
            }
            objetos[idx] = obj;
            r.statusCode = 200;
            r.headers.contentType = ContentType.json;
            r.write(jsonEncode(obj));
          }
        }
      }
    } else {
      r.statusCode = 404;
    }
    await r.close();
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

  test('inventario: listar objetos sin archivados y con archivados', () async {
    final s = await coreFalso();
    addTearDown(s.close);
    final c = ClienteCore(direccion: direccionDe(s), clave: 'buena');

    final soloActivos = await c.listarObjetos();
    expect(soloActivos.length, 1);
    expect(soloActivos.first.nombre, 'Cuaderno');
    expect(soloActivos.first.lugar, 'Escritorio');

    final todos = await c.listarObjetos(archivados: true);
    expect(todos.length, 2);
    expect(todos[1].nombre, 'Lápiz');
    expect(todos[1].lugar, isNull);
    expect(todos[1].archivado, isTrue);
  });

  test('inventario: crear objeto con lugar y sin lugar (null)', () async {
    final s = await coreFalso();
    addTearDown(s.close);
    final c = ClienteCore(direccion: direccionDe(s), clave: 'buena');

    final nuevoConLugar = await c.crearObjeto('Martillo', 'Taller');
    expect(nuevoConLugar.id, 'obj-3');
    expect(nuevoConLugar.nombre, 'Martillo');
    expect(nuevoConLugar.lugar, 'Taller');
    expect(nuevoConLugar.archivado, isFalse);

    final nuevoSinLugar = await c.crearObjeto('Cinta', '');
    expect(nuevoSinLugar.id, 'obj-4');
    expect(nuevoSinLugar.nombre, 'Cinta');
    expect(nuevoSinLugar.lugar, isNull);
  });

  test('inventario: PATCH con clave de administrador edita, mueve, archiva y restaura', () async {
    final s = await coreFalso();
    addTearDown(s.close);
    final c = ClienteCore(direccion: direccionDe(s), clave: 'buena', claveAdmin: 'admin-buena');

    // Renombrar
    final renombrado = await c.editarObjeto('obj-1', {'nombre': 'Libreta'});
    expect(renombrado.nombre, 'Libreta');

    // Mover a otro lugar
    final movido = await c.editarObjeto('obj-1', {'lugar': 'Mochila'});
    expect(movido.lugar, 'Mochila');

    // Mover a sin lugar
    final sinLugar = await c.editarObjeto('obj-1', {'lugar': null});
    expect(sinLugar.lugar, isNull);

    // Archivar
    final archivado = await c.editarObjeto('obj-1', {'archivado': true});
    expect(archivado.archivado, isTrue);

    // Restaurar
    final restaurado = await c.editarObjeto('obj-2', {'archivado': false});
    expect(restaurado.archivado, isFalse);
  });

  test('inventario: errores 401, 404, 422 y 503', () async {
    final s = await coreFalso();
    addTearDown(s.close);

    // 401 con clave normal equivocada al listar
    final cClaveMala = ClienteCore(direccion: direccionDe(s), clave: 'mala');
    await expectLater(
      cClaveMala.listarObjetos(),
      throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.claveInvalida)),
    );

    // 401 en PATCH con clave de administrador equivocada
    final cAdminMala = ClienteCore(direccion: direccionDe(s), clave: 'buena', claveAdmin: 'admin-mala');
    await expectLater(
      cAdminMala.editarObjeto('obj-1', {'nombre': 'Nuevo'}),
      throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.claveInvalida)),
    );

    // 404 objeto que no existe
    final cAdmin = ClienteCore(direccion: direccionDe(s), clave: 'buena', claveAdmin: 'admin-buena');
    await expectLater(
      cAdmin.editarObjeto('obj-999', {'nombre': 'Inexistente'}),
      throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.noExiste)),
    );

    // 422 datos inválidos al crear (nombre vacío)
    await expectLater(
      cAdmin.crearObjeto('', 'Lugar'),
      throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.datosInvalidos)),
    );

    // 422 datos inválidos en PATCH
    await expectLater(
      cAdmin.editarObjeto('obj-1', {'nombre': ''}),
      throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.datosInvalidos)),
    );

    // 503 cuando el core no tiene configurada la clave de administrador
    final coreSinAdmin = await coreFalso(tieneAdmin: false);
    addTearDown(coreSinAdmin.close);
    final cSinAdminConfigurada =
        ClienteCore(direccion: direccionDe(coreSinAdmin), clave: 'buena', claveAdmin: 'admin-buena');
    await expectLater(
      cSinAdminConfigurada.editarObjeto('obj-1', {'nombre': 'Algo'}),
      throwsA(isA<ErrorCore>().having((e) => e.fallo, 'fallo', FalloCore.coreSinClave)),
    );
  });
}
