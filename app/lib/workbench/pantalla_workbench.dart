// Pestaña Workbench: centro de desarrollo. Reparte tareas entre modelos, vigila cuotas y sigue las entregas.
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'pagina_entregas.dart';
import 'pagina_panel.dart';
import 'pagina_proveedores.dart';
import 'pagina_proyectos.dart';
import 'pagina_servidor.dart';
import 'pagina_tareas.dart';
import 'piezas.dart';

const secciones = ['Panel', 'Tareas', 'Proveedores', 'Entregas', 'Servidor', 'Proyectos'];

class PantallaWorkbench extends StatefulWidget {
  const PantallaWorkbench({super.key, required this.almacen});

  final AlmacenWorkbench almacen;

  @override
  State<PantallaWorkbench> createState() => _PantallaWorkbenchState();
}

class _PantallaWorkbenchState extends State<PantallaWorkbench> {
  late final DatosWorkbench _datos = DatosWorkbench(widget.almacen)..cargar();
  int _seccion = 0;

  @override
  void dispose() {
    _datos.dispose();
    super.dispose();
  }

  void _ir(int seccion) => setState(() => _seccion = seccion);

  Widget _pagina() => switch (_seccion) {
        0 => PaginaPanel(datos: _datos, alIr: _ir),
        1 => PaginaTareas(datos: _datos),
        2 => PaginaProveedores(datos: _datos),
        3 => PaginaEntregas(datos: _datos),
        4 => PaginaServidor(datos: _datos),
        _ => PaginaProyectos(datos: _datos, alIr: _ir),
      };

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: wbFondo,
      child: DefaultTextStyle(
        style: const TextStyle(color: wbTexto, fontSize: 14),
        child: SafeArea(
          child: ListenableBuilder(
            listenable: _datos,
            builder: (context, _) => LayoutBuilder(
              builder: (context, limites) {
                final ancho = limites.maxWidth >= 900;
                final contenido = Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (!ancho) _BarraSuperior(seccion: _seccion, alIr: _ir),
                    Expanded(
                      child: _datos.cargando
                          ? const Center(child: Text('Cargando', style: wbCuerpo))
                          : SingleChildScrollView(
                              padding: EdgeInsets.all(ancho ? 32 : 16),
                              child: _pagina(),
                            ),
                    ),
                    if (_datos.aviso != null) _Aviso(datos: _datos),
                  ],
                );
                if (!ancho) return contenido;
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _BarraLateral(seccion: _seccion, alIr: _ir, servidor: _datos.servidor),
                    Expanded(child: contenido),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => Navigator.of(context).pop(),
          child: const Padding(
            padding: EdgeInsets.only(right: 12),
            child: Text('‹', style: TextStyle(fontSize: 28, color: wbTenue)),
          ),
        ),
        const Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Workbench', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
              Text('CENTRO DE DESARROLLO', style: wbEtiqueta, overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ],
    );
  }
}

class _BarraSuperior extends StatelessWidget {
  const _BarraSuperior({required this.seccion, required this.alIr});

  final int seccion;
  final ValueChanged<int> alIr;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: wbBorde))),
      padding: const EdgeInsets.fromLTRB(16, 10, 0, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _Marca(),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (var i = 0; i < secciones.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: Ficha(secciones[i], elegida: i == seccion, alTocar: () => alIr(i)),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BarraLateral extends StatelessWidget {
  const _BarraLateral({required this.seccion, required this.alIr, required this.servidor});

  final int seccion;
  final ValueChanged<int> alIr;
  final Registro? servidor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 244,
      decoration: const BoxDecoration(
        color: Color(0xFF0A0A0C),
        border: Border(right: BorderSide(color: wbBorde)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Align(alignment: Alignment.centerLeft, child: _Marca()),
          const SizedBox(height: 28),
          const Padding(padding: EdgeInsets.only(left: 12, bottom: 8), child: Text('ESPACIO', style: wbEtiqueta)),
          for (var i = 0; i < secciones.length; i++)
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => alIr(i),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                decoration: BoxDecoration(
                  color: i == seccion ? const Color(0x0EFFFFFF) : null,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(secciones[i], style: TextStyle(color: i == seccion ? wbTexto : wbTenue, fontSize: 13)),
              ),
            ),
          const Spacer(),
          Tarjeta(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        ((servidor?['nombre'] as String?) ?? 'Servidor').toUpperCase(),
                        style: wbEtiqueta,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Pastilla((servidor?['estado'] as String?) ?? 'sin_probar'),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  (servidor?['url'] as String?) ?? 'sin configurar',
                  style: wbEtiqueta.copyWith(letterSpacing: 0),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.datos});

  final DatosWorkbench datos;

  @override
  Widget build(BuildContext context) {
    final color = datos.avisoEsError ? wbRojo : wbVerde;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: datos.cerrarAviso,
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          border: Border.all(color: color.withValues(alpha: 0.4)),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            Expanded(child: Text(datos.aviso!, style: TextStyle(color: color, fontSize: 13))),
            Text('×', style: TextStyle(color: color, fontSize: 16)),
          ],
        ),
      ),
    );
  }
}
