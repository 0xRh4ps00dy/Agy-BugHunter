# Alcance Autorizado y Validación Pre-Ejecución

- **Autorización Obligatoria:** Toda actividad de reconocimiento, auditoría o verificación de seguridad debe limitarse estrictamente a los activos autorizados en `scope.md`.
- **Motor Determinista (`engine/scope.py`):** La validación aplica siempre **deny-wins** y **default-deny**. Si un activo coincide con una regla de exclusión (`Out of Scope`) o no coincide con ninguna regla de inclusión, se bloquea.
- **Validación Pre-Ejecución:**
  - Antes de lanzar cualquier herramienta CLI contra un dominio, URL o IP, valida el objetivo mediante `.agent/scripts/validate-scope.ps1` o `.agent/scripts/validate_scope.py`.
  - Además, el hook nativo `.agent/hooks.json` (`PreToolUse` en `run_command`) audita automáticamente comandos de red/reconocimiento cuando existe `scope.md`.
- **Higiene de Evidencia:** Anonimiza o redacta cookies, tokens, credenciales y PII antes de guardar logs, capturas o reportes. Nunca subas artefactos de engagement (`scope.md`, `findings/`, `evidence/`, `recon/`) al repositorio Git.
