# Reglas del repo Ashur Core

Estas reglas valen para toda sesión de Claude Code (u otra IA) que trabaje en este repo.

## Idioma
- Toda la documentación, los mensajes de commit y las respuestas a Sergio van en español.

## Modularidad
- El core es solo memoria, chat, inventario de objetos físicos y contactos. Todo lo demás es un módulo en `modules/`.
- Un módulo cumple el contrato de `docs/MODULOS.md` y no depende de otro módulo.
- Un módulo por tarea: una tarea no toca dos módulos ni mezcla un módulo con cambios del core.
- La galaxia es un contrato de datos (`contracts/galaxy-state.schema.json`): el cliente solo la dibuja.

## Cambios
- Cambios mínimos: entrega solo lo pedido, sin funciones, abstracciones ni configuraciones extra.
- Sin temas ni ajustes de apariencia en la app.
- Ninguna dependencia nueva (paquete de pubspec.yaml, librería del servidor, herramienta) sin aprobación de Sergio.
- Detente y pregunta antes de borrar archivos, crear un remoto o hacer push.

## Advisor
- Consulta al advisor antes de cada decisión de arquitectura (incluido escribir un ADR en `docs/adr/`).
- Consulta al advisor antes de dar una tarea por cerrada.

## Fuera del repo
- `../ashur` (repo anterior) y `../_referencias/` son solo lectura. Las rutas que empiezan con `../` son relativas a la raíz de este repo.
- `~/.ashur` (en la Mac de Sergio) es la instalación en ejecución: nunca se lee ni se modifica.
