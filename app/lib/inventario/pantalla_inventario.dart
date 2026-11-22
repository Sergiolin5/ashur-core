// Pantalla Inventario: lista de objetos físicos, creación y edición (docs/adr/0014-inventario.md, docs/adr/0015-inventario-en-la-app.md).
// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

import '../conexion/cliente.dart';
import '../conexion/fuente.dart';
import '../pantallas.dart';
import 'objeto.dart';

final _decoracionCampo = BoxDecoration(
  color: const Color(0xFF141622),
  border: Border.all(color: const Color(0x33FFFFFF)),
  borderRadius: BorderRadius.circular(8),
);

final _decoracionTarjeta = BoxDecoration(
  color: const Color(0xFF141622),
  border: Border.all(color: const Color(0x33FFFFFF)),
  borderRadius: BorderRadius.circular(8),
);

const _estiloCampo = TextStyle(color: colorTexto, fontSize: 15);
const _estiloPista = TextStyle(color: Color(0x80E8E8F0), fontSize: 15);

class PantallaInventario extends StatefulWidget {
  const PantallaInventario({super.key, required this.fuente, this.cliente});

  final FuenteGalaxia fuente;
  final ClienteCore? cliente;

  @override
  State<PantallaInventario> createState() => _PantallaInventarioState();
}

class _PantallaInventarioState extends State<PantallaInventario> {
  final _nombreController = TextEditingController();
  final _lugarController = TextEditingController();
  final _controladorRenombrar = TextEditingController();
  final _controladorMover = TextEditingController();

