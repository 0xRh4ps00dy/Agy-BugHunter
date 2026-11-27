# Entorno del Sistema (Windows PowerShell y Python)

- **Sistema Operativo Host:** Windows (PowerShell 5.1 / 7+) con Python 3.9+.
- **Comandos de Terminal:** Usa comandos nativos de Windows PowerShell o scripts multiplataforma en Python (`python`).
- **Equivalencias Linux → Windows PowerShell:**
  - `grep` → `Select-String` (o `rg` si está disponible).
  - `awk` / `sed` → `ForEach-Object`, `-replace`, o scripts en Python.
  - `export VAR=val` → `$env:VAR = "val"`.
  - `/tmp/` → `$env:TEMP\`.
  - `python3` → `python` (o `py -3`).
- **Codificación:** Usa siempre UTF-8 sin BOM al escribir archivos para evitar incompatibilidades entre Windows y herramientas CLI/Python.
