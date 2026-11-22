// Personalidad, correcciones, roles y claves de personas. Nada de esta vista se escribe en el dispositivo.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart' show Clipboard, ClipboardData;

import 'almacen.dart';
import 'fuente.dart';
import 'cliente.dart';

const _decoracionCampo = BoxDecoration(
  color: Color(0xFF141622),
  border: Border.fromBorderSide(BorderSide(color: Color(0x33FFFFFF))),
  borderRadius: BorderRadius.all(Radius.circular(8)),
);
const _estiloCampo = TextStyle(color: Color(0xFFE8E8F0), fontSize: 15);
const _estiloPista = TextStyle(color: Color(0x80E8E8F0), fontSize: 15);

class LoDeAshur extends StatefulWidget {
  const LoDeAshur({super.key, required this.fuente, this.clienteOverride});

  final FuenteGalaxia fuente;
  final ClienteCore? clienteOverride;

  @override
  State<LoDeAshur> createState() => _LoDeAshurState();
}

class _LoDeAshurState extends State<LoDeAshur> {
  final _base = TextEditingController();
  final _sobreSergio = TextEditingController();
  final _inicial = TextEditingController();
  final _intermedio = TextEditingController();
  final _pleno = TextEditingController();
  final _trato = TextEditingController();
  final _umbralIntermedio = TextEditingController();
  final _umbralPleno = TextEditingController();
  final _nombreRol = TextEditingController();
  final _herramientasRol = TextEditingController();
  final Map<int, TextEditingController> _correccionCampos = {};