  ClienteCore? _clienteActual;
  List<Objeto> _objetos = [];
  bool _cargando = true;
  bool _guardando = false;
  bool _verArchivados = false;
  bool _sinConfigurar = false;
  bool _tieneAdmin = false;
  String? _error;
  String? _renombrandoId;
  String? _moviendoId;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _nombreController.dispose();
    _lugarController.dispose();
    _controladorRenombrar.dispose();
    _controladorMover.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    if (!mounted) return;
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final c = widget.cliente ?? await widget.fuente.cliente();
      if (!mounted) return;
      if (c == null) {
        setState(() {
          _cargando = false;
          _sinConfigurar = true;
          _objetos = [];
        });
        return;
      }
      _clienteActual = c;
      final lista = await c.listarObjetos(archivados: _verArchivados);
      final admin = c.claveAdmin != null && c.claveAdmin!.isNotEmpty;
      if (!mounted) return;
      setState(() {
        _objetos = lista;
        _tieneAdmin = admin;
        _cargando = false;
        _sinConfigurar = false;
      });
    } on ErrorCore catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(e);
        _cargando = false;
        _objetos = [];
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Error inesperado: $e';
        _cargando = false;
        _objetos = [];
      });
    }
  }

  String _mensajeError(ErrorCore e) => switch (e.fallo) {
        FalloCore.inalcanzable =>
          'No se pudo llegar al core. Revisa la dirección y que Tailscale esté encendido. ${e.detalle}',
        FalloCore.claveInvalida =>
          'El core rechazó la clave. Revisa que sea correcta en la pestaña Estado.',
        FalloCore.noExiste => 'El objeto no existe.',
        FalloCore.conflicto => 'El objeto no está disponible.',
        FalloCore.datosInvalidos => 'Datos inválidos. Revisa el nombre y el lugar.',
        FalloCore.coreSinClave => 'El core no tiene configurada esa clave.',
        FalloCore.otro => 'El core respondió algo inesperado. ${e.detalle}',
      };

  Future<void> _crearObjeto() async {
    final nombre = _nombreController.text.trim();
    if (nombre.isEmpty) return;
    final lugar = _lugarController.text.trim();
    final c = _clienteActual ?? widget.cliente ?? await widget.fuente.cliente();
    if (c == null || !mounted) return;
    setState(() => _guardando = true);
    try {
      await c.crearObjeto(nombre, lugar.isEmpty ? null : lugar);
      if (!mounted) return;
      _nombreController.clear();
      _lugarController.clear();
      await widget.fuente.actualizar();
      await _cargar();
    } on ErrorCore catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(e);
        _guardando = false;
      });
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Future<void> _guardarRenombrar(Objeto objeto) async {
    final nuevo = _controladorRenombrar.text.trim();
    if (nuevo.isEmpty || nuevo == objeto.nombre) {
      setState(() => _renombrandoId = null);
      return;
    }
    final c = _clienteActual ?? widget.cliente ?? await widget.fuente.cliente();
    if (c == null || !mounted) return;
    setState(() => _guardando = true);
    try {
      await c.editarObjeto(objeto.id, {'nombre': nuevo});
      _renombrandoId = null;
      await _cargar();
    } on ErrorCore catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(e);
        _guardando = false;
      });
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Future<void> _guardarMover(Objeto objeto) async {
    final nuevo = _controladorMover.text.trim();
    final lugarFinal = nuevo.isEmpty ? null : nuevo;
    if (lugarFinal == objeto.lugar) {
      setState(() => _moviendoId = null);
      return;
    }
    final c = _clienteActual ?? widget.cliente ?? await widget.fuente.cliente();
    if (c == null || !mounted) return;
    setState(() => _guardando = true);
    try {
      await c.editarObjeto(objeto.id, {'lugar': lugarFinal});
      _moviendoId = null;
      await _cargar();
    } on ErrorCore catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(e);
        _guardando = false;
      });
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Future<void> _cambiarArchivado(Objeto objeto, bool archivado) async {
    final c = _clienteActual ?? widget.cliente ?? await widget.fuente.cliente();
    if (c == null || !mounted) return;
    setState(() => _guardando = true);
    try {
      await c.editarObjeto(objeto.id, {'archivado': archivado});
      await widget.fuente.actualizar();
      await _cargar();
    } on ErrorCore catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(e);
        _guardando = false;
      });
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Widget _tarjetaObjeto(Objeto objeto) {
    final sinLugar = objeto.lugar == null || objeto.lugar!.trim().isEmpty;
    final textoLugar = sinLugar ? 'Sin lugar' : objeto.lugar!;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: _decoracionTarjeta,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            objeto.nombre,
            style: const TextStyle(color: colorTexto, fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          Text(
            textoLugar,
            style: const TextStyle(color: Color(0x80E8E8F0), fontSize: 14),
          ),
          if (objeto.archivado) ...[
            const SizedBox(height: 2),
            const Text('(Archivado)', style: TextStyle(color: Color(0x80E8E8F0), fontSize: 12)),
          ],
          if (_tieneAdmin) ...[
            const SizedBox(height: 8),
            if (_renombrandoId == objeto.id) ...[
              CupertinoTextField(
                controller: _controladorRenombrar,
                placeholder: 'Nuevo nombre',
                decoration: _decoracionCampo,
                style: _estiloCampo,
                placeholderStyle: _estiloPista,
              ),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  CupertinoButton(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    onPressed: () => setState(() => _renombrandoId = null),
                    child: const Text('Cancelar'),
                  ),
                  CupertinoButton.filled(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    onPressed: _guardando ? null : () => _guardarRenombrar(objeto),
                    child: const Text('Guardar'),
                  ),
                ],
              ),
            ] else if (_moviendoId == objeto.id) ...[
              CupertinoTextField(
                controller: _controladorMover,
                placeholder: 'Lugar (vacío para sin lugar)',
                decoration: _decoracionCampo,
                style: _estiloCampo,
                placeholderStyle: _estiloPista,
              ),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  CupertinoButton(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    onPressed: () => setState(() => _moviendoId = null),
                    child: const Text('Cancelar'),
                  ),
                  CupertinoButton.filled(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    onPressed: _guardando ? null : () => _guardarMover(objeto),
                    child: const Text('Guardar'),
                  ),
                ],
              ),
            ] else ...[
              Row(
                children: [
                  CupertinoButton(
                    padding: const EdgeInsets.only(right: 12),
                    onPressed: () {
                      setState(() {
                        _renombrandoId = objeto.id;
                        _moviendoId = null;
                        _controladorRenombrar.text = objeto.nombre;
                      });
                    },
                    child: const Text('Renombrar'),
                  ),
                  CupertinoButton(
                    padding: const EdgeInsets.only(right: 12),
                    onPressed: () {
                      setState(() {
                        _moviendoId = objeto.id;
                        _renombrandoId = null;
                        _controladorMover.text = objeto.lugar ?? '';
                      });
                    },
                    child: const Text('Mover'),
                  ),
                  const Spacer(),
                  CupertinoButton(
                    padding: EdgeInsets.zero,
                    onPressed: _guardando ? null : () => _cambiarArchivado(objeto, !objeto.archivado),
                    child: Text(objeto.archivado ? 'Restaurar' : 'Archivar'),
                  ),
                ],
              ),
            ],
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: colorFondo,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => Navigator.of(context).pop(),
                    child: const Padding(
                      padding: EdgeInsets.only(right: 16),
                      child: Text('‹', style: TextStyle(fontSize: 28)),
                    ),
                  ),
                  const Text('Inventario', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                children: [
                  if (_error != null) ...[
                    Text(_error!, style: const TextStyle(color: Color(0xFFFF8A8A), fontSize: 14)),
                    const SizedBox(height: 12),
                  ],
                  if (_sinConfigurar) ...[
                    const Text('Todavía no hay un core configurado.',
                        style: TextStyle(color: Color(0x80E8E8F0), fontSize: 14)),
                    const SizedBox(height: 12),
                  ],
                  if (!_tieneAdmin && !_sinConfigurar) ...[
                    const Text(
                      'Hace falta la clave de administrador en la pestaña Estado.',
                      style: TextStyle(color: Color(0x80E8E8F0), fontSize: 13),
                    ),
                    const SizedBox(height: 12),
                  ],
                  Row(
                    children: [
                      const Text('Ver archivados', style: TextStyle(color: colorTexto, fontSize: 15)),
                      const Spacer(),
                      CupertinoSwitch(
                        value: _verArchivados,
                        onChanged: (valor) {
                          setState(() => _verArchivados = valor);
                          _cargar();
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Nuevo objeto', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  CupertinoTextField(
                    controller: _nombreController,
                    placeholder: 'Nombre',
                    decoration: _decoracionCampo,
                    style: _estiloCampo,
                    placeholderStyle: _estiloPista,
                  ),
                  const SizedBox(height: 8),
                  CupertinoTextField(
                    controller: _lugarController,
                    placeholder: 'Lugar (opcional)',
                    decoration: _decoracionCampo,
                    style: _estiloCampo,
                    placeholderStyle: _estiloPista,
                  ),
                  const SizedBox(height: 8),
                  CupertinoButton.filled(
                    onPressed: _guardando ? null : _crearObjeto,
                    child: const Text('Crear objeto'),
                  ),
                  const SizedBox(height: 20),
                  const Text('Objetos', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  if (_cargando)
                    const Center(child: Padding(padding: EdgeInsets.all(16), child: Text('Cargando…')))
                  else if (_objetos.isEmpty)
                    const Text('No hay objetos.', style: TextStyle(color: Color(0x80E8E8F0)))
                  else
                    for (final objeto in _objetos) ...[
                      _tarjetaObjeto(objeto),
                      const SizedBox(height: 12),
                    ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
