#!/usr/bin/env python3
"""
agy_cli.py — Clean, cross-platform CLI (`agy-bh`) for Agy-BugHunter.

Eliminates verbose PowerShell ExecutionPolicy invocations by providing short,
consistent commands usable from any directory on Windows, macOS, and Linux:

    agy-bh install [--mcp]
    agy-bh uninstall
    agy-bh new C:\\Auditorias\\acme [--name "Acme Corp"]
    agy-bh scope api.acme.com [staging.acme.com ...] [--file scope.md]
    agy-bh status [dir]
    agy-bh phase recon done "42 live hosts"
    agy-bh tested api.acme.com idor --result negative --note "UUIDv4 + owner check"
    agy-bh finding "IDOR on /api/v1/invoices" High api.acme.com --status validated
    agy-bh note "Next: check OAuth redirect_uri on auth.acme.com"
"""
import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "agy-bughunter"
PLUGIN_ROOT = Path.home() / ".gemini" / "config" / "plugins" / PLUGIN_NAME


def _load_module(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_script(filename: str) -> Path:
    for base in (REPO_ROOT / ".agent" / "scripts", PLUGIN_ROOT / "scripts"):
        candidate = base / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not locate {filename}. Run `agy-bh install` from the Agy-BugHunter repo first."
    )


