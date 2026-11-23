// Tareas: tablero por estado, alta de tareas y el detalle de cada una.
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'piezas.dart';

const _coloresPrioridad = {'baja': wbApagado, 'media': wbAzul, 'alta': wbAcento, 'urgente': wbRojo};

Future<void> repartirCola(DatosWorkbench datos) => datos.hacer(() async {
      final asignadas = await datos.almacen.repartirCola();
      return asignadas > 0 ? '$asignadas tareas repartidas' : 'No hay tareas en cola';
    });

void abrirTarea(BuildContext context, DatosWorkbench datos, String id) {
  Navigator.of(context).push(PageRouteBuilder<void>(
    pageBuilder: (context, _, _) => PantallaTarea(datos: datos, id: id),
    transitionsBuilder: (context, animacion, _, hijo) => FadeTransition(opacity: animacion, child: hijo),
  ));
}

class PaginaTareas extends StatefulWidget {
  const PaginaTareas({super.key, required this.datos});

  final DatosWorkbench datos;

  @override
  State<PaginaTareas> createState() => _PaginaTareasState();
}

class _PaginaTareasState extends State<PaginaTareas> {
  /// Estado de la única columna que se muestra, o null para verlas todas.
  String? _columna;

  @override
  Widget build(BuildContext context) {
    final datos = widget.datos;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Encabezado(
          etiqueta: 'Flujo de trabajo',
          titulo: 'Tablero de tareas',
          descripcion: 'Cada tarea va al modelo con más margen de cuota. Abre una tarea para asignarla a un '
              'proveedor concreto cuando quieras control manual.',
          acciones: [
            Boton('Repartir cola', alTocar: () => repartirCola(datos)),
            Boton(
              'Nueva tarea',
              principal: true,
              alTocar: () => abrirHoja<void>(
                context,
                titulo: 'Nueva tarea',
                descripcion: 'Describe el trabajo y decide quién lo ejecuta. Si lo dejas en automático, se asigna '
                    'al repartir la cola.',
                child: _FormularioTarea(datos: datos),
              ),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              Ficha('Todas', elegida: _columna == null, alTocar: () => setState(() => _columna = null)),
              for (final estado in estadosTarea.entries)
                Ficha(
                  '${estado.value} ${datos.tareas.where((t) => t['estado'] == estado.key).length}',
                  elegida: _columna == estado.key,
                  alTocar: () => setState(() => _columna = estado.key),
                ),
            ],
          ),
        ),
        if (_columna != null)
          _Columna(datos: datos, estado: _columna!, nombre: estadosTarea[_columna]!)
        else
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final estado in estadosTarea.entries)
                  Container(
                    width: 240,
                    margin: const EdgeInsets.only(right: 12),
                    child: _Columna(datos: datos, estado: estado.key, nombre: estado.value),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Columna extends StatelessWidget {
  const _Columna({required this.datos, required this.estado, required this.nombre});

  final DatosWorkbench datos;
  final String estado;
  final String nombre;

  @override
  Widget build(BuildContext context) {
    final tareas = datos.tareas.where((t) => t['estado'] == estado).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            children: [
              Expanded(child: Text(nombre.toUpperCase(), style: wbEtiqueta)),
              Text('${tareas.length}', style: wbEtiqueta),
            ],
          ),
        ),
        if (tareas.isEmpty)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 22),
            decoration: BoxDecoration(
              border: Border.all(color: wbBorde),
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: const Text('Vacío', style: wbEtiqueta),
          ),
        for (final t in tareas)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => abrirTarea(context, datos, t['id'] as String),
              child: Tarjeta(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text((tiposTarea[t['tipo']] ?? '${t['tipo']}').toUpperCase(), style: wbEtiqueta),
                        ),
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            color: _coloresPrioridad[t['prioridad']] ?? wbApagado,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('${t['titulo']}'),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            (datos.proveedor(t['proveedor_id'])?['nombre'] as String?) ?? 'sin asignar',
                            style: wbCuerpo.copyWith(fontSize: 11),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (((t['ejecuciones'] as num?) ?? 0) > 0) Text('${t['ejecuciones']}×', style: wbEtiqueta),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _FormularioTarea extends StatefulWidget {
  const _FormularioTarea({required this.datos});

  final DatosWorkbench datos;

  @override
  State<_FormularioTarea> createState() => _FormularioTareaState();
}

class _FormularioTareaState extends State<_FormularioTarea> {
  final _titulo = TextEditingController();
  final _contexto = TextEditingController();
  String _tipo = 'funcion';
  String _prioridad = 'media';
  String _proyecto = '';
  String _proveedor = '';

