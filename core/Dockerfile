# Se construye en GitHub Actions desde la raíz del repo (.github/workflows/imagen-core.yml):
#   docker build -f core/Dockerfile .
# En la Mac no hay Docker. Ver docs/adr/0013-modulos-en-el-core.md.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /usr/local/bin/uv

# La imagen copia la forma del repo: /app/core y /app/modules, así el core encuentra los módulos sin configuración.
WORKDIR /app/core
COPY core/pyproject.toml core/uv.lock core/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY core/ashur_core ./ashur_core
COPY modules /app/modules

# La base de datos vive en un volumen local montado desde el servidor, nunca dentro del contenedor.
VOLUME /datos

EXPOSE 8720
CMD ["/app/core/.venv/bin/uvicorn", "ashur_core.app:app", "--host", "0.0.0.0", "--port", "8720"]
