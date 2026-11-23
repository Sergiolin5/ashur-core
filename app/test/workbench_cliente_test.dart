// Separado de workbench_test.dart: en un archivo con testWidgets, Flutter cambia el HttpClient y todo responde 400.
import 'dart:convert';
import 'dart:io';

import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/workbench/almacen.dart';
import 'package:ashur/workbench/almacen_core.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un core falso: `listar` corre ya, `ejecutar_tarea` queda como pedido y `romper` responde 502.
Future<HttpServer> _core(List<String> vistos) async {
  final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  servidor.listen((pedido) async {
    final r = pedido.response;
    final ruta = pedido.uri.path;
    final cuerpo = await utf8.decoder.bind(pedido).join();
    vistos.add('${pedido.method} $ruta $cuerpo');
    r.headers.contentType = ContentType.json;
    if (ruta == '/modulos/workbench/acciones/listar') {
      r.write(jsonEncode({
        'resultado': {
          'registros': [
            {'id': 't1', 'titulo': 'Probar'},
          ],
        },
      }));
    } else if (ruta == '/modulos/workbench/acciones/ejecutar_tarea') {
      r.statusCode = 202;
      r.write(jsonEncode({'id': 7, 'estado': 'pendiente', 'resultado': null}));
    } else if (ruta == '/pedidos/7/aprobar') {
      if (pedido.headers.value('X-Ashur-Clave-Admin') != 'admin') {
        r.statusCode = 401;
      } else {
        r.write(jsonEncode({
          'id': 7,
          'estado': 'hecho',
          'resultado': {
            'registro': {'id': 't1', 'estado': 'revision', 'resultado': 'Hecho.'},
          },
        }));
      }
    } else {
      r.statusCode = 502;
      r.write(jsonEncode({'detail': 'El módulo workbench falló: ValueError: Falta titulo.'}));
    }
    await r.close();
  });
  return servidor;
}

void main() {
  late HttpServer servidor;
  final vistos = <String>[];

  setUp(() async {
    vistos.clear();
    servidor = await _core(vistos);
  });
  tearDown(() => servidor.close(force: true));

  ClienteCore cliente({String? admin = 'admin'}) => ClienteCore(
        direccion: Uri.parse('http://127.0.0.1:${servidor.port}'),
        clave: 'buena',
        claveAdmin: admin,
      );

  test('lista los registros con una acción que solo lee', () async {
    final almacen = AlmacenWorkbenchCore(() async => cliente());
    expect(await almacen.listar(tipoTareas), [
      {'id': 't1', 'titulo': 'Probar'},
    ]);
    expect(vistos.single, 'POST /modulos/workbench/acciones/listar {"tipo":"tareas"}');
  });

  test('una acción que escribe se aprueba con la clave de administrador', () async {
    final tarea = await AlmacenWorkbenchCore(() async => cliente()).ejecutarTarea('t1');
    expect(tarea['resultado'], 'Hecho.');
    expect(vistos.last, startsWith('POST /pedidos/7/aprobar'));
  });

  test('sin clave de administrador, ejecutar avisa y no aprueba', () async {
    final almacen = AlmacenWorkbenchCore(() async => cliente(admin: null));
    await expectLater(
      almacen.ejecutarTarea('t1'),
      throwsA(isA<ErrorWorkbench>().having((e) => e.mensaje, 'mensaje', contains('clave de administrador'))),
    );
    expect(vistos.where((v) => v.contains('/aprobar')), isEmpty);
  });

  test('el error de un módulo llega con su motivo', () async {
    await expectLater(
      AlmacenWorkbenchCore(() async => cliente()).crear(tipoTareas, {'titulo': ''}),
      throwsA(isA<ErrorWorkbench>().having((e) => e.mensaje, 'mensaje', contains('Falta titulo'))),
    );
  });

  test('sin core configurado, avisa', () async {
    await expectLater(
      AlmacenWorkbenchCore(() async => null).listar(tipoTareas),
      throwsA(isA<ErrorWorkbench>()),
    );
  });
}
