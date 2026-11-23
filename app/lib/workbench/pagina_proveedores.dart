// Proveedores: los modelos y agentes que ejecutan las tareas, con su plan y su cuota.
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'piezas.dart';

class PaginaProveedores extends StatelessWidget {
  const PaginaProveedores({super.key, required this.datos});

  final DatosWorkbench datos;

  void _editar(BuildContext context, Registro? proveedor) => abrirHoja<void>(
        context,
        titulo: proveedor == null ? 'Nuevo proveedor' : 'Editar proveedor',
        descripcion: 'Define el modelo que ejecuta las tareas y cuántas ejecuciones te quedan en el periodo.',
        child: _FormularioProveedor(datos: datos, proveedor: proveedor),
      );

  @override
  Widget build(BuildContext context) {
    final lista = datos.proveedores;
    final cuota = lista.fold<num>(0, (s, p) => s + ((p['cuota'] as num?) ?? 0));
    final usadas = lista.fold<num>(0, (s, p) => s + ((p['usadas'] as num?) ?? 0));
    final libre = cuota > 0 ? ((cuota - usadas) / cuota * 100).clamp(0, 100).round() : 0;
    final activos = lista.where((p) => p['estado'] == 'activo').length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Encabezado(
          etiqueta: 'Modelos y agentes',
          titulo: 'Proveedores',
          descripcion: 'Reparte el trabajo según lo que te queda de cada plan. Las tareas se ejecutan con el modelo '
              'asignado a cada proveedor.',
          acciones: [Boton('Añadir proveedor', principal: true, alTocar: () => _editar(context, null))],
        ),
        Tarjeta(
          child: Row(
            children: [
              Expanded(child: _Resumen('Cuota libre', '$libre%')),
              Expanded(child: _Resumen('Ejecuciones usadas', '$usadas / $cuota')),
              Expanded(child: _Resumen('Activos', '$activos de ${lista.length}')),
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (lista.isEmpty)
          const Vacio(
            titulo: 'Todavía no hay proveedores',
            descripcion: 'Añade Claude, GPT, Gemini o Copilot para empezar a repartir tareas.',
          ),
        LayoutBuilder(
          builder: (context, limites) {
            final columnas = limites.maxWidth >= 900 ? 3 : (limites.maxWidth >= 560 ? 2 : 1);
            final ancho = (limites.maxWidth - 12 * (columnas - 1)) / columnas;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                for (final p in lista)
                  SizedBox(width: ancho, child: _TarjetaProveedor(p, alEditar: () => _editar(context, p))),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _Resumen extends StatelessWidget {
  const _Resumen(this.etiqueta, this.valor);

  final String etiqueta;
  final String valor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(etiqueta.toUpperCase(), style: wbEtiqueta),
        const SizedBox(height: 6),
        Text(valor, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _TarjetaProveedor extends StatelessWidget {
  const _TarjetaProveedor(this.proveedor, {required this.alEditar});

  final Registro proveedor;
  final VoidCallback alEditar;

  @override
  Widget build(BuildContext context) {
    final p = proveedor;
    final color = Color((p['color'] as int?) ?? 0xFF9C9A8E);
    final nombre = (p['nombre'] as String?) ?? '?';
    final fortalezas = (p['fortalezas'] as List?) ?? const [];
    final libre = cuotaLibre(p);
    return Tarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  (nombre.length > 2 ? nombre.substring(0, 2) : nombre).toUpperCase(),
                  style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(nombre, overflow: TextOverflow.ellipsis),
                    Text(
                      '${familias[p['familia']] ?? p['familia']} · ${p['plan'] == 'pro' ? 'Pro' : 'Libre'}',
                      style: wbCuerpo.copyWith(fontSize: 11),
                    ),
                  ],
                ),
              ),
              Pastilla((p['estado'] as String?) ?? 'activo'),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              const Expanded(child: Text('CUOTA DEL PERIODO', style: wbEtiqueta)),
              Text('${p['usadas'] ?? 0}/${p['cuota'] ?? 0}', style: wbCuerpo),
            ],
          ),
          const SizedBox(height: 6),
          BarraCuota(
            usadas: (p['usadas'] as num?) ?? 0,
            cuota: (p['cuota'] as num?) ?? 0,
            pausado: p['estado'] == 'pausado',
          ),
          const SizedBox(height: 6),
          Text(libre > 0 ? '$libre ejecuciones disponibles' : 'Cuota agotada', style: wbCuerpo.copyWith(fontSize: 11)),
          const SizedBox(height: 12),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final f in fortalezas.take(3)) Ficha('$f'),
              if (fortalezas.isEmpty) Ficha('${p['modelo']}'),
            ],
          ),
          const SizedBox(height: 12),
          Align(alignment: Alignment.centerLeft, child: Boton('Editar', alTocar: alEditar)),
        ],
      ),
    );
  }
}

