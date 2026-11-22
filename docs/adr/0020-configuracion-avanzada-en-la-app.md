# ADR 0020: configuración avanzada en la app

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Relacionada:** `docs/adr/0019-ajustes-de-modulos-y-nodos.md`

## Contexto
La decisión 19 deja la configuración de los módulos y nodos en el core y sitúa su pantalla en la pestaña Estado. Las
rutas para personalidad, correcciones, roles y claves de personas ya existen (ADR 0022 y 0024), pero la sección de la
app todavía no está creada. La app es pública y la personalidad de Sergio es privada.

## Decisión
- La pestaña Estado incluye una sección «Configuración avanzada», después de los datos de conexión con el core. Puede
  desplazarse junto con el resto de la pantalla.
- La sección usa el core como fuente de verdad: al abrirla lee por HTTP los datos disponibles y envía los cambios al
  core. No agrega copias locales de la personalidad, correcciones, roles, identidades ni claves de personas.
- Las lecturas usan `X-Ashur-Clave`. Las acciones que cambian datos solo muestran controles si existe una clave de
  administrador guardada. Esa clave usa el Llavero que ya emplea la app; no se agrega otro mecanismo de almacenamiento.
- «Lo de Ashur» agrupa personalidad, correcciones, roles y acceso de las personas. Su contrato de cliente y sus reglas
  se detallan en el ADR 0026. La sección admite las demás áreas de configuración previstas por el ADR 0019 sin cambiar
  los endpoints del core.
- **Nodos:** lista los nodos, su estado, modo y modelos. La clave de administrador permite elegir modelos (o todos),
  fijar o devolver al nodo su contexto, configurar un horario (o estar disponible a toda hora), archivar/restaurar y
  crear nodos. La clave nueva de un nodo solo se muestra una vez y se puede copiar; la app no la guarda.
- **Módulos:** lista los módulos y sus errores. Cada ajuste se dibuja según su tipo; los secretos nunca muestran el
  valor recibido y solo indican si están configurados. Guardar el valor `null` vuelve al valor por defecto.
- Sin clave de administrador se muestran los valores, pero no aparecen controles de cambio. Los datos de nodos y
  módulos se leen del core y no se guardan en el teléfono.
- La pantalla sigue el estilo y los componentes Cupertino que ya usa Estado. No agrega paquetes ni modifica temas.

## Costos
- La sección requiere conexión con el core para mostrar los valores actuales; no presenta personalidad almacenada en
  caché cuando el core no responde.
- La clave nueva de una persona desaparece al cerrar su diálogo. Si no se copia en ese momento, habrá que crear otra,
  lo que invalida la anterior.

## Verificado (2026-11-22)
- `flutter test` cubre el cliente de nodos y ajustes de módulos contra un core falso en localhost (incluidos 401, 404,
  422 y 503), los controles según la clave de administrador, los tipos de ajustes y el envío de `null` para volver al
  valor por defecto.
- `flutter analyze` revisa la app Flutter.

Eso se verificó en la Mac con el commit 788f7a5 de la rama `config-avanzada`, antes de unirla sobre Face ID
(ADR 0025). La unión, las guardas de `SecretoBloqueado` y el almacén falso de `lo_de_ashur_test.dart` puesto al día no
se compilaron: en el equipo Windows no hay Flutter.

## Pendiente
- Correr `flutter analyze` y `flutter test` en la Mac con la unión.
- Verificar en un iPhone la lectura y edición de ajustes y el copiado de la clave de nodo, también con Face ID
  cancelado.
- Un nodo restaurado ya no se puede usar, porque archivarlo le quita la clave para siempre (ADR 0016). «Restaurar» solo
  sirve para verlo en la lista; para volver a usar el equipo, hay que crear un nodo nuevo.
