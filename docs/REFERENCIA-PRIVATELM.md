# Referencia: PrivateLM

Clon de solo lectura en `../_referencias/cross-platform-llm-client`
(commit `8a5f3b0`, licencia MIT en `LICENSE`). Las rutas de abajo son relativas a esa carpeta.
No se copia código: se recrea lo que sirve.

## Funciones que recreamos
1. **Chat con sesiones persistentes:** lista de conversaciones con título, fecha y último mensaje.
   `lib/models/chat_session.dart`, `lib/models/chat_message.dart`, `lib/widgets/chat_drawer.dart`.
2. **Mensajes con adjuntos (imagen y archivo):** el mensaje lleva imagen en base64, ruta y datos del archivo.
   `lib/models/chat_message.dart`, `lib/widgets/attachment_preview.dart`.
3. **Inferencia local o en la nube detrás de una sola interfaz,** con `supportsLocalInference` para que la UI oculte
   lo local donde no existe. `lib/services/inference_service.dart`, `lib/services/inference_stub.dart`.
4. **Un solo servicio de nube que normaliza varios proveedores** (OpenAI, Anthropic, Gemini, Kimi, OpenRouter,
   DeepSeek y un endpoint propio). `lib/services/cloud_service.dart`, `README.md` (sección Cloud Inference).
5. **Servidor compatible con OpenAI dentro de la app** (`/health`, `/v1/models`, `/v1/chat/completions`), solo en
   loopback salvo que se active la red, y entonces con clave obligatoria. `lib/services/openai_server_service_io.dart`.
6. **Repartir un modelo entre varios teléfonos de la misma Wi-Fi** (maestro y trabajadores): es la idea de "nodos de
   casa" aplicada a teléfonos. `lib/services/cluster_service.dart`.
7. **Auto-configuración según la RAM del dispositivo** (contexto y tokens recomendados). `README.md` (What It Does),
   `lib/services/device_info_service.dart`.
8. **Separar el razonamiento ("thinking") de la respuesta** y mostrarlo plegado. `lib/utils/thought_parser.dart`,
   `lib/widgets/thought_disclosure.dart`.

## Estructura que conviene reutilizar
- **Capas vista / controlador / servicio:** `lib/views/`, `lib/controllers/`, `lib/services/`, con el diagrama de
  `README.md` (Technical Architecture). La idea de capas sirve; el gestor de estado (GetX, `pubspec.yaml`) no se
  adopta: la app usa lo que trae Flutter (`docs/adr/0006-estado-en-flutter.md`).
- **Importación condicional por plataforma** para que cada plataforma compile solo lo suyo:
  `lib/services/inference_service.dart` (import de `inference_android.dart` o `inference_stub.dart`) y
  `lib/services/openai_server_service.dart` (export `_stub` / `_io`).
- **Utilidades pequeñas y probadas:** filtro de secuencias de parada en streaming
  (`lib/services/stop_sequence_filter.dart`, `test/stop_sequence_filter_test.dart`) y enmascarado de claves antes
  de registrar texto (`lib/core/redact.dart`, `test/redact_test.dart`).

## Lo que le falta
### Mac
- Existe la carpeta `macos/`, pero la inferencia local no corre en macOS: `supportsLocalInference` es
  `Platform.isAndroid || Platform.isIOS` (`lib/services/inference_android.dart`, línea 9).
- El README no lista macOS entre las plataformas soportadas (`README.md`, Supported Platforms).
### Windows
- No hay carpeta `windows/` en el repo (tampoco `linux/`); la raíz solo tiene `android/`, `ios/`, `macos/` y `web/`.
- Varias funciones dependen de `Platform.isAndroid` (descargas, notificaciones, importar carpetas):
  `lib/services/download_service.dart`, `lib/services/image_generation_notification_service.dart`,
  `lib/controllers/model_controller.dart`.
### Servidores
- No hay un servidor central: todo vive en el dispositivo (Hive, `lib/services/hive_service.dart`). No hay memoria
  compartida entre dispositivos.
- El servidor que trae es un endpoint de inferencia de un solo dispositivo, no un core
  (`lib/services/openai_server_service_io.dart`).
- El clúster solo junta teléfonos y solo Android puede ser maestro (`ClusterService.canBeMaster`,
  `lib/services/cluster_service.dart`); no contempla computadoras ni servidores de casa como nodos.
