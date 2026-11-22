// Una conversación con Ashur. La respuesta no es inmediata: mientras un nodo la prepara, la pantalla pregunta al core
// cada pocos segundos (docs/adr/0016-chat-y-nodos.md, docs/adr/0023-chat-en-la-app.md).
import 'dart:async';

// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

import '../conexion/cliente.dart';
import '../pantallas.dart';
import 'pantalla_chats.dart' show textoError;

final _decoracionCampo = BoxDecoration(
  color: const Color(0xFF141622),
  border: Border.all(color: const Color(0x33FFFFFF)),
  borderRadius: BorderRadius.circular(8),
);
const _estiloCampo = TextStyle(color: colorTexto, fontSize: 15);
const _estiloPista = TextStyle(color: Color(0x80E8E8F0), fontSize: 14);

/// Si la respuesta sigue abierta: hay espera y no falló. Un trabajo fallido ya no avanza.
bool esperaAbierta(Map<String, dynamic>? espera) => espera != null && espera['estado'] != 'fallido';

/// En qué va la respuesta de Ashur, para la persona.
String textoEspera(Map<String, dynamic> espera) => switch (espera['estado']) {
      'pendiente' => 'Esperando a que un equipo tome el mensaje…',
      'tomado' => 'Ashur está respondiendo${espera['modelo'] == null ? '' : ' con ${espera['modelo']}'}…',
      'fallido' => 'Ashur no pudo responder: ${espera['error'] ?? 'sin detalle'}. Puedes escribir de nuevo.',
      _ => 'Esperando…',
    };

class PantallaConversacion extends StatefulWidget {
  const PantallaConversacion({
    super.key,
    required this.cliente,
    required this.id,
    this.intervalo = const Duration(seconds: 2),
  });

  final ClienteCore cliente;
  final String id;

  /// Cada cuánto se pregunta por la respuesta mientras está abierta.
  final Duration intervalo;

  @override
  State<PantallaConversacion> createState() => _PantallaConversacionState();
}

class _PantallaConversacionState extends State<PantallaConversacion> {
  final _texto = TextEditingController();
  List<Map<String, dynamic>> _mensajes = [];
  Map<String, dynamic>? _espera;
  String? _titulo;
  String? _error;
  bool _enviando = false;
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    _actualizar();
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _texto.dispose();
    super.dispose();
  }

  void _mostrar(Map<String, dynamic> completa) {
    setState(() {
      _mensajes = (completa['mensajes'] as List).cast<Map<String, dynamic>>();
      _espera = completa['espera'] as Map<String, dynamic>?;
      _titulo = (completa['conversacion'] as Map<String, dynamic>)['titulo'] as String?;
      _error = null;
    });
    _reloj?.cancel();
    _reloj = esperaAbierta(_espera) ? Timer(widget.intervalo, _actualizar) : null;
  }

  Future<void> _actualizar() async {
    try {
      final completa = await widget.cliente.verConversacion(widget.id);
      if (!mounted) return;
      _mostrar(completa);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = textoError(e));
      // Un corte de red no debe dejar la respuesta sin llegar: se vuelve a preguntar.
      if (esperaAbierta(_espera)) _reloj = Timer(widget.intervalo, _actualizar);
    }
  }

  Future<void> _enviar() async {
    final texto = _texto.text.trim();
    if (texto.isEmpty) return;
    setState(() => _enviando = true);
    try {
      final completa = await widget.cliente.enviarMensaje(widget.id, texto);
      if (!mounted) return;
      _texto.clear();
      _mostrar(completa);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = textoError(e));
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  Widget _burbuja(Map<String, dynamic> mensaje) {
    final deSergio = mensaje['rol'] == 'user';
    return Align(
      alignment: deSergio ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 520),
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: deSergio ? const Color(0xFF24345C) : const Color(0xFF141622),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(mensaje['texto'] as String, style: _estiloCampo),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bloqueado = _enviando || esperaAbierta(_espera);
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
                  Expanded(
                    child: Text(
                      _titulo == null || _titulo!.isEmpty ? 'Conversación nueva' : _titulo!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: ListView(
                  reverse: true, // lo último queda abajo, junto al campo
                  children: [for (final m in _mensajes.reversed) _burbuja(m)],
                ),
              ),
              if (_espera != null) ...[
                const SizedBox(height: 6),
                Text(textoEspera(_espera!), style: _estiloPista),
              ],
              if (_error != null) ...[
                const SizedBox(height: 6),
                Text(_error!, style: const TextStyle(color: Color(0xFFFF8A8A), fontSize: 14)),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: CupertinoTextField(
                      controller: _texto,
                      enabled: !bloqueado,
                      placeholder: 'Escríbele a Ashur',
                      minLines: 1,
                      maxLines: 4,
                      decoration: _decoracionCampo,
                      style: _estiloCampo,
                      placeholderStyle: _estiloPista,
                    ),
                  ),
                  CupertinoButton(
                    padding: const EdgeInsets.only(left: 12),
                    onPressed: bloqueado ? null : _enviar,
                    child: const Text('Enviar'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
