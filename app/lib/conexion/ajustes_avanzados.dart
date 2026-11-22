// Ajustes de nodos y módulos que expone el core (ADR 0019).
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart' show Clipboard, ClipboardData;

import 'cliente.dart';
import 'fuente.dart';

const _fondoCampo = BoxDecoration(
  color: Color(0xFF141622),
  border: Border.fromBorderSide(BorderSide(color: Color(0x33FFFFFF))),
  borderRadius: BorderRadius.all(Radius.circular(8)),
);
const _textoCampo = TextStyle(color: Color(0xFFE8E8F0), fontSize: 15);

class AjustesAvanzados extends StatefulWidget {
  const AjustesAvanzados({
    super.key,
    required this.fuente,
    this.clienteOverride,
  });

  final FuenteGalaxia fuente;
  final ClienteCore? clienteOverride;

  @override
  State<AjustesAvanzados> createState() => _AjustesAvanzadosState();
}

class _AjustesAvanzadosState extends State<AjustesAvanzados> {
  ClienteCore? _cliente;
  List<Map<String, dynamic>> _nodos = [];
  List<Map<String, dynamic>> _modulos = [];
  final Map<String, List<Map<String, dynamic>>> _ajustesModulo = {};
  final Map<String, TextEditingController> _campos = {};
  final _nombreNodo = TextEditingController();
  String? _error;
  bool _cargando = true;
  bool _ocupado = false;
  bool _admin = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _nombreNodo.dispose();
    for (final campo in _campos.values) {
      campo.dispose();
    }
    super.dispose();
  }

  Future<void> _cargar() async {
    final guardados = await widget.fuente.ajustes();
    _cliente = widget.clienteOverride ?? await widget.fuente.cliente();
    _admin = (_cliente?.claveAdmin ?? guardados.$3)?.trim().isNotEmpty == true;
    if (_cliente == null) {
      if (mounted) setState(() => _cargando = false);
      return;
    }
    try {
      final resultados = await Future.wait<dynamic>([
        _cliente!.listarNodos(),
        _cliente!.listarModulos(),
      ]);
      final modulos = (resultados[1] as List<Map<String, dynamic>>);
      final ajustes = <String, List<Map<String, dynamic>>>{};
      for (final modulo in modulos) {
        if (modulo['error'] == null && modulo['manifiesto'] != null) {
          ajustes[modulo['id'] as String] = await _cliente!.verAjustesModulo(
            modulo['id'] as String,
          );
        }
      }
      if (!mounted) return;
      setState(() {
        _nodos = resultados[0] as List<Map<String, dynamic>>;
        _modulos = modulos;
        _ajustesModulo
          ..clear()
          ..addAll(ajustes);
        _sincronizarCampos();
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

  void _sincronizarCampos() {
    for (final nodo in _nodos) {
      final id = nodo['id'] as String;
      final ajustes = nodo['ajustes'] as Map<String, dynamic>? ?? {};
      final ofrecidos = ajustes['modelos_ofrecidos'] as List<dynamic>?;
      _campo('modelos:$id', ofrecidos?.join(', ') ?? '');
      _campo('contexto:$id', ajustes['num_ctx']?.toString() ?? '');
      final horario = ajustes['horario'] as Map<String, dynamic>?;
      _campo('desde:$id', horario?['desde']?.toString() ?? '');
      _campo('hasta:$id', horario?['hasta']?.toString() ?? '');
    }
    for (final ajustes in _ajustesModulo.values) {
      for (final ajuste in ajustes) {
        if (ajuste['tipo'] != 'booleano') {
          // El valor de un secreto nunca viene del core; el campo siempre empieza vacío.
          _campo(
            'mod:${ajuste['id']}',
            ajuste['secreto'] == true ? '' : ajuste['valor']?.toString() ?? '',
          );
        }
      }
    }
  }

  TextEditingController _campo(String id, String inicial) =>
      _campos.putIfAbsent(id, () => TextEditingController(text: inicial));

  Future<void> _accion(Future<void> Function() accion) async {
    if (_ocupado || !_admin || _cliente == null) return;
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

  Future<void> _guardarNodo(String id, Map<String, dynamic> cambios) async {
    await _accion(() async {
      final nodo = await _cliente!.editarNodo(id, cambios);
      final i = _nodos.indexWhere((n) => n['id'] == id);
      if (i >= 0 && mounted) setState(() => _nodos[i] = nodo);
      _sincronizarCampos();
    });
  }

  Future<void> _crearNodo() async {
    final nombre = _nombreNodo.text.trim();
    if (nombre.isEmpty) {
      setState(() => _error = 'El nodo necesita un nombre.');
      return;
    }
    await _accion(() async {
      final creado = await _cliente!.crearNodo(nombre);
      final nodo = Map<String, dynamic>.from(creado['nodo'] as Map);
      final clave = creado['clave'] as String;
      if (mounted)
        setState(() {
          _nodos = [..._nodos, nodo];
          _nombreNodo.clear();
          _sincronizarCampos();
        });
      if (!mounted) return;
      await showCupertinoDialog<void>(
        context: context,
        builder: (context) => CupertinoAlertDialog(
          title: const Text('Clave del nodo'),
          content: Column(
            children: [
              const SizedBox(height: 10),
              const Text('Cópiala ahora. No se volverá a mostrar.'),
              const SizedBox(height: 8),
              Text(clave, textAlign: TextAlign.center),
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

  Future<void> _guardarAjuste(String modulo, String id, dynamic valor) async {
    await _accion(() async {
      final nuevos = await _cliente!.cambiarAjustesModulo(modulo, {id: valor});
      if (mounted) setState(() => _ajustesModulo[modulo] = nuevos);
      _sincronizarCampos();
    });
  }

  String _mensajeError(Object error) {
    if (error is! ErrorCore) return error.toString();
    return switch (error.fallo) {
      FalloCore.claveInvalida =>
        'El core rechazó una clave. Revisa las claves configuradas.',
      FalloCore.noExiste =>
        'El core ya no encuentra ese elemento. Actualiza la pantalla.',
      FalloCore.datosInvalidos => error.detalle,
      FalloCore.coreSinClave => 'El core no tiene una clave configurada.',
      FalloCore.inalcanzable => 'No se pudo llegar al core. ${error.detalle}',
      FalloCore.conflicto => error.detalle,
      FalloCore.otro => 'El core respondió algo inesperado. ${error.detalle}',
    };
  }

  Widget _campoTexto(
    String etiqueta,
    TextEditingController controller, {
    bool numerico = false,
    bool oculto = false,
  }) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(etiqueta),
      const SizedBox(height: 4),
      CupertinoTextField(
        controller: controller,
        keyboardType: numerico ? TextInputType.number : TextInputType.text,
        obscureText: oculto,
        autocorrect: false,
        decoration: _fondoCampo,
        style: _textoCampo,
      ),
    ],
  );

  Widget _boton(String texto, VoidCallback accion) => CupertinoButton(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    onPressed: _ocupado ? null : accion,
    child: Text(texto),
  );

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const Text('Nodos', style: TextStyle(fontWeight: FontWeight.w600)),
      if (_cargando)
        const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text('Cargando la configuración…'),
        ),
      if (!_cargando && _cliente == null)
        const Text('Conecta con el core para ver los nodos y módulos.'),
      if (_error != null)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(_error!),
        ),
      if (!_cargando && _cliente != null && _nodos.isEmpty)
        const Text('No hay nodos registrados.'),
      for (final nodo in _nodos) _tarjetaNodo(nodo),
      if (_admin) ...[
        _campoTexto('Nombre del nodo nuevo', _nombreNodo),
        CupertinoButton.filled(
          onPressed: _ocupado ? null : _crearNodo,
          child: const Text('Crear nodo'),
        ),
      ],
      const SizedBox(height: 20),
      const Text('Módulos', style: TextStyle(fontWeight: FontWeight.w600)),
      if (!_cargando && _cliente != null && _modulos.isEmpty)
        const Text('No hay módulos registrados.'),
      for (final modulo in _modulos) _tarjetaModulo(modulo),
      if (!_admin && _cliente != null)
        const Padding(
          padding: EdgeInsets.only(top: 12),
          child: Text(
            'Hace falta la clave de administrador para cambiar estos ajustes. Configúrala en Estado.',
          ),
        ),
    ],
  );

  Widget _tarjetaNodo(Map<String, dynamic> nodo) {
    final id = nodo['id'] as String;
    final ajustes = nodo['ajustes'] as Map<String, dynamic>? ?? {};
    final modelos = (nodo['modelos'] as List<dynamic>? ?? [])
        .map((modelo) => (modelo as Map<String, dynamic>)['nombre'].toString())
        .toList();
    final ofrecidos = ajustes['modelos_ofrecidos'] as List<dynamic>?;
    final todos = ofrecidos == null;
    final seleccionados = ofrecidos ?? <dynamic>[];
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            nodo['nombre']?.toString() ?? id,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          Text(
            '${nodo['en_linea'] == true ? 'En línea' : 'Fuera de línea'} · Modo ${nodo['modo'] ?? '—'}',
          ),
          Text('Modelos: ${modelos.isEmpty ? 'Ninguno' : modelos.join(', ')}'),
          if (_admin) ...[
            Row(
              children: [
                const Expanded(child: Text('Todos los modelos')),
                CupertinoSwitch(
                  value: todos,
                  onChanged: _ocupado
                      ? null
                      : (valor) => _guardarNodo(id, {
                          'modelos_ofrecidos': valor ? null : <String>[],
                        }),
                ),
              ],
            ),
            if (!todos) ...[
              for (final modelo in modelos)
                Row(
                  children: [
                    Expanded(child: Text(modelo)),
                    CupertinoSwitch(
                      value: seleccionados.contains(modelo),
                      onChanged: _ocupado
                          ? null
                          : (prestado) {
                              final seleccion = seleccionados.toSet();
                              if (prestado) {
                                seleccion.add(modelo);
                              } else {
                                seleccion.remove(modelo);
                              }
                              _guardarNodo(id, {
                                'modelos_ofrecidos': seleccion.toList(),
                              });
                            },
                    ),
                  ],
                ),
            ],
            Row(
              children: [
                Expanded(
                  child: _campoTexto(
                    'Contexto (vacío = nodo)',
                    _campo(
                      'contexto:$id',
                      ajustes['num_ctx']?.toString() ?? '',
                    ),
                    numerico: true,
                  ),
                ),
                _boton('Guardar', () {
                  final texto = _campos['contexto:$id']!.text.trim();
                  final numero = texto.isEmpty ? null : int.tryParse(texto);
                  if (texto.isNotEmpty && numero == null) {
                    setState(
                      () => _error = 'El contexto debe ser un número entero.',
                    );
                    return;
                  }
                  _guardarNodo(id, {'num_ctx': numero});
                }),
              ],
            ),
            Row(
              children: [
                Expanded(
                  child: _campoTexto(
                    'Desde',
                    _campo(
                      'desde:$id',
                      (ajustes['horario'] as Map?)?['desde']?.toString() ?? '',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _campoTexto(
                    'Hasta',
                    _campo(
                      'hasta:$id',
                      (ajustes['horario'] as Map?)?['hasta']?.toString() ?? '',
                    ),
                  ),
                ),
              ],
            ),
            Row(
              children: [
                _boton(
                  'Guardar horario',
                  () => _guardarNodo(id, {
                    'horario':
                        _campos['desde:$id']!.text.trim().isEmpty &&
                            _campos['hasta:$id']!.text.trim().isEmpty
                        ? null
                        : {
                            'desde': _campos['desde:$id']!.text.trim(),
                            'hasta': _campos['hasta:$id']!.text.trim(),
                          },
                  }),
                ),
                _boton(
                  'A toda hora',
                  () => _guardarNodo(id, {'horario': null}),
                ),
                _boton(
                  nodo['archivado'] == true ? 'Restaurar' : 'Archivar',
                  () => _guardarNodo(id, {
                    'archivado': nodo['archivado'] != true,
                  }),
                ),
              ],
            ),
          ] else ...[
            Text(
              'Presta: ${todos ? 'todos los modelos' : ofrecidos.join(', ')}',
            ),
            Text('Contexto: ${ajustes['num_ctx'] ?? 'el del nodo'}'),
            Text(
              'Horario: ${ajustes['horario'] == null ? 'a toda hora' : '${ajustes['horario']['desde']}–${ajustes['horario']['hasta']}'}',
            ),
            if (nodo['archivado'] == true) const Text('Archivado'),
          ],
          Container(height: 1, color: const Color(0x33FFFFFF)),
        ],
      ),
    );
  }

  Widget _tarjetaModulo(Map<String, dynamic> modulo) {
    final id = modulo['id'] as String;
    final manifiesto = modulo['manifiesto'] as Map<String, dynamic>?;
    final error = modulo['error'];
    final ajustes = _ajustesModulo[id] ?? [];
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            manifiesto?['nombre']?.toString() ?? id,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          if (error != null) Text('Error del módulo: $error'),
          if (manifiesto != null && ajustes.isEmpty)
            const Text('Este módulo no declara ajustes.'),
          for (final ajuste in ajustes) _filaAjuste(id, ajuste),
          Container(height: 1, color: const Color(0x33FFFFFF)),
        ],
      ),
    );
  }

  Widget _filaAjuste(String modulo, Map<String, dynamic> ajuste) {
    final id = ajuste['id'] as String;
    final secreto = ajuste['secreto'] == true;
    final tipo = ajuste['tipo'] as String;
    final valor = ajuste['valor'];
    final clave = 'mod:$modulo:$id';
    Widget control;
    if (tipo == 'booleano') {
      control = Row(
        children: [
          Expanded(child: Text('${ajuste['descripcion']}')),
          CupertinoSwitch(
            value: valor == true,
            onChanged: !_admin || _ocupado
                ? null
                : (nuevo) => _guardarAjuste(modulo, id, nuevo),
          ),
          if (_admin)
            _boton(
              'Volver al valor por defecto',
              () => _guardarAjuste(modulo, id, null),
            ),
        ],
      );
    } else if (!_admin) {
      control = Text(
        secreto
            ? '${ajuste['descripcion']} · ${ajuste['configurado'] == true ? 'Configurado' : 'Sin configurar'}'
            : '${ajuste['descripcion']}: ${valor ?? ajuste['por_defecto'] ?? 'Sin configurar'}',
      );
    } else {
      control = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('${ajuste['descripcion']}'),
          if (secreto)
            Text(
              ajuste['configurado'] == true ? 'Configurado' : 'Sin configurar',
            ),
          Row(
            children: [
              Expanded(
                child: _campoTexto(
                  secreto
                      ? 'Nuevo valor secreto'
                      : ajuste['descripcion'].toString(),
                  _campo(clave, secreto ? '' : valor?.toString() ?? ''),
                  numerico: tipo == 'numero',
                  oculto: secreto,
                ),
              ),
              if (secreto && _admin)
                _boton('Pegar', () async {
                  final datos = await Clipboard.getData(Clipboard.kTextPlain);
                  if (datos?.text?.isNotEmpty == true)
                    _campos[clave]!.text = datos!.text!;
                }),
            ],
          ),
          if (_admin)
            Row(
              children: [
                _boton('Guardar', () {
                  final texto = _campos[clave]!.text;
                  final nuevo = tipo == 'numero' ? num.tryParse(texto) : texto;
                  if (tipo == 'numero' && nuevo == null) {
                    setState(
                      () => _error =
                          'El ajuste «${ajuste['descripcion']}» debe ser un número.',
                    );
                    return;
                  }
                  _guardarAjuste(modulo, id, nuevo);
                }),
                _boton(
                  'Volver al valor por defecto',
                  () => _guardarAjuste(modulo, id, null),
                ),
              ],
            ),
        ],
      );
    }
    return Padding(padding: const EdgeInsets.only(top: 10), child: control);
  }
}
