# Agy-BugHunter — Workspace Rules (Google Antigravity)

This repository is the **Google Antigravity** adaptation of the BugHunter security-assessment and bug-bounty harness (85 modular skills + 16 workflow command skills + deterministic scope/recon engine + HackerOne MCP server).

## 1. Authorized Scope & Pre-Flight Enforcement (Hard Rule)

- **Authorization required:** Only assess domains, subdomains, IPs, CIDRs, or applications explicitly authorized in `scope.md`.
- **Deterministic enforcement:** Scope is validated in **code** via `engine/scope.py` (deny-wins, default-deny) — never by guesswork.
- **Pre-flight check:** Before running any active HTTP, recon, or scanning command against a target, validate the target with:
  ```powershell
  .\.agent\scripts\validate-scope.ps1 -Target <host-or-url> -ScopeFile scope.md
  # or cross-platform:
  python .agent/scripts/validate_scope.py --target <host-or-url> --scope scope.md
  ```
- **Automated hook guard:** `.agent/hooks.json` registers a native Antigravity `PreToolUse` hook (`.agent/scripts/scope_guard_hook.py`) on `run_command` that checks active network/recon commands against `scope.md` when present.
- **Hard stop:** If `scope.md` is missing or returns `OUT-OF-SCOPE`, stop immediately and do not probe the asset.

## 2. Antigravity Native Tools & Conventions

When any skill references legacy Claude Code tool names, use the native Antigravity equivalent:

| Legacy Reference | Antigravity Equivalent |
|---|---|
| `TodoWrite` / `TodoRead` | `update_steps` (live checklist) and/or `TASKS.md` |
| `Task` | `invoke_subagent` (`research` for read-only exploration, `self` for full tasks) |
| `WebFetch` | `search_web` or controlled HTTP via PowerShell (`Invoke-WebRequest`) / `python` |
| `AskUserQuestion` | `ask_question` (for structured choices) or direct reply |
| Slash commands (`/hunt`, `/scope`, ...) | Load the corresponding `.agent/skills/cmd-<name>/SKILL.md` |

## 3. Host Environment (Windows PowerShell & Cross-Platform Python)

- Prefer native **Windows PowerShell** commands or cross-platform **Python** (`python` / `py -3`) over Linux-only shell idioms:
  - `grep` → `Select-String` (or `rg` if installed)
  - `awk` / `sed` → PowerShell pipelines (`ForEach-Object`, `-replace`) or Python
  - `export VAR=val` → `$env:VAR = "val"`
  - `/tmp/` → `$env:TEMP\`
  - `python3` → `python` (or `py -3`)
- Always read and write text files in **UTF-8** (BOM-free) to prevent encoding issues on Windows.

## 4. Audit Progress Persistence & Session Resume

- **Always check `PROGRESS.md` on startup:** When working inside an engagement directory that contains `PROGRESS.md` (and `progress.json`), read `PROGRESS.md` first to resume without repeating already-tested endpoints or negative checks.
- **Keep progress up to date:** After completing a phase, testing a target/vulnerability class (including negative results), confirming a finding, or pausing a session, update `PROGRESS.md` / `progress.json` using `audit_progress.py` (bundled in `.agent/scripts/` and in the global plugin `~/.gemini/config/plugins/agy-bughunter/scripts/`).

## 5. Evidence Hygiene & Repository Safety

- **Never commit** engagement artifacts (`scope.md`, `PROGRESS.md`, `progress.json`, `findings/`, `evidence/`, `recon/`, `targets/`, `*.har`, screenshots, tokens, or `TASKS.md`).
- Redact session cookies, `Authorization` headers, API keys, and third-party PII before saving PoCs or reports (follow `.agent/skills/evidence-hygiene/SKILL.md`).
- Follow the 7-Question Gate (`.agent/skills/triage-validation/SKILL.md`) before drafting any vulnerability report.

## 6. Workspace Customization Layout

- `AGENTS.md` — Always-on workspace rules (this file).
- `.agent/rules/` — Modular rules (environment, scope, workflow).
- `.agent/skills/` — 101 Antigravity skills (85 domain/hunting skills + 16 `cmd-*` workflow skills, including supporting `references/` and `scripts/`).
- `.agent/hooks.json` — Native Antigravity lifecycle hooks (`PreToolUse` scope guard).
- `.agent/scripts/` — Scope validator (`validate_scope.py`, `validate-scope.ps1`), hook handler (`scope_guard_hook.py`), and audit progress tracker (`audit_progress.py`).
- `.agent/mcp_config.example.json` — Ready-to-use Antigravity MCP configuration template for the bundled HackerOne MCP server (`mcp/hackerone/server.py`) and optional Burp MCP.
