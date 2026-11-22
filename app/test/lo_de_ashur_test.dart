import 'dart:convert';
import 'dart:io';

import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
import 'package:ashur/conexion/lo_de_ashur.dart';
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

const _personalidad = <String, dynamic>{
  'base': 'Ashur',
  'sobre_sergio': 'Sergio',
  'madurez': {'inicial': 'i', 'intermedio': 'm', 'pleno': 'p'},
  'trato': ['claro'],
  'umbrales': {'intermedio': 2000, 'pleno': 20000},
};

const _vista = <String, dynamic>{
  'personalidad': _personalidad,
  'correcciones': [
    {
      'texto': 'Sé breve.',
      'fuente': 'Sergio, con-1',
      'fecha': '2026-11-22T00:00:00Z',
    },
  ],
  'madurez': {
    'nivel': 'inicial',
    'recuerdos': 12,
    'umbrales': {'intermedio': 2000, 'pleno': 20000},
  },
};

Future<HttpServer> _coreFalso({
  int? estado,
  String detalle = 'detalle inválido',
}) async {
  final servidor = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  servidor.listen((pedido) async {
    final respuesta = pedido.response;
    expect(
      pedido.headers.value(
        pedido.method == 'GET' ? 'X-Ashur-Clave' : 'X-Ashur-Clave-Admin',
      ),
      pedido.method == 'GET' ? 'normal' : 'admin',
    );
    if (estado != null) {
      respuesta.statusCode = estado;
      respuesta.headers.contentType = ContentType.json;
      respuesta.write(jsonEncode({'detail': detalle}));
      await respuesta.close();
      return;
    }
    final cuerpo = pedido.method == 'GET'
        ? ''
        : await utf8.decodeStream(pedido);
    final ruta = pedido.uri.path;
    dynamic valor;
    var status = 200;
    switch ('${pedido.method} $ruta') {
      case 'GET /personalidad':
        valor = _vista;
        break;
      case 'PUT /personalidad':
        expect(jsonDecode(cuerpo), _personalidad);
        expect(pedido.headers.value('X-Ashur-Clave-Admin'), 'admin');
        valor = _vista;
        break;
      case 'PUT /personalidad/correcciones':
        expect(jsonDecode(cuerpo), [
          {
            'texto': 'Una corrección editada.',
            'fuente': 'Sergio, con-1',
            'fecha': '2026-11-22T00:00:00Z',
          },
        ]);
        expect(pedido.headers.value('X-Ashur-Clave-Admin'), 'admin');
        valor = _vista;
        break;
      case 'GET /roles':
        valor = [
          {
            'id': 'rol-1',
            'nombre': 'Familia',
            'herramientas': ['buscar_objetos', 'modulo-luces-*'],
          },
        ];
        break;
      case 'POST /roles':
        expect(jsonDecode(cuerpo), {
          'nombre': 'Familia',
          'herramientas': ['buscar_objetos'],
        });
        status = 201;
        valor = {
          'id': 'rol-2',
          'nombre': 'Familia',
          'herramientas': ['buscar_objetos'],
        };
        break;
      case 'PATCH /roles/rol-1':
        expect(jsonDecode(cuerpo), {
          'nombre': 'Casa',
          'herramientas': ['buscar_*'],
        });
        valor = {
          'id': 'rol-1',
          'nombre': 'Casa',
          'herramientas': ['buscar_*'],
        };
        break;
      case 'GET /identidades':
        valor = [
          {
            'id': 'ide-1',
            'nombre': 'Ana',
            'clase': 'persona',
            'archivada': false,
            'menciones': 2,
            'nivel': 1,
            'rol': 'rol-1',
            'con_clave': false,
          },
          {
            'id': 'ide-2',
            'nombre': 'Luna',
            'clase': 'mascota',
            'archivada': false,
            'menciones': 1,
            'nivel': 1,
            'rol': null,
            'con_clave': false,
          },
        ];
        break;
      case 'PATCH /identidades/ide-1':
        expect(jsonDecode(cuerpo), {'rol': null});
        valor = {
          'id': 'ide-1',
          'nombre': 'Ana',
          'clase': 'persona',
          'archivada': false,
          'menciones': 2,
          'nivel': 1,
          'rol': null,
          'con_clave': false,
        };
        break;
      case 'POST /identidades/ide-1/clave':
        status = 201;
        valor = {
          'identidad': {
            'id': 'ide-1',
            'nombre': 'Ana',
            'clase': 'persona',
            'archivada': false,
            'menciones': 2,
            'nivel': 1,
            'rol': 'rol-1',
            'con_clave': true,
          },
          'clave': 'clave-de-una-sola-vez',
        };
        break;
      case 'GET /modulos':
        valor = [
          {
            'id': 'prueba',
            'manifiesto': {
              'id': 'prueba',
              'nombre': 'Prueba',
              'version': '1',
              'descripcion': 'Módulo de prueba',
              'acciones': [],
              'ajustes': [
                {
                  'id': 'saludo',
                  'tipo': 'texto',
                  'descripcion': 'Saludo',
                  'por_defecto': 'hola',
                },
              ],
            },
            'error': null,
          },
        ];
        break;
      case 'GET /modulos/prueba/ajustes':
        valor = [
          {
            'id': 'saludo',
            'tipo': 'texto',
            'descripcion': 'Saludo',
            'secreto': false,
            'por_defecto': 'hola',
            'valor': 'buenas',
            'configurado': true,
          },
        ];
        break;
      case 'PATCH /modulos/prueba/ajustes':
        expect(jsonDecode(cuerpo), {'saludo': 'adiós'});
        valor = [
          {
            'id': 'saludo',
            'tipo': 'texto',
            'descripcion': 'Saludo',
            'secreto': false,
            'por_defecto': 'hola',
            'valor': 'adiós',
            'configurado': true,
          },
        ];
        break;
      case 'GET /nodos':
        valor = [
          {
            'id': 'nodo-1',
            'nombre': 'Mac',
            'archivado': false,
            'en_linea': true,
            'modo': 'full',
            'modelos': [
              {
                'nombre': 'qwen2.5:7b',
                'tamano': 1,
                'capacidades': ['completion'],
              },
            ],
            'ultimo_latido': null,
            'ajustes': {
              'modelos_ofrecidos': null,
              'num_ctx': null,
              'horario': null,
            },
          },
        ];
        break;
      case 'PATCH /nodos/nodo-1':
        expect(jsonDecode(cuerpo), {
          'modelos_ofrecidos': ['qwen2.5:7b'],
          'num_ctx': 8192,
          'horario': {'desde': '08:00', 'hasta': '22:00'},
        });
        valor = {
          'id': 'nodo-1',
          'nombre': 'Mac',
          'archivado': false,
          'en_linea': true,
          'modo': 'full',
          'modelos': [
            {
              'nombre': 'qwen2.5:7b',
              'tamano': 1,
              'capacidades': ['completion'],
            },
          ],
          'ultimo_latido': null,
          'ajustes': {
            'modelos_ofrecidos': ['qwen2.5:7b'],
            'num_ctx': 8192,
            'horario': {'desde': '08:00', 'hasta': '22:00'},
          },
        };
        break;
      default:
        status = 404;
        valor = {'detail': 'ruta desconocida'};
    }
    respuesta.statusCode = status;
    respuesta.headers.contentType = ContentType.json;
    respuesta.write(jsonEncode(valor));
    await respuesta.close();
  });
  return servidor;
}

