// Dibujo de la galaxia. Las fórmulas son las de docs/GALAXIA.md (sección «Modelo matemático»)
// y los parámetros están registrados en docs/adr/0002-render-galaxia.md.
import 'dart:math' as math;

import 'package:flutter/widgets.dart';

import 'modelo.dart';

// ── Reglas elegidas por Sergio (2026-11-21) ──
/// true: los planetas más pesados orbitan más cerca del núcleo.
const pesadosCerca = true;

/// true: las órbitas lejanas son más lentas (Kepler, T ∝ d^{3/2}); false: todos los planetas con el mismo
/// periodo T_0, es decir, la misma velocidad angular.
const periodoKepler = false;

// ── Parámetros del cliente, como fracción de la mitad del lado corto de la pantalla ──
const radioNucleo = 0.09;
const radioPlanetaMin = 0.025; // R_min
const radioPlanetaMax = 0.06; // R_max
const distanciaMin = 0.34; // d_min
const distanciaMax = 0.88; // d_max
const distanciaAgente = 0.17;
const radioAgente = 0.012;
const distanciaAsteroide = 0.035; // por fuera del radio del planeta que bloquea
const radioAsteroide = 0.009;

// ── Parámetros de tiempo, en segundos ──
const periodoBase = 24.0; // T_0
const periodoAgente = 7.0;
const periodoAsteroide = 5.0;
const duracionEstrella = 2.4; // τ
const cicloEstrellas = 7.0; // cada estrella se repite en bucle; el contrato aún no trae instantes
const desfaseEstrellas = 2.3;

// ── Polvo ──
const brazos = 2; // N
const espiralA = 0.06; // a
const espiralB = 0.28; // b
const vueltasBrazo = 2.6; // hasta qué ángulo llega cada brazo, en vueltas
const omegaPolvo = 0.03; // ω, rad/s
const densidadPolvo = 700; // ρ fija: el contrato aún no trae t_A

const _fondo = Color(0xFF05060B);
const _colorNucleo = Color(0xFFFFE6A8);
const _colorAgente = Color(0xFF9FD8FF);
const _colorPlaneta = Color(0xFF8C9EFF);
const _colorAsteroide = Color(0xFF9E8F80);
const _colorEstrella = Color(0xFFFFFFFF);
const _colorPolvo = Color(0xFFB8A6FF);

/// Geometría de la galaxia en un instante: dónde está cada cuerpo y qué tamaño tiene.
class Geometria {
  Geometria(this.estado, Size tamano, double t)
      : centro = tamano.center(Offset.zero),
        escala = math.min(tamano.width, tamano.height) / 2 {
    final planetas = estado.cuerpos.where((c) => c.tipo == TipoCuerpo.planeta);
    _masaMax = planetas.isEmpty ? 1 : planetas.map((c) => c.masa).reduce(math.max);
    if (_masaMax <= 0) _masaMax = 1;
    for (final c in estado.cuerpos) {
      _porId[c.id] = c;
    }
    for (final c in estado.cuerpos) {
      posicion(c.id, t);
    }
  }

  final EstadoGalaxia estado;
  final Offset centro;
  final double escala;
  late double _masaMax;
  final _porId = <String, Cuerpo>{};
  final _posiciones = <String, Offset>{};

  double masaNormalizada(Cuerpo c) => (c.masa / _masaMax).clamp(0.0, 1.0);

  double radio(Cuerpo c) => escala *
      switch (c.tipo) {
        TipoCuerpo.nucleo => radioNucleo,
        TipoCuerpo.agente => radioAgente,
        TipoCuerpo.asteroide => radioAsteroide,
        TipoCuerpo.planeta =>
          radioPlanetaMin + (radioPlanetaMax - radioPlanetaMin) * math.sqrt(masaNormalizada(c)),
      };

  double _distancia(Cuerpo c) {
    switch (c.tipo) {
      case TipoCuerpo.nucleo:
        return 0;
      case TipoCuerpo.agente:
        return escala * distanciaAgente;
      case TipoCuerpo.asteroide:
        final planeta = _porId[c.orbita!.centro];
        return (planeta == null ? 0 : radio(planeta)) + escala * distanciaAsteroide;
      case TipoCuerpo.planeta:
        final m = masaNormalizada(c);
        final f = pesadosCerca ? 1 - m : m;
        return escala * (distanciaMin + (distanciaMax - distanciaMin) * f);
    }
  }

  double _periodo(Cuerpo c, double d) => switch (c.tipo) {
        TipoCuerpo.nucleo => 1,
        TipoCuerpo.agente => periodoAgente,
        TipoCuerpo.asteroide => periodoAsteroide,
        TipoCuerpo.planeta =>
          periodoKepler ? periodoBase * math.pow(d / (escala * distanciaMin), 1.5) : periodoBase,
      };

  /// p_i(t) = c_i + d_i (cos θ_i, sin θ_i), con θ_i(t) = 2π(φ_i + t / T_i).
  Offset posicion(String id, double t) {
    final ya = _posiciones[id];
    if (ya != null) return ya;
    final c = _porId[id];
    if (c == null || c.orbita == null) return _posiciones[id] = centro;
    _posiciones[id] = centro; // evita ciclos si el contrato trae una órbita circular
    final base = posicion(c.orbita!.centro, t);
    final d = _distancia(c);
    final theta = 2 * math.pi * (c.orbita!.fase + t / _periodo(c, d));
    return _posiciones[id] = base + Offset(math.cos(theta), math.sin(theta)) * d;
  }

