// Servidor: la conexión al servidor que compila, su estado y sus servicios.
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'piezas.dart';

class PaginaServidor extends StatefulWidget {
  const PaginaServidor({super.key, required this.datos});

  final DatosWorkbench datos;

  @override
  State<PaginaServidor> createState() => _PaginaServidorState();
}

class _PaginaServidorState extends State<PaginaServidor> {
  late final Registro? _inicial = widget.datos.servidor;
  late final _nombre = TextEditingController(text: (_inicial?['nombre'] as String?) ?? 'ZimaOS');
  late final _url = TextEditingController(text: _inicial?['url'] as String?);
  late final _salud = TextEditingController(text: (_inicial?['ruta_salud'] as String?) ?? '/');
  late final _compilacion = TextEditingController(text: _inicial?['ruta_compilacion'] as String?);
  late final _servicios = TextEditingController(text: ((_inicial?['servicios'] as List?) ?? const []).join(', '));
  late final _notas = TextEditingController(text: _inicial?['notas'] as String?);
  bool _probando = false;

  DatosWorkbench get _datos => widget.datos;

  @override
  void dispose() {
    for (final c in [_nombre, _url, _salud, _compilacion, _servicios, _notas]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _guardar() => _datos.hacer(() async {
        final registro = <String, dynamic>{
          'nombre': _nombre.text.trim().isEmpty ? 'ZimaOS' : _nombre.text.trim(),
          'url': _url.text.trim().replaceFirst(RegExp(r'/+$'), ''),
          'ruta_salud': _salud.text.trim().isEmpty ? '/' : _salud.text.trim(),
          'ruta_compilacion': _compilacion.text.trim(),
          'servicios': [
            for (final s in _servicios.text.split(','))
              if (s.trim().isNotEmpty) s.trim(),
          ],
          'notas': _notas.text.trim(),
        };
        final actual = _datos.servidor;
        if (actual == null) {
          await _datos.almacen.crear(tipoServidores, registro);
        } else {
          await _datos.almacen.editar(tipoServidores, actual['id'] as String, registro);
        }
        return 'Servidor guardado';
      });

  Future<void> _probar() async {
    final actual = _datos.servidor;
    if (actual == null) {
      await _datos.hacer(() async => throw const ErrorWorkbench('Guarda la configuración antes de probar'));
      return;
    }
    setState(() => _probando = true);
    await _datos.hacer(() async {
      final s = await _datos.almacen.probarServidor(actual['id'] as String);
      if (s['estado'] == 'en_linea') return 'En línea · ${s['latencia_ms']} ms';
      throw ErrorWorkbench('Sin respuesta: ${s['detalle'] ?? 'revisa la URL'}');
    });
    if (mounted) setState(() => _probando = false);
  }

  @override
  Widget build(BuildContext context) {
    final s = _datos.servidor;
    final servicios = (s?['servicios'] as List?) ?? const [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Encabezado(
          etiqueta: 'Infraestructura',
          titulo: 'Servidor',
          descripcion: 'Aquí vive tu centro de desarrollo. Workbench comprueba que responde y le envía las '
              'compilaciones de Ashur.',
          acciones: [
            Boton(_probando ? 'Probando' : 'Probar conexión', alTocar: _probando ? null : _probar),
            Boton('Guardar', principal: true, alTocar: _guardar),
          ],
        ),
        Seccion(
          etiqueta: 'Conexión',
          titulo: 'Datos del servidor',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Campo('Nombre', _nombre),
              Campo('URL base', _url, pista: 'http://servidor:8720'),
              Campo('Ruta de salud', _salud, pista: '/'),
              Campo('Ruta de compilación', _compilacion, pista: '/hooks/build'),
              Campo('Servicios (separados por comas)', _servicios, pista: 'Docker, Ollama, Gitea'),
              Campo('Notas', _notas, pista: 'Puertos, túneles, recordatorios.', lineas: 3),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Seccion(
          etiqueta: 'Estado',
          titulo: (s?['url'] as String?)?.isNotEmpty == true ? s!['url'] as String : 'Sin URL',
          accion: Pastilla((s?['estado'] as String?) ?? 'sin_probar'),
          child: Column(
            children: [
              Dato('Latencia', s?['latencia_ms'] == null ? '—' : '${s!['latencia_ms']} ms'),
              Dato('Última prueba', s?['ultima_prueba'] == null ? 'Nunca' : fechaCorta(s!['ultima_prueba'])),
              Dato('Detalle', (s?['detalle'] as String?) ?? '—'),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Seccion(
          etiqueta: 'Servicios',
          titulo: 'Lo que corre en el servidor',
          child: servicios.isEmpty
              ? const Text('Añade los servicios que corren en tu servidor.', style: wbCuerpo)
              : Wrap(spacing: 6, runSpacing: 6, children: [for (final x in servicios) Ficha('$x')]),
        ),
      ],
    );
  }
}
