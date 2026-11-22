import 'package:flutter/widgets.dart';

import 'diseno.dart';

const colorFondo = PaletaAshur.fondo;
const colorTexto = PaletaAshur.texto;

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
            CabeceraAshur(
              titulo: titulo,
              alVolver: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 560),
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 30,
                        vertical: 38,
                      ),
                      decoration: panelAshur(elevado: true),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 88,
                            height: 88,
                            decoration: BoxDecoration(
                              color: PaletaAshur.fondo.withValues(alpha: 0.55),
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: PaletaAshur.borde,
                                width: 0.7,
                              ),
                            ),
                            alignment: Alignment.center,
                            child: const MarcaAshur(tamano: 66),
                          ),
                          if (titulo == 'Chats') ...[
                            const SizedBox(height: 12),
                            Container(
                              width: 6,
                              height: 6,
                              decoration: const BoxDecoration(
                                color: PaletaAshur.ambar,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ],
                          const SizedBox(height: 20),
                          Text(
                            titulo == 'Chats'
                                ? 'Un espacio cercano para conversar'
                                : titulo,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: PaletaAshur.texto,
                              fontSize: 20,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Este espacio está preparado para cuando su contenido esté conectado.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: PaletaAshur.textoSuave,
                              fontSize: 14,
                              height: 1.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
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
      if (MediaQuery.disableAnimationsOf(context)) return hijo;
      final curva = CurvedAnimation(
        parent: animacion,
        curve: Curves.easeInCubic,
      );
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
  transitionsBuilder: (context, animacion, secundaria, hijo) {
    if (MediaQuery.disableAnimationsOf(context)) return hijo;
    return FadeTransition(opacity: animacion, child: hijo);
  },
);
