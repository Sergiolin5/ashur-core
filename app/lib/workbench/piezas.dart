// Piezas visuales de Workbench: colores, tarjetas, botones, pastillas de estado, campos y hojas.
// Campos de texto con pegar: Flutter marca este import como obsoleto en favor del paquete cupertino_ui, que no está
// aprobado. Ver docs/adr/0011-app-conectada-al-core.md.
// ignore: deprecated_member_use
import 'package:flutter/cupertino.dart';

const wbFondo = Color(0xFF08080A);
const wbPanel = Color(0xFF111114);
const wbBorde = Color(0x14FFFFFF);
const wbTexto = Color(0xFFFFFFFF);
const wbTenue = Color(0x8CFFFFFF);
const wbApagado = Color(0x4DFFFFFF);
const wbAcento = Color(0xFFD9A06A);
const wbVerde = Color(0xFF8FBF9E);
const wbTurquesa = Color(0xFF7FB8AE);
const wbAzul = Color(0xFF8FA9D9);
const wbLila = Color(0xFFC7A6D9);
const wbRojo = Color(0xFFC2554B);

const wbEtiqueta = TextStyle(color: wbApagado, fontSize: 10, letterSpacing: 1.6, fontFamily: 'Menlo');
const wbTitulo = TextStyle(color: wbTexto, fontSize: 17, fontWeight: FontWeight.w600);
const wbCuerpo = TextStyle(color: wbTenue, fontSize: 13, height: 1.4);

/// Color y nombre visible de cada estado (tareas, entregas, proveedores, servidores y proyectos).
const _estados = <String, (String, Color)>{
  'cola': ('En cola', wbApagado),
  'asignada': ('Asignada', wbAzul),
  'ejecutando': ('Ejecutando', wbAcento),
  'revision': ('Revisión', wbLila),
  'lista': ('Lista', wbVerde),
  'error': ('Con error', wbRojo),
  'borrador': ('Borrador', wbApagado),
  'compilando': ('Compilando', wbAcento),
  'publicada': ('Publicada', wbVerde),
  'fallida': ('Fallida', wbRojo),
  'activo': ('Activo', wbVerde),
  'pausado': ('En pausa', wbApagado),
  'archivado': ('Archivado', wbApagado),
  'en_linea': ('En línea', wbVerde),
  'sin_conexion': ('Sin conexión', wbRojo),
  'sin_probar': ('Sin probar', wbApagado),
};

class Pastilla extends StatelessWidget {
  const Pastilla(this.estado, {super.key});

  final String estado;

  @override
  Widget build(BuildContext context) {
    final (nombre, color) = _estados[estado] ?? (estado, wbApagado);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(nombre, style: TextStyle(color: color, fontSize: 11)),
    );
  }
}

class Tarjeta extends StatelessWidget {
  const Tarjeta({super.key, required this.child, this.padding = const EdgeInsets.all(16), this.brillo});

  final Widget child;
  final EdgeInsets padding;

  /// Color del resplandor en la esquina superior derecha.
  final Color? brillo;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: wbPanel,
        gradient: brillo == null
            ? null
            : RadialGradient(
                center: Alignment.topRight,
                radius: 1.4,
                colors: [
                  Color.alphaBlend(brillo!.withValues(alpha: 0.32), wbPanel),
                  Color.alphaBlend(brillo!.withValues(alpha: 0.1), wbPanel),
                  wbPanel,
                ],
                stops: const [0, 0.35, 0.7],
              ),
        border: Border.all(color: wbBorde),
        borderRadius: BorderRadius.circular(14),
      ),
      child: child,
    );
  }
}

/// Tarjeta con etiqueta, título y una acción a la derecha.
class Seccion extends StatelessWidget {
  const Seccion({super.key, required this.etiqueta, required this.titulo, this.accion, required this.child});

