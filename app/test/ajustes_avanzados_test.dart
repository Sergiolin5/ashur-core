import 'dart:convert';
import 'dart:io';

import 'package:ashur/conexion/ajustes_avanzados.dart';
import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

class _ClienteFalso extends ClienteCore {
  _ClienteFalso({String? claveAdmin})
    : super(
        direccion: Uri.parse('http://127.0.0.1'),
        clave: 'normal',
        claveAdmin: claveAdmin,
      );

  final Map<String, dynamic> cambios = {};

  @override
  Future<List<Map<String, dynamic>>> listarNodos() async => [
    {
      'id': 'casa',
      'nombre': 'Casa',
      'archivado': false,
      'en_linea': true,
      'modo': 'full',
      'modelos': [
        {
          'nombre': 'qwen',
          'tamano': 1,
          'capacidades': ['completion'],
        },
      ],
      'ajustes': {'modelos_ofrecidos': null, 'num_ctx': null, 'horario': null},
    },
  ];

  @override
  Future<List<Map<String, dynamic>>> listarModulos() async => [
    {
      'id': 'demo',
      'manifiesto': {'nombre': 'Demo'},
      'error': null,
    },
    {'id': 'roto', 'manifiesto': null, 'error': 'No carga'},
  ];

  @override
  Future<List<Map<String, dynamic>>> verAjustesModulo(String id) async => [
    {
      'id': 'texto',
      'tipo': 'texto',
      'descripcion': 'Texto',
      'secreto': false,
      'valor': 'hola',
    },
    {
      'id': 'numero',
      'tipo': 'numero',
      'descripcion': 'Número',
      'secreto': false,
      'valor': 7,
    },
    {
      'id': 'booleano',
      'tipo': 'booleano',
      'descripcion': 'Booleano',
      'secreto': false,
      'valor': true,
    },
    {
      'id': 'secreto',
      'tipo': 'texto',
      'descripcion': 'Secreto',
      'secreto': true,
      'valor': null,
      'configurado': true,
    },
  ];

  @override
  Future<List<Map<String, dynamic>>> cambiarAjustesModulo(
    String id,
    Map<String, dynamic> cambios,
  ) async {
    this.cambios.addAll(cambios);
    return verAjustesModulo(id);
  }
}

Future<FuenteGalaxia> _fuente() async => FuenteGalaxia(
  almacen: AlmacenEnMemoria(),
  cache: CacheEnMemoria(),
  cargarEjemplo: () async => throw StateError('No se necesita galaxia'),
);

