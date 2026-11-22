// Pantalla Chats: las conversaciones con Ashur. Se abre tocando el núcleo (docs/adr/0023-chat-en-la-app.md).
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

import '../conexion/cliente.dart';
import '../conexion/fuente.dart';
import '../pantallas.dart';
import 'pantalla_conversacion.dart';

final _decoracionTarjeta = BoxDecoration(
  color: const Color(0xFF141622),
  border: Border.all(color: const Color(0x33FFFFFF)),
  borderRadius: BorderRadius.circular(8),
);
const _estiloPista = TextStyle(color: Color(0x80E8E8F0), fontSize: 14);

/// El texto que se muestra cuando no hay cliente: sin core, o con las claves bloqueadas por Face ID.
String textoSinCliente(FuenteGalaxia fuente) => fuente.estado == EstadoConexion.bloqueada
    ? 'Las claves están bloqueadas: desbloquéalas con Face ID en la pestaña Estado.'
    : 'Todavía no hay un core configurado.';

/// El mensaje para la persona cuando falla una llamada al core.
String textoError(Object error) {
  if (error is ErrorCore) {
    return switch (error.fallo) {
      FalloCore.inalcanzable => 'No se pudo llegar al core. ${error.detalle}',
      FalloCore.claveInvalida => 'El core rechazó la clave.',
      FalloCore.conflicto => error.detalle.isEmpty ? 'Ashur todavía está respondiendo.' : error.detalle,
      _ => 'El core respondió algo inesperado. ${error.detalle}',
    };
  }
  return 'Algo falló: $error';
}

class PantallaChats extends StatefulWidget {
  const PantallaChats({super.key, required this.fuente, this.cliente});

  final FuenteGalaxia fuente;

  /// Para las pruebas; en la app sale de [fuente].
  final ClienteCore? cliente;

  @override
  State<PantallaChats> createState() => _PantallaChatsState();
}

class _PantallaChatsState extends State<PantallaChats> {
  ClienteCore? _cliente;
  List<Map<String, dynamic>> _conversaciones = [];
  bool _cargando = true;
  bool _creando = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final c = widget.cliente ?? await widget.fuente.cliente();
      if (!mounted) return;
      if (c == null) {
        setState(() => _cargando = false);
        return;
      }
      final lista = await c.listarConversaciones();
      if (!mounted) return;
      setState(() {
        _cliente = c;
        _conversaciones = lista;
        _cargando = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _cargando = false;
        _error = textoError(e);
      });
    }
  }

  Future<void> _abrir(String id) async {
    final c = _cliente;
    if (c == null) return;
    await Navigator.of(context).push(rutaSimple(PantallaConversacion(cliente: c, id: id)));
    if (mounted) await _cargar(); // el título y el orden cambian al escribir
  }

  Future<void> _nueva() async {
    final c = _cliente;
    if (c == null) return;
    setState(() => _creando = true);
    try {
      final conversacion = await c.crearConversacion();
      if (!mounted) return;
      setState(() => _creando = false);
      await _abrir(conversacion['id'] as String);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _creando = false;
        _error = textoError(e);
      });
    }
  }

  Widget _tarjeta(Map<String, dynamic> conversacion) {
    final titulo = conversacion['titulo'] as String?;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => _abrir(conversacion['id'] as String),
      child: Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 10),
        decoration: _decoracionTarjeta,
        child: Text(
          titulo == null || titulo.isEmpty ? 'Conversación nueva' : titulo,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: colorTexto, fontSize: 16),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: colorFondo,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => Navigator.of(context).pop(),
                    child: const Padding(
                      padding: EdgeInsets.only(right: 16),
                      child: Text('‹', style: TextStyle(fontSize: 28)),
                    ),
                  ),
                  const Text('Chats', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 16),
              if (_cargando) const Text('Cargando…', style: _estiloPista),
              if (!_cargando && _cliente == null && _error == null)
                Text(textoSinCliente(widget.fuente), style: _estiloPista),
              if (_error != null) ...[
                Text(_error!, style: const TextStyle(color: Color(0xFFFF8A8A), fontSize: 14)),
                const SizedBox(height: 12),
              ],
              if (_cliente != null) ...[
                CupertinoButton.filled(
                  onPressed: _creando ? null : _nueva,
                  child: const Text('Nueva conversación'),
                ),
                const SizedBox(height: 16),
                if (_conversaciones.isEmpty) const Text('Todavía no hay conversaciones.', style: _estiloPista),
                Expanded(
                  child: ListView(children: [for (final c in _conversaciones) _tarjeta(c)]),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