  final String etiqueta;
  final String titulo;
  final Widget? accion;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Tarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(etiqueta.toUpperCase(), style: wbEtiqueta),
                    const SizedBox(height: 4),
                    Text(titulo, style: wbTitulo),
                  ],
                ),
              ),
              ?accion,
            ],
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class Boton extends StatelessWidget {
  const Boton(this.texto, {super.key, required this.alTocar, this.principal = false, this.peligro = false});

  final String texto;

  /// `null` lo deja apagado.
  final VoidCallback? alTocar;
  final bool principal;
  final bool peligro;

  @override
  Widget build(BuildContext context) {
    final color = peligro ? wbRojo : wbTexto;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: alTocar,
      child: Opacity(
        opacity: alTocar == null ? 0.4 : 1,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            color: principal ? wbAcento : null,
            border: principal ? null : Border.all(color: color.withValues(alpha: 0.2)),
            borderRadius: BorderRadius.circular(9),
          ),
          child: Text(
            texto,
            style: TextStyle(
              color: principal ? const Color(0xFF160F08) : color,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

/// Encabezado de una página: etiqueta, título, descripción y acciones.
class Encabezado extends StatelessWidget {
  const Encabezado({
    super.key,
    required this.etiqueta,
    required this.titulo,
    required this.descripcion,
    this.acciones = const [],
  });

  final String etiqueta;
  final String titulo;
  final String descripcion;
  final List<Widget> acciones;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(etiqueta.toUpperCase(), style: wbEtiqueta.copyWith(color: wbAcento)),
          const SizedBox(height: 8),
          Text(titulo, style: const TextStyle(color: wbTexto, fontSize: 30, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text(descripcion, style: wbCuerpo),
          if (acciones.isNotEmpty) ...[
            const SizedBox(height: 14),
            Wrap(spacing: 8, runSpacing: 8, children: acciones),
          ],
        ],
      ),
    );
  }
}

class Vacio extends StatelessWidget {
  const Vacio({super.key, required this.titulo, required this.descripcion});

  final String titulo;
  final String descripcion;

  @override
  Widget build(BuildContext context) {
    return Tarjeta(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 36),
      child: Column(
        children: [
          Text(titulo, style: wbTitulo, textAlign: TextAlign.center),
          const SizedBox(height: 6),
          Text(descripcion, style: wbCuerpo, textAlign: TextAlign.center),
        ],
      ),
    );
  }
}

/// Barra de cuota usada: verde, ámbar desde 55 % y roja desde 80 %.
class BarraCuota extends StatelessWidget {
  const BarraCuota({super.key, required this.usadas, required this.cuota, this.pausado = false});

  final num usadas;
  final num cuota;
  final bool pausado;

  @override
  Widget build(BuildContext context) {
    final parte = cuota > 0 ? (usadas / cuota).clamp(0.0, 1.0).toDouble() : 0.0;
    final color = pausado
        ? wbApagado
        : parte >= 0.8
            ? wbRojo
            : parte >= 0.55
                ? wbAcento
                : wbTurquesa;
    return ClipRRect(
      borderRadius: BorderRadius.circular(3),
      child: Container(
        height: 5,
        color: const Color(0x14FFFFFF),
        alignment: Alignment.centerLeft,
        child: FractionallySizedBox(widthFactor: parte, child: Container(color: color)),
      ),
    );
  }
}

/// Dato con su etiqueta arriba.
class Dato extends StatelessWidget {
  const Dato(this.etiqueta, this.valor, {super.key});

  final String etiqueta;
  final String valor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(child: Text(etiqueta, style: wbCuerpo)),
          Flexible(child: Text(valor, style: const TextStyle(color: wbTexto, fontSize: 13))),
        ],
      ),
    );
  }
}

class Campo extends StatelessWidget {
  const Campo(this.etiqueta, this.controlador, {super.key, this.pista, this.lineas = 1, this.numero = false});

