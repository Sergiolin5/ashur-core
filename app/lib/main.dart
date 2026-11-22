import 'dart:ui' show DisplayFeature, DisplayFeatureType;

import 'package:flutter/widgets.dart';

import 'galaxia/vista.dart';
import 'pantallas.dart';

void main() {
  runApp(const AppAshur());
}

class AppAshur extends StatelessWidget {
  const AppAshur({super.key});

  @override
  Widget build(BuildContext context) {
    return WidgetsApp(
      title: 'Ashur',
      color: colorFondo,
      textStyle: const TextStyle(color: colorTexto, fontSize: 15),
      debugShowCheckedModeBanner: false,
      pageRouteBuilder: <T>(RouteSettings ajustes, WidgetBuilder constructor) =>
          PageRouteBuilder<T>(
            settings: ajustes,
            pageBuilder: (context, animacion, secundaria) => constructor(context),
          ),
      home: const Inicio(),
    );
  }
}

/// Pantalla de inicio: la galaxia y, abajo, las tres pestañas.
class Inicio extends StatelessWidget {
  const Inicio({super.key});

  static const pestanas = ['Estado', 'Casa', 'Workbench'];

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: colorFondo,
      child: Column(
        children: [
          Expanded(
            // Con el teléfono abierto, la galaxia queda en la mitad derecha, como se ve con el teléfono cerrado.
            child: Padding(
              padding: EdgeInsets.only(left: margenPorPliegue(MediaQuery.displayFeaturesOf(context))),
              child: VistaGalaxia(
                alTocarNucleo: (punto, tamano) => Navigator.of(context)
                    .push(rutaZoom(const PantallaVacia(titulo: 'Chats'), punto, tamano)),
              ),
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Row(
                children: [
                  for (final nombre in pestanas)
                    Expanded(
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => Navigator.of(context)
                            .push(rutaSimple(PantallaVacia(titulo: nombre))),
                        child: Center(child: Text(nombre)),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Cuánto correr la galaxia a la derecha: hasta el borde derecho de un pliegue o bisagra vertical, si la pantalla
/// tiene uno. Sin pliegue, 0.
double margenPorPliegue(List<DisplayFeature> caracteristicas) {
  for (final c in caracteristicas) {
    final esPliegue = c.type == DisplayFeatureType.fold || c.type == DisplayFeatureType.hinge;
    if (esPliegue && c.bounds.height > c.bounds.width) return c.bounds.right;
  }
  return 0;
}