  Cuerpo? get nucleo {
    for (final c in estado.cuerpos) {
      if (c.tipo == TipoCuerpo.nucleo) return c;
    }
    return null;
  }
}

class PintorGalaxia extends CustomPainter {
  PintorGalaxia({required this.estado, required this.tiempo}) : super(repaint: tiempo);

  final EstadoGalaxia estado;
  final ValueNotifier<double> tiempo;

  // Posición fija de cada grano de polvo a lo largo de su brazo, con una semilla constante.
  static final List<(int, double, double)> _granos = () {
    final azar = math.Random(7);
    return [
      for (var i = 0; i < densidadPolvo; i++)
        (i % brazos, azar.nextDouble(), azar.nextDouble() * 2 - 1),
    ];
  }();

  @override
  void paint(Canvas canvas, Size size) {
    final t = tiempo.value;
    final g = Geometria(estado, size, t);
    canvas.drawRect(Offset.zero & size, Paint()..color = _fondo);
    _polvo(canvas, g, t);
    _orbitas(canvas, g);
    for (final c in estado.cuerpos) {
      _cuerpo(canvas, g, c, g.posicion(c.id, t));
    }
    _estrellas(canvas, g, t);
  }

  /// r_k(θ) = a e^{bθ}, con θ ↦ θ + 2πk/N + ωt.
  void _polvo(Canvas canvas, Geometria g, double t) {
    final pintura = Paint();
    final thetaMax = vueltasBrazo * 2 * math.pi;
    for (final (k, avance, dispersion) in _granos) {
      final theta = avance * thetaMax;
      final r = g.escala * espiralA * math.exp(espiralB * theta);
      if (r > g.escala * 1.3) continue;
      final ang = theta + 2 * math.pi * k / brazos + omegaPolvo * t + dispersion * 0.35;
      final p = g.centro + Offset(math.cos(ang), math.sin(ang)) * r;
      pintura.color = _colorPolvo.withValues(alpha: 0.10 + 0.25 * (1 - avance));
      canvas.drawCircle(p, 0.8 + 1.2 * (1 - avance), pintura);
    }
  }

  void _orbitas(Canvas canvas, Geometria g) {
    final pintura = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.6
      ..color = const Color(0x22FFFFFF);
    for (final c in estado.cuerpos) {
      if (c.tipo != TipoCuerpo.planeta) continue;
      canvas.drawCircle(g.centro, (g.posicion(c.id, tiempo.value) - g.centro).distance, pintura);
    }
  }

  void _cuerpo(Canvas canvas, Geometria g, Cuerpo c, Offset p) {
    final r = g.radio(c);
    switch (c.tipo) {
      case TipoCuerpo.nucleo:
        canvas.drawCircle(
          p,
          r * 2.2,
          Paint()
            ..shader = RadialGradient(colors: [
              _colorNucleo.withValues(alpha: 0.45),
              _colorNucleo.withValues(alpha: 0),
            ]).createShader(Rect.fromCircle(center: p, radius: r * 2.2)),
        );
        canvas.drawCircle(p, r, Paint()..color = _colorNucleo);
      case TipoCuerpo.agente:
        canvas.drawCircle(p, r, Paint()..color = _colorAgente);
      case TipoCuerpo.planeta:
        canvas.drawCircle(p, r, Paint()..color = _colorPlaneta);
      case TipoCuerpo.asteroide:
        final camino = Path();
        for (var i = 0; i < 6; i++) {
          final a = i * math.pi / 3;
          final ri = r * (i.isEven ? 1.0 : 0.7);
          final q = p + Offset(math.cos(a), math.sin(a)) * ri;
          i == 0 ? camino.moveTo(q.dx, q.dy) : camino.lineTo(q.dx, q.dy);
        }
        canvas.drawPath(camino..close(), Paint()..color = _colorAsteroide);
    }
  }

  /// e(t) = (1 − s) p_origen(t) + s p_destino(t), con s = (t − t_0) / τ.
  void _estrellas(Canvas canvas, Geometria g, double t) {
    for (var i = 0; i < estado.eventos.length; i++) {
      final e = estado.eventos[i];
      final local = (t - i * desfaseEstrellas) % cicloEstrellas;
      if (t < i * desfaseEstrellas || local > duracionEstrella) continue;
      final s = local / duracionEstrella;
      final cabeza = Offset.lerp(g.posicion(e.origen, t), g.posicion(e.destino, t), s)!;
      final cola = Offset.lerp(g.posicion(e.origen, t), g.posicion(e.destino, t), math.max(0, s - 0.12))!;
      canvas.drawLine(
        cola,
        cabeza,
        Paint()
          ..strokeWidth = 1.6
          ..strokeCap = StrokeCap.round
          ..shader = LinearGradient(colors: [
            _colorEstrella.withValues(alpha: 0),
            _colorEstrella,
          ]).createShader(Rect.fromPoints(cola, cabeza)),
      );
      canvas.drawCircle(cabeza, 2.2, Paint()..color = _colorEstrella);
    }
  }

  @override
  bool shouldRepaint(PintorGalaxia old) => old.estado != estado;
}
