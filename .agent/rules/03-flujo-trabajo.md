# Flujo de Trabajo y Herramientas (Antigravity)

- **Gestión de Tareas y Progreso Persistente:**
  - Usa `update_steps` para checklists en vivo durante la sesión.
  - En carpetas de auditoría con `PROGRESS.md` / `progress.json`, léelo al iniciar para retomar donde lo dejaste y actualízalo (con `audit_progress.py` o editando `PROGRESS.md`) al completar fases, descartar rutas o confirmar hallazgos.
- **Delegación de Subagentes:**
  - Usa `invoke_subagent` (`research` para exploración de solo lectura, `self` para tareas completas) en lugar del antiguo `Task`.
- **Consultas Web y HTTP:**
  - Usa `search_web` para búsquedas de información y `Invoke-WebRequest` / `python` para peticiones HTTP controladas dentro del alcance autorizado.
- **Skills y Comandos:**
  - Las 85 skills y los 16 flujos de comando (`cmd-*`) están en `.agent/skills/<nombre>/SKILL.md` con frontmatter YAML válido (`name` y `description`) y sus carpetas de soporte (`references/`, `scripts/`).
- **MCP:**
  - El servidor MCP de HackerOne está en `mcp/hackerone/server.py`. Copia `.agent/mcp_config.example.json` a tu configuración de Antigravity (`~/.gemini/config/mcp_config.json`) para habilitarlo.
