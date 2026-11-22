# ADR 0017: el programa del nodo de casa

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
El core ya tiene el chat y la cola de trabajos (`docs/adr/0016-chat-y-nodos.md`). Faltaba el programa que corre en
cada equipo de Sergio y le presta su modelo a Ashur. Es la fase 2 del diseño aprobado.

## Decisión
- **Dónde vive:** `nodo/`, en la raíz, como cliente del core, igual que `app/`.
  - No es un módulo: el contrato de `docs/MODULOS.md` es para código que corre dentro del core.
  - Tampoco es parte del core.
- **Sin paquetes:** solo la librería estándar de Python, desde la 3.9 (la de Xcode en la Mac, ADR 0003), para que corra
  en Windows y en la Mac sin instalar nada.
- **Ollama queda en el propio equipo:** el nodo le habla en `127.0.0.1:11434` y nunca lo abre a la red. Es una ventaja
  de que el nodo vaya a buscar el trabajo al core (`docs/REFERENCIA-ANTERIOR.md`, punto 2).
- **Dos hilos:**
  - uno manda el latido cada 15 s con el modo y los modelos;
  - el otro toma trabajos, se los pasa a Ollama y devuelve la respuesta: `/api/chat`, sin streaming, para conversar,
    y `/api/embed` para los embeddings (ADR 0018).

  Así el nodo sigue en línea mientras el modelo piensa.
- **Modo según la carga** (`nodo/ashur_nodo/politica.py`): una función pura sobre cuatro señales (punto 5):

  | Señales | Modo |
  | --- | --- |
  | Con batería, sin cargador y por debajo del 30 % | `off` |
  | Otros programas usan el 70 % o más del procesador | `busy` |
  | Con batería, sin cargador | `light` |
  | Sergio tocó el equipo hace menos de 5 minutos | `light` |
  | Libre y enchufado | `full` |

  Una señal que no se puede leer no cuenta. La carga se mide entre trabajos, para no contar el propio modelo. Sergio
  siempre gana en sus máquinas (punto 4).
- **Lectores de señales** (`nodo/ashur_nodo/senales.py`):
  - **Windows:** `ctypes`, con `GetLastInputInfo`, `GetSystemPowerStatus` y `GetSystemTimes`.
  - **Mac:** `ioreg`, `pmset` y `os.getloadavg`.
- **Qué modelos presta:** todos los de Ollama, o solo los de `ASHUR_MODELOS` (configurable, decisión de Sergio). Ashur
  elige entre ellos (ADR 0016).
- **Contexto:** lo fija el nodo, 8192 por defecto, porque depende de la memoria de cada equipo. El core no lo manda.

## Costos
- **Ollama descarga el modelo después de un rato sin uso,** así que la primera respuesta tarda más.
- **La pantalla bloqueada no se lee:** cuenta como inactividad, porque bloqueado nadie toca el equipo.
- **Correrlo a mano:** todavía no arranca solo con el equipo ni se actualiza solo.

## Verificado (2026-11-22, en el equipo Windows)
- `uv run pytest ../nodo/tests` (5 pruebas):
  - la política de modos;
  - los modelos de Ollama en el formato del protocolo;
  - una respuesta vacía de Ollama vuelve como error, para que el core la reintente en lugar de esperar 300 s;
  - las señales reales de Windows: inactividad, carga, cargador y batería.
- De punta a punta, con el core real (uvicorn y una base temporal), este nodo y el Ollama real:
  - El equipo estaba enchufado y se había usado hace 3 minutos, así que se ofreció en `light`. Ashur eligió `qwen2.5:3b`, el único que ese modo permite.
  - Dos mensajes recibieron respuesta en 6,8 s y 3,8 s. El segundo recordó el primero.
  - Los cuatro mensajes quedaron como recuerdos.

## Sin verificar
- **`qwen2.5:7b`:** Sergio detuvo la prueba que forzaba el modo `full` mientras él usaba el equipo; forzarlo pasaba por
  encima de «Sergio siempre gana». El 7B se mide solo cuando el equipo informe `full` por sí mismo, o con su permiso.
  Falta saber cuánto tarda con 4 GB de memoria gráfica y si caben 8192 de contexto.
- **La Mac:** ni los lectores de `ioreg` y `pmset` ni Python 3.9 se probaron. Se probó solo con Python 3.13 en Windows.

## Pendiente
- Arrancar el nodo con el equipo: un servicio en Windows y un `launchd` en la Mac.
