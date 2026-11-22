import 'dart:async';

import 'package:ashur/conexion/almacen.dart';
import 'package:ashur/conexion/cliente.dart';
import 'package:ashur/conexion/fuente.dart';
import 'package:ashur/galaxia/camara.dart';
import 'package:ashur/galaxia/modelo.dart';
import 'package:ashur/galaxia/pintor.dart';
import 'package:ashur/inventario/objeto.dart';
import 'package:ashur/inventario/pantalla_inventario.dart';
import 'package:ashur/main.dart';
// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

class _ClienteCoreFalso extends ClienteCore {
  _ClienteCoreFalso({required super.direccion, required super.clave, super.claveAdmin});

  final List<Objeto> objetos = [
    const Objeto(id: 'obj-1', nombre: 'Cuaderno', lugar: 'Escritorio', archivado: false, menciones: 1),
    const Objeto(id: 'obj-2', nombre: 'Lápiz', lugar: null, archivado: true, menciones: 0),
  ];

  @override
  Future<List<Objeto>> listarObjetos({bool archivados = false}) async {
    return archivados ? List.of(objetos) : objetos.where((o) => !o.archivado).toList();
  }

  @override
  Future<Objeto> crearObjeto(String nombre, String? lugar) async {
    final nuevo = Objeto(
      id: 'obj-${objetos.length + 1}',
      nombre: nombre,
      lugar: lugar,
      archivado: false,
      menciones: 0,
    );
    objetos.add(nuevo);
    return nuevo;
  }

  @override
  Future<Objeto> editarObjeto(String id, Map<String, dynamic> cambios) async {
    final idx = objetos.indexWhere((o) => o.id == id);
    final actual = objetos[idx];
    final nuevo = Objeto(
      id: actual.id,
      nombre: cambios['nombre'] as String? ?? actual.nombre,
      lugar: cambios.containsKey('lugar') ? cambios['lugar'] as String? : actual.lugar,
      archivado: cambios['archivado'] as bool? ?? actual.archivado,
      menciones: actual.menciones,
    );
    objetos[idx] = nuevo;
    return nuevo;
  }
}

/// Un core que tarda en mandar la lista: responde cuando la prueba lo decide.
class _ClienteCoreLento extends ClienteCore {
  _ClienteCoreLento({required super.direccion, required super.clave});

  final respuesta = Completer<List<Objeto>>();

  @override
  Future<List<Objeto>> listarObjetos({bool archivados = false}) => respuesta.future;
}

class _FuenteEspia extends FuenteGalaxia {
  _FuenteEspia({
    required super.almacen,
    required super.cache,
    required super.cargarEjemplo,
    required this.alActualizar,
  });

  final void Function() alActualizar;

  @override
  Future<void> actualizar() async {
    alActualizar();
    await super.actualizar();
  }
}

