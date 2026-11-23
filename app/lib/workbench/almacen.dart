// Datos de Workbench: proyectos, proveedores, tareas, entregas y servidores.
// Cada registro es un mapa con las claves de abajo; `AlmacenWorkbench` es por donde las pantallas los leen y cambian.
import 'package:flutter/foundation.dart';

typedef Registro = Map<String, dynamic>;

/// Tipos de registro.
const tipoProyectos = 'proyectos';
const tipoProveedores = 'proveedores';
const tipoTareas = 'tareas';
const tipoEntregas = 'entregas';
const tipoServidores = 'servidores';

const tiposTarea = {
  'funcion': 'Función',
  'error': 'Error',
  'refactor': 'Refactor',
  'diseno': 'Diseño',
  'revision': 'Revisión',
  'docs': 'Docs',
  'qa': 'QA',
};

const prioridades = {'baja': 'Baja', 'media': 'Media', 'alta': 'Alta', 'urgente': 'Urgente'};

/// Estados de una tarea, en el orden de las columnas del tablero.
const estadosTarea = {
  'cola': 'En cola',
  'asignada': 'Asignadas',
  'ejecutando': 'Ejecutando',
  'revision': 'Revisión',
  'lista': 'Listas',
  'error': 'Con error',
};

const canales = {'interno': 'Interno', 'beta': 'Beta', 'produccion': 'Producción'};

const familias = {
  'claude': 'Claude',
  'gpt': 'OpenAI',
  'gemini': 'Gemini',
  'copilot': 'Copilot',
  'propio': 'Propio',
};

const coloresFamilia = {
  'claude': 0xFFD9A06A,
  'gpt': 0xFF7FB8AE,
  'gemini': 0xFF8FA9D9,
  'copilot': 0xFFC7A6D9,
  'propio': 0xFF9C9A8E,
};

const plataformas = ['ios', 'macos', 'web', 'android', 'windows'];

/// Pasos de una entrega: clave del registro y nombre visible.
const pasosEntrega = {
  'guardada': 'Guardar',
  'compilada': 'Compilar',
  'firmada': 'Firmar',
  'publicada': 'Publicar',
};

class ErrorWorkbench implements Exception {
  const ErrorWorkbench(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

abstract class AlmacenWorkbench {
  Future<List<Registro>> listar(String tipo);
  Future<Registro> crear(String tipo, Registro datos);
  Future<Registro> editar(String tipo, String id, Registro cambios);
  Future<void> borrar(String tipo, String id);

  /// Asigna cada tarea en cola al proveedor activo con más cuota libre. Devuelve cuántas asignó.
  Future<int> repartirCola();

  /// Corre la tarea con el modelo de su proveedor y deja el resultado en revisión.
  Future<Registro> ejecutarTarea(String id);

  /// Comprueba si el servidor responde y anota estado, latencia y detalle.
  Future<Registro> probarServidor(String id);

  /// Pide al servidor que compile la entrega.
  Future<Registro> compilarEntrega(String id);
}

/// Cuota libre de un proveedor, nunca negativa.
int cuotaLibre(Registro proveedor) {
  final libre = ((proveedor['cuota'] as num?) ?? 0) - ((proveedor['usadas'] as num?) ?? 0);
  return libre < 0 ? 0 : libre.toInt();
}

/// Lo que ven las pantallas: las cinco listas cargadas y avisos cortos de lo último que pasó.
class DatosWorkbench extends ChangeNotifier {
  DatosWorkbench(this.almacen);

  final AlmacenWorkbench almacen;

  List<Registro> proyectos = [];
  List<Registro> proveedores = [];
  List<Registro> tareas = [];
  List<Registro> entregas = [];
  List<Registro> servidores = [];
  bool cargando = true;
  String? aviso;
  bool avisoEsError = false;

  Registro? get servidor => servidores.isEmpty ? null : servidores.first;

  Registro? proyecto(Object? id) => _buscar(proyectos, id);
  Registro? proveedor(Object? id) => _buscar(proveedores, id);
  Registro? tarea(Object? id) => _buscar(tareas, id);

  static Registro? _buscar(List<Registro> lista, Object? id) {
    for (final r in lista) {
      if (r['id'] == id) return r;
    }
    return null;
  }

  Future<void> cargar() async {
    try {
      final listas = await Future.wait([
        almacen.listar(tipoProyectos),
        almacen.listar(tipoProveedores),
        almacen.listar(tipoTareas),
        almacen.listar(tipoEntregas),
        almacen.listar(tipoServidores),
      ]);
      proyectos = listas[0];
      proveedores = listas[1];
      tareas = listas[2];
      entregas = listas[3];
      servidores = listas[4];
    } catch (e) {
      aviso = '$e';
      avisoEsError = true;
    }
    cargando = false;
    notifyListeners();
  }

  /// Corre un cambio, recarga y deja un aviso: `hecho` si salió bien o el error si no. Devuelve si salió bien.
  Future<bool> hacer(Future<String?> Function() cambio) async {
    var bien = true;
    try {
      aviso = await cambio();
      avisoEsError = false;
    } catch (e) {
      aviso = '$e';
      avisoEsError = true;
      bien = false;
    }
    await cargar();
    return bien;
  }

  void cerrarAviso() {
    aviso = null;
    notifyListeners();
  }
}
