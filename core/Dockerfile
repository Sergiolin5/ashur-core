# Se construye en GitHub Actions (.github/workflows/imagen-core.yml); en la Mac no hay Docker.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY ashur_core ./ashur_core

# La base de datos vive en un volumen local montado desde el servidor, nunca dentro del contenedor.
VOLUME /datos

EXPOSE 8720
CMD ["/app/.venv/bin/uvicorn", "ashur_core.app:app", "--host", "0.0.0.0", "--port", "8720"]
