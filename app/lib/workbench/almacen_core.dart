// Workbench guardado en el core: cada operación es una acción del módulo `workbench` (modules/workbench/).
import '../conexion/cliente.dart';
import 'almacen.dart';

class AlmacenWorkbenchCore implements AlmacenWorkbench {
  AlmacenWorkbenchCore(this.cliente);

  /// Da el cliente del core, o null si la app todavía no tiene dirección y clave.
  final Future<ClienteCore?> Function() cliente;

  /// Un modelo puede tardar minutos en responder.
  static const _esperaLarga = Duration(minutes: 4);

  Future<Registro> _accion(String accion, [Registro parametros = const {}, Duration? espera]) async {
    final c = await cliente();
    if (c == null) throw const ErrorWorkbench('Conecta la app al core en la pestaña Estado.');
    try {
      return await c.accionModulo('workbench', accion, parametros, espera);
    } on ErrorCore catch (e) {
      throw ErrorWorkbench(switch (e.fallo) {
        FalloCore.inalcanzable => 'No se pudo llegar al core. ${e.detalle}',
        FalloCore.claveInvalida => e.detalle.isEmpty
            ? 'El core no aceptó la clave.'
            : 'Para esto ${e.detalle}. Ponla en la pestaña Estado.',
        FalloCore.noExiste => 'Este core no tiene el módulo Workbench. Hay que actualizarlo.',
        FalloCore.coreSinClave => 'El core no tiene su clave configurada.',
        _ => e.detalle,
      });
    }
  }

  @override
  Future<List<Registro>> listar(String tipo) async =>
      ((await _accion('listar', {'tipo': tipo}))['registros'] as List).cast<Registro>();

  @override
  Future<Registro> crear(String tipo, Registro datos) async =>
      (await _accion('crear', {'tipo': tipo, 'datos': datos}))['registro'] as Registro;

  @override
  Future<Registro> editar(String tipo, String id, Registro cambios) async =>
      (await _accion('editar', {'tipo': tipo, 'id': id, 'cambios': cambios}))['registro'] as Registro;

  @override
  Future<void> borrar(String tipo, String id) => _accion('borrar', {'tipo': tipo, 'id': id});

  @override
  Future<int> repartirCola() async => (await _accion('repartir_cola'))['asignadas'] as int;

  @override
  Future<Registro> ejecutarTarea(String id) async {
    final tarea = (await _accion('ejecutar_tarea', {'id': id}, _esperaLarga))['registro'] as Registro;
    if (tarea['estado'] == 'error') throw ErrorWorkbench('La ejecución falló: ${tarea['error']}');
    return tarea;
  }

  @override
  Future<Registro> probarServidor(String id) async =>
      (await _accion('probar_servidor', {'id': id}, const Duration(seconds: 20)))['registro'] as Registro;

  @override
  Future<Registro> compilarEntrega(String id) async {
    final respuesta = await _accion('compilar_entrega', {'id': id}, const Duration(seconds: 20));
    final entrega = respuesta['registro'] as Registro;
    if (respuesta['aceptada'] != true) throw ErrorWorkbench('El servidor no aceptó la compilación. ${entrega['registro']}');
    return entrega;
  }
}
