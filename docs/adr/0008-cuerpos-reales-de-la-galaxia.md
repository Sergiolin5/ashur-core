# ADR 0008: cada cuerpo de la galaxia es una cosa real del sistema

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Sergio pidió que los cuerpos de la galaxia sean cosas del sistema y que la galaxia tenga escalas como las reales,
sin perder la estética. Además, quedaba abierto cómo llega al cliente lo que hace crecer el polvo (decisión 6).

## Decisión
- **`ref` en cada cuerpo:** cada cuerpo trae `ref: {tipo, id}`, con `tipo` igual a `identidad`, `modulo` o
  `agente`. Es `null` para el núcleo, las colecciones del core y los asteroides. El `id` del cuerpo es propio de la
  galaxia, y el de `ref` es el de la cosa, para que dos listas distintas no choquen.
- **Recuerdos:** no son cuerpos. Dan masa al núcleo y hacen crecer el polvo.
- **Identidades:** son un planeta del core. Cada identidad sube y baja de nivel según su importancia: contacto sin
  peso, `personaje` sobre el planeta, `luna` que lo orbita o planeta propio, con un margen para que no parpadee
  (`docs/GALAXIA.md`). El core decide el nivel.
- **Polvo:** el contrato trae `aprendizaje: {inicio, recuerdos}`, y el cliente calcula la densidad con la fórmula de
  `docs/GALAXIA.md`. Los parámetros viven en `app/lib/galaxia/pintor.dart` y son provisionales.
- **Cliente:** las lunas se dibujan como puntos tenues que orbitan su planeta, con el mismo cálculo que los
  asteroides. Los personajes no se dibujan todavía, porque solo se ven con el zoom.

## Pendiente
- **Zoom y nivel de detalle** (decisión 14). Sin verificar:
  - Moverse y acercarse con `InteractiveViewer` y `TransformationController`, que vienen con Flutter, y pasar la
    matriz al pintor.
  - Tocar el núcleo con el zoom puesto: el toque se convierte con la matriz inversa y mantiene el mínimo de 22 px en
    pantalla del ADR 0002.
  - Acercarse con dos dedos y tocar con uno pueden chocar.
  - No dibujar lo que queda fuera de la pantalla o mide menos de un píxel.
  - Repensar el polvo en coordenadas del mundo.
- **Umbrales de las identidades:** el core todavía no los calcula, y el core todavía no publica la galaxia.
- **Objetos del inventario** (decisión 12) y **otras lunas** (decisión 13).
- **De dónde sale `aprendizaje.inicio`** (decisión 15).
