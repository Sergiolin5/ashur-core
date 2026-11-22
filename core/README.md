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

Rutas: memoria (`docs/adr/0004-memoria.md`), galaxia (0011), identidades (0012) y módulos (0013).

Variables de entorno:

| Variable | Qué es |
| --- | --- |
| `ASHUR_CLAVE` | Clave para crear y listar recuerdos, en el encabezado `X-Ashur-Clave`. Sin ella, esos endpoints responden 503. |
| `ASHUR_CLAVE_ADMIN` | Clave de administrador en el encabezado `X-Ashur-Clave-Admin`, para editar y borrar recuerdos. Sin ella, nadie puede. |
| `ASHUR_DB` | Ruta de la base SQLite. Por defecto, `/datos/ashur.db`. |
| `ASHUR_MODULOS` | Carpeta de los módulos. Por defecto, `modules/` al lado de `core/`. |