void main() {
  setUp(() => rootBundle.clear());

  testWidgets('tocar ☰ abre Inventario', (tester) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final fuente = FuenteGalaxia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
    );
    await tester.runAsync(() => fuente.actualizar());

    await tester.pumpWidget(AppAshur(fuente: fuente));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('☰'), findsOneWidget);
    await tester.tap(find.text('☰'));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byType(PantallaInventario), findsOneWidget);
    expect(find.text('Inventario'), findsOneWidget);
  });

  testWidgets('tocar el planeta Objetos abre Inventario', (tester) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    const tamano = Size(400, 800);

    final fuente = FuenteGalaxia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
    );
    await tester.runAsync(() => fuente.actualizar());

    await tester.pumpWidget(AppAshur(fuente: fuente));
    await tester.pump(const Duration(milliseconds: 100));

    final estado = fuente.galaxia!;
    const t = 1.0;
    await tester.pump(const Duration(seconds: 1));
    final planetaObjetos = Camara.inicial.aPantalla(
      Geometria(estado, tamano, t).posicion('objetos', t),
      tamano.center(Offset.zero),
    );

    await tester.tapAt(planetaObjetos);
    await tester.pump(const Duration(milliseconds: 600));

    expect(find.byType(PantallaInventario), findsOneWidget);
    expect(find.text('Inventario'), findsOneWidget);
  });

  testWidgets('muestra objetos con nombre y lugar, o «Sin lugar»', (tester) async {
    final cliente = _ClienteCoreFalso(
      direccion: Uri.parse('http://127.0.0.1:8720'),
      clave: 'buena',
      claveAdmin: null,
    );

    final fuente = FuenteGalaxia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
    );

    await tester.pumpWidget(WidgetsApp(
      color: const Color(0xFF05060B),
      localizationsDelegates: const [
        DefaultWidgetsLocalizations.delegate,
        DefaultCupertinoLocalizations.delegate,
      ],
      pageRouteBuilder: <T>(settings, builder) =>
          PageRouteBuilder<T>(settings: settings, pageBuilder: (context, _, __) => builder(context)),
      home: PantallaInventario(fuente: fuente, cliente: cliente),
    ));
    await tester.pump();

    // Objeto activo visible
    expect(find.text('Cuaderno'), findsOneWidget);
    expect(find.text('Escritorio'), findsOneWidget);

    // Sin clave de administrador: no aparecen los controles y avisa
    expect(find.text('Renombrar'), findsNothing);
    expect(find.text('Mover'), findsNothing);
    expect(find.text('Archivar'), findsNothing);
    expect(find.text('Hace falta la clave de administrador en la pestaña Estado.'), findsOneWidget);

    // Activamos el interruptor de archivados
    final switchFinder = find.byType(CupertinoSwitch);
    expect(switchFinder, findsOneWidget);
    await tester.tap(switchFinder);
    await tester.pump();

    // Ahora aparece también el archivado, con «Sin lugar»
    expect(find.text('Lápiz'), findsOneWidget);
    expect(find.text('Sin lugar'), findsOneWidget);
    expect(find.text('(Archivado)'), findsOneWidget);
  });

  testWidgets('con clave de administrador aparecen controles, y archivar llama a actualizar', (tester) async {
    var actualizaciones = 0;
    final cliente = _ClienteCoreFalso(
      direccion: Uri.parse('http://127.0.0.1:8720'),
      clave: 'buena',
      claveAdmin: 'admin-buena',
    );

    final fuente = _FuenteEspia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
      alActualizar: () => actualizaciones++,
    );

    await tester.pumpWidget(WidgetsApp(
      color: const Color(0xFF05060B),
      localizationsDelegates: const [
        DefaultWidgetsLocalizations.delegate,
        DefaultCupertinoLocalizations.delegate,
      ],
      pageRouteBuilder: <T>(settings, builder) =>
          PageRouteBuilder<T>(settings: settings, pageBuilder: (context, _, __) => builder(context)),
      home: PantallaInventario(fuente: fuente, cliente: cliente),
    ));
    await tester.pump();

    // Controles de administrador presentes
    expect(find.text('Renombrar'), findsOneWidget);
    expect(find.text('Mover'), findsOneWidget);
    expect(find.text('Archivar'), findsOneWidget);
    expect(find.text('Hace falta la clave de administrador en la pestaña Estado.'), findsNothing);

    // Tocamos Archivar
    await tester.tap(find.text('Archivar'));
    await tester.pump();

    // fuente.actualizar() fue llamado
    expect(actualizaciones, 1);
  });

  testWidgets('crear objeto envía nombre y lugar y llama a actualizar', (tester) async {
    var actualizaciones = 0;
    final cliente = _ClienteCoreFalso(
      direccion: Uri.parse('http://127.0.0.1:8720'),
      clave: 'buena',
      claveAdmin: 'admin-buena',
    );

    final fuente = _FuenteEspia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
      alActualizar: () => actualizaciones++,
    );

    await tester.pumpWidget(WidgetsApp(
      color: const Color(0xFF05060B),
      localizationsDelegates: const [
        DefaultWidgetsLocalizations.delegate,
        DefaultCupertinoLocalizations.delegate,
      ],
      pageRouteBuilder: <T>(settings, builder) =>
          PageRouteBuilder<T>(settings: settings, pageBuilder: (context, _, __) => builder(context)),
      home: PantallaInventario(fuente: fuente, cliente: cliente),
    ));
    await tester.pump();

    // Ingresamos nombre y lugar
    await tester.enterText(find.byType(CupertinoTextField).first, 'Regla');
    await tester.enterText(find.byType(CupertinoTextField).at(1), 'Estante');
    await tester.pump();

    // Tocamos Crear objeto
    await tester.tap(find.text('Crear objeto'));
    await tester.pump();

    // Objeto creado aparece en la lista
    expect(find.text('Regla'), findsOneWidget);
    expect(find.text('Estante'), findsOneWidget);
    expect(actualizaciones, 1);
  });

  testWidgets('salir de Inventario mientras la lista carga no lanza errores', (tester) async {
    final cliente = _ClienteCoreLento(direccion: Uri.parse('http://127.0.0.1:8720'), clave: 'buena');
    final fuente = FuenteGalaxia(
      almacen: AlmacenEnMemoria(),
      cache: CacheEnMemoria(),
      cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
    );

    await tester.pumpWidget(WidgetsApp(
      color: const Color(0xFF05060B),
      localizationsDelegates: const [
        DefaultWidgetsLocalizations.delegate,
        DefaultCupertinoLocalizations.delegate,
      ],
      pageRouteBuilder: <T>(settings, builder) =>
          PageRouteBuilder<T>(settings: settings, pageBuilder: (context, _, __) => builder(context)),
      home: PantallaInventario(fuente: fuente, cliente: cliente),
    ));
    await tester.pump();
    expect(find.byType(PantallaInventario), findsOneWidget);

    // Se sale de la pantalla antes de que llegue la lista.
    await tester.pumpWidget(const SizedBox());
    cliente.respuesta.complete(const [
      Objeto(id: 'obj-1', nombre: 'Cuaderno', lugar: 'Escritorio', archivado: false, menciones: 1),
    ]);
    await tester.pump();

    expect(tester.takeException(), isNull);
  });
}
