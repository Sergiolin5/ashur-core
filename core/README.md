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
