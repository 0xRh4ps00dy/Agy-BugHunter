# Guía de Code Review para Programas de Bug Bounty

Flujo recomendado para auditar un repositorio de código fuente dentro de un programa de Bug Bounty usando `abh` (Agy-BugHunter).

## 1. Preparación y Scope (obligatorio)

1. **Confirma que el repositorio está en scope** en las reglas del programa (y si vas a probar contra un entorno vivo, valídalo antes con `abh scope <target>`).
2. **Crea tu carpeta de auditoría** para llevar el control:
   ```powershell
   abh new mi-programa
   ```
   (o importa el scope directamente con `abh import h1:<handle> -o scope.md`).

## 2. Mapeo rápido del repositorio (15–30 min)

Antes de buscar bugs al azar, entiende qué hace la aplicación:

- **Stack y dependencias:** revisa `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `pom.xml`, `Cargo.toml` (busca dependencias desactualizadas o con CVEs conocidos).
- **Entrypoints (superficie de ataque):** localiza dónde entran los datos del usuario:
  - Rutas REST/HTTP, controladores, resolvers GraphQL, servicios gRPC, WebSockets, webhooks o workers/colas.
- **Autenticación y Autorización:** identifica dónde están los middlewares/guards de sesión, JWT, OAuth, roles y aislamiento multi-tenant.

## 3. Búsqueda dirigida por clases de vulnerabilidad (Sinks → Sources)

En lugar de leer archivo por archivo, busca **sinks peligrosos** y traza hacia atrás si el usuario controla la entrada:

- **Broken Access Control / IDOR:** endpoints que reciben `id`, `user_id`, `org_id`, `file_id` y consultan la BD sin comprobar que el recurso pertenece al usuario/tenant autenticado.
- **Inyecciones:**
  - **SQLi:** concatenación de strings o f-strings en queries SQL (`SELECT ... + req.body`).
  - **RCE / Command Injection:** `eval`, `exec`, `os.system`, `subprocess(..., shell=True)`, `child_process.exec`.
  - **SSRF:** llamadas HTTP (`requests`, `fetch`, `axios`, `urllib`, `http.Get`) donde la URL o parte de ella viene del usuario.
  - **Path Traversal / File Upload:** `open()`, `send_file()`, `fs.readFile()` con rutas construidas desde parámetros sin `basename`/normalización.
  - **SSTI / XSS:** renderizado de plantillas sin escapar o `dangerouslySetInnerHTML` / `innerHTML`.
- **Deserialización y Crypto:** `pickle.loads`, `yaml.load` sin `SafeLoader`, `unserialize`, verificación débil de JWT (`alg: none` o secreto débil) o firmas HMAC sin `compare_digest`.
- **CI/CD y Secretos:** revisa `.github/workflows/` (inyección en `pull_request_target` o `${{ github.event... }}`) y posibles credenciales/tokens en configs o historial.

## 4. Validación y Reporte

1. **Verifica la explotabilidad:** confirma que la entrada del usuario realmente llega al sink sin sanitización efectiva (idealmente reproduciéndolo en local con Docker/tests).
2. **Filtra falsos positivos:** usa `/triage` o `/validate` (7-Question Gate) para asegurar que tiene impacto real y no es un bug teórico.
3. **Registra y redacta:** guarda el avance con `abh tested` / `abh finding` y genera el borrador con `/report`.

## 5. Enfoque defensivo y prompts recomendados (Antigravity)

Para auditorías de código fuente, conviene redactar las peticiones con enfoque de **ingeniería de software, calidad y hardening** (evitando jerga ofensiva genérica) y apuntar a archivos o directorios concretos:

- **Análisis de arquitectura y autenticación:**
  > *"Analiza la arquitectura y los flujos de autenticación en los archivos de este proyecto para detectar posibles fallos lógicos o de validación."*
- **Revisión OWASP Top 10 en un directorio concreto:**
  > *"Revisa el código fuente en `src/` buscando malas prácticas de seguridad según OWASP Top 10 (inyecciones, gestión de sesiones, permisos) y propón soluciones."*
- **Control de acceso y mínimo privilegio:**
  > *"Haz una revisión defensiva de los endpoints y controladores de este directorio para asegurar que aplican correctamente el principio de mínimo privilegio."*

> **Nota:** Si trabajas solo en revisión de código estático, puedes abrir `agy .` directamente en la carpeta del repositorio (sin cargar reglas de red teaming en el contexto inicial) o desactivar temporalmente las reglas globales ofensivas en `~/.gemini/config/plugins/`.
