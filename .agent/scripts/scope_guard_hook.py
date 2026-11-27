#!/usr/bin/env python3
"""
scope_guard_hook.py — Native Google Antigravity PreToolUse hook for `run_command`.

Reads Antigravity's camelCase JSON hook payload from stdin, checks whether the
command invokes an active network/recon tool against external hosts, and if
`scope.md` exists in the working directory, validates every extracted host
deterministically via `engine/scope.py` (deny-wins, default-deny).

Non-network commands (git, python tests, file utilities, localhost probes) are
always allowed with zero friction.
"""
import json
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
for _candidate in (_SCRIPT_DIR.parent, _SCRIPT_DIR.parents[1]):
    if (_candidate / "engine" / "scope.py").is_file():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break

from engine.scope import _scope_from_md  # noqa: E402

# Tools that perform active network/recon requests against targets
NETWORK_TOOLS_RE = re.compile(
    r"(?:^|[;&|(\s])("
    r"curl(?:\.exe)?|wget(?:\.exe)?|Invoke-WebRequest|iwr|Invoke-RestMethod|irm|"
    r"httpx|nuclei|ffuf|subfinder|katana|gau|waybackurls|nmap|masscan|"
    r"sqlmap|dalfox|gobuster|feroxbuster|dirsearch|nikto|wfuzz|grpcurl"
    r")(?:\s|$)",
    re.IGNORECASE,
)

# Extract http(s)://... URLs from the command line
URL_RE = re.compile(r"https?://[^\s'\"`<>|;&)]+", re.IGNORECASE)

# Extract explicit target flags like -u host, --target host, -d domain.com
FLAG_TARGET_RE = re.compile(
    r"(?:^|\s)(?:-u|--url|-t|--target|-d|--domain|-h|--host)\s+['\"]?([a-zA-Z0-9._:-]+\.[a-zA-Z0-9.-]+)['\"]?"
)

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def emit(decision: str, reason: str | None = None) -> None:
    payload: dict[str, str] = {"decision": decision}
    if reason:
        payload["reason"] = reason
    sys.stdout.write(json.dumps(payload) + "\n")


def extract_targets(command: str) -> list[str]:
    targets: list[str] = []
    for url in URL_RE.findall(command):
        targets.append(url.rstrip(".,;)"))
    for host in FLAG_TARGET_RE.findall(command):
        if host.lower() not in LOCAL_HOSTS and not host.startswith("-"):
            targets.append(host)
    return targets


def is_local_target(target: str) -> bool:
    cleaned = re.sub(r"^https?://", "", target, flags=re.IGNORECASE)
    host = cleaned.split("/")[0].split(":")[0].lower().strip("[]")
    return host in LOCAL_HOSTS or host.endswith(".localhost")


def find_scope_md(cwd: str | None, workspace_paths: list[str]) -> Path | None:
    candidates: list[Path] = []
    if cwd:
        candidates.append(Path(cwd) / "scope.md")
    for ws in workspace_paths:
        candidates.append(Path(ws) / "scope.md")
    for path in candidates:
        if path.is_file():
            return path
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        emit("allow")
        return 0

    tool_call = data.get("toolCall") or {}
    if tool_call.get("name") != "run_command":
        emit("allow")
        return 0

    args = tool_call.get("args") or {}
    command = str(args.get("CommandLine") or "")
    if not command or not NETWORK_TOOLS_RE.search(command):
        emit("allow")
        return 0

    targets = [t for t in extract_targets(command) if not is_local_target(t)]
    if not targets:
        emit("allow")
        return 0

    scope_md = find_scope_md(data.get("cwd"), data.get("workspacePaths") or [])
    if scope_md is None:
        # No active engagement scope.md present; do not block general dev commands.
        emit("allow")
        return 0

    try:
        scope = _scope_from_md(str(scope_md))
    except Exception as exc:
        emit("deny", f"Failed to parse {scope_md}: {exc}")
        return 0

    blocked: list[str] = []
    for target in targets:
        reason = scope.reject_reason(target)
        if reason is not None:
            blocked.append(f"{target} ({reason})")

    if blocked:
        emit(
            "deny",
            f"Blocked by scope-guard ({scope_md.name}): " + "; ".join(blocked),
        )
        return 0

    emit("allow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
