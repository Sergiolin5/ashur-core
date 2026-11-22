// El chat con Ashur (docs/adr/0014-chat.md).
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

import '../pantallas.dart';
import 'cliente.dart';
import 'fuente.dart';

class PantallaChat extends StatefulWidget {
  const PantallaChat({super.key, required this.fuente});

  final FuenteGalaxia fuente;

  @override
  State<PantallaChat> createState() => _PantallaChatState();
}

class _PantallaChatState extends State<PantallaChat> {
  final _texto = TextEditingController();
  final _desplazamiento = ScrollController();
  List<MensajeChat> _mensajes = [];
  String? _aviso;
  bool _esperando = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _texto.dispose();
    _desplazamiento.dispose();
    super.dispose();
  }

  String _explicar(ErrorCore e) => switch (e.fallo) {
        FalloCore.inalcanzable => 'No se pudo llegar al core. Revisa Tailscale.',
        FalloCore.claveInvalida => 'El core rechazó la clave.',
        FalloCore.coreSinClave => e.detalle.isEmpty ? 'El core no puede responder ahora.' : e.detalle,
        FalloCore.otro => 'El core respondió algo inesperado. ${e.detalle}',
      };

  Future<void> _cargar() async {
    final cliente = await widget.fuente.cliente();
    if (cliente == null) {
      setState(() => _aviso = 'Configura el core en Estado para hablar con Ashur.');
      return;
    }
    try {
      final mensajes = await cliente.chat();
      setState(() => _mensajes = mensajes);
      _bajar();
    } on ErrorCore catch (e) {
      setState(() => _aviso = _explicar(e));
    }
  }

  Future<void> _enviar() async {
    final texto = _texto.text.trim();
    final cliente = await widget.fuente.cliente();
    if (texto.isEmpty || cliente == null || _esperando) return;
    setState(() {
      _esperando = true;
      _aviso = null;
      _mensajes = [..._mensajes, MensajeChat(id: -1, deAshur: false, texto: texto)];
      _texto.clear();
    });
    _bajar();
    try {
      await cliente.hablar(texto);
      _mensajes = await cliente.chat();
      widget.fuente.actualizar(); // los recuerdos nuevos hacen crecer el polvo
    } on ErrorCore catch (e) {
      _aviso = _explicar(e);
    }
    if (mounted) setState(() => _esperando = false);
    _bajar();
  }

  void _bajar() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_desplazamiento.hasClients) _desplazamiento.jumpTo(_desplazamiento.position.maxScrollExtent);
      });

  Widget _burbuja(MensajeChat m) => Align(
        alignment: m.deAshur ? Alignment.centerLeft : Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          constraints: const BoxConstraints(maxWidth: 300),
          decoration: BoxDecoration(
            color: m.deAshur ? const Color(0xFF1B1E2C) : const Color(0xFF2B3A6B),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Text(m.texto),
        ),
      );

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
              Row(children: [
                GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => Navigator.of(context).pop(),
                  child: const Padding(
                    padding: EdgeInsets.only(right: 16),
                    child: Text('‹', style: TextStyle(fontSize: 28)),
                  ),
                ),
                const Text('Ashur', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
              ]),
              const SizedBox(height: 8),
              Expanded(
                child: ListView(controller: _desplazamiento, children: [
                  for (final m in _mensajes) _burbuja(m),
                  if (_esperando) const Padding(padding: EdgeInsets.all(8), child: Text('Ashur está pensando…')),
                ]),
              ),
              if (_aviso != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Text(_aviso!, style: const TextStyle(color: Color(0xFFE7B66B))),
                ),
              Row(children: [
                Expanded(
                  child: CupertinoTextField(
                    controller: _texto,
                    placeholder: 'Escríbele a Ashur',
                    onSubmitted: (_) => _enviar(),
                    decoration: BoxDecoration(
                      color: const Color(0xFF141622),
                      border: Border.all(color: const Color(0x33FFFFFF)),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    style: const TextStyle(color: colorTexto, fontSize: 15),
                    placeholderStyle: const TextStyle(color: Color(0x80E8E8F0), fontSize: 15),
                  ),
                ),
                CupertinoButton(
                  padding: const EdgeInsets.only(left: 10),
                  onPressed: _esperando ? null : _enviar,
                  child: const Text('Enviar'),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}
