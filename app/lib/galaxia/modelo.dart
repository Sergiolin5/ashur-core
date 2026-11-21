// Modelo Dart del contrato contracts/galaxy-state.schema.json.
import 'dart:convert';

import 'package:flutter/services.dart';

const rutaEjemplo = '../contracts/galaxy-state.ejemplo.json';

enum TipoCuerpo { nucleo, agente, planeta, asteroide }

enum TipoEvento { llega, crea, transforma }

class Orbita {
  const Orbita({required this.centro, required this.fase});

  final String centro;
  final double fase;

  factory Orbita.fromJson(Map<String, dynamic> j) => Orbita(
        centro: j['centro'] as String,
        fase: (j['fase'] as num).toDouble(),
      );
}

class Cuerpo {
  const Cuerpo({
    required this.tipo,
    required this.id,
    required this.nombre,
    required this.masa,
    required this.orbita,
  });

  final TipoCuerpo tipo;
  final String id;
  final String nombre;
  final double masa;
  final Orbita? orbita;

  factory Cuerpo.fromJson(Map<String, dynamic> j) => Cuerpo(
        tipo: TipoCuerpo.values.byName(j['tipo'] as String),
        id: j['id'] as String,
        nombre: j['nombre'] as String,
        masa: (j['masa'] as num).toDouble(),
        orbita: j['orbita'] == null
            ? null
            : Orbita.fromJson(j['orbita'] as Map<String, dynamic>),
      );
}

class Evento {
  const Evento({required this.tipo, required this.origen, required this.destino});

  final TipoEvento tipo;
  final String origen;
  final String destino;

  factory Evento.fromJson(Map<String, dynamic> j) => Evento(
        tipo: TipoEvento.values.byName(j['tipo'] as String),
        origen: j['origen'] as String,
        destino: j['destino'] as String,
      );
}

class EstadoGalaxia {
  const EstadoGalaxia({required this.cuerpos, required this.eventos});

  final List<Cuerpo> cuerpos;
  final List<Evento> eventos;

  factory EstadoGalaxia.fromJson(Map<String, dynamic> j) => EstadoGalaxia(
        cuerpos: [
          for (final c in j['cuerpos'] as List) Cuerpo.fromJson(c as Map<String, dynamic>)
        ],
        eventos: [
          for (final e in j['eventos'] as List) Evento.fromJson(e as Map<String, dynamic>)
        ],
      );

  static Future<EstadoGalaxia> cargar(AssetBundle bundle, [String ruta = rutaEjemplo]) async =>
      EstadoGalaxia.fromJson(jsonDecode(await bundle.loadString(ruta)) as Map<String, dynamic>);
}