  @override
  void initState() {
    super.initState();
    _titulo.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _titulo.dispose();
    _contexto.dispose();
    super.dispose();
  }

  void _crear() {
    final datos = widget.datos;
    Navigator.of(context).pop();
    datos.hacer(() async {
      await datos.almacen.crear(tipoTareas, {
        'titulo': _titulo.text.trim(),
        'contexto': _contexto.text.trim(),
        'tipo': _tipo,
        'prioridad': _prioridad,
        'proyecto_id': _proyecto.isEmpty ? null : _proyecto,
        'proveedor_id': _proveedor.isEmpty ? null : _proveedor,
        'estado': _proveedor.isEmpty ? 'cola' : 'asignada',
      });
      return 'Tarea creada';
    });
  }

  @override
  Widget build(BuildContext context) {
    final datos = widget.datos;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Campo('Título', _titulo, pista: 'Rediseñar el onboarding'),
        Campo(
          'Contexto',
          _contexto,
          pista: 'Qué hay que lograr, restricciones y criterios de aceptación.',
          lineas: 4,
        ),
        Selector('Tipo', opciones: tiposTarea, valor: _tipo, alElegir: (v) => setState(() => _tipo = v)),
        Selector(
          'Prioridad',
          opciones: prioridades,
          valor: _prioridad,
          alElegir: (v) => setState(() => _prioridad = v),
        ),
        Selector(
          'Proyecto',
          opciones: {'': 'Sin proyecto', for (final p in datos.proyectos) p['id'] as String: '${p['nombre']}'},
          valor: _proyecto,
          alElegir: (v) => setState(() => _proyecto = v),
        ),
        Selector(
          'Ejecuta',
          opciones: {
            '': 'Automático',
            for (final p in datos.proveedores.where((p) => p['estado'] == 'activo'))
              p['id'] as String: '${p['nombre']}',
          },
          valor: _proveedor,
          alElegir: (v) => setState(() => _proveedor = v),
        ),
        PieHoja(texto: 'Crear tarea', alGuardar: _titulo.text.trim().isEmpty ? null : _crear),
      ],
    );
  }
}

/// Detalle de una tarea: contexto, resultado, a quién está asignada y las acciones.
class PantallaTarea extends StatefulWidget {
  const PantallaTarea({super.key, required this.datos, required this.id});

  final DatosWorkbench datos;
  final String id;

  @override
  State<PantallaTarea> createState() => _PantallaTareaState();
}

class _PantallaTareaState extends State<PantallaTarea> {
  bool _ejecutando = false;
  bool _confirmarBorrado = false;

  DatosWorkbench get _datos => widget.datos;

  Future<void> _asignar(Registro tarea, String proveedorId) => _datos.hacer(() async {
        final proveedor = _datos.proveedor(proveedorId);
        await _datos.almacen.editar(tipoTareas, widget.id, {
          'proveedor_id': proveedor?['id'],
          if (tarea['estado'] == 'cola' && proveedor != null) 'estado': 'asignada',
        });
        return 'Asignada a ${proveedor?['nombre'] ?? 'nadie'}';
      });

  Future<void> _ejecutar() async {
    setState(() => _ejecutando = true);
    await _datos.hacer(() async {
      final tarea = await _datos.almacen.ejecutarTarea(widget.id);
      return tarea['espera_equipo'] == true ? 'En espera de un equipo' : 'Ejecución terminada';
    });
    if (mounted) setState(() => _ejecutando = false);
  }

  Future<void> _cancelarEspera() => _datos.hacer(() async {
        await _datos.almacen.editar(tipoTareas, widget.id, {'estado': 'asignada', 'espera_equipo': false});
        return 'Espera cancelada';
      });

