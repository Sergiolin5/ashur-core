import 'dart:math' as math;

import 'package:flutter/widgets.dart';

/// Tokens visuales compartidos por la app. No son ajustes configurables.
abstract final class PaletaAshur {
  static const fondo = Color(0xFF05060B);
  static const superficie = Color(0xFF111520);
  static const superficieElevada = Color(0xFF171D2A);
  static const texto = Color(0xFFE8EDF5);
  static const textoSuave = Color(0xFFAAB4C4);
  static const plata = Color(0xFFC9D2E0);
  static const azul = Color(0xFF5C9FC7);
  static const cian = Color(0xFF3CC7E6);
  static const ambar = Color(0xFFD8A977);
  static const borde = Color(0x4DC9D2E0);
}

BoxDecoration panelAshur({bool elevado = false}) => BoxDecoration(
  color: elevado ? PaletaAshur.superficieElevada : PaletaAshur.superficie,
  borderRadius: BorderRadius.circular(14),
  border: Border.all(color: PaletaAshur.borde, width: 0.7),
  boxShadow: const [
    BoxShadow(color: Color(0x160E8BBB), blurRadius: 22, spreadRadius: -8),
  ],
);

BoxDecoration campoAshur() => BoxDecoration(
  color: PaletaAshur.superficie,
  borderRadius: BorderRadius.circular(10),
  border: Border.all(color: const Color(0x55C9D2E0), width: 0.7),
);

/// Firma visual abstracta de Ashur: núcleo luminoso y órbitas contenidas.
class MarcaAshur extends StatelessWidget {
  const MarcaAshur({super.key, this.tamano = 34, this.conNombre = false});

  final double tamano;
  final bool conNombre;

  @override
  Widget build(BuildContext context) {
    final marca = Semantics(
      label: 'Núcleo y órbitas de Ashur',
      child: SizedBox.square(
        dimension: tamano,
        child: const CustomPaint(painter: _PintorMarca()),
      ),
    );
    if (!conNombre) return marca;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        marca,
        const SizedBox(width: 10),
        Text(
          'Ashur',
          style: TextStyle(
            color: PaletaAshur.plata,
            fontFamily: 'serif',
            fontSize: tamano * 0.66,
            height: 1,
            letterSpacing: 0.2,
          ),
        ),
      ],
    );
  }
}

class _PintorMarca extends CustomPainter {
  const _PintorMarca();

  @override
  void paint(Canvas canvas, Size size) {
    final centro = size.center(Offset.zero);
    final escala = size.shortestSide;
    final trazo = escala * 0.025;
    final orbital = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = trazo
      ..color = PaletaAshur.plata.withValues(alpha: 0.76);
    canvas.save();
    canvas.translate(centro.dx, centro.dy);
    canvas.rotate(-math.pi / 5);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: escala * 0.9,
        height: escala * 0.43,
      ),
      orbital,
    );
    canvas.rotate(math.pi / 2.2);
    orbital.color = PaletaAshur.azul.withValues(alpha: 0.82);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: escala * 0.76,
        height: escala * 0.34,
      ),
      orbital,
    );
    canvas.restore();
    canvas.drawCircle(
      centro,
      escala * 0.105,
      Paint()
        ..color = PaletaAshur.cian.withValues(alpha: 0.42)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, escala * 0.11),
    );
    canvas.drawCircle(
      centro,
      escala * 0.075,
      Paint()..color = PaletaAshur.cian,
    );
  }

  @override
  bool shouldRepaint(covariant _PintorMarca oldDelegate) => false;
}

class CabeceraAshur extends StatelessWidget {
  const CabeceraAshur({
    super.key,
    required this.titulo,
    this.alVolver,
    this.detalle,
  });

  final String titulo;
  final VoidCallback? alVolver;
  final String? detalle;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(18, 15, 18, 12),
    child: Row(
      children: [
        if (alVolver != null) ...[
          Semantics(
            button: true,
            label: 'Volver',
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: alVolver,
              child: const Padding(
                padding: EdgeInsets.only(right: 15, top: 4, bottom: 4),
                child: Text(
                  '‹',
                  style: TextStyle(
                    color: PaletaAshur.plata,
                    fontSize: 30,
                    height: 1,
                  ),
                ),
              ),
            ),
          ),
        ] else ...[
          const MarcaAshur(tamano: 32),
          const SizedBox(width: 11),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                titulo,
                style: const TextStyle(
                  color: PaletaAshur.texto,
                  fontSize: 21,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.1,
                ),
              ),
              if (detalle != null) ...[
                const SizedBox(height: 3),
                Text(
                  detalle!,
                  style: const TextStyle(
                    color: PaletaAshur.textoSuave,
                    fontSize: 12,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    ),
  );
}

class IconoMenuAshur extends StatelessWidget {
  const IconoMenuAshur({super.key, required this.alTocar});

  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: 'Abrir inventario',
    child: GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: alTocar,
      child: Container(
        width: 42,
        height: 42,
        decoration: panelAshur(),
        alignment: Alignment.center,
        child: const CustomPaint(size: Size(18, 14), painter: _PintorMenu()),
      ),
    ),
  );
}

class _PintorMenu extends CustomPainter {
  const _PintorMenu();

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..color = PaletaAshur.plata
      ..strokeWidth = 1.4
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 3; i++) {
      final y = size.height * (i + 0.5) / 3;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), p);
    }
  }

  @override
  bool shouldRepaint(covariant _PintorMenu oldDelegate) => false;
}
