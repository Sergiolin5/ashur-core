// Pestaña Estado: cómo está la conexión con el core, y dónde se pegan su dirección y su clave.
// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

import '../pantallas.dart';
import 'fuente.dart';

// Campo oscuro, para que el texto claro de la app se lea.
final _decoracionCampo = BoxDecoration(
  color: const Color(0xFF141622),
  border: Border.all(color: const Color(0x33FFFFFF)),
  borderRadius: BorderRadius.circular(8),
);
const _estiloCampo = TextStyle(color: colorTexto, fontSize: 15);
const _estiloPista = TextStyle(color: Color(0x80E8E8F0), fontSize: 15);

class PantallaEstado extends StatefulWidget {
  const PantallaEstado({super.key, required this.fuente});

  final FuenteGalaxia fuente;

  @override
  State<PantallaEstado> createState() => _PantallaEstadoState();
}

class _PantallaEstadoState extends State<PantallaEstado> {
  final _direccion = TextEditingController();
  final _clave = TextEditingController();

  @override
  void initState() {
    super.initState();
    widget.fuente.ajustes().then((ajustes) {
      if (!mounted) return;
      _direccion.text = ajustes.$1 ?? '';
      _clave.text = ajustes.$2 ?? '';
    });
  }

  @override
  void dispose() {
    _direccion.dispose();
    _clave.dispose();
    super.dispose();
  }

  String _texto(FuenteGalaxia f) => switch (f.estado) {
        EstadoConexion.sinConfigurar => 'Todavía no hay un core configurado. La galaxia es de ejemplo.',
        EstadoConexion.conectando => 'Conectando con el core…',
        EstadoConexion.conectado => 'Conectado. La galaxia es la del core: ${f.galaxia?.aprendizaje.recuerdos ?? 0} recuerdos.',
        EstadoConexion.sinConexion =>
          'No se pudo llegar al core. Revisa la dirección y que Tailscale esté encendido. ${f.detalle}',
        EstadoConexion.claveInvalida => 'El core rechazó la clave. Revisa que sea ASHUR_CLAVE.',
        EstadoConexion.coreSinClave => 'El core no tiene ASHUR_CLAVE configurada.',
        EstadoConexion.error => 'El core respondió algo inesperado. ${f.detalle}',
      };

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: colorFondo,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: ListenableBuilder(
            listenable: widget.fuente,
            builder: (context, _) => Column(
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
                    const Text('Estado', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 20),
                Text(_texto(widget.fuente)),
                const SizedBox(height: 24),
                const Text('Dirección del core'),
                const SizedBox(height: 6),
                CupertinoTextField(
                  controller: _direccion,
                  placeholder: 'http://servidor:8720',
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  decoration: _decoracionCampo,
                  style: _estiloCampo,
                  placeholderStyle: _estiloPista,
                ),
                const SizedBox(height: 16),
                const Text('Clave (ASHUR_CLAVE)'),
                const SizedBox(height: 6),
                CupertinoTextField(
                  controller: _clave,
                  obscureText: true,
                  autocorrect: false,
                  decoration: _decoracionCampo,
                  style: _estiloCampo,
                ),
                const SizedBox(height: 20),
                CupertinoButton.filled(
                  onPressed: widget.fuente.estado == EstadoConexion.conectando
                      ? null
                      : () => widget.fuente.guardarAjustes(_direccion.text, _clave.text),
                  child: const Text('Guardar y conectar'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
