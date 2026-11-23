// Proyectos: cada producto que se desarrolla desde Workbench, con sus tareas y sus entregas.
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'piezas.dart';

class PaginaProyectos extends StatelessWidget {
  const PaginaProyectos({super.key, required this.datos, required this.alIr});

  final DatosWorkbench datos;
  final ValueChanged<int> alIr;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Encabezado(
          etiqueta: 'Cartera',
          titulo: 'Proyectos',
          descripcion: 'Cada producto que desarrollas desde aquí, con sus tareas y sus entregas.',
          acciones: [
            Boton(
              'Nuevo proyecto',
              principal: true,
              alTocar: () => abrirHoja<void>(
                context,
                titulo: 'Nuevo proyecto',
                descripcion: 'Un proyecto agrupa sus tareas y sus entregas.',
                child: _FormularioProyecto(datos: datos),
              ),
            ),
          ],
        ),
        if (datos.proyectos.isEmpty)
          const Vacio(titulo: 'Sin proyectos', descripcion: 'Crea Ashur para agrupar sus tareas y sus versiones.'),
        for (final p in datos.proyectos)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Tarjeta(
              brillo: Color((p['color'] as int?) ?? 0xFFD9A06A),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text('${p['nombre']}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                      ),
                      Pastilla((p['estado'] as String?) ?? 'activo'),
                    ],
                  ),
                  Text(
                    (p['stack'] as String?)?.isNotEmpty == true ? p['stack'] as String : 'Sin stack definido',
                    style: wbEtiqueta.copyWith(letterSpacing: 0),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    (p['descripcion'] as String?)?.isNotEmpty == true
                        ? p['descripcion'] as String
                        : 'Sin descripción todavía.',
                    style: wbCuerpo,
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [for (final x in (p['plataformas'] as List?) ?? const []) Ficha('$x')],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${datos.tareas.where((t) => t['proyecto_id'] == p['id']).length} tareas · '
                          '${datos.entregas.where((e) => e['proyecto_id'] == p['id']).length} entregas',
                          style: wbCuerpo,
                        ),
                      ),
                      Boton('Abrir', alTocar: () => alIr(1)),
                    ],
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _FormularioProyecto extends StatefulWidget {
  const _FormularioProyecto({required this.datos});

  final DatosWorkbench datos;

  @override
  State<_FormularioProyecto> createState() => _FormularioProyectoState();
}

class _FormularioProyectoState extends State<_FormularioProyecto> {
  final _nombre = TextEditingController();
  final _descripcion = TextEditingController();
  final _stack = TextEditingController();
  final _repo = TextEditingController();
  final _plataformas = {'ios', 'macos'};

  @override
  void initState() {
    super.initState();
    _nombre.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    for (final c in [_nombre, _descripcion, _stack, _repo]) {
      c.dispose();
    }
    super.dispose();
  }

  void _crear() {
    final datos = widget.datos;
    Navigator.of(context).pop();
    datos.hacer(() async {
      await datos.almacen.crear(tipoProyectos, {
        'nombre': _nombre.text.trim(),
        'descripcion': _descripcion.text.trim(),
        'stack': _stack.text.trim(),
        'repo': _repo.text.trim(),
        'plataformas': [
          for (final p in plataformas)
            if (_plataformas.contains(p)) p,
        ],
        'color': 0xFFD9A06A,
        'estado': 'activo',
      });
      return 'Proyecto creado';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Campo('Nombre', _nombre, pista: 'Ashur'),
        Campo('Descripción', _descripcion, lineas: 3),
        Campo('Stack', _stack, pista: 'Flutter, Python, SQLite'),
        Campo('Repositorio', _repo, pista: 'https://github.com/…'),
        const Text('PLATAFORMAS', style: wbEtiqueta),
        const SizedBox(height: 6),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final p in plataformas)
              Ficha(
                p,
                elegida: _plataformas.contains(p),
                alTocar: () => setState(() {
                  if (!_plataformas.remove(p)) _plataformas.add(p);
                }),
              ),
          ],
        ),
        const SizedBox(height: 14),
        PieHoja(texto: 'Crear proyecto', alGuardar: _nombre.text.trim().isEmpty ? null : _crear),
      ],
    );
  }
}