class _FormularioProveedor extends StatefulWidget {
  const _FormularioProveedor({required this.datos, this.proveedor});

  final DatosWorkbench datos;
  final Registro? proveedor;

  @override
  State<_FormularioProveedor> createState() => _FormularioProveedorState();
}

class _FormularioProveedorState extends State<_FormularioProveedor> {
  late final Registro? _p = widget.proveedor;
  late final _nombre = TextEditingController(text: _p?['nombre'] as String?);
  late final _modelo = TextEditingController(text: _p?['modelo'] as String?);
  late final _cuota = TextEditingController(text: '${_p?['cuota'] ?? 100}');
  late final _usadas = TextEditingController(text: '${_p?['usadas'] ?? 0}');
  late final _fortalezas = TextEditingController(text: ((_p?['fortalezas'] as List?) ?? const []).join(', '));
  late final _notas = TextEditingController(text: _p?['notas'] as String?);
  late String _familia = (_p?['familia'] as String?) ?? 'claude';
  late String _plan = (_p?['plan'] as String?) ?? 'libre';
  late String _estado = (_p?['estado'] as String?) ?? 'activo';

  @override
  void initState() {
    super.initState();
    _nombre.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    for (final c in [_nombre, _modelo, _cuota, _usadas, _fortalezas, _notas]) {
      c.dispose();
    }
    super.dispose();
  }

  void _guardar() {
    final datos = widget.datos;
    final registro = <String, dynamic>{
      'nombre': _nombre.text.trim(),
      'familia': _familia,
      'modelo': _modelo.text.trim(),
      'plan': _plan,
      'cuota': int.tryParse(_cuota.text.trim()) ?? 0,
      'usadas': int.tryParse(_usadas.text.trim()) ?? 0,
      'estado': _estado,
      'color': coloresFamilia[_familia],
      'fortalezas': [
        for (final f in _fortalezas.text.split(','))
          if (f.trim().isNotEmpty) f.trim(),
      ],
      'notas': _notas.text.trim(),
    };
    Navigator.of(context).pop();
    datos.hacer(() async {
      if (_p == null) {
        await datos.almacen.crear(tipoProveedores, registro);
        return 'Proveedor añadido';
      }
      await datos.almacen.editar(tipoProveedores, _p['id'] as String, registro);
      return 'Proveedor actualizado';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Campo('Nombre', _nombre, pista: 'Claude'),
        Selector('Familia', opciones: familias, valor: _familia, alElegir: (v) => setState(() => _familia = v)),
        Campo('Modelo', _modelo, pista: 'Identificador del modelo que ejecuta las tareas'),
        Selector(
          'Plan',
          opciones: const {'libre': 'Libre', 'pro': 'Pro'},
          valor: _plan,
          alElegir: (v) => setState(() => _plan = v),
        ),
        Row(
          children: [
            Expanded(child: Campo('Cuota', _cuota, numero: true)),
            const SizedBox(width: 12),
            Expanded(child: Campo('Usadas', _usadas, numero: true)),
          ],
        ),
        Selector(
          'Estado',
          opciones: const {'activo': 'Activo', 'pausado': 'En pausa'},
          valor: _estado,
          alElegir: (v) => setState(() => _estado = v),
        ),
        Campo('Fortalezas', _fortalezas, pista: 'Arquitectura, refactors largos'),
        Campo('Notas', _notas, pista: 'Límites del plan, ventanas de uso, recordatorios.', lineas: 2),
        PieHoja(texto: 'Guardar', alGuardar: _nombre.text.trim().isEmpty ? null : _guardar),
      ],
    );
  }
}
