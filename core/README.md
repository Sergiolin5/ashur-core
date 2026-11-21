# core
Servidor REST de Ashur: memoria, chat e inventario de objetos físicos, y el registro de módulos.
Stack: Python 3.13, FastAPI y SQLite, desplegado como contenedor en ZimaOS (`docs/adr/0003-stack-servidor.md`).

Desde esta carpeta:

```bash
uv run pytest
```

```bash
uv run uvicorn ashur_core.app:app --port 8720
```

Variables de entorno (`docs/adr/0004-memoria.md`):

| Variable | Qué es |
| --- | --- |
| `ASHUR_CLAVE` | Clave que piden los endpoints de la memoria en el encabezado `X-Ashur-Clave`. Sin ella, la memoria responde 503. |
| `ASHUR_DB` | Ruta de la base SQLite. Por defecto, `/datos/ashur.db`. |
