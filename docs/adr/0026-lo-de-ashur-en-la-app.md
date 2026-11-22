# ADR 0026: «Lo de Ashur» en la app

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Relacionadas:** `docs/adr/0020-configuracion-avanzada-en-la-app.md`, `docs/adr/0022-personas-y-roles.md` y
  `docs/adr/0024-personalidad-madurez-y-correcciones.md`

## Contexto
El core ya permite consultar y cambiar la personalidad, las correcciones, los roles y el acceso de las personas. Sergio
pidió poder administrar esos datos desde «Configuración avanzada» en Estado, sin guardar la personalidad privada en la
app.

## Decisión
- **Personalidad:** Estado lee `GET /personalidad` y presenta base, lo que Ashur sabe de Sergio, los tres niveles de
  madurez, el trato y los umbrales. También muestra el nivel y el total de recuerdos actuales. `PUT /personalidad`
  reemplaza esos campos; la app comprueba que el umbral intermedio sea menor que el pleno.
- **Correcciones:** muestra texto, fuente y fecha. Editar o borrar una fila envía la lista completa a
  `PUT /personalidad/correcciones`; el core conserva sus límites de longitud y cantidad.
- **Roles:** `GET /roles` muestra roles y herramientas. `POST /roles` crea y `PATCH /roles/{id}` edita. Los patrones se
  conservan literalmente, con coincidencia sensible a mayúsculas y el formato del contrato. La pantalla avisa:
  «buscar_* muestra todo tu inventario y los nombres de tus identidades; modulo-* corre con los privilegios del módulo».
- **Personas:** la app filtra identidades de clase `persona`; permite asignar o quitar un rol con `PATCH /identidades/{id}`.
  `POST /identidades/{id}/clave` abre un diálogo con la clave recibida una sola vez y un botón «Copiar».
- **Acceso de administrador:** si no hay clave administrativa, la personalidad, las correcciones, los roles y las
  personas se leen y se muestran, pero no aparecen controles de edición.
- **Privacidad:** los datos recibidos viven solo en memoria mientras la sección está abierta. No se guardan en archivos,
  caché ni almacenamiento seguro. La clave de una persona tampoco se escribe en el dispositivo; solo queda en la memoria
  del diálogo y en el portapapeles si Sergio pulsa «Copiar».
- **Errores:** 401, 404, 409 y 503 se distinguen en la pantalla; 422 muestra el campo `detail` devuelto por el core.
  Los endpoints y sus validaciones no cambian.

## Costos
- Sin conexión con el core no se muestran valores guardados anteriormente.
- La clave de una persona solo puede copiarse mientras está abierto su diálogo; si se pierde, se crea una nueva y la
  anterior deja de servir.
- El formulario puede recibir errores 422 del core si un dato no cumple el contrato; la respuesta conserva el detalle
  para que Sergio lo corrija.

## Verificado (2026-11-22)
- `flutter test` recorre las rutas de personalidad, correcciones, roles e identidades contra un core falso en localhost,
  comprueba los encabezados de acceso y los errores 401, 404, 409, 422 y 503.
- Las pruebas de widgets comprueban que la clave nueva se ve una sola vez, no se guarda en el almacén local y que sin
  clave administrativa no aparecen controles de cambio.
- `flutter analyze` revisa la app Flutter.

## Pendiente
- Ashur Code revisó la rama y la unió a main sobre Face ID (ADR 0025), sin Flutter en ese equipo. Falta correr
  `flutter analyze` y `flutter test` en la Mac con la unión, y probar la sección en el iPhone, también con Face ID
  cancelado.
