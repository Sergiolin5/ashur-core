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
  const VistaGalaxia({super.key, required this.alTocarNucleo});

  final void Function(Offset punto, Size tamano) alTocarNucleo;

  @override
  State<VistaGalaxia> createState() => _VistaGalaxiaState();
}

class _VistaGalaxiaState extends State<VistaGalaxia> with SingleTickerProviderStateMixin {
  final _tiempo = ValueNotifier<double>(0);
  final _camara = ValueNotifier<Camara>(Camara.inicial);
  Camara _alEmpezar = Camara.inicial;
  Offset _focoAnterior = Offset.zero;
  late final Ticker _ticker;
  EstadoGalaxia? _estado;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker((transcurrido) {
      _tiempo.value = transcurrido.inMicroseconds / Duration.microsecondsPerSecond;
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
    _camara.dispose();
    super.dispose();
  }

  void _tocar(TapUpDetails d, Size tamano) {
    final estado = _estado;
    if (estado == null) return;
    if (tocaNucleo(estado, tamano, _tiempo.value, _camara.value, d.localPosition)) {
      widget.alTocarNucleo(d.localPosition, tamano);
    }
  }

  void _empezarEscala(ScaleStartDetails d) {
    _alEmpezar = _camara.value;
    _focoAnterior = d.localFocalPoint;
  }

  void _escalar(ScaleUpdateDetails d, Size tamano) {
    // El zoom parte del que había al empezar; el movimiento se suma cuadro a cuadro.
    final movida = _camara.value.mover(d.localFocalPoint - _focoAnterior, tamano);
    _focoAnterior = d.localFocalPoint;
    _camara.value = movida.acercar(_alEmpezar.zoom * d.scale, d.localFocalPoint, tamano);
  }

  void _rueda(PointerSignalEvent e, Size tamano) {
    if (e is! PointerScrollEvent) return;
    final factor = math.exp(-e.scrollDelta.dy / 300);
    _camara.value = _camara.value.acercar(_camara.value.zoom * factor, e.localPosition, tamano);
  }

  @override
  Widget build(BuildContext context) {
    final estado = _estado;
    if (estado == null) return const SizedBox.expand();
    return LayoutBuilder(
      builder: (context, restricciones) {
        final tamano = restricciones.biggest;
        return Listener(
          onPointerSignal: (e) => _rueda(e, tamano),
          child: GestureDetector(
            onTapUp: (d) => _tocar(d, tamano),
            onScaleStart: _empezarEscala,
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
