import 'package:ashur/workbench/almacen.dart';
import 'package:ashur/workbench/pantalla_workbench.dart';
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

/// Workbench en memoria, con el mismo reparto que el módulo del core.
class _AlmacenFalso implements AlmacenWorkbench {
  final datos = <String, List<Registro>>{
    tipoProyectos: [],
    tipoProveedores: [],
    tipoTareas: [],
    tipoEntregas: [],
    tipoServidores: [],
  };
  int _cuenta = 0;

  @override
  Future<List<Registro>> listar(String tipo) async => [for (final r in datos[tipo]!) Map.of(r)];

  @override
  Future<Registro> crear(String tipo, Registro d) async {
    if (tipo == tipoTareas && d['titulo'] == 'romper') throw const ErrorWorkbench('No se pudo crear');
    final r = {...d, 'id': '${tipo[0]}${++_cuenta}'};
    datos[tipo]!.insert(0, r);
    return r;
  }

  @override
  Future<Registro> editar(String tipo, String id, Registro cambios) async =>
      datos[tipo]!.firstWhere((r) => r['id'] == id)..addAll(cambios);

  @override
  Future<void> borrar(String tipo, String id) async => datos[tipo]!.removeWhere((r) => r['id'] == id);

  @override
  Future<int> repartirCola() async {
    final proveedor = datos[tipoProveedores]!.firstWhere((p) => p['estado'] == 'activo');
    final cola = datos[tipoTareas]!.where((t) => t['estado'] == 'cola').toList();
    for (final t in cola) {
      t.addAll({'estado': 'asignada', 'proveedor_id': proveedor['id']});
    }
    return cola.length;
  }

  @override
  Future<Registro> ejecutarTarea(String id) => editar(tipoTareas, id, {
        'estado': 'revision',
        'resultado': 'Respuesta del modelo',
        'modelo_usado': 'modelo-x',
        'ejecuciones': 1,
      });

  @override
  Future<Registro> probarServidor(String id) =>
      editar(tipoServidores, id, {'estado': 'en_linea', 'latencia_ms': 42, 'detalle': 'HTTP 200'});

  @override
  Future<Registro> compilarEntrega(String id) =>
      editar(tipoEntregas, id, {'estado': 'compilando', 'registro': 'HTTP 200 ok'});
}

Future<void> _abrir(WidgetTester tester, _AlmacenFalso almacen, {Size tamano = const Size(420, 900)}) async {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(WidgetsApp(
    color: const Color(0xFF000000),
    localizationsDelegates: const [DefaultWidgetsLocalizations.delegate, DefaultCupertinoLocalizations.delegate],
    pageRouteBuilder: <T>(RouteSettings ajustes, WidgetBuilder constructor) =>
        PageRouteBuilder<T>(settings: ajustes, pageBuilder: (context, _, _) => constructor(context)),
    home: PantallaWorkbench(almacen: almacen),
  ));
  await tester.pumpAndSettle();
}

Future<void> _tocar(WidgetTester tester, String texto, {bool primero = false}) async {
  final boton = primero ? find.text(texto).first : find.text(texto).last;
  await tester.ensureVisible(boton);
  await tester.pumpAndSettle();
  await tester.tap(boton);
  await tester.pumpAndSettle();
}