def _write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def cmd_install(args: argparse.Namespace) -> int:
    agent_dir = REPO_ROOT / ".agent"
    if not (agent_dir / "skills").is_dir():
        print(f"[ERROR] .agent/skills not found in {REPO_ROOT}", file=sys.stderr)
        return 1

    if PLUGIN_ROOT.exists():
        shutil.rmtree(PLUGIN_ROOT)
    PLUGIN_ROOT.mkdir(parents=True, exist_ok=True)

    # 1. plugin.json
    plugin_json = {
        "name": PLUGIN_NAME,
        "author": "Agy-BugHunter (adapted from Claude-BugHunter by Sachin Sharma)",
    }
    _write_utf8(PLUGIN_ROOT / "plugin.json", json.dumps(plugin_json, indent=2) + "\n")

    # 2. hooks.json (at plugin root per Antigravity plugin spec)
    shutil.copy2(agent_dir / "hooks.json", PLUGIN_ROOT / "hooks.json")

    # 3. rules/AGENTS.md
    (PLUGIN_ROOT / "rules").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "AGENTS.md", PLUGIN_ROOT / "rules" / "AGENTS.md")

    # 4. skills/ (all 101 skills + references/scripts)
    shutil.copytree(
        agent_dir / "skills",
        PLUGIN_ROOT / "skills",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    # 5. scripts/
    shutil.copytree(
        agent_dir / "scripts",
        PLUGIN_ROOT / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    # 6. engine/scope.py (self-contained deterministic scope engine)
    eng_dir = PLUGIN_ROOT / "engine"
    eng_dir.mkdir(parents=True, exist_ok=True)
    _write_utf8(eng_dir / "__init__.py", "")
    shutil.copy2(REPO_ROOT / "engine" / "scope.py", eng_dir / "scope.py")

    # 7. Optional HackerOne MCP server
    if args.mcp:
        mcp_dir = PLUGIN_ROOT / "mcp" / "hackerone"
        mcp_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / "mcp" / "hackerone" / "server.py", mcp_dir / "server.py")
        server_path = str(mcp_dir / "server.py").replace("\\", "/")
        mcp_cfg = {
            "mcpServers": {
                "hackerone": {
                    "command": "python",
                    "args": [server_path],
                    "env": {
                        "HACKERONE_API_USERNAME": "",
                        "HACKERONE_API_TOKEN": "",
                    },
                }
            }
        }
        _write_utf8(PLUGIN_ROOT / "mcp_config.json", json.dumps(mcp_cfg, indent=2) + "\n")
        print("[OK] HackerOne MCP configurado en mcp_config.json")

    skill_count = sum(1 for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir())
    print(f"[OK] Plugin '{PLUGIN_NAME}' instalado ({skill_count} skills + reglas + scope-guard + progreso)")
    print(f"     Ruta: {PLUGIN_ROOT}")
    return 0


def cmd_uninstall(_args: argparse.Namespace) -> int:
    if PLUGIN_ROOT.exists():
        shutil.rmtree(PLUGIN_ROOT)
        print(f"[OK] Plugin desinstalado: {PLUGIN_ROOT}")
    else:
        print(f"[INFO] El plugin no estaba instalado en {PLUGIN_ROOT}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    target_dir = Path(args.path).expanduser().resolve()
    eng_name = args.name or target_dir.name

    for sub in ("", "recon", "findings", "evidence"):
        (target_dir / sub if sub else target_dir).mkdir(parents=True, exist_ok=True)

    scope_file = target_dir / "scope.md"
    if not scope_file.exists():
        _write_utf8(
            scope_file,
            f"# Scope — {eng_name}\n\n"
            "## In scope\n"
            "- (pega aquí los dominios autorizados, wildcards *.ejemplo.com o CIDRs)\n\n"
            "## Out of scope\n"
            "- (pega aquí los activos excluidos, p. ej. admin.ejemplo.com)\n\n"
            "## Notes\n"
            "- Tipo: WAPT / Bug Bounty / External Red Team\n",
        )

    prog_mod = _load_module("audit_progress", _find_script("audit_progress.py"))
    if not (target_dir / "progress.json").exists():
        prog_mod.main(["init", "--dir", str(target_dir), "--name", eng_name])

    print(f"[OK] Auditoría creada en: {target_dir}")
    print(f"  1. Rellena el alcance:  {scope_file}")
    print(f"  2. Progreso guardado:   {target_dir / 'PROGRESS.md'}")
    print(f"  3. Abre '{target_dir}' en Google Antigravity para empezar.")
    return 0


def cmd_scope(args: argparse.Namespace) -> int:
    val_mod = _load_module("validate_scope", _find_script("validate_scope.py"))
    argv = ["--scope", args.file, *args.targets]
    return val_mod.main(argv)


def cmd_progress_proxy(subcmd: str, argv: list[str]) -> int:
    prog_mod = _load_module("audit_progress", _find_script("audit_progress.py"))
    return prog_mod.main([subcmd, *argv])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agy-bh",
        description="CLI de Agy-BugHunter para Google Antigravity.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inst = sub.add_parser("install", help="Instala el plugin global en ~/.gemini/config/plugins/agy-bughunter/")
    p_inst.add_argument("--mcp", action="store_true", help="Incluye el servidor MCP de HackerOne")

    sub.add_parser("uninstall", help="Desinstala el plugin global")

    p_new = sub.add_parser("new", help="Crea una carpeta de auditoría independiente")
    p_new.add_argument("path", help="Ruta donde crear la auditoría (p. ej. C:\\Auditorias\\acme)")
    p_new.add_argument("--name", "-n", default=None, help="Nombre descriptivo del cliente/programa")

    p_scope = sub.add_parser("scope", help="Valida uno o más objetivos contra scope.md")
    p_scope.add_argument("targets", nargs="+", help="Dominios, URLs o IPs a validar")
    p_scope.add_argument("--file", "-f", default="scope.md", help="Ruta a scope.md (por defecto: scope.md)")

    p_status = sub.add_parser("status", help="Muestra el PROGRESS.md actual")
    p_status.add_argument("dir", nargs="?", default=".", help="Carpeta de la auditoría (por defecto: .)")

    p_phase = sub.add_parser("phase", help="Actualiza el estado de una fase")
    p_phase.add_argument("name", help="Fase: scope, recon, surface, hunting, validation, reporting")
    p_phase.add_argument("state", choices=["pending", "in_progress", "done", "skipped"])
    p_phase.add_argument("summary", nargs="?", default="", help="Resumen breve")
    p_phase.add_argument("--dir", "-d", default=".")

    p_tested = sub.add_parser("tested", help="Registra un objetivo/clase ya probado")
    p_tested.add_argument("target")
    p_tested.add_argument("vuln_class")
    p_tested.add_argument("--result", "-r", default="negative", choices=["negative", "promising", "confirmed", "blocked"])
    p_tested.add_argument("--note", "-n", default="")
    p_tested.add_argument("--dir", "-d", default=".")

    p_find = sub.add_parser("finding", help="Registra un hallazgo")
    p_find.add_argument("title")
    p_find.add_argument("severity", choices=["Critical", "High", "Medium", "Low", "Info"])
    p_find.add_argument("target")
    p_find.add_argument("--status", "-s", default="candidate", choices=["candidate", "validated", "reported", "rejected"])
    p_find.add_argument("--dir", "-d", default=".")

    p_note = sub.add_parser("note", help="Añade una nota o siguiente paso")
    p_note.add_argument("text")
    p_note.add_argument("--dir", "-d", default=".")

    p_import = sub.add_parser("import", help="Importa scope desde HackerOne/Bugcrowd/Intigriti (ej. abh import h1:handle -o scope.md)")
    p_import.add_argument("import_args", nargs=argparse.REMAINDER, help="Argumentos para `cbh scope import`")

    args = parser.parse_args(argv)

    if args.cmd == "install":
        return cmd_install(args)
    if args.cmd == "uninstall":
        return cmd_uninstall(args)
    if args.cmd == "new":
        return cmd_new(args)
    if args.cmd == "scope":
        return cmd_scope(args)
    if args.cmd == "status":
        return cmd_progress_proxy("status", ["--dir", args.dir])
    if args.cmd == "phase":
        return cmd_progress_proxy("phase", ["--dir", args.dir, "--name", args.name, "--state", args.state, "--summary", args.summary])
    if args.cmd == "tested":
        return cmd_progress_proxy("tested", ["--dir", args.dir, "--target", args.target, "--class", args.vuln_class, "--result", args.result, "--note", args.note])
    if args.cmd == "finding":
        return cmd_progress_proxy("finding", ["--dir", args.dir, "--title", args.title, "--severity", args.severity, "--target", args.target, "--status", args.status])
    if args.cmd == "note":
        return cmd_progress_proxy("note", ["--dir", args.dir, "--text", args.text])
    if args.cmd == "import":
        from cbh import cli as cbh_cli
        return cbh_cli.main(["scope", "import", *args.import_args])
    return 0


if __name__ == "__main__":
    sys.exit(main())