ClienteCore _cliente(HttpServer servidor) => ClienteCore(
  direccion: Uri.parse('http://127.0.0.1:${servidor.port}'),
  clave: 'normal',
  claveAdmin: 'admin',
);

class _AlmacenObservado implements AlmacenSecreto {
  _AlmacenObservado(this.valores);

  final Map<String, String> valores;
  final List<(String, String)> escrituras = [];

  @override
  Future<String?> leer(String clave, {bool protegido = false}) async => valores[clave];

  @override
  Future<void> escribir(String clave, String valor, {bool protegido = false}) async {
    escrituras.add((clave, valor));
    valores[clave] = valor;
  }

  @override
  Future<void> borrar(String clave) async => valores.remove(clave);
}

class _ClienteWidgetFalso extends ClienteCore {
  _ClienteWidgetFalso()
    : super(direccion: Uri.parse('http://127.0.0.1'), clave: 'normal');

  @override
  Future<Map<String, dynamic>> verPersonalidad() async => _vista;

  @override
  Future<List<Map<String, dynamic>>> listarRoles() async => [
    {
      'id': 'rol-1',
      'nombre': 'Familia',
      'herramientas': ['buscar_objetos'],
    },
  ];

  @override
  Future<List<Map<String, dynamic>>> listarIdentidades() async => [
    {
      'id': 'ide-1',
      'nombre': 'Ana',
      'clase': 'persona',
      'archivada': false,
      'menciones': 2,
      'nivel': 1,
      'rol': 'rol-1',
      'con_clave': false,
    },
    {
      'id': 'ide-2',
      'nombre': 'Luna',
      'clase': 'mascota',
      'archivada': false,
      'menciones': 1,
      'nivel': 1,
      'rol': null,
      'con_clave': false,
    },
  ];

  @override
  Future<Map<String, dynamic>> crearClaveIdentidad(String id) async => {
    'identidad': {
      'id': id,
      'nombre': 'Ana',
      'clase': 'persona',
      'archivada': false,
      'menciones': 2,
      'nivel': 1,
      'rol': 'rol-1',
      'con_clave': true,
    },
    'clave': 'clave-de-una-sola-vez',
  };
}

FuenteGalaxia _fuente(
  HttpServer servidor, {
  required bool admin,
  required _AlmacenObservado almacen,
}) {
  // Las claves ya en la entrada protegida de Face ID (ADR 0025): así leerlas no migra nada ni escribe en el almacén.
  almacen.valores.addAll({
    claveDireccion: 'http://127.0.0.1:${servidor.port}',
    claveClaves: jsonEncode({'clave': 'normal', 'admin': admin ? 'admin' : null}),
  });
  return FuenteGalaxia(
    almacen: almacen,
    cache: CacheEnMemoria(),
    cargarEjemplo: () async => throw StateError('No se usa en esta prueba.'),
  );
}

