import 'package:flutter/widgets.dart';

const colorFondo = Color(0xFF05060B);
const colorTexto = Color(0xFFE8E8F0);

/// Pantalla vacía con un encabezado y una flecha para volver.
class PantallaVacia extends StatelessWidget {
  const PantallaVacia({super.key, required this.titulo});

  final String titulo;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: colorFondo,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => Navigator.of(context).pop(),
                    child: const Padding(
                      padding: EdgeInsets.only(right: 16),
                      child: Text('‹', style: TextStyle(fontSize: 28)),
                    ),
                  ),
                  Text(titulo, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                ],
              ),
            ),
            const Expanded(child: SizedBox()),
          ],
        ),
      ),
    );
  }
}

/// Transición de zoom hacia adentro, centrada en el punto tocado.
Route<void> rutaZoom(Widget pantalla, Offset punto, Size tamano) {
  final alineacion = Alignment(
    tamano.width == 0 ? 0 : punto.dx / tamano.width * 2 - 1,
    tamano.height == 0 ? 0 : punto.dy / tamano.height * 2 - 1,
  );
  return PageRouteBuilder<void>(
    transitionDuration: const Duration(milliseconds: 500),
    reverseTransitionDuration: const Duration(milliseconds: 350),
    pageBuilder: (context, animacion, secundaria) => pantalla,
    transitionsBuilder: (context, animacion, secundaria, hijo) {
      final curva = CurvedAnimation(parent: animacion, curve: Curves.easeInCubic);
      return FadeTransition(
        opacity: curva,
        child: ScaleTransition(
          alignment: alineacion,
          scale: Tween<double>(begin: 0.05, end: 1).animate(curva),
          child: hijo,
        ),
      );
    },
  );
}

/// Transición simple para las pestañas.
Route<void> rutaSimple(Widget pantalla) => PageRouteBuilder<void>(
      transitionDuration: const Duration(milliseconds: 200),
      pageBuilder: (context, animacion, secundaria) => pantalla,
      transitionsBuilder: (context, animacion, secundaria, hijo) =>
          FadeTransition(opacity: animacion, child: hijo),
    );
