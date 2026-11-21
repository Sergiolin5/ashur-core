# Herramientas

## REA
- **Repositorio:** github.com/morluto/rea
- **Para qué se usa:** herramienta inicial de Claude Code y de Ashur, conectada vía MCP.
- **Qué requiere:** un cliente MCP (Claude Code ya lo es; Ashur lo será desde el core). Los requisitos de
  instalación, el lenguaje y las herramientas concretas que expone están **por verificar**: al escribir este
  documento no había acceso a la red para leer el repositorio, y no se instaló nada.

## Advisor de Claude Code
- **Para qué se usa:** un revisor más fuerte que ve toda la conversación de la sesión. En este repo se consulta antes
  de cada decisión de arquitectura (incluido cada ADR) y antes de cerrar una tarea (ver `CLAUDE.md`).
- **Qué requiere:**
  - Claude Code.
  - La clave `"advisorModel"` en los ajustes. El repo la trae en `.claude/settings.json` (`{"advisorModel": "opus"}`).
  - Verificado el 2026-11-21: al añadir `"advisorModel": "opus"` a `~/.claude/settings.json`, la herramienta
    `advisor` apareció en la sesión en curso sin reiniciarla.
