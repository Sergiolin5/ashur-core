// Pestaña Estado: cómo está la conexión con el core, y dónde se pegan su dirección y su clave.
// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

import 'package:flutter/services.dart' show Clipboard;

import '../pantallas.dart';
import 'ajustes_avanzados.dart';
import 'fuente.dart';
import 'lo_de_ashur.dart';

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
  final _claveAdmin = TextEditingController();

  @override
  void initState() {
    super.initState();
    widget.fuente.ajustes().then((ajustes) {
      if (!mounted) return;
      _direccion.text = ajustes.$1 ?? '';
      _clave.text = ajustes.$2 ?? '';
      _claveAdmin.text = ajustes.$3 ?? '';
    }, onError: (Object _) {}); // Face ID falló: los campos quedan vacíos para volver a pegar las claves.
  }

  @override
  void dispose() {
    _direccion.dispose();
    _clave.dispose();
    _claveAdmin.dispose();
    super.dispose();
  }

  Future<void> _desbloquear() async {
    await widget.fuente.actualizar();
    if (!mounted || widget.fuente.estado == EstadoConexion.bloqueada) return;
    final ajustes = await widget.fuente.ajustes();
    if (!mounted) return;
    _clave.text = ajustes.$2 ?? '';
    _claveAdmin.text = ajustes.$3 ?? '';
  }

  /// Botón para pegar en un campo lo que hay en el portapapeles: la clave tiene 64 caracteres.
  Widget _pegarEn(TextEditingController campo) => CupertinoButton(
    padding: const EdgeInsets.only(left: 12),
    onPressed: () async {
      final datos = await Clipboard.getData(Clipboard.kTextPlain);
      final texto = datos?.text?.trim();
      if (texto != null && texto.isNotEmpty) campo.text = texto;
    },
    child: const Text('Pegar'),
  );

  String _texto(FuenteGalaxia f) => switch (f.estado) {
    EstadoConexion.sinConfigurar =>
      'Todavía no hay un core configurado. La galaxia es de ejemplo.',
    EstadoConexion.bloqueada =>
      'Las claves están protegidas con Face ID y no se desbloquearon. Desbloquéalas o vuelve a pegarlas.',
    EstadoConexion.conectando => 'Conectando con el core…',
    EstadoConexion.conectado =>
      'Conectado. La galaxia es la del core: ${f.galaxia?.aprendizaje.recuerdos ?? 0} recuerdos.',
    EstadoConexion.sinConexion =>
      'No se pudo llegar al core. Revisa la dirección y que Tailscale esté encendido. ${f.detalle}',
    EstadoConexion.claveInvalida =>
      'El core rechazó la clave. Revisa que sea ASHUR_CLAVE.',
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
          child: SingleChildScrollView(
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
                      const Text(
                        'Estado',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(_texto(widget.fuente)),
                  if (widget.fuente.estado == EstadoConexion.bloqueada)
                    CupertinoButton(
                      padding: const EdgeInsets.only(top: 12),
                      onPressed: _desbloquear,
                      child: const Text('Desbloquear con Face ID'),
                    ),
                  const SizedBox(height: 24),
                  const Text('Dirección del core'),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: CupertinoTextField(
                          controller: _direccion,
                          placeholder: 'http://servidor:8720',
                          keyboardType: TextInputType.url,
                          autocorrect: false,
                          decoration: _decoracionCampo,
                          style: _estiloCampo,
                          placeholderStyle: _estiloPista,
                        ),
                      ),
                      _pegarEn(_direccion),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Clave (ASHUR_CLAVE)'),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: CupertinoTextField(
                          controller: _clave,
                          obscureText: true,
                          autocorrect: false,
                          decoration: _decoracionCampo,
                          style: _estiloCampo,
                        ),
                      ),
                      _pegarEn(_clave),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Clave de administrador (ASHUR_CLAVE_ADMIN)'),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: CupertinoTextField(
                          controller: _claveAdmin,
                          obscureText: true,
                          autocorrect: false,
                          decoration: _decoracionCampo,
                          style: _estiloCampo,
                        ),
                      ),
                      _pegarEn(_claveAdmin),
                    ],
                  ),
                  const SizedBox(height: 20),
                  CupertinoButton.filled(
                    onPressed: widget.fuente.estado == EstadoConexion.conectando
                        ? null
                        : () => widget.fuente.guardarAjustes(
                            _direccion.text,
                            _clave.text,
                            _claveAdmin.text,
                          ),
                    child: const Text('Guardar y conectar'),
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Configuración avanzada',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  AjustesAvanzados(fuente: widget.fuente),
                  const SizedBox(height: 20),
                  LoDeAshur(fuente: widget.fuente),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
