# Plantilla de módulo

Copia esta carpeta como `modules/<id>/` (sin el guion bajo) y sigue `docs/MODULOS.md`:

- `modulo.json`: el manifiesto (`contracts/modulo.schema.json`). Su `id` es el nombre de la carpeta.
- `modulo.py`: una función por acción, `def <accion>(contexto, **parametros) -> dict`.
- `autoprueba.py`: pruebas sin red ni core, con un contexto falso. Desde `core/`:
  `uv run pytest ../modules/<id>/autoprueba.py`.

Su planeta en la galaxia lo nombra en `ref` (`docs/adr/0008-cuerpos-reales-de-la-galaxia.md`). Para construir un
módulo con otra IA, usa `docs/PROMPT-MODULOS.md`.
