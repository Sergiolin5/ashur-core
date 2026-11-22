import 'dart:ui' show DisplayFeature, DisplayFeatureType;

import 'package:flutter/widgets.dart';

// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart' show DefaultCupertinoLocalizations;
import 'package:flutter/services.dart' show rootBundle;

import 'conexion/almacen.dart';
import 'conexion/fuente.dart';
import 'conexion/pantalla_estado.dart';
import 'galaxia/modelo.dart';
import 'galaxia/vista.dart';
import 'pantallas.dart';

void main() {
  final fuente = FuenteGalaxia(
    almacen: AlmacenLlavero(),
    cache: CacheEnMemoria(),
    cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
  );
  runApp(AppAshur(fuente: fuente));
  fuente.actualizar();
}

class AppAshur extends StatelessWidget {
  const AppAshur({super.key, required this.fuente});

  final FuenteGalaxia fuente;

  @override
  Widget build(BuildContext context) {
    return WidgetsApp(
      title: 'Ashur',
      color: colorFondo,
      textStyle: const TextStyle(color: colorTexto, fontSize: 15),
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [DefaultWidgetsLocalizations.delegate, DefaultCupertinoLocalizations.delegate],
      pageRouteBuilder: <T>(RouteSettings ajustes, WidgetBuilder constructor) =>
          PageRouteBuilder<T>(
            settings: ajustes,
            pageBuilder: (context, animacion, secundaria) => constructor(context),
          ),
      home: Inicio(fuente: fuente),
    );
  }
}

/// Pantalla de inicio: la galaxia y, abajo, las tres pestañas.
class Inicio extends StatelessWidget {
  const Inicio({super.key, required this.fuente});

  final FuenteGalaxia fuente;

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
              child: ListenableBuilder(
                listenable: fuente,
                builder: (context, _) {
                  final galaxia = fuente.galaxia;
                  // Sin datos todavía (o con un core configurado que nunca respondió), no se muestra el ejemplo.
                  if (galaxia == null) return const Center(child: Text('Esperando al core'));
                  return VistaGalaxia(
                    estado: galaxia,
                    alTocarNucleo: (punto, tamano) => Navigator.of(context)
                        .push(rutaZoom(const PantallaVacia(titulo: 'Chats'), punto, tamano)),
                  );
                },
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
                        onTap: () => Navigator.of(context).push(rutaSimple(
                            nombre == 'Estado' ? PantallaEstado(fuente: fuente) : PantallaVacia(titulo: nombre))),
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
