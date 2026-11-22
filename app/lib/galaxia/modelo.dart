// Modelo Dart del contrato contracts/galaxy-state.schema.json.
import 'dart:convert';

import 'package:flutter/services.dart';

const rutaEjemplo = '../contracts/galaxy-state.ejemplo.json';

enum TipoCuerpo { nucleo, agente, planeta, asteroide, personaje, luna }

enum TipoRef { identidad, modulo, agente }

enum TipoEvento { llega, crea, transforma }

class Orbita {
  const Orbita({required this.centro, required this.fase});

  final String centro;
  final double fase;

  factory Orbita.fromJson(Map<String, dynamic> j) => Orbita(
        centro: j['centro'] as String,
        fase: (j['fase'] as num).toDouble(),
      );

  Map<String, dynamic> aJson() => {'centro': centro, 'fase': fase};
}

/// La cosa real del sistema que representa un cuerpo.
class Ref {
  const Ref({required this.tipo, required this.id});

  final TipoRef tipo;
  final String id;

  factory Ref.fromJson(Map<String, dynamic> j) => Ref(
        tipo: TipoRef.values.byName(j['tipo'] as String),
        id: j['id'] as String,
      );

  Map<String, dynamic> aJson() => {'tipo': tipo.name, 'id': id};
}

/// Lo que hace crecer el polvo: desde cuándo aprende Ashur y cuántos recuerdos tiene.
class Aprendizaje {
  const Aprendizaje({required this.inicio, required this.recuerdos});

  final DateTime inicio;
  final int recuerdos;

  factory Aprendizaje.fromJson(Map<String, dynamic> j) => Aprendizaje(
        inicio: DateTime.parse(j['inicio'] as String),
        recuerdos: j['recuerdos'] as int,
      );

  Map<String, dynamic> aJson() => {'inicio': inicio.toIso8601String(), 'recuerdos': recuerdos};
}

class Cuerpo {
  const Cuerpo({
    required this.tipo,
    required this.id,
    required this.nombre,
    required this.masa,
    required this.orbita,
    required this.ref,
  });

  final TipoCuerpo tipo;
  final String id;
  final String nombre;
  final double masa;
  final Orbita? orbita;
  final Ref? ref;

  factory Cuerpo.fromJson(Map<String, dynamic> j) => Cuerpo(
        tipo: TipoCuerpo.values.byName(j['tipo'] as String),
        id: j['id'] as String,
        nombre: j['nombre'] as String,
        masa: (j['masa'] as num).toDouble(),
        orbita: j['orbita'] == null
            ? null
            : Orbita.fromJson(j['orbita'] as Map<String, dynamic>),
        ref: j['ref'] == null ? null : Ref.fromJson(j['ref'] as Map<String, dynamic>),
      );

  Map<String, dynamic> aJson() => {
        'tipo': tipo.name,
        'id': id,
        'nombre': nombre,
        'masa': masa,
        'orbita': orbita?.aJson(),
        'ref': ref?.aJson(),
      };
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

  Map<String, dynamic> aJson() => {'tipo': tipo.name, 'origen': origen, 'destino': destino};
}

class EstadoGalaxia {
  const EstadoGalaxia({required this.aprendizaje, required this.cuerpos, required this.eventos});

  final Aprendizaje aprendizaje;
  final List<Cuerpo> cuerpos;
  final List<Evento> eventos;

  factory EstadoGalaxia.fromJson(Map<String, dynamic> j) => EstadoGalaxia(
        aprendizaje: Aprendizaje.fromJson(j['aprendizaje'] as Map<String, dynamic>),
        cuerpos: [
          for (final c in j['cuerpos'] as List) Cuerpo.fromJson(c as Map<String, dynamic>)
        ],
        eventos: [
          for (final e in j['eventos'] as List) Evento.fromJson(e as Map<String, dynamic>)
        ],
      );

  Map<String, dynamic> aJson() => {
        'aprendizaje': aprendizaje.aJson(),
        'cuerpos': [for (final c in cuerpos) c.aJson()],
        'eventos': [for (final e in eventos) e.aJson()],
      };

  static Future<EstadoGalaxia> cargar(AssetBundle bundle, [String ruta = rutaEjemplo]) async =>
      EstadoGalaxia.fromJson(jsonDecode(await bundle.loadString(ruta)) as Map<String, dynamic>);
}
