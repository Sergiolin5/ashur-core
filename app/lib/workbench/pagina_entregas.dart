// Entregas: cada versión recorre cuatro pasos (guardar, compilar, firmar, publicar).
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'piezas.dart';

class PaginaEntregas extends StatefulWidget {
  const PaginaEntregas({super.key, required this.datos});

  final DatosWorkbench datos;

  @override
  State<PaginaEntregas> createState() => _PaginaEntregasState();
}

class _PaginaEntregasState extends State<PaginaEntregas> {
  String? _compilando;
  final _registrosAbiertos = <String>{};

  DatosWorkbench get _datos => widget.datos;

  Future<void> _cambiarPaso(Registro entrega, String paso) => _datos.hacer(() async {
        final hecho = entrega[paso] != true;
        await _datos.almacen.editar(tipoEntregas, entrega['id'] as String, {
          paso: hecho,
          if (paso == 'publicada') ...{
            'estado': hecho ? 'publicada' : 'lista',
            'publicada_el': hecho ? DateTime.now().toUtc().toIso8601String() : null,
          },
        });
        return null;
      });

  Future<void> _compilar(Registro entrega) async {
    setState(() => _compilando = entrega['id'] as String);
    await _datos.hacer(() async {
      await _datos.almacen.compilarEntrega(entrega['id'] as String);
      return 'Compilación aceptada por el servidor';
    });
    if (mounted) setState(() => _compilando = null);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Encabezado(
          etiqueta: 'Salida a producción',
          titulo: 'Entregas',
          descripcion: 'Guarda, compila, firma y publica. La compilación se dispara en tu servidor; los pasos '
              'restantes los confirmas tú.',
          acciones: [
            Boton(
              'Nueva entrega',
              principal: true,
              alTocar: () => abrirHoja<void>(
                context,
                titulo: 'Nueva entrega',
                descripcion: 'Abre una versión y recorre sus cuatro pasos hasta publicar.',
                child: _FormularioEntrega(datos: _datos),
              ),
            ),
          ],
        ),
        if (_datos.entregas.isEmpty)
          const Vacio(
            titulo: 'Sin entregas todavía',
            descripcion: 'Crea la primera versión de Ashur para seguir su recorrido hasta producción.',
          ),
        for (final e in _datos.entregas)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: _tarjeta(e),
          ),
      ],
    );
  }

  Widget _tarjeta(Registro e) {
    final id = e['id'] as String;
    final registro = (e['registro'] as String?) ?? '';
    return Tarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text('${e['version']}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
              Pastilla((e['estado'] as String?) ?? 'borrador'),
              Boton(
                _compilando == id ? 'Compilando' : 'Compilar en servidor',
                alTocar: _compilando == null ? () => _compilar(e) : null,
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${_datos.proyecto(e['proyecto_id'])?['nombre'] ?? 'Ashur'} · ${canales[e['canal']] ?? e['canal']}',
            style: wbCuerpo,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final paso in pasosEntrega.entries)
                GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => _cambiarPaso(e, paso.key),
                  child: Container(
                    width: 150,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: e[paso.key] == true ? wbVerde.withValues(alpha: 0.1) : null,
                      border: Border.all(color: e[paso.key] == true ? wbVerde.withValues(alpha: 0.3) : wbBorde),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(paso.value, style: TextStyle(color: e[paso.key] == true ? wbVerde : wbTenue)),
                        const SizedBox(height: 4),
                        Text(e[paso.key] == true ? '✓ HECHO' : 'PENDIENTE', style: wbEtiqueta),
                      ],
                    ),
                  ),
                ),
            ],
          ),
          if (registro.isNotEmpty) ...[
            const SizedBox(height: 12),
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => setState(() {
                if (!_registrosAbiertos.remove(id)) _registrosAbiertos.add(id);
              }),
              child: Text(
                '${_registrosAbiertos.contains(id) ? '▾' : '▸'} REGISTRO DE COMPILACIÓN',
                style: wbEtiqueta,
              ),
            ),
            if (_registrosAbiertos.contains(id))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(registro, style: const TextStyle(color: wbTenue, fontSize: 12, fontFamily: 'Menlo')),
              ),
          ],
          if (e['publicada_el'] != null) ...[
            const SizedBox(height: 10),
            Text('Publicada el ${fechaCorta(e['publicada_el'])}', style: wbCuerpo.copyWith(fontSize: 11)),
          ],
        ],
      ),
    );
  }
}

class _FormularioEntrega extends StatefulWidget {
  const _FormularioEntrega({required this.datos});

  final DatosWorkbench datos;

  @override
  State<_FormularioEntrega> createState() => _FormularioEntregaState();
}

class _FormularioEntregaState extends State<_FormularioEntrega> {
  final _version = TextEditingController();
  String _canal = 'beta';
  String _proyecto = '';

  @override
  void initState() {
    super.initState();
    _version.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _version.dispose();
    super.dispose();
  }

  void _crear() {
    final datos = widget.datos;
    Navigator.of(context).pop();
    datos.hacer(() async {
      await datos.almacen.crear(tipoEntregas, {
        'version': _version.text.trim(),
        'canal': _canal,
        'proyecto_id': _proyecto.isEmpty ? null : _proyecto,
        'estado': 'borrador',
      });
      return 'Entrega creada';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Campo('Versión', _version, pista: 'v1.0.0'),
        Selector('Canal', opciones: canales, valor: _canal, alElegir: (v) => setState(() => _canal = v)),
        Selector(
          'Proyecto',
          opciones: {'': 'Ashur', for (final p in widget.datos.proyectos) p['id'] as String: '${p['nombre']}'},
          valor: _proyecto,
          alElegir: (v) => setState(() => _proyecto = v),
        ),
        PieHoja(texto: 'Crear entrega', alGuardar: _version.text.trim().isEmpty ? null : _crear),
      ],
    );
  }
}
