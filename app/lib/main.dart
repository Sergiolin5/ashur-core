import 'dart:ui' show DisplayFeature, DisplayFeatureType;

import 'package:flutter/cupertino.dart'
    show CupertinoButton, CupertinoTheme, CupertinoThemeData;
import 'package:flutter/widgets.dart';

// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart' show DefaultCupertinoLocalizations;
import 'package:flutter/services.dart' show rootBundle;

import 'conexion/almacen.dart';
import 'conexion/cache_archivo.dart';
import 'conexion/fuente.dart';
import 'conexion/pantalla_estado.dart';
import 'diseno.dart';
import 'galaxia/modelo.dart';
import 'galaxia/vista.dart';
import 'inventario/pantalla_inventario.dart';
import 'pantallas.dart';

void main() {
  final fuente = FuenteGalaxia(
    almacen: AlmacenLlavero(),
    cache: CacheArchivo(),
    cargarEjemplo: () => EstadoGalaxia.cargar(rootBundle),
  );
  runApp(AppAshur(fuente: fuente));
  fuente.actualizar();
}

class AppAshur extends StatelessWidget {
  const AppAshur({super.key, required this.fuente});

  final FuenteGalaxia fuente;

  @override
  Widget build(BuildContext context) => CupertinoTheme(
    data: const CupertinoThemeData(
      brightness: Brightness.dark,
      primaryColor: PaletaAshur.azul,
    ),
    child: WidgetsApp(
      title: 'Ashur',
      color: colorFondo,
      textStyle: const TextStyle(color: colorTexto, fontSize: 15),
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        DefaultWidgetsLocalizations.delegate,
        DefaultCupertinoLocalizations.delegate,
      ],
      pageRouteBuilder: <T>(RouteSettings ajustes, WidgetBuilder constructor) =>
          PageRouteBuilder<T>(
            settings: ajustes,
            pageBuilder: (context, animacion, secundaria) =>
                constructor(context),
          ),
      home: Inicio(fuente: fuente),
    ),
  );
}

/// Pantalla de inicio: la galaxia y la navegación principal.
class Inicio extends StatelessWidget {
  const Inicio({super.key, required this.fuente});

  final FuenteGalaxia fuente;

  static const pestanas = ['Estado', 'Casa', 'Workbench'];

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: colorFondo,
    child: Stack(
      children: [
        Column(
          children: [
            Expanded(
              // En un dispositivo plegable, la galaxia ocupa el panel derecho.
              child: Padding(
                padding: EdgeInsets.only(
                  left: margenPorPliegue(MediaQuery.displayFeaturesOf(context)),
                ),
                child: ListenableBuilder(
                  listenable: fuente,
                  builder: (context, _) {
                    final galaxia = fuente.galaxia;
                    if (galaxia == null) {
                      return const Center(
                        child: Text(
                          'Esperando al core',
                          style: TextStyle(color: PaletaAshur.textoSuave),
                        ),
                      );
                    }
                    return VistaGalaxia(
                      estado: galaxia,
                      alTocarNucleo: (punto, tamano) => Navigator.of(context)
                          .push(
                            rutaZoom(
                              const PantallaVacia(titulo: 'Chats'),
                              punto,
                              tamano,
                            ),
                          ),
                      alTocarCuerpo: (cuerpo, punto, tamano) {
                        if (cuerpo == 'objetos') {
                          Navigator.of(context).push(
                            rutaZoom(
                              PantallaInventario(fuente: fuente),
                              punto,
                              tamano,
                            ),
                          );
                        }
                      },
                    );
                  },
                ),
              ),
            ),
            SafeArea(
              top: false,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 620),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                    child: Container(
                      decoration: panelAshur(),
                      child: Row(
                        children: [
                          for (final nombre in pestanas)
                            Expanded(
                              child: CupertinoButton(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 10,
                                ),
                                onPressed: () => Navigator.of(context).push(
                                  rutaSimple(
                                    nombre == 'Estado'
                                        ? PantallaEstado(fuente: fuente)
                                        : PantallaVacia(titulo: nombre),
                                  ),
                                ),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    IconoPestanaAshur(
                                      seccion: switch (nombre) {
                                        'Estado' => SeccionAshur.estado,
                                        'Casa' => SeccionAshur.casa,
                                        _ => SeccionAshur.workbench,
                                      },
                                    ),
                                    const SizedBox(height: 5),
                                    Text(
                                      nombre,
                                      style: const TextStyle(
                                        color: PaletaAshur.plata,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ],
                                ),
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
        SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 0),
            child: Row(
              children: [
                IconoMenuAshur(
                  alTocar: () =>
                      Navigator.of(context)
                          .push(rutaSimple(PantallaInventario(fuente: fuente))),
                ),
                const SizedBox(width: 12),
                const MarcaAshur(conNombre: true),
                const Spacer(),
                ListenableBuilder(
                  listenable: fuente,
                  builder: (context, _) {
                    final conectado = fuente.estado == EstadoConexion.conectado;
                    final conectando =
                        fuente.estado == EstadoConexion.conectando;
                    final estado = switch (fuente.estado) {
                      EstadoConexion.sinConfigurar => 'Sin configurar',
                      EstadoConexion.bloqueada => 'Bloqueado',
                      EstadoConexion.conectando => 'Conectando',
                      EstadoConexion.conectado => 'Conectado',
                      EstadoConexion.sinConexion => 'Sin conexión',
                      EstadoConexion.claveInvalida => 'Clave inválida',
                      EstadoConexion.coreSinClave => 'Core sin clave',
                      EstadoConexion.error => 'Error de conexión',
                    };
                    final color = conectado
                        ? PaletaAshur.cian
                        : conectando
                        ? PaletaAshur.ambar
                        : PaletaAshur.textoSuave;
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 9,
                      ),
                      decoration: panelAshur(),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: color,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            estado,
                            style: TextStyle(color: color, fontSize: 12),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}

/// Cuánto correr la galaxia a la derecha ante un pliegue o bisagra vertical.
double margenPorPliegue(List<DisplayFeature> caracteristicas) {
  for (final c in caracteristicas) {
    final esPliegue =
        c.type == DisplayFeatureType.fold || c.type == DisplayFeatureType.hinge;
    if (esPliegue && c.bounds.height > c.bounds.width) return c.bounds.right;
  }
  return 0;
}
