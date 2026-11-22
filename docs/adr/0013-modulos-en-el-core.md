# ADR 0013: los módulos son Python y corren dentro del core

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Faltaba decidir cómo se registra y corre un módulo (`docs/MODULOS.md`, sección 2). Sin eso, ningún módulo hecho por
otra IA podía conectarse al core. Sergio eligió módulos en Python dentro del core, por ser lo más rápido para el
esqueleto, y dejó abierta la puerta a módulos como servicios aparte más adelante.

## Decisión
- **Forma de un módulo:** `modules/<id>/` trae:
  - `modulo.json`, según `contracts/modulo.schema.json`; su `id` es el nombre de la carpeta;
  - `modulo.py`, con una función por acción: `def <accion>(contexto, **parametros) -> dict`;
  - `autoprueba.py`, que corre sin red ni core, con un contexto falso.

  `modules/_plantilla/` es el ejemplo ejecutable. Las carpetas que empiezan con `_` no se registran.
- **Registro:** el core descubre `modules/` en el primer pedido (la carpeta se cambia con `ASHUR_MODULOS`). Un módulo
  que no cumple el contrato o falla al cargar aparece en `GET /modulos` con su error y no tumba el core.
- **Contexto:** lo único que recibe un módulo es `contexto.recordar(texto, ...)`, que guarda un recuerdo con `origen`
  igual al id del módulo, por el mismo camino que `POST /recuerdos`. No recibe la base: no guarda memoria propia.
- **Endpoints:**

  | Método y ruta | Clave | Qué hace |
  | --- | --- | --- |
  | `GET /modulos` | normal | Lista los módulos y sus errores. |
  | `POST /modulos/{id}/acciones/{accion}` | normal | Si la acción solo lee, la corre. Si escribe, crea un pedido pendiente (202). |
  | `GET /pedidos` | normal | Lista los pedidos; `?estado=pendiente` filtra. |
  | `POST /pedidos/{id}/aprobar` | administrador | Corre la acción. Toma el pedido de forma atómica, así que nunca corre dos veces. |
  | `POST /pedidos/{id}/rechazar` | administrador | Lo descarta. |

  Un pedido pasa por `pendiente`, `corriendo` y `hecho`, o termina `rechazado` o `fallido`. Si la acción lanza una
  excepción, el core responde 502 con su mensaje, y el pedido queda `fallido`.
- **Base:** esquema 6, con la tabla `pedidos`.
- **Galaxia:** cada módulo registrado es un planeta con `ref: {"tipo": "modulo"}`, id `modulo-<id>` y fase fija; su
  masa es 1 más la cantidad de recuerdos con su origen.
- **Imagen:** se construye desde la raíz del repo (`docker build -f core/Dockerfile .`) para incluir `modules/`. La
  imagen copia la forma del repo (`/app/core` y `/app/modules`). La raíz tiene un `.dockerignore` que solo deja entrar
  lo necesario; `core/.dockerignore` ya no se usa.

## Costos
- **Los módulos corren con todos los privilegios del core:** pueden leer las variables de entorno (las claves) y la
  base. La única barrera es la revisión de Claude Code antes de integrarlos.
- **Paquetes:** un módulo que necesita un paquete tiene que cambiar `core/pyproject.toml`, lo que pide la aprobación de
  Sergio y, por `CLAUDE.md`, es una tarea aparte del módulo.
- **Sin límite de tiempo:** una acción que se cuelga ocupa un hilo del servidor.
- **Pedidos colgados:** si el core se cae mientras corre un pedido aprobado, ese pedido queda en `corriendo` para
  siempre.
- **Un solo lenguaje:** los módulos en otros lenguajes tendrían que llegar como servicios aparte (pendiente).

## Pendiente
- **Límite de tiempo para las acciones** (lo señaló el diseño del módulo Network): hoy una acción larga o colgada ocupa
  un hilo del core. Un escaneo de red no puede correr así.
- Asteroides para pedidos pendientes o módulos rotos, y estrellas fugaces para lo que un módulo entrega.
- Módulos como servicios HTTP aparte, para otros lenguajes.
- Que Ashur ofrezca las acciones de los módulos en el chat, cuando exista.