  final String etiqueta;
  final TextEditingController controlador;
  final String? pista;
  final int lineas;
  final bool numero;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(etiqueta.toUpperCase(), style: wbEtiqueta),
          const SizedBox(height: 6),
          CupertinoTextField(
            controller: controlador,
            placeholder: pista,
            maxLines: lineas,
            keyboardType: numero ? TextInputType.number : null,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
            decoration: BoxDecoration(
              color: const Color(0x08FFFFFF),
              border: Border.all(color: const Color(0x1FFFFFFF)),
              borderRadius: BorderRadius.circular(8),
            ),
            style: const TextStyle(color: wbTexto, fontSize: 14),
            placeholderStyle: const TextStyle(color: wbApagado, fontSize: 14),
          ),
        ],
      ),
    );
  }
}

/// Elige una opción entre varias fichas.
class Selector extends StatelessWidget {
  const Selector(this.etiqueta, {super.key, required this.opciones, required this.valor, required this.alElegir});

  final String etiqueta;

  /// Valor guardado y nombre visible.
  final Map<String, String> opciones;
  final String valor;
  final ValueChanged<String> alElegir;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(etiqueta.toUpperCase(), style: wbEtiqueta),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final o in opciones.entries)
                Ficha(o.value, elegida: o.key == valor, alTocar: () => alElegir(o.key)),
            ],
          ),
        ],
      ),
    );
  }
}

class Ficha extends StatelessWidget {
  const Ficha(this.texto, {super.key, this.elegida = false, this.alTocar});

  final String texto;
  final bool elegida;
  final VoidCallback? alTocar;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: alTocar,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: elegida ? wbAcento.withValues(alpha: 0.12) : null,
          border: Border.all(color: elegida ? wbAcento.withValues(alpha: 0.5) : const Color(0x1FFFFFFF)),
          borderRadius: BorderRadius.circular(7),
        ),
        child: Text(texto, style: TextStyle(color: elegida ? const Color(0xFFEBC49F) : wbTenue, fontSize: 12)),
      ),
    );
  }
}

/// Abre una hoja centrada sobre la pantalla, con título, descripción y el contenido. Se cierra tocando afuera.
Future<T?> abrirHoja<T>(BuildContext context, {required String titulo, String? descripcion, required Widget child}) {
  return Navigator.of(context).push<T>(PageRouteBuilder<T>(
    opaque: false,
    pageBuilder: (context, _, _) => GestureDetector(
      onTap: () => Navigator.of(context).pop(),
      child: ColoredBox(
        color: const Color(0xB3000000),
        child: SafeArea(
          child: Center(
            child: GestureDetector(
              onTap: () {},
              child: Container(
                constraints: const BoxConstraints(maxWidth: 520),
                margin: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF0E0E11),
                  border: Border.all(color: const Color(0x1FFFFFFF)),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(titulo, style: wbTitulo.copyWith(fontSize: 20)),
                      if (descripcion != null) ...[
                        const SizedBox(height: 6),
                        Text(descripcion, style: wbCuerpo),
                      ],
                      const SizedBox(height: 18),
                      child,
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
    transitionsBuilder: (context, animacion, _, hijo) => FadeTransition(opacity: animacion, child: hijo),
  ));
}

/// Fila de botones al pie de una hoja: Cancelar y el botón principal.
class PieHoja extends StatelessWidget {
  const PieHoja({super.key, required this.texto, required this.alGuardar});

  final String texto;
  final VoidCallback? alGuardar;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.end,
      spacing: 8,
      runSpacing: 8,
      children: [
        Boton('Cancelar', alTocar: () => Navigator.of(context).pop()),
        Boton(texto, principal: true, alTocar: alGuardar),
      ],
    );
  }
}

/// Fecha corta en hora local, o una raya si no hay.
String fechaCorta(Object? iso) {
  final f = iso is String ? DateTime.tryParse(iso)?.toLocal() : null;
  if (f == null) return '—';
  String dos(int n) => n.toString().padLeft(2, '0');
  return '${f.day}/${f.month}/${f.year % 100} ${dos(f.hour)}:${dos(f.minute)}';
}
