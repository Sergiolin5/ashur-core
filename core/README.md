# core
Servidor REST de Ashur: memoria, chat, inventario de objetos físicos e identidades, y el registro de módulos.
Stack: Python 3.13, FastAPI y SQLite, desplegado como contenedor en ZimaOS (`docs/adr/0003-stack-servidor.md`).

Desde esta carpeta:

```bash
uv run pytest
```

```bash
uv run uvicorn ashur_core.app:app --port 8720
```

Rutas: memoria (`docs/adr/0004-memoria.md`), galaxia (0011), identidades (0012), módulos (0013), inventario (0014), chat y nodos (0016), búsqueda híbrida (0018), ajustes de módulos y nodos (0019), herramientas del chat (0021), personas y roles (0022) y personalidad, madurez y correcciones (0024).

Variables de entorno:

| Variable | Qué es |
| --- | --- |
| `ASHUR_CLAVE` | La clave de Sergio, en el encabezado `X-Ashur-Clave`. Sin ella, todo responde 503. Las demás personas usan su propia clave en el mismo encabezado, y solo les abre su chat (`docs/adr/0022-personas-y-roles.md`). |
| `ASHUR_CLAVE_ADMIN` | Clave de administrador en el encabezado `X-Ashur-Clave-Admin`, para editar y borrar recuerdos. Sin ella, nadie puede. |
| `ASHUR_DB` | Ruta de la base SQLite. Por defecto, `/datos/ashur.db`. |
| `ASHUR_MODULOS` | Carpeta de los módulos. Por defecto, `modules/` al lado de `core/`. |
| `ASHUR_ZONA` | Zona horaria de Sergio, como nombre IANA, para el día con que el modelo ve cada recuerdo. Las fechas se guardan igual en UTC. Por defecto, UTC (`docs/adr/0004-memoria.md`). |