Future<void> _escribir(WidgetTester tester, String pista, String texto) async {
  await tester.enterText(find.widgetWithText(CupertinoTextField, pista), texto);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('el panel vacío invita a crear y lleva al tablero', (tester) async {
    await _abrir(tester, _AlmacenFalso());
    expect(find.text('Todo el trabajo, repartido.'), findsOneWidget);
    expect(find.text('La cola está vacía.'), findsOneWidget);
    expect(find.text('Añade tu primer proveedor para empezar.'), findsOneWidget);
    await _tocar(tester, 'Crear la primera tarea');
    expect(find.text('Tablero de tareas'), findsOneWidget);
    expect(find.text('Vacío'), findsNWidgets(6));
  });

  testWidgets('crea un proveedor y una tarea, reparte la cola, ejecuta y aprueba', (tester) async {
    final almacen = _AlmacenFalso();
    await _abrir(tester, almacen);

    await _tocar(tester, 'Proveedores');
    await _tocar(tester, 'Añadir proveedor');
    expect(find.text('Nuevo proveedor'), findsOneWidget);
    await _escribir(tester, 'Claude', 'Claude Max');
    await _tocar(tester, 'Guardar');
    expect(find.text('Proveedor añadido'), findsOneWidget);
    expect(find.text('100 ejecuciones disponibles'), findsOneWidget);
    expect(almacen.datos[tipoProveedores]!.single['familia'], 'claude');

    await _tocar(tester, 'Tareas');
    await _tocar(tester, 'Nueva tarea');
    await _escribir(tester, 'Rediseñar el onboarding', 'Arreglar el zoom');
    await _tocar(tester, 'Urgente');
    await _tocar(tester, 'Crear tarea');
    expect(almacen.datos[tipoTareas]!.single, containsPair('prioridad', 'urgente'));
    expect(almacen.datos[tipoTareas]!.single, containsPair('estado', 'cola'));

    await _tocar(tester, 'Repartir cola');
    expect(find.text('1 tareas repartidas'), findsOneWidget);
    expect(almacen.datos[tipoTareas]!.single['estado'], 'asignada');

    await _tocar(tester, 'Listas 0'); // una sola columna
    expect(find.text('Arreglar el zoom'), findsNothing);
    expect(find.text('Vacío'), findsOneWidget);
    await _tocar(tester, 'Asignadas 1');
    expect(find.text('Arreglar el zoom'), findsOneWidget);

    almacen.datos[tipoTareas]!.single['titulo'] = 'Arreglar el zoom ya'; // cambió en otro equipo
    await _tocar(tester, 'Actualizar');
    expect(find.text('Arreglar el zoom ya'), findsOneWidget);
    almacen.datos[tipoTareas]!.single['titulo'] = 'Arreglar el zoom';
    await _tocar(tester, 'Actualizar');

    await _tocar(tester, 'Arreglar el zoom');
    expect(find.text('Pendiente de ejecución'), findsOneWidget);
    await _tocar(tester, 'Ejecutar');
    expect(find.text('Respuesta del modelo'), findsOneWidget);
    expect(find.text('modelo-x'), findsOneWidget);
    await _tocar(tester, 'Aprobar');
    expect(almacen.datos[tipoTareas]!.single['estado'], 'lista');

    await _tocar(tester, 'Eliminar tarea');
    await _tocar(tester, 'Sí, eliminar');
    expect(almacen.datos[tipoTareas], isEmpty);
    expect(find.text('Tablero de tareas'), findsOneWidget);
  });

  testWidgets('un error del almacén se ve como aviso', (tester) async {
    await _abrir(tester, _AlmacenFalso());
    await _tocar(tester, 'Tareas');
    await _tocar(tester, 'Nueva tarea');
    await _escribir(tester, 'Rediseñar el onboarding', 'romper');
    await _tocar(tester, 'Crear tarea');
    expect(find.text('No se pudo crear'), findsOneWidget);
  });

  testWidgets('una entrega recorre sus pasos y se compila en el servidor', (tester) async {
    final almacen = _AlmacenFalso();
    await _abrir(tester, almacen);
    await _tocar(tester, 'Entregas');
    expect(find.text('Sin entregas todavía'), findsOneWidget);
    await _tocar(tester, 'Nueva entrega');
    await _escribir(tester, 'v1.0.0', 'v0.2.0');
    await _tocar(tester, 'Crear entrega');
    expect(find.text('PENDIENTE'), findsNWidgets(4));

    await _tocar(tester, 'Publicar');
    final entrega = almacen.datos[tipoEntregas]!.single;
    expect(entrega['publicada'], true);
    expect(entrega['estado'], 'publicada');
    expect(entrega['publicada_el'], isNotNull);

    await _tocar(tester, 'Compilar en servidor');
    expect(find.text('Compilación aceptada por el servidor'), findsOneWidget);
    await _tocar(tester, '▸ REGISTRO DE COMPILACIÓN');
    expect(find.text('HTTP 200 ok'), findsOneWidget);
  });

  testWidgets('guarda el servidor, lo prueba y crea un proyecto', (tester) async {
    final almacen = _AlmacenFalso();
    await _abrir(tester, almacen);
    await _tocar(tester, 'Servidor', primero: true); // la sección, no la tarjeta del panel
    await _tocar(tester, 'Probar conexión');
    expect(find.text('Guarda la configuración antes de probar'), findsOneWidget);
    await _escribir(tester, 'http://servidor:8720', 'http://zima:8720/');
    await _escribir(tester, 'Docker, Ollama, Gitea', 'Docker, Ollama');
    await _tocar(tester, 'Guardar');
    expect(almacen.datos[tipoServidores]!.single['url'], 'http://zima:8720');
    expect(almacen.datos[tipoServidores]!.single['servicios'], ['Docker', 'Ollama']);
    await _tocar(tester, 'Probar conexión');
    expect(find.text('En línea · 42 ms'), findsOneWidget);

    await _tocar(tester, 'Proyectos');
    await _tocar(tester, 'Nuevo proyecto');
    await _escribir(tester, 'Ashur', 'Ashur Core');
    await _tocar(tester, 'android');
    await _tocar(tester, 'Crear proyecto');
    expect(almacen.datos[tipoProyectos]!.single['plataformas'], ['ios', 'macos', 'android']);
    expect(find.text('0 tareas · 0 entregas'), findsOneWidget);
  });

  testWidgets('en una pantalla ancha usa la barra lateral', (tester) async {
    await _abrir(tester, _AlmacenFalso(), tamano: const Size(1280, 800));
    expect(find.text('ESPACIO'), findsOneWidget);
    expect(find.text('sin configurar'), findsOneWidget);
    await _tocar(tester, 'Proyectos');
    expect(find.text('Sin proyectos'), findsOneWidget);
  });
}