void main() {
  setUpAll(() => HttpOverrides.global = null);

  test(
    'cliente usa las rutas y encabezados de nodos y ajustes de módulos',
    () async {
      final pedidos = <Map<String, dynamic>>[];
      final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      servidor.listen((pedido) async {
        final cuerpo = await utf8.decodeStream(pedido);
        pedidos.add({
          'path': pedido.uri.path,
          'normal': pedido.headers.value('X-Ashur-Clave'),
          'admin': pedido.headers.value('X-Ashur-Clave-Admin'),
          'body': cuerpo,
        });
        final respuesta = pedido.response;
        respuesta.headers.contentType = ContentType.json;
        if (pedido.uri.path == '/nodos') {
          if (pedido.method == 'POST') {
            respuesta.statusCode = 201;
            respuesta.write(
              jsonEncode({
                'nodo': {'id': 'nuevo'},
                'clave': 'solo-una-vez',
              }),
            );
          } else {
            respuesta.write('[]');
          }
        } else if (pedido.uri.path == '/nodos/casa') {
          respuesta.write(jsonEncode({'id': 'casa'}));
        } else if (pedido.uri.path.endsWith('/ajustes') &&
            pedido.method == 'PATCH') {
          respuesta.write('[]');
        } else if (pedido.uri.path == '/modulos') {
          respuesta.write('[]');
        } else {
          respuesta.write('[]');
        }
        await respuesta.close();
      });
      addTearDown(servidor.close);
      final cliente = ClienteCore(
        direccion: Uri.parse('http://127.0.0.1:${servidor.port}'),
        clave: 'normal',
        claveAdmin: 'admin',
      );

      await cliente.listarNodos();
      await cliente.crearNodo('Sala');
      await cliente.editarNodo('casa', {'num_ctx': 4096});
      await cliente.listarModulos();
      await cliente.verAjustesModulo('demo');
      await cliente.cambiarAjustesModulo('demo', {'saludo': null});

      expect(pedidos.map((p) => p['path']), [
        '/nodos',
        '/nodos',
        '/nodos/casa',
        '/modulos',
        '/modulos/demo/ajustes',
        '/modulos/demo/ajustes',
      ]);
      expect(pedidos[0]['normal'], 'normal');
      expect(pedidos[1]['admin'], 'admin');
      expect(pedidos[2]['admin'], 'admin');
      expect(pedidos[5]['admin'], 'admin');
      expect(pedidos[2]['body'], '{"num_ctx":4096}');
      expect(pedidos[5]['body'], '{"saludo":null}');
    },
  );

  test('cliente traduce errores 401, 404, 422 con detail y 503', () async {
    Future<void> comprobar(
      int codigo,
      Future<Object?> Function(ClienteCore) pedir,
      FalloCore esperado,
    ) async {
      final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      servidor.listen((pedido) async {
        await utf8.decodeStream(pedido);
        pedido.response.statusCode = codigo;
        pedido.response.headers.contentType = ContentType.json;
        pedido.response.write(jsonEncode({'detail': 'dato incorrecto'}));
        await pedido.response.close();
      });
      addTearDown(servidor.close);
      final cliente = ClienteCore(
        direccion: Uri.parse('http://127.0.0.1:${servidor.port}'),
        clave: 'normal',
        claveAdmin: 'admin',
      );
      await expectLater(
        pedir(cliente),
        throwsA(
          isA<ErrorCore>()
              .having((e) => e.fallo, 'fallo', esperado)
              .having(
                (e) => e.detalle,
                'detalle',
                codigo == 422 ? 'dato incorrecto' : isA<String>(),
              ),
        ),
      );
    }

    await comprobar(401, (c) => c.listarNodos(), FalloCore.claveInvalida);
    await comprobar(
      404,
      (c) => c.editarNodo('no', {'archivado': true}),
      FalloCore.noExiste,
    );
    await comprobar(
      422,
      (c) => c.cambiarAjustesModulo('demo', {'invalido': 4}),
      FalloCore.datosInvalidos,
    );
    await comprobar(503, (c) => c.crearNodo('Casa'), FalloCore.coreSinClave);
  });

  testWidgets(
    'sin clave de administrador muestra la información y oculta controles',
    (tester) async {
      final fuente = await _fuente();
      await tester.pumpWidget(
        CupertinoApp(
          home: SingleChildScrollView(
            child: AjustesAvanzados(
              fuente: fuente,
              clienteOverride: _ClienteFalso(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Casa'), findsOneWidget);
      expect(find.text('Todos los modelos'), findsNothing);
      expect(find.text('Crear nodo'), findsNothing);
      expect(
        find.text(
          'Hace falta la clave de administrador para cambiar estos ajustes. Configúrala en Estado.',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('Configurado'), findsOneWidget);
      expect(find.byType(CupertinoTextField), findsNothing);
      expect(find.text('secreto-valor'), findsNothing);
      expect(find.text('Error del módulo: No carga'), findsOneWidget);
    },
  );

  testWidgets('admin puede volver un ajuste a su valor por defecto con null', (
    tester,
  ) async {
    final fuente = await _fuente();
    final cliente = _ClienteFalso(claveAdmin: 'admin');
    await tester.pumpWidget(
      CupertinoApp(
        home: SingleChildScrollView(
          child: AjustesAvanzados(fuente: fuente, clienteOverride: cliente),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Todos los modelos'), findsOneWidget);
    expect(find.text('Crear nodo'), findsOneWidget);
    expect(find.text('Nuevo valor secreto'), findsOneWidget);
    expect(find.text('Texto: hola'), findsNothing);
    expect(find.byType(CupertinoSwitch), findsAtLeastNWidgets(2));
    expect(find.text('Volver al valor por defecto'), findsNWidgets(4));
    expect(find.text('secreto-valor'), findsNothing);
    final restablecer = find.text('Volver al valor por defecto').last;
    await tester.ensureVisible(restablecer);
    await tester.pumpAndSettle();
    await tester.tap(restablecer);
    await tester.pumpAndSettle();
    expect(cliente.cambios.containsKey('secreto'), isTrue);
    expect(cliente.cambios['secreto'], isNull);
  });
}
