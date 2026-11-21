import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

import 'camara.dart';
import 'modelo.dart';
import 'pintor.dart';

/// La galaxia en vivo. Tocar el núcleo llama a [alTocarNucleo] con el punto tocado.
class VistaGalaxia extends StatefulWidget {
  const VistaGalaxia({super.key, required this.alTocarNucleo, this.camara});

  final void Function(Offset punto, Size tamano) alTocarNucleo;

  /// Para las pruebas: la cámara que usa la vista. Si es null, la vista crea la suya.
  final ValueNotifier<Camara>? camara;

  @override
  State<VistaGalaxia> createState() => _VistaGalaxiaState();
}

class _VistaGalaxiaState extends State<VistaGalaxia> with SingleTickerProviderStateMixin {
  final _tiempo = ValueNotifier<double>(0);
  late final ValueNotifier<Camara> _camara = widget.camara ?? ValueNotifier<Camara>(Camara.inicial);
  Camara _alEmpezar = Camara.inicial;
  bool _yaBuscoQueSeguir = false;
  Offset _focoAnterior = Offset.zero;
  late final Ticker _ticker;
  EstadoGalaxia? _estado;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker((transcurrido) {
      _tiempo.value = transcurrido.inMicroseconds / Duration.microsecondsPerSecond;
      _seguirCuerpo();
    })
      ..start();
    EstadoGalaxia.cargar(rootBundle).then((e) {
      if (mounted) setState(() => _estado = e);
    });
  }

  @override
  void dispose() {
    _ticker.dispose();
    _tiempo.dispose();
    if (widget.camara == null) _camara.dispose();
    super.dispose();
  }

  void _tocar(TapUpDetails d, Size tamano) {
    final estado = _estado;
    if (estado == null) return;
    if (tocaNucleo(estado, tamano, _tiempo.value, _camara.value, d.localPosition)) {
      widget.alTocarNucleo(d.localPosition, tamano);
    }
  }

  Size _tamano = Size.zero;

  /// Mantiene en su ancla al cuerpo que se acercó, mientras la galaxia sigue girando.
  void _seguirCuerpo() {
    final estado = _estado;
    final camara = _camara.value;
    if (estado == null || camara.sigue == null || _tamano.isEmpty) return;
    final g = Geometria(estado, _tamano, _tiempo.value);
    if (g.cuerpo(camara.sigue!) == null) {
      _camara.value = camara.soltar();
      return;
    }
    _camara.value = camara.centrarEn(g.posicion(camara.sigue!, _tiempo.value), _tamano);
  }

  /// Al acercar, la cámara se queda con el cuerpo que está bajo el foco.
  Camara _seguirLoQueHayEn(Camara camara, Offset foco, Size tamano) {
    final estado = _estado;
    if (estado == null) return camara;
    final id = cuerpoEn(estado, tamano, _tiempo.value, camara, foco);
    return id == null ? camara : camara.seguir(id, foco);
  }

  void _empezarEscala(ScaleStartDetails d, Size tamano) {
    _alEmpezar = _camara.value;
    _focoAnterior = d.localFocalPoint;
    _yaBuscoQueSeguir = false;
  }

  void _escalar(ScaleUpdateDetails d, Size tamano) {
    if (d.pointerCount >= 2 && !_yaBuscoQueSeguir) {
      // El primer cuadro con dos dedos decide a quién seguir, con el foco de ese momento.
      _yaBuscoQueSeguir = true;
      _camara.value = _seguirLoQueHayEn(_camara.value.soltar(), d.localFocalPoint, tamano);
    }
    final camara = _camara.value;
    if (d.pointerCount < 2) {
      // Un dedo mueve la vista y suelta el cuerpo seguido.
      _camara.value = camara.mover(d.localFocalPoint - _focoAnterior, tamano);
    } else if (camara.sigue != null) {
      // Siguiendo un cuerpo: el zoom crece alrededor de él, que se queda bajo los dedos.
      _camara.value = Camara(
        zoom: (_alEmpezar.zoom * d.scale).clamp(1.0, zoomMaximo),
        desplazamiento: camara.desplazamiento,
        sigue: camara.sigue,
        ancla: d.localFocalPoint,
      );
      _seguirCuerpo();
    } else {
      final movida = camara.mover(d.localFocalPoint - _focoAnterior, tamano);
      _camara.value = movida.acercar(_alEmpezar.zoom * d.scale, d.localFocalPoint, tamano);
    }
    _focoAnterior = d.localFocalPoint;
  }

  void _rueda(PointerSignalEvent e, Size tamano) {
    if (e is! PointerScrollEvent) return;
    final factor = math.exp(-e.scrollDelta.dy / 300);
    var camara = _camara.value;
    if (camara.sigue == null && factor > 1) camara = _seguirLoQueHayEn(camara, e.localPosition, tamano);
    _camara.value = camara.acercar(camara.zoom * factor, e.localPosition, tamano);
  }

  @override
  Widget build(BuildContext context) {
    final estado = _estado;
    if (estado == null) return const SizedBox.expand();
    return LayoutBuilder(
      builder: (context, restricciones) {
        final tamano = restricciones.biggest;
        _tamano = tamano;
        return Listener(
          onPointerSignal: (e) => _rueda(e, tamano),
          child: GestureDetector(
            onTapUp: (d) => _tocar(d, tamano),
            onScaleStart: (d) => _empezarEscala(d, tamano),
            onScaleUpdate: (d) => _escalar(d, tamano),
            child: CustomPaint(
              size: tamano,
              painter: PintorGalaxia(estado: estado, tiempo: _tiempo, camara: _camara),
            ),
          ),
        );
      },
    );
  }
}

/// Si el toque en [punto] de la pantalla cae sobre el núcleo: |s_toque − s_núcleo| ≤ max(zR, 22).
bool tocaNucleo(EstadoGalaxia estado, Size tamano, double t, Camara camara, Offset punto) {
  final g = Geometria(estado, tamano, t);
  final nucleo = g.nucleo;
  if (nucleo == null) return false;
  final enPantalla = camara.aPantalla(g.posicion(nucleo.id, t), g.centro);
  final alcance = math.max(g.radio(nucleo) * camara.zoom, 22.0);
  return (punto - enPantalla).distance <= alcance;
}

/// El cuerpo más cercano a [punto] de la pantalla, si alguno está a menos de max(zR, alcanceSeguir) píxeles. Los personajes
/// no cuentan: viven dentro de su planeta.
String? cuerpoEn(EstadoGalaxia estado, Size tamano, double t, Camara camara, Offset punto) {
  final g = Geometria(estado, tamano, t);
  String? mejor;
  var distanciaMejor = double.infinity;
  for (final c in estado.cuerpos) {
    if (c.tipo == TipoCuerpo.personaje) continue;
    final distancia = (camara.aPantalla(g.posicion(c.id, t), g.centro) - punto).distance;
    if (distancia <= math.max(g.radio(c) * camara.zoom, alcanceSeguir) && distancia < distanciaMejor) {
      mejor = c.id;
      distanciaMejor = distancia;
    }
  }
  return mejor;
}