void main() {
  setUpAll(() => HttpOverrides.global = null);

  test(
    'cliente Lo de Ashur consulta y modifica todas las rutas acordadas',
    () async {
      final servidor = await _coreFalso();
      addTearDown(servidor.close);
      final cliente = _cliente(servidor);

      expect(await cliente.verPersonalidad(), _vista);
      expect(await cliente.guardarPersonalidad(_personalidad), _vista);
      expect(
        await cliente.reemplazarCorrecciones([
          {
            'texto': 'Una corrección editada.',
            'fuente': 'Sergio, con-1',
            'fecha': '2026-11-22T00:00:00Z',
          },
        ]),
        _vista,
      );
      expect(await cliente.listarRoles(), hasLength(1));
      expect(
        await cliente.crearRol('Familia', ['buscar_objetos']),
        containsPair('id', 'rol-2'),
      );
      expect(
        await cliente.editarRol('rol-1', 'Casa', ['buscar_*']),
        containsPair('nombre', 'Casa'),
      );
      expect(await cliente.listarIdentidades(), hasLength(2));
      expect(
        await cliente.asignarRol('ide-1', null),
        containsPair('rol', null),
      );
      expect(
        await cliente.crearClaveIdentidad('ide-1'),
        containsPair('clave', 'clave-de-una-sola-vez'),
      );
      expect(await cliente.listarModulos(), hasLength(1));
      expect(await cliente.verAjustesModulo('prueba'), hasLength(1));
      expect(
        await cliente.cambiarAjustesModulo('prueba', {'saludo': 'adiós'}),
        hasLength(1),
      );
      expect(await cliente.listarNodos(), hasLength(1));
      expect(
        await cliente.editarNodo('nodo-1', {
          'modelos_ofrecidos': ['qwen2.5:7b'],
          'num_ctx': 8192,
          'horario': {'desde': '08:00', 'hasta': '22:00'},
        }),
        containsPair('id', 'nodo-1'),
      );
    },
  );

  test(
    'cliente conserva los errores del core y expone detail en 422',
    () async {
      for (final (status, fallo) in [
        (401, FalloCore.claveInvalida),
        (404, FalloCore.noExiste),
        (409, FalloCore.conflicto),
        (422, FalloCore.datosInvalidos),
        (503, FalloCore.coreSinClave),
      ]) {
        final servidor = await _coreFalso(
          estado: status,
          detalle: 'Esa identidad está archivada.',
        );
        final cliente = _cliente(servidor);
        await expectLater(
          cliente.crearClaveIdentidad('ide-1'),
          throwsA(
            isA<ErrorCore>()
                .having((error) => error.fallo, 'fallo', fallo)
                .having(
                  (error) => error.detalle,
                  'detalle',
                  status == 409 || status == 422
                      ? 'Esa identidad está archivada.'
                      : '',
                ),
          ),
        );
        await servidor.close(force: true);
      }
    },
  );

  testWidgets(
    'la clave nueva aparece una vez y no se guarda en el dispositivo',
    (tester) async {
      final servidor = await _coreFalso();
      addTearDown(servidor.close);
      final almacen = _AlmacenObservado({});
      final fuente = _fuente(servidor, admin: true, almacen: almacen);
      await tester.pumpWidget(
        CupertinoApp(
          home: SingleChildScrollView(
            child: LoDeAshur(
              fuente: fuente,
              clienteOverride: _ClienteWidgetFalso(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Crear clave'));
      await tester.tap(find.text('Crear clave'));
      await tester.pumpAndSettle();

      expect(find.text('clave-de-una-sola-vez'), findsOneWidget);
      expect(find.text('Copiar'), findsOneWidget);
      expect(almacen.escrituras, isEmpty);

      await tester.tap(find.text('Cerrar'));
      await tester.pumpAndSettle();
      expect(find.text('clave-de-una-sola-vez'), findsNothing);
      expect(almacen.escrituras, isEmpty);
    },
  );

  testWidgets(
    'sin clave de administrador se ve la configuración sin controles de edición',
    (tester) async {
      final servidor = await _coreFalso();
      addTearDown(servidor.close);
      final almacen = _AlmacenObservado({});
      final fuente = _fuente(servidor, admin: false, almacen: almacen);
      await tester.pumpWidget(
        CupertinoApp(
          home: SingleChildScrollView(
            child: LoDeAshur(
              fuente: fuente,
              clienteOverride: _ClienteWidgetFalso(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Lo de Ashur'));

      expect(
        find.text('Madurez actual: inicial · 12 recuerdos'),
        findsOneWidget,
      );
      expect(find.text('Base'), findsOneWidget);
      expect(find.text('Sé breve.'), findsOneWidget);
      expect(find.text('Guardar personalidad'), findsNothing);
      expect(find.text('Guardar corrección'), findsNothing);
      expect(find.text('Crear rol'), findsNothing);
      expect(find.text('Cambiar rol'), findsNothing);
      expect(find.text('Crear clave'), findsNothing);
    },
  );
}
