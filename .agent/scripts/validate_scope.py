#!/usr/bin/env python3
"""
validate_scope.py — Antigravity pre-flight scope validator.

Delegates directly to `engine/scope.py` (deterministic deny-wins, default-deny,
IDN/IPv6 canonicalization, backslash-hardened authority parsing).

Usage:
    python .agent/scripts/validate_scope.py --target api.example.com --scope scope.md
    python .agent/scripts/validate_scope.py api.example.com staging.example.com --scope scope.md
"""
import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
for _candidate in (_SCRIPT_DIR.parent, _SCRIPT_DIR.parents[1]):
    if (_candidate / "engine" / "scope.py").is_file():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break

from engine.scope import _scope_from_md  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate target(s) against scope.md using engine/scope.py (deny-wins, default-deny)."
    )
    parser.add_argument(
        "positional_targets",
        nargs="*",
        help="Target domain(s), URL(s), or IP(s)",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Target domain, URL, or IP (repeatable)",
    )
    parser.add_argument(
        "--scope",
        default="scope.md",
        help="Path to scope.md (default: scope.md)",
    )
    args = parser.parse_args(argv)

    targets = list(args.target) + list(args.positional_targets)
    if not targets:
        parser.error("Provide at least one target via --target or positional argument.")

    scope_path = Path(args.scope)
    if not scope_path.exists():
        print(f"[BLOCKED] Scope file not found: {scope_path}", file=sys.stderr)
        return 1

    scope = _scope_from_md(str(scope_path))
    for warning in getattr(scope, "warnings", []):
        print(f"[WARN] {warning}", file=sys.stderr)

    exit_code = 0
    for target in targets:
        reason = scope.reject_reason(target)
        if reason is None:
            print(f"[OK] IN-SCOPE: {target} ({scope_path})")
        else:
            print(f"[BLOCKED] OUT-OF-SCOPE: {target} ({reason})", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
