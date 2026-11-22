# Ashur Network

Módulo de análisis de observaciones de redes y dispositivos para Ashur.

## Alcance de esta versión

Esta versión recibe observaciones como parámetros y puede:

- Validar y normalizar observaciones.
- Consolidar observaciones con evidencias suficientes de identidad.
- Comparar dos instantáneas.
- Señalar servicios y puertos que merecen revisión.
- Entregar cambios relevantes a la memoria central de Ashur.

No escanea redes, no descubre dispositivos por sí mismo, no abre conexiones,
no ejecuta comandos, no mantiene procesos persistentes y no conserva una
base de datos propia.

## Acciones

- `analizar_observaciones`: recibe `observaciones`, valida y normaliza.
- `consolidar_servidores`: recibe `observaciones` y agrupa dispositivos.
- `comparar_observaciones`: recibe `anterior` y `actual`.
- `analizar_exposicion`: recibe `servidores` consolidados.
- `recordar_cambios`: recibe `eventos` y, opcionalmente, `limite`.

Consulta `modulo.py` para los campos y las validaciones exactas.

## Identidad y correlación

La consolidación utiliza primero `dispositivo.id_dispositivo`. Si no existe,
usa la combinación de `red_id` y MAC.

Sin esos datos, las observaciones no se fusionan y no participan en la
comparación entre instantáneas. Un hostname o una IP por sí solos no
constituyen evidencia suficiente.

La confianza indicada es una clasificación inicial de la evidencia
disponible, no una probabilidad estadística calibrada.

## Análisis de exposición

Las reglas de puertos son heurísticas. Un hallazgo no confirma una
vulnerabilidad, no prueba que un servicio sea accesible desde Internet y
no implica que un dispositivo esté comprometido.

## Memoria

El módulo no guarda memoria propia. `recordar_cambios` usa únicamente
`contexto.recordar()` para entregar recuerdos al core.

No consulta identidades ni objetos del inventario.

## Arquitectura futura

La arquitectura objetivo contempla agentes distribuidos en equipos
compatibles, observación de redes autorizadas, sincronización segura con
un Ashur Core central, identidad probabilística de dispositivos,
monitorización adaptativa y visualización topológica propia.

Nada de lo anterior está implementado por esta primera versión.

El futuro transporte, autenticación individual de agentes, TLS,
persistencia de instantáneas, ejecución periódica, agentes y visualización
requieren tareas independientes y revisión de arquitectura.

La topología de red no forma parte del contrato actual de la galaxia.

## Autoprueba

Desde `core/`:

    uv run pytest ../modules/network/autoprueba.py

Las pruebas usan datos inventados, un contexto falso y no necesitan red,
servicios externos ni una instancia de Ashur.
