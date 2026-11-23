# Workbench

Centro de desarrollo de Ashur: la pestaña Workbench de la app. Rehace Nexo DevHub, la app que Sergio armó en Base44.

- **Datos propios** (`contexto.datos`, ADR 0029): `proyectos`, `proveedores`, `tareas`, `entregas` y `servidores`.
- **Acciones que solo cambian sus datos:** `listar`, `crear`, `editar`, `borrar`, `repartir_cola`, `probar_servidor`.
- **Acciones que escriben** (esperan a un administrador): `ejecutar_tarea`, que gasta cuota de un modelo, y
  `compilar_entrega`, que llama al servidor.
- **Ajustes:** las claves de Claude, OpenAI y Gemini (secretas) y la dirección de un servidor propio compatible con la
  API de OpenAI, como Ollama. Copilot no tiene API: sus tareas no se ejecutan desde Ashur.
- **Reparto:** cada tarea en cola va al proveedor activo con más cuota libre.

Autoprueba, desde `core/`: `uv run pytest ../modules/workbench/autoprueba.py`.