  Future<void> _borrar() async {
    final bien = await _datos.hacer(() async {
      await _datos.almacen.borrar(tipoTareas, widget.id);
      return 'Tarea eliminada';
    });
    if (bien && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: wbFondo,
      child: DefaultTextStyle(
        style: const TextStyle(color: wbTexto, fontSize: 14),
        child: SafeArea(
          child: ListenableBuilder(
            listenable: _datos,
            builder: (context, _) {
              final tarea = _datos.tarea(widget.id);
              return SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 820),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Boton('‹ Tablero', alTocar: () => Navigator.of(context).pop()),
                        ),
                        const SizedBox(height: 16),
                        if (tarea == null)
                          const Vacio(titulo: 'Esta tarea ya no existe.', descripcion: 'Vuelve al tablero.')
                        else
                          ..._detalle(tarea),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  List<Widget> _detalle(Registro tarea) {
    final proveedorId = (tarea['proveedor_id'] as String?) ?? '';
    final proyecto = _datos.proyecto(tarea['proyecto_id'])?['nombre'];
    return [
      Wrap(
        spacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Pastilla(tarea['estado'] as String),
          Text(
            '${tiposTarea[tarea['tipo']] ?? tarea['tipo']} · ${prioridades[tarea['prioridad']] ?? tarea['prioridad']}'
            '${proyecto == null ? '' : ' · $proyecto'}',
            style: wbCuerpo,
          ),
        ],
      ),
      const SizedBox(height: 10),
      Text('${tarea['titulo']}', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w600)),
      const SizedBox(height: 16),
      Selector(
        'Ejecuta',
        opciones: {'': 'Sin asignar', for (final p in _datos.proveedores) p['id'] as String: '${p['nombre']}'},
        valor: proveedorId,
        alElegir: (v) => _asignar(tarea, v),
      ),
      if (tarea['espera_equipo'] == true) ...[
        Text(
          tarea['equipo'] == null
              ? 'Esperando a que un equipo la tome. Se resuelve cuando tu equipo esté en la red con el ejecutor.'
              : 'La tomó ${tarea['equipo']} el ${fechaCorta(tarea['tomada'])}. Está trabajando en ella.',
          style: wbCuerpo,
        ),
        const SizedBox(height: 10),
        Align(alignment: Alignment.centerLeft, child: Boton('Cancelar espera', alTocar: _cancelarEspera)),
      ] else
        Align(
          alignment: Alignment.centerLeft,
          child: Boton(
            _ejecutando ? 'Ejecutando' : 'Ejecutar',
            principal: true,
            alTocar: _ejecutando || proveedorId.isEmpty ? null : _ejecutar,
          ),
        ),
      if (_datos.aviso != null) ...[
        const SizedBox(height: 12),
        Text(_datos.aviso!, style: TextStyle(color: _datos.avisoEsError ? wbRojo : wbVerde, fontSize: 13)),
      ],
      const SizedBox(height: 16),
      Seccion(
        etiqueta: 'Contexto',
        titulo: 'Qué hay que lograr',
        child: Text(
          (tarea['contexto'] as String?)?.isNotEmpty == true
              ? tarea['contexto'] as String
              : 'Sin contexto. Añade criterios para obtener mejores resultados.',
          style: wbCuerpo,
        ),
      ),
      const SizedBox(height: 12),
      Seccion(
        etiqueta: 'Resultado',
        titulo: (tarea['modelo_usado'] as String?) ?? 'Pendiente de ejecución',
        accion: tarea['estado'] == 'revision'
            ? Boton(
                'Aprobar',
                alTocar: () => _datos.hacer(() async {
                  await _datos.almacen.editar(tipoTareas, widget.id, {'estado': 'lista'});
                  return 'Tarea marcada como lista';
                }),
              )
            : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if ((tarea['error'] as String?)?.isNotEmpty == true)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(tarea['error'] as String, style: const TextStyle(color: wbRojo, fontSize: 13)),
              ),
            if ((tarea['resultado'] as String?)?.isNotEmpty == true)
              Text(
                tarea['resultado'] as String,
                style: const TextStyle(color: wbTexto, fontSize: 13, fontFamily: 'Menlo', height: 1.5),
              )
            else
              const Text('Aún no hay respuesta. Ejecuta la tarea para que el modelo la resuelva.', style: wbCuerpo),
          ],
        ),
      ),
      const SizedBox(height: 12),
      Seccion(
        etiqueta: 'Detalles',
        titulo: 'Historial',
        child: Column(
          children: [
            Dato('Ejecuciones', '${tarea['ejecuciones'] ?? 0}'),
            Dato('Proveedor', (_datos.proveedor(proveedorId)?['nombre'] as String?) ?? 'Sin asignar'),
            Dato('Proyecto', (proyecto as String?) ?? '—'),
            Dato('Última ejecución', fechaCorta(tarea['ultima_ejecucion'])),
          ],
        ),
      ),
      const SizedBox(height: 16),
      Align(
        alignment: Alignment.centerLeft,
        child: _confirmarBorrado
            ? Wrap(
                spacing: 8,
                children: [
                  Boton('Sí, eliminar', peligro: true, alTocar: _borrar),
                  Boton('Cancelar', alTocar: () => setState(() => _confirmarBorrado = false)),
                ],
              )
            : Boton('Eliminar tarea', peligro: true, alTocar: () => setState(() => _confirmarBorrado = true)),
      ),
    ];
  }
}
