# nodo
Programa de un nodo de casa: presta el modelo del equipo a Ashur (`docs/adr/0017-programa-del-nodo.md`). Usa solo la
librería estándar de Python, desde la 3.9 (la de Xcode en la Mac), así que no instala nada. Le habla a Ollama, que sigue escuchando
solo en el propio equipo.

1. Con la clave de administrador, crea el nodo en el core. La clave del nodo se muestra una sola vez:

   ```bash
   curl -X POST http://servidor:8720/nodos -H "X-Ashur-Clave-Admin: …" -H "Content-Type: application/json" -d '{"nombre": "windows"}'
   ```

2. En el equipo, desde esta carpeta. En Windows (PowerShell):

   ```powershell
   $env:ASHUR_CORE = 'http://servidor:8720'; $env:ASHUR_CLAVE_NODO = '…'; python -m ashur_nodo
   ```

   En la Mac:

   ```bash
   ASHUR_CORE=http://servidor:8720 ASHUR_CLAVE_NODO=… python3 -m ashur_nodo
   ```

Variables de entorno:

| Variable | Qué es |
| --- | --- |
| `ASHUR_CORE` | Dirección del core. Obligatoria. |
| `ASHUR_CLAVE_NODO` | La clave que devolvió `POST /nodos`. Obligatoria. |
| `ASHUR_OLLAMA` | Dirección de Ollama. Por defecto, `http://127.0.0.1:11434`. |
| `ASHUR_MODELOS` | Los modelos que este equipo presta, separados por comas. Por defecto, todos los de Ollama. |
| `ASHUR_NUM_CTX` | Tamaño del contexto que se le pide a Ollama, si el core no fija otro. Por defecto, 8192. |
| `ASHUR_ESPERA_S` | Cuánto espera una respuesta de Ollama. Por defecto, 280 s (el plazo del core es 300 s). |
| `ASHUR_MODO` | Fuerza un modo (`full`, `light`, `busy` u `off`) en lugar de calcularlo. Para pruebas. |

Pruebas, desde `core/`:

```bash
uv run pytest ../nodo/tests
```

Desde la app (o con `PATCH /nodos/{id}` y la clave de administrador) se fijan los modelos que presta, el contexto y
un horario. Llegan en la respuesta de cada latido y mandan sobre las variables de entorno
(`docs/adr/0019-ajustes-de-modulos-y-nodos.md`).
