// Panel: resumen de tareas, cuotas, servidor y última entrega.
import 'package:flutter/widgets.dart';

import 'almacen.dart';
import 'pagina_tareas.dart';
import 'piezas.dart';

class PaginaPanel extends StatelessWidget {
  const PaginaPanel({super.key, required this.datos, required this.alIr});

  final DatosWorkbench datos;

  /// Cambia de sección, por su posición en `secciones`.
  final ValueChanged<int> alIr;

  @override
  Widget build(BuildContext context) {
    final tareas = datos.tareas;
    final enCurso = tareas.where((t) => const ['cola', 'asignada', 'ejecutando', 'revision'].contains(t['estado']));
    final cuota = datos.proveedores.fold<num>(0, (s, p) => s + ((p['cuota'] as num?) ?? 0));
    final usadas = datos.proveedores.fold<num>(0, (s, p) => s + ((p['usadas'] as num?) ?? 0));
    final libre = cuota > 0 ? ((cuota - usadas) / cuota * 100).clamp(0, 100).round() : 0;
    final servidor = datos.servidor;
    final servicios = (servidor?['servicios'] as List?) ?? const [];
    final ultima = datos.entregas.isEmpty ? null : datos.entregas.first;
    final cola = (enCurso.isNotEmpty ? enCurso : tareas).take(6).toList();
    int cuenta(List<Registro> lista, String estado) => lista.where((r) => r['estado'] == estado).length;

    final cifras = [
      _Cifra('Tareas en curso', '${enCurso.length}', wbAcento, {
        'En revisión': '${cuenta(tareas, 'revision')}',
        'En cola': '${cuenta(tareas, 'cola')}',
      }),
      _Cifra('Cuota libre', '$libre%', wbTurquesa, {
        'Modelos': '${cuenta(datos.proveedores, 'activo')}',
        'En pausa': '${cuenta(datos.proveedores, 'pausado')}',
      }),
      _Cifra('Latencia del servidor', '${servidor?['latencia_ms'] ?? 0}ms', wbAzul, {
        'Servicios': '${servicios.length}',
        'Estado': switch (servidor?['estado']) {
          'en_linea' => 'En línea',
          'sin_conexion' => 'Sin conexión',
          _ => 'Sin probar',
        },
      }),
      _Cifra('Entregas', '${datos.entregas.length}', wbLila, {
        'Última': (ultima?['version'] as String?) ?? '—',
        'Canal': canales[ultima?['canal']] ?? '—',
      }),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Encabezado(
          etiqueta: 'Centro de desarrollo',
          titulo: 'Todo el trabajo, repartido.',
          descripcion: 'Enruta cada tarea al modelo que mejor la resuelve, vigila lo que te queda de cada plan y '
              'entrega Ashur desde tu servidor.',
          acciones: [
            Boton('Abrir tablero', principal: true, alTocar: () => alIr(1)),
            Boton('Repartir cola', alTocar: () => repartirCola(datos)),
          ],
        ),
        LayoutBuilder(
          builder: (context, limites) {
            final columnas = limites.maxWidth >= 900 ? 4 : (limites.maxWidth >= 480 ? 2 : 1);
            final ancho = (limites.maxWidth - 12 * (columnas - 1)) / columnas;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [for (final c in cifras) SizedBox(width: ancho, child: c)],
            );
          },
        ),
        const SizedBox(height: 12),
        Seccion(
          etiqueta: 'Flujo',
          titulo: 'Cola de trabajo',
          accion: Boton('Tablero', alTocar: () => alIr(1)),
          child: cola.isEmpty
              ? Column(
                  children: [
                    const Text('La cola está vacía.', style: wbCuerpo),
                    const SizedBox(height: 10),
                    Boton('Crear la primera tarea', alTocar: () => alIr(1)),
                  ],
                )
              : Column(
                  children: [
                    for (final t in cola)
                      GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => abrirTarea(context, datos, t['id'] as String),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              Container(
                                width: 3,
                                height: 30,
                                color: Color((datos.proveedor(t['proveedor_id'])?['color'] as int?) ?? 0xFF4B4B52),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('${t['titulo']}', overflow: TextOverflow.ellipsis),
                                    Text(
                                      '${datos.proyecto(t['proyecto_id'])?['nombre'] ?? 'General'} · '
                                      '${datos.proveedor(t['proveedor_id'])?['nombre'] ?? 'sin asignar'}',
                                      style: wbCuerpo.copyWith(fontSize: 11),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              Pastilla(t['estado'] as String),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
        ),
        const SizedBox(height: 12),
        Seccion(
          etiqueta: 'Modelos',
          titulo: 'Cuota por proveedor',
          accion: Boton('Gestionar', alTocar: () => alIr(2)),
          child: datos.proveedores.isEmpty
              ? const Text('Añade tu primer proveedor para empezar.', style: wbCuerpo)
              : Column(
                  children: [
                    for (final p in datos.proveedores.take(4))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    p['estado'] == 'pausado' ? '${p['nombre']} · en pausa' : '${p['nombre']}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                Text('${p['usadas'] ?? 0}/${p['cuota'] ?? 0}', style: wbCuerpo),
                              ],
                            ),
                            const SizedBox(height: 6),
                            BarraCuota(
                              usadas: (p['usadas'] as num?) ?? 0,
                              cuota: (p['cuota'] as num?) ?? 0,
                              pausado: p['estado'] == 'pausado',
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
        ),
        const SizedBox(height: 12),
        Seccion(
          etiqueta: ultima == null
              ? 'Sin entregas'
              : '${datos.proyecto(ultima['proyecto_id'])?['nombre'] ?? 'Ashur'} · ${ultima['version']}',
          titulo: 'Pipeline de entrega',
          accion: Boton('Entregas', alTocar: () => alIr(3)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  for (final paso in pasosEntrega.entries)
                    Expanded(
                      child: Column(
                        children: [
                          Text(
                            ultima?[paso.key] == true ? '✓' : '·',
                            style: TextStyle(color: ultima?[paso.key] == true ? wbVerde : wbApagado, fontSize: 18),
                          ),
                          Text(paso.value, style: wbCuerpo.copyWith(fontSize: 11)),
                        ],
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                ultima == null
                    ? 'Crea una entrega para seguir su recorrido hasta producción.'
                    : '${ultima['estado'] == 'publicada' ? 'Publicada' : 'En curso'} · canal '
                        '${canales[ultima['canal']] ?? ultima['canal']}.',
                style: wbCuerpo,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Seccion(
          etiqueta: 'Infraestructura',
          titulo: (servidor?['nombre'] as String?) ?? 'Servidor',
          accion: Pastilla((servidor?['estado'] as String?) ?? 'sin_probar'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text((servidor?['url'] as String?) ?? 'Sin URL configurada'),
              const SizedBox(height: 4),
              Text(
                '${servicios.length} servicios · '
                '${servidor?['ultima_prueba'] == null ? 'sin comprobar todavía' : 'última prueba ${fechaCorta(servidor!['ultima_prueba'])}'}',
                style: wbCuerpo,
              ),
              const SizedBox(height: 10),
              Wrap(spacing: 6, runSpacing: 6, children: [for (final s in servicios.take(5)) Ficha('$s')]),
              const SizedBox(height: 10),
              Boton('Abrir consola', alTocar: () => alIr(4)),
            ],
          ),
        ),
      ],
    );
  }
}

class _Cifra extends StatelessWidget {
  const _Cifra(this.titulo, this.valor, this.color, this.detalles);

  final String titulo;
  final String valor;
  final Color color;
  final Map<String, String> detalles;

  @override
  Widget build(BuildContext context) {
    return Tarjeta(
      brillo: color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(titulo, style: wbCuerpo),
          const SizedBox(height: 18),
          Text(valor, style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w300)),
          const SizedBox(height: 10),
          for (final d in detalles.entries)
            Row(
              children: [
                Expanded(child: Text(d.key.toUpperCase(), style: wbEtiqueta)),
                Text(d.value, style: wbCuerpo),
              ],
            ),
        ],
      ),
    );
  }
}