  ClienteCore? _cliente;
  Map<String, dynamic>? _vista;
  List<Map<String, dynamic>> _roles = [];
  List<Map<String, dynamic>> _personas = [];
  String? _rolEditando;
  String? _error;
  bool _adminDisponible = false;
  bool _cargando = true;
  bool _ocupado = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    for (final campo in [
      _base,
      _sobreSergio,
      _inicial,
      _intermedio,
      _pleno,
      _trato,
      _umbralIntermedio,
      _umbralPleno,
      _nombreRol,
      _herramientasRol,
      ..._correccionCampos.values,
    ]) {
      campo.dispose();
    }
    super.dispose();
  }

  Future<void> _cargar() async {
    try {
      _adminDisponible = (await widget.fuente.ajustes()).$3?.trim().isNotEmpty == true;
    } on SecretoBloqueado {
      _adminDisponible = false; // Face ID falló: cliente() deja la conexión en bloqueada.
    }
    _cliente = widget.clienteOverride ?? await widget.fuente.cliente();
    if (_cliente == null) {
      if (mounted)
        setState(() {
          _cargando = false;
        });
      return;
    }
    try {
      final datos = await Future.wait<dynamic>([
        _cliente!.verPersonalidad(),
        _cliente!.listarRoles(),
        _cliente!.listarIdentidades(),
      ]);
      if (!mounted) return;
      setState(() {
        _vista = Map<String, dynamic>.from(datos[0] as Map);
        _roles = (datos[1] as List<Map<String, dynamic>>);
        _personas = (datos[2] as List<Map<String, dynamic>>)
            .where((identidad) => identidad['clase'] == 'persona')
            .toList();
        _ponerPersonalidadEnCampos();
        _cargando = false;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(error);
        _cargando = false;
      });
    }
  }

  void _ponerPersonalidadEnCampos() {
    final personalidad = _vista?['personalidad'] as Map<String, dynamic>? ?? {};
    final madurez = personalidad['madurez'] as Map<String, dynamic>? ?? {};
    final trato = personalidad['trato'] as List<dynamic>? ?? [];
    final umbrales =
        personalidad['umbrales'] as Map<String, dynamic>? ??
        _vista?['madurez']?['umbrales'] as Map<String, dynamic>? ??
        {};
    _base.text = personalidad['base']?.toString() ?? '';
    _sobreSergio.text = personalidad['sobre_sergio']?.toString() ?? '';
    _inicial.text = madurez['inicial']?.toString() ?? '';
    _intermedio.text = madurez['intermedio']?.toString() ?? '';
    _pleno.text = madurez['pleno']?.toString() ?? '';
    _trato.text = trato.join('\n');
    _umbralIntermedio.text = (umbrales['intermedio'] ?? 2000).toString();
    _umbralPleno.text = (umbrales['pleno'] ?? 20000).toString();
    _ponerCorreccionesEnCampos();
  }

  void _ponerCorreccionesEnCampos() {
    for (final campo in _correccionCampos.values) {
      campo.dispose();
    }
    _correccionCampos.clear();
    final lista = _vista?['correcciones'] as List<dynamic>? ?? [];
    for (var i = 0; i < lista.length; i++) {
      final correccion = lista[i] as Map<String, dynamic>;
      _correccionCampos[i] = TextEditingController(
        text: correccion['texto']?.toString() ?? '',
      );
    }
  }

  Future<void> _guardarPersonalidad() async {
    final intermedio = int.tryParse(_umbralIntermedio.text.trim());
    final pleno = int.tryParse(_umbralPleno.text.trim());
    if (_base.text.trim().isEmpty ||
        _inicial.text.trim().isEmpty ||
        _intermedio.text.trim().isEmpty ||
        _pleno.text.trim().isEmpty ||
        intermedio == null ||
        pleno == null ||
        intermedio >= pleno) {
      setState(
        () => _error = 'Completa la personalidad y verifica que el umbral intermedio sea menor que el pleno.',
      );
      return;
    }
    final personalidad = <String, dynamic>{
      'base': _base.text,
      'sobre_sergio': _sobreSergio.text.trim().isEmpty
          ? null
          : _sobreSergio.text,
      'madurez': {
        'inicial': _inicial.text,
        'intermedio': _intermedio.text,
        'pleno': _pleno.text,
      },
      'trato': _trato.text
          .split('\n')
          .map((linea) => linea.trim())
          .where((linea) => linea.isNotEmpty)
          .toList(),
      'umbrales': {'intermedio': intermedio, 'pleno': pleno},
    };
    await _conOcupado(() async {
      final resultado = await _cliente!.guardarPersonalidad(personalidad);
      _actualizarVista(resultado);
    });
  }

  void _actualizarVista(Map<String, dynamic> vista) {
    if (!mounted) return;
    setState(() {
      _vista = vista;
      _error = null;
      _ponerPersonalidadEnCampos();
    });
  }

  Future<void> _guardarCorreccion(int indice) async {
    final actual = List<Map<String, dynamic>>.from(
      (_vista?['correcciones'] as List<dynamic>? ?? []).map(
        (item) => Map<String, dynamic>.from(item as Map),
      ),
    );
    final texto = _correccionCampos[indice]?.text.trim() ?? '';
    if (texto.isEmpty || texto.length > 200) {
      setState(
        () => _error = 'Cada corrección debe tener entre 1 y 200 caracteres.',
      );
      return;
    }
    actual[indice] = {...actual[indice], 'texto': texto};
    await _conOcupado(
      () async =>
          _actualizarVista(await _cliente!.reemplazarCorrecciones(actual)),
    );
  }

  Future<void> _borrarCorreccion(int indice) async {
    final actual = List<Map<String, dynamic>>.from(
      (_vista?['correcciones'] as List<dynamic>? ?? []).map(
        (item) => Map<String, dynamic>.from(item as Map),
      ),
    )..removeAt(indice);
    await _conOcupado(
      () async =>
          _actualizarVista(await _cliente!.reemplazarCorrecciones(actual)),
    );
  }

  Future<void> _guardarRol() async {
    final nombre = _nombreRol.text.trim();
    final herramientas = _herramientasRol.text
        .split(RegExp(r'[\n,]'))
        .map((nombre) => nombre.trim())
        .where((nombre) => nombre.isNotEmpty)
        .toList();
    if (nombre.isEmpty) {
      setState(() => _error = 'El rol necesita un nombre.');
      return;
    }
    await _conOcupado(() async {
      final rol = _rolEditando == null
          ? await _cliente!.crearRol(nombre, herramientas)
          : await _cliente!.editarRol(_rolEditando!, nombre, herramientas);
      setState(() {
        final indice = _roles.indexWhere(
          (elemento) => elemento['id'] == rol['id'],
        );
        if (indice < 0) {
          _roles = [..._roles, rol];
        } else {
          _roles[indice] = rol;
        }
        _rolEditando = rol['id'] as String;
        _nombreRol.text = rol['nombre'] as String;
        _herramientasRol.text = (rol['herramientas'] as List<dynamic>).join(
          '\n',
        );
        _error = null;
      });
    });
  }

  void _nuevoRol() {
    setState(() {
      _rolEditando = null;
      _nombreRol.clear();
      _herramientasRol.clear();
      _error = null;
    });
  }

  Future<void> _elegirRol(Map<String, dynamic> persona) async {
    await showCupertinoModalPopup<void>(
      context: context,
      builder: (context) => CupertinoActionSheet(
        title: Text('Rol de ${persona['nombre']}'),
        actions: [
          for (final rol in _roles)
            CupertinoActionSheetAction(
              onPressed: () {
                Navigator.of(context).pop();
                _cambiarRol(persona, rol['id'] as String);
              },
              child: Text(rol['nombre'] as String),
            ),
          CupertinoActionSheetAction(
            onPressed: () {
              Navigator.of(context).pop();
              _cambiarRol(persona, null);
            },
            child: const Text('Quitar rol'),
          ),
        ],
        cancelButton: CupertinoActionSheetAction(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
      ),
    );
  }

  Future<void> _cambiarRol(Map<String, dynamic> persona, String? rol) async {
    await _conOcupado(() async {
      final identidad = await _cliente!.asignarRol(
        persona['id'] as String,
        rol,
      );
      final indice = _personas.indexWhere(
        (persona) => persona['id'] == identidad['id'],
      );
      if (indice >= 0) setState(() => _personas[indice] = identidad);
    });
  }

  Future<void> _crearClave(Map<String, dynamic> persona) async {
    await _conOcupado(() async {
      final respuesta = await _cliente!.crearClaveIdentidad(
        persona['id'] as String,
      );
      final identidad = Map<String, dynamic>.from(
        respuesta['identidad'] as Map,
      );
      final clave = respuesta['clave'] as String;
      final indice = _personas.indexWhere(
        (elemento) => elemento['id'] == identidad['id'],
      );
      if (indice >= 0) setState(() => _personas[indice] = identidad);
      if (!mounted) return;
      await showCupertinoDialog<void>(
        context: context,
        builder: (context) => CupertinoAlertDialog(
          title: const Text('Clave nueva'),
          content: Column(
            children: [
              const SizedBox(height: 12),
              Text(clave, textAlign: TextAlign.center, style: _estiloCampo),
              CupertinoButton(
                onPressed: () => Clipboard.setData(ClipboardData(text: clave)),
                child: const Text('Copiar'),
              ),
            ],
          ),
          actions: [
            CupertinoDialogAction(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cerrar'),
            ),
          ],
        ),
      );
    });
  }

  Future<void> _conOcupado(Future<void> Function() accion) async {
    if (_ocupado || _cliente == null || !_adminDisponible) return;
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      await accion();
    } on Object catch (error) {
      if (mounted) setState(() => _error = _mensajeError(error));
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  String _mensajeError(Object error) {
    if (error is! ErrorCore) return error.toString();
    return switch (error.fallo) {
      FalloCore.claveInvalida =>
        'El core rechazó una clave. Revisa las claves configuradas.',
      FalloCore.noExiste =>
        'El core ya no encuentra ese elemento. Actualiza la pantalla.',
      FalloCore.conflicto =>
        error.detalle.isEmpty ? 'La identidad está archivada.' : error.detalle,
      FalloCore.datosInvalidos => error.detalle,
      FalloCore.coreSinClave => 'El core no tiene una clave configurada.',
      FalloCore.inalcanzable => 'No se pudo llegar al core. ${error.detalle}',
      FalloCore.otro => 'El core respondió algo inesperado. ${error.detalle}',
    };
  }

  Widget _campo(
    String titulo,
    TextEditingController controlador, {
    int? lineas,
    TextInputType? tipo,
  }) {
    if (!_adminDisponible) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(titulo),
            const SizedBox(height: 4),
            Text(controlador.text.isEmpty ? '—' : controlador.text),
          ],
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(titulo),
          const SizedBox(height: 4),
          CupertinoTextField(
            controller: controlador,
            minLines: lineas ?? 1,
            maxLines: lineas == null ? 1 : null,
            keyboardType: tipo,
            autocorrect: false,
            decoration: _decoracionCampo,
            style: _estiloCampo,
            placeholderStyle: _estiloPista,
          ),
        ],
      ),
    );
  }

  Widget _boton(String texto, VoidCallback accion) => CupertinoButton(
    onPressed: _ocupado ? null : accion,
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
    child: Text(texto),
  );

  @override
  Widget build(BuildContext context) {
    final correcciones = _vista?['correcciones'] as List<dynamic>? ?? [];
    final madurez = _vista?['madurez'] as Map<String, dynamic>?;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Lo de Ashur',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        if (_cargando) const Text('Cargando la configuración…'),
        if (!_cargando && _cliente == null)
          const Text('Conecta con el core para ver la configuración avanzada.'),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(_error!),
          ),
        if (madurez != null) ...[
          Text(
            'Madurez actual: ${madurez['nivel']} · ${madurez['recuerdos']} recuerdos',
          ),
          const SizedBox(height: 12),
        ],
        if (_vista != null) ...[
          _campo('Base', _base, lineas: 3),
          _campo('Lo que sabe de Sergio', _sobreSergio, lineas: 3),
          _campo('Madurez inicial', _inicial, lineas: 2),
          _campo('Madurez intermedia', _intermedio, lineas: 2),
          _campo('Madurez plena', _pleno, lineas: 2),
          _campo('Trato (una línea por regla)', _trato, lineas: 3),
          _campo(
            'Umbral intermedio',
            _umbralIntermedio,
            tipo: TextInputType.number,
          ),
          _campo('Umbral pleno', _umbralPleno, tipo: TextInputType.number),
          if (_adminDisponible)
            CupertinoButton.filled(
              onPressed: _ocupado ? null : _guardarPersonalidad,
              child: const Text('Guardar personalidad'),
            ),
          const SizedBox(height: 20),
          const Text(
            'Correcciones',
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          if (correcciones.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('No hay correcciones.'),
            ),
          for (var i = 0; i < correcciones.length; i++)
            _filaCorreccion(i, correcciones[i] as Map<String, dynamic>),
          const SizedBox(height: 20),
          const Text('Roles', style: TextStyle(fontWeight: FontWeight.w600)),
          for (final rol in _roles) _filaRol(rol),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'buscar_* muestra todo tu inventario y los nombres de tus identidades; modulo-* corre con los privilegios del módulo.',
            ),
          ),
          if (_adminDisponible) ...[
            _campo('Nombre del rol', _nombreRol),
            _campo('Herramientas (una por línea)', _herramientasRol, lineas: 3),
            Row(
              children: [
                CupertinoButton.filled(
                  onPressed: _ocupado ? null : _guardarRol,
                  child: Text(
                    _rolEditando == null ? 'Crear rol' : 'Guardar rol',
                  ),
                ),
                if (_rolEditando != null) _boton('Crear otro rol', _nuevoRol),
              ],
            ),
          ],
          const SizedBox(height: 20),
          const Text('Personas', style: TextStyle(fontWeight: FontWeight.w600)),
          if (_personas.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('No hay personas activas.'),
            ),
          for (final persona in _personas) _filaPersona(persona),
        ],
      ],
    );
  }

  Widget _filaCorreccion(int indice, Map<String, dynamic> correccion) {
    final fuente = correccion['fuente']?.toString() ?? 'Sin fuente';
    final fecha = correccion['fecha']?.toString() ?? 'Sin fecha';
    final texto = correccion['texto']?.toString() ?? '';
    final campo = _correccionCampos.putIfAbsent(
      indice,
      () => TextEditingController(text: texto),
    );
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Fuente: $fuente'),
          Text('Fecha: $fecha'),
          const SizedBox(height: 4),
          if (_adminDisponible)
            CupertinoTextField(
              controller: campo,
              maxLength: 200,
              maxLines: null,
              decoration: _decoracionCampo,
              style: _estiloCampo,
            )
          else
            Text(texto),
          if (_adminDisponible)
            Row(
              children: [
                _boton('Guardar corrección', () => _guardarCorreccion(indice)),
                _boton('Borrar', () => _borrarCorreccion(indice)),
              ],
            ),
        ],
      ),
    );
  }

  Widget _filaRol(Map<String, dynamic> rol) {
    final herramientas = (rol['herramientas'] as List<dynamic>? ?? []).join(
      ', ',
    );
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: Text('${rol['nombre']}: $herramientas')),
          if (_adminDisponible)
            _boton('Editar', () {
              setState(() {
                _rolEditando = rol['id'] as String;
                _nombreRol.text = rol['nombre'] as String;
                _herramientasRol.text = (rol['herramientas'] as List<dynamic>)
                    .join('\n');
              });
            }),
        ],
      ),
    );
  }

  Widget _filaPersona(Map<String, dynamic> persona) {
    final rolActual = _roles
        .where((rol) => rol['id'] == persona['rol'])
        .firstOrNull;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${persona['nombre']} · Rol: ${rolActual?['nombre'] ?? 'ninguno'} · ${persona['con_clave'] == true ? 'con clave' : 'sin clave'}',
          ),
          if (_adminDisponible)
            Row(
              children: [
                _boton('Cambiar rol', () => _elegirRol(persona)),
                _boton('Crear clave', () => _crearClave(persona)),
              ],
            ),
        ],
      ),
    );
  }
}
