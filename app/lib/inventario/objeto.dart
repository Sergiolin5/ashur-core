// Un objeto del inventario físico (contracts/objeto.schema.json, docs/adr/0014-inventario.md).
class Objeto {
  const Objeto({
    required this.id,
    required this.nombre,
    required this.lugar,
    required this.archivado,
    required this.menciones,
  });

  final String id;
  final String nombre;
  final String? lugar;
  final bool archivado;
  final int menciones;

  factory Objeto.fromJson(Map<String, dynamic> json) => Objeto(
        id: json['id'] as String,
        nombre: json['nombre'] as String,
        lugar: json['lugar'] as String?,
        archivado: json['archivado'] as bool,
        menciones: (json['menciones'] as num).toInt(),
      );

  Map<String, dynamic> aJson() => {
        'id': id,
        'nombre': nombre,
        'lugar': lugar,
        'archivado': archivado,
        'menciones': menciones,
      };
}
