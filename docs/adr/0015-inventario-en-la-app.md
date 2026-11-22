# ADR 0015: el inventario de objetos en la app

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto
El inventario de objetos físicos quedó definido en el core con el ADR 0014 y el contrato `contracts/objeto.schema.json`.
Faltaba llevarlo a la app Flutter (`app/`) para que Sergio pueda ver sus objetos, agregar nuevos y administrarlos
directamente desde su teléfono.

## Decisión
- **Pantalla Inventario:**
  - Se abre de dos maneras:
    - Tocando el planeta Objetos en la galaxia (usando `cuerpoEn` en `VistaGalaxia`, sin interferir con el zoom de dos
      dedos ni la cámara que sigue a un cuerpo).
    - Mediante un botón ☰ translúcido en la esquina superior izquierda de la pantalla principal, dentro de `SafeArea`,
      que abre el inventario directamente sin menú intermedio.
  - Muestra la lista de objetos obtenida con `GET /objetos` (encabezado `X-Ashur-Clave`). Cada objeto muestra su nombre
    y su lugar; si no tiene lugar o viene vacío, se muestra «Sin lugar».
  - Incluye un interruptor para ver también los objetos archivados (`GET /objetos?archivados=true`).
  - Formulario para crear un objeto con `POST /objetos`: envía nombre y lugar opcional. Siempre envía el campo `lugar`
    en el cuerpo JSON, con valor `null` si está vacío.
  - La lista no se persiste en el teléfono: sin conexión, la pantalla lo indica claramente con un mensaje al estilo de
    la pestaña Estado.
- **Clave de administrador en el teléfono:**
  - Se agrega un tercer campo opcional en la pestaña Estado: «Clave de administrador (ASHUR_CLAVE_ADMIN)», con botón
    «Pegar» y `obscureText`.
  - Se almacena con el `AlmacenSecreto` existente (`flutter_secure_storage` en el Llavero), sin paquetes nuevos.
  - Se envía en el encabezado `X-Ashur-Clave-Admin`, que el core acepta sola, sin la clave normal; la app la usa solo
    en `PATCH /objetos/{id}`.
- **Acciones de administración:**
  - Con la clave de administrador configurada, cada objeto muestra controles para mover (cambiar de lugar o dejar sin
    lugar con `null`), renombrar, archivar y restaurar mediante `PATCH /objetos/{id}`. Solo se envían los campos que
    cambian.
  - Sin la clave de administrador, esos controles no aparecen y una línea indica que hace falta la clave de
    administrador en la pestaña Estado.
- **Actualización de la galaxia:**
  - Tras crear, archivar o restaurar un objeto, se llama a `fuente.actualizar()` para que el planeta Objetos actualice
    su masa (1 + objetos sin archivar) y cambie de tamaño en la galaxia.

## Costos
- **Clave de administrador en el teléfono:** Sergio decidió guardar la clave de administrador en el teléfono para
  poder editar y archivar objetos desde la app. El costo es que esa clave tiene privilegios totales en el core: también
  puede editar y borrar recuerdos, editar identidades y aprobar pedidos de módulos. Si el teléfono se extravía o se ve
  comprometido, quien tenga acceso al Llavero obtiene control administrativo sobre esos recursos del core.

## Verificado (2026-11-22)
- `flutter test` (28 pruebas): cliente HTTP contra core simulado en localhost (listar activos y archivados, crear con y
  sin lugar, PATCH con `X-Ashur-Clave-Admin`, y códigos de error 401, 404, 422 y 503) y pruebas de widgets (apertura
  tocando el planeta Objetos, apertura con el botón ☰, interruptor de archivados, controles según presencia de la
  clave de administrador y llamada a `fuente.actualizar()`).
- `flutter analyze`: sin errores ni advertencias (0 issues).

Eso se verificó en la Mac con el commit a47f4a5 de la rama `app-inventario`.

## Verificado en la Mac (2026-11-22, después de la revisión)
- Los ajustes hechos en Windows (`mounted` antes de cada `setState` tras un `await`, sin `Objeto.aJson()`, sin la
  condición `cuerpo != 'nucleo'`) compilan: `flutter analyze` sin avisos y `flutter test` con 29 pruebas, todas bien.
- Prueba nueva: salir de Inventario mientras la lista todavía carga no lanza errores. Nota: también pasa sin el
  `mounted` que sigue a `listarObjetos`, porque el `catch` de `_cargar` atrapa el error y vuelve a revisar `mounted`.

## Verificado en el iPhone real (2026-11-22)
- Sergio pegó la clave de administrador en la pestaña Estado, abrió Inventario, creó un objeto con lugar, lo renombró,
  lo movió y lo archivó; el planeta Objetos cambió de tamaño. Todo funcionó.

## Pendiente
- Visualización de objetos individuales dentro del planeta o como satélites cuando se decida cómo representarlos
  gráficamente en la galaxia (decisión 12 de `docs/DECISIONES-ABIERTAS.md`).
