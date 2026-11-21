// Cámara de la galaxia: zoom y desplazamiento. Las fórmulas están en docs/GALAXIA.md («Zoom y nivel de detalle»).
import 'dart:math' as math;

import 'package:flutter/widgets.dart';

/// Zoom máximo. Con 1 se ve la galaxia entera.
const zoomMaximo = 40.0;

/// Radio en pantalla, en píxeles, desde el que algo empieza a verse y desde el que se ve del todo.
const radioVisibleMin = 1.5; // r_min
const radioVisibleTotal = 6.0; // r_full

/// Un planeta muestra a sus personajes cuando mide al menos esto en pantalla, en píxeles.
const radioPlanetaConPersonajes = 40.0;

/// Por debajo de esto, en píxeles, no se dibuja.
const radioMinimoDibujo = 0.3;

/// Cuánto puede alejarse el centro de la galaxia del centro de la pantalla, en mitades del lado corto.
const desplazamientoMaximo = 1.2;

@immutable
class Camara {
  const Camara({this.zoom = 1, this.desplazamiento = Offset.zero});

  /// z: cuánto se acerca la vista.
  final double zoom;

  /// d: cuánto se movió la vista, en píxeles.
  final Offset desplazamiento;

  static const inicial = Camara();

  /// s = c + z (w − c) + d
  Offset aPantalla(Offset mundo, Offset centro) => centro + (mundo - centro) * zoom + desplazamiento;

  /// w = c + (s − c − d) / z
  Offset aMundo(Offset pantalla, Offset centro) => centro + (pantalla - centro - desplazamiento) / zoom;

  /// Acerca o aleja alrededor del punto [foco] de la pantalla, sin moverlo: d' = f − c − z'(w_f − c).
  Camara acercar(double nuevoZoom, Offset foco, Size tamano) {
    final centro = tamano.center(Offset.zero);
    final z = nuevoZoom.clamp(1.0, zoomMaximo);
    final debajo = aMundo(foco, centro);
    return Camara(zoom: z, desplazamiento: foco - centro - (debajo - centro) * z).limitada(tamano);
  }

  /// Mueve la vista [delta] píxeles.
  Camara mover(Offset delta, Size tamano) =>
      Camara(zoom: zoom, desplazamiento: desplazamiento + delta).limitada(tamano);

  /// En z = 1 la galaxia vuelve al centro; si no, su centro no se aleja más de lo permitido.
  Camara limitada(Size tamano) {
    if (zoom <= 1) return inicial;
    final limite = desplazamientoMaximo * math.min(tamano.width, tamano.height) / 2 * zoom;
    final d = desplazamiento.distance;
    return d <= limite ? this : Camara(zoom: zoom, desplazamiento: desplazamiento * (limite / d));
  }
}

/// α = clamp((zR − r_min) / (r_full − r_min), 0, 1), con zR el radio en pantalla.
double opacidadPorTamano(double radioEnPantalla) =>
    ((radioEnPantalla - radioVisibleMin) / (radioVisibleTotal - radioVisibleMin)).clamp(0.0, 1.0);
