# Workbench

Centro de desarrollo de Ashur: la pestaña Workbench de la app. Rehace Nexo DevHub, la app que Sergio armó en Base44.

- **Datos propios** (`contexto.datos`, ADR 0029): `proyectos`, `proveedores`, `tareas`, `entregas`, `servidores` y
  `equipos`.
- **Acciones que solo cambian sus datos:** `listar`, `crear`, `editar`, `borrar`, `repartir_cola`, `probar_servidor`.
- **Acciones que escriben** (esperan a un administrador): `ejecutar_tarea`, que gasta cuota de un modelo, y
  `compilar_entrega`, que llama al servidor.
- **Ajustes:** las claves de Claude, OpenAI y Gemini (secretas) y la dirección de un servidor propio compatible con la
  API de OpenAI, como Ollama. Copilot no tiene API: sus tareas no se ejecutan desde Ashur.
- **Familias de equipo** (`claude_code`, `codex`, `gemini_cli`): no usan clave. `ejecutar_tarea` deja la tarea
  esperando, y la resuelve un equipo de Sergio con el programa oficial y su sesión ya iniciada (abajo). Ashur nunca ve
  esas credenciales. `tomar_tarea` y `entregar_tarea` son para ese programa.
- **Reparto:** cada tarea en cola va al proveedor activo con más cuota libre.

Autoprueba, desde `core/`: `uv run pytest ../modules/workbench/autoprueba.py`.

## Ejecutor: tareas con Claude Code desde un equipo

Anthropic y OpenAI no dejan iniciar sesión con la suscripción desde una app propia; sí dejan usar su programa oficial
con la cuenta de uno. Por eso las tareas de las familias de equipo las resuelve `ejecutor.py`, que corre en un equipo
de Sergio y solo usa la biblioteca estándar de Python:

```bash
ASHUR_CORE=http://servidor:8720 ASHUR_CLAVE=... python3 modules/workbench/ejecutor.py
```

- Es el equipo el que le pide trabajo al core cada 10 segundos. No hay que abrirle puertos ni saber su dirección.
- Con el equipo apagado, la tarea espera. Una tarea tomada y no entregada en 45 minutos se vuelve a ofrecer.
- Claude Code corre con `claude -p`, sin herramientas ni servidores MCP y en una carpeta vacía: solo devuelve texto.
- `ASHUR_EQUIPO` cambia el nombre con que aparece el equipo. `ASHUR_EJECUTOR_FAMILIAS=claude_code,codex,gemini_cli`
  activa las otras familias; Codex y Gemini CLI quedaron escritos pero **sin probar**, porque no estaban instalados.
- La clave es la normal del core, no la de administrador.

### Que arranque solo en la Mac

1. Guarda la clave en el Llavero, para no dejarla en texto plano (la pide sin mostrarla):

   ```bash
   security add-generic-password -U -s ashur-workbench-ejecutor -a ashur -w
   ```

2. Copia `com.ashur.workbench.ejecutor.plist` a `~/Library/LaunchAgents/` y cambia en la copia `RUTA_DEL_REPO`,
   `DIRECCION_DEL_CORE` y `RUTA_DE_LOS_PROGRAMAS` (la carpeta donde está `claude`; la da `dirname "$(which claude)"`).
3. Actívalo con `launchctl load ~/Library/LaunchAgents/com.ashur.workbench.ejecutor.plist`. Para apagarlo,
   `launchctl unload` con la misma ruta. Lo que imprime queda en `/tmp/ashur-workbench-ejecutor.log`.
