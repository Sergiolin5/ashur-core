import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

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
    super.dispose();
  }

  void _tocar(TapUpDetails d, Size tamano) {
    final estado = _estado;
    if (estado == null) return;
    final g = Geometria(estado, tamano, _tiempo.value);
    final nucleo = g.nucleo;
    if (nucleo == null) return;
    final alcance = g.radio(nucleo) < 22 ? 22 : g.radio(nucleo);
    if ((d.localPosition - g.posicion(nucleo.id, _tiempo.value)).distance <= alcance) {
      widget.alTocarNucleo(d.localPosition, tamano);
    }
  }

  @override
  Widget build(BuildContext context) {
    final estado = _estado;
    if (estado == null) return const SizedBox.expand();
    return LayoutBuilder(
      builder: (context, restricciones) {
        final tamano = restricciones.biggest;
        return GestureDetector(
          onTapUp: (d) => _tocar(d, tamano),
          child: CustomPaint(
            size: tamano,
            painter: PintorGalaxia(estado: estado, tiempo: _tiempo),
          ),
        );
      },
    );
  }
}
