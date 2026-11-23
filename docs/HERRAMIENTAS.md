# Herramientas

## REA
- **Repositorio:** github.com/morluto/rea
- **Para qué se usa:** herramienta inicial de Claude Code y de Ashur, conectada vía MCP.
- **Qué es:** «Reverse Engineer Anything», un servidor MCP y una línea de comandos (`rea`) de ingeniería inversa para
  binarios, apps de Electron y JavaScript, y sitios web. El paquete de npm es `rea-agents`.
- **Instalación:** `npx rea-agents@latest setup` (lo corrió Sergio el 2026-11-22; versión 6.10.1). Registra el servidor
  MCP `rea` en Claude Code e instala la skill `reverse-engineer-anything`. Las herramientas MCP aparecen recién en una
  sesión nueva; la línea de comandos sirve de inmediato.
- **Uso verificado:** `rea analyze-javascript-application <carpeta> --json` sobre el JavaScript público de Nexo
  (`modules/workbench/README.md`). Leyó los 48 archivos, pero no reconoció las rutas de TanStack: las pantallas se
  sacaron leyendo los archivos a mano.

## Advisor de Claude Code
- **Para qué se usa:** un revisor más fuerte que ve toda la conversación de la sesión. En este repo se consulta antes
  de cada decisión de arquitectura (incluido cada ADR) y antes de cerrar una tarea (ver `CLAUDE.md`).
- **Qué requiere:**
  - Claude Code.
  - La clave `"advisorModel"` en los ajustes. El repo la trae en `.claude/settings.json` (`{"advisorModel": "opus"}`).
  - Verificado el 2026-11-21: al añadir `"advisorModel": "opus"` a `~/.claude/settings.json`, la herramienta
    `advisor` apareció en la sesión en curso sin reiniciarla.
