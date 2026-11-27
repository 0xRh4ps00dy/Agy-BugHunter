#!/usr/bin/env python3
"""
audit_progress.py — Persistent audit progress tracker for Agy-BugHunter engagements.

Maintains both `progress.json` (structured state) and `PROGRESS.md` (human-readable
dashboard) inside any standalone engagement directory so sessions can be paused
and resumed cleanly across conversations.

Usage:
    python audit_progress.py init --dir . --name "Acme Corp"
    python audit_progress.py status --dir .
    python audit_progress.py phase --dir . --name recon --state done --summary "42 live hosts"
    python audit_progress.py tested --dir . --target api.acme.com --class idor --result negative --note "UUIDv4 + owner check"
    python audit_progress.py finding --dir . --title "IDOR on /api/v1/invoices" --severity High --target api.acme.com --status validated
    python audit_progress.py note --dir . --text "Next: test OAuth redirect_uri on auth.acme.com"
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PHASES = [
    ("scope", "Scope & Pre-flight"),
    ("recon", "Reconnaissance & Asset Discovery"),
    ("surface", "Attack Surface Mapping"),
    ("hunting", "Active Vulnerability Testing"),
    ("validation", "Finding Validation (7-Question Gate)"),
    ("reporting", "Evidence Hygiene & Reporting"),
]

VALID_PHASE_STATES = {"pending", "in_progress", "done", "skipped"}
STATE_ICON = {
    "pending": "[ ]",
    "in_progress": "[~]",
    "done": "[x]",
    "skipped": "[-]",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def default_state(name: str) -> dict:
    ts = now_utc()
    return {
        "engagement": name,
        "created_at": ts,
        "updated_at": ts,
        "phases": {
            key: {"label": label, "state": "pending", "summary": "", "updated_at": ""}
            for key, label in DEFAULT_PHASES
        },
        "tested": [],
        "findings": [],
        "notes": [],
    }


def load_state(eng_dir: Path) -> dict:
    json_path = eng_dir / "progress.json"
    if not json_path.exists():
        return default_state(eng_dir.name)
    return json.loads(json_path.read_text(encoding="utf-8"))


def render_markdown(state: dict) -> str:
    lines: list[str] = [
        f"# Audit Progress — {state.get('engagement', 'Engagement')}",
        "",
        f"- **Created:** {state.get('created_at', '-')}",
        f"- **Last updated:** {state.get('updated_at', '-')}",
        "",
        "## Phases",
        "",
    ]
    for key, info in state.get("phases", {}).items():
        icon = STATE_ICON.get(info.get("state", "pending"), "[ ]")
        label = info.get("label", key)
        summary = f" — {info['summary']}" if info.get("summary") else ""
        lines.append(f"- {icon} **{label}** (`{key}`){summary}")

    lines.extend(["", "## Findings", ""])
    findings = state.get("findings", [])
    if not findings:
        lines.append("_No findings recorded yet._")
    else:
        lines.append("| ID | Severity | Status | Target | Title | Recorded |")
        lines.append("|---|---|---|---|---|---|")
        for f in findings:
            lines.append(
                f"| {f['id']} | {f['severity']} | {f['status']} | `{f['target']}` | {f['title']} | {f['timestamp']} |"
            )

    lines.extend(["", "## Tested Surface & Negative Results", ""])
    tested = state.get("tested", [])
    if not tested:
        lines.append("_No tested items recorded yet._")
    else:
        lines.append("| Target | Class | Result | Note | Recorded |")
        lines.append("|---|---|---|---|---|")
        for t in tested:
            lines.append(
                f"| `{t['target']}` | `{t['vuln_class']}` | {t['result']} | {t['note']} | {t['timestamp']} |"
            )

    lines.extend(["", "## Session Notes & Next Steps", ""])
    notes = state.get("notes", [])
    if not notes:
        lines.append("_No session notes yet._")
    else:
        for n in notes:
            lines.append(f"- **[{n['timestamp']}]** {n['text']}")

    lines.append("")
    return "\n".join(lines)


def save_state(eng_dir: Path, state: dict) -> None:
    state["updated_at"] = now_utc()
    eng_dir.mkdir(parents=True, exist_ok=True)
    (eng_dir / "progress.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (eng_dir / "PROGRESS.md").write_text(
        render_markdown(state),
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage persistent audit progress (progress.json + PROGRESS.md).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize progress files in an engagement directory")
    p_init.add_argument("--dir", default=".", help="Engagement directory")
    p_init.add_argument("--name", default=None, help="Engagement name")

    p_status = sub.add_parser("status", help="Print current PROGRESS.md")
    p_status.add_argument("--dir", default=".", help="Engagement directory")

    p_phase = sub.add_parser("phase", help="Update a phase status")
    p_phase.add_argument("--dir", default=".", help="Engagement directory")
    p_phase.add_argument("--name", required=True, help="Phase key (scope, recon, surface, hunting, validation, reporting)")
    p_phase.add_argument("--state", required=True, choices=sorted(VALID_PHASE_STATES))
    p_phase.add_argument("--summary", default="", help="Brief summary of progress")

    p_tested = sub.add_parser("tested", help="Log a tested target/class (including negative results)")
    p_tested.add_argument("--dir", default=".", help="Engagement directory")
    p_tested.add_argument("--target", required=True)
    p_tested.add_argument("--class", dest="vuln_class", required=True)
    p_tested.add_argument("--result", default="negative", choices=["negative", "promising", "confirmed", "blocked"])
    p_tested.add_argument("--note", default="")

    p_finding = sub.add_parser("finding", help="Record or update a finding")
    p_finding.add_argument("--dir", default=".", help="Engagement directory")
    p_finding.add_argument("--title", required=True)
    p_finding.add_argument("--severity", default="Medium", choices=["Critical", "High", "Medium", "Low", "Info"])
    p_finding.add_argument("--target", required=True)
    p_finding.add_argument("--status", default="candidate", choices=["candidate", "validated", "reported", "rejected"])

    p_note = sub.add_parser("note", help="Append a timestamped session note or next step")
    p_note.add_argument("--dir", default=".", help="Engagement directory")
    p_note.add_argument("--text", required=True)

    args = parser.parse_args(argv)
    eng_dir = Path(args.dir).resolve()

    if args.cmd == "init":
        state = default_state(args.name or eng_dir.name)
        save_state(eng_dir, state)
        print(f"[OK] Initialized progress tracker in {eng_dir}")
        return 0

    if args.cmd == "status":
        md_path = eng_dir / "PROGRESS.md"
        if not md_path.exists():
            print(f"[INFO] No PROGRESS.md found in {eng_dir}. Run `init` first.")
            return 0
        print(md_path.read_text(encoding="utf-8"))
        return 0

    state = load_state(eng_dir)

    if args.cmd == "phase":
        phases = state.setdefault("phases", {})
        entry = phases.get(args.name, {"label": args.name.title(), "state": "pending", "summary": ""})
        entry["state"] = args.state
        if args.summary:
            entry["summary"] = args.summary
        entry["updated_at"] = now_utc()
        phases[args.name] = entry
        save_state(eng_dir, state)
        print(f"[OK] Phase '{args.name}' -> {args.state}")
        return 0

    if args.cmd == "tested":
        state.setdefault("tested", []).append(
            {
                "target": args.target,
                "vuln_class": args.vuln_class,
                "result": args.result,
                "note": args.note,
                "timestamp": now_utc(),
            }
        )
        save_state(eng_dir, state)
        print(f"[OK] Logged tested item: {args.target} ({args.vuln_class} -> {args.result})")
        return 0

    if args.cmd == "finding":
        findings = state.setdefault("findings", [])
        fid = f"F-{len(findings) + 1:03d}"
        findings.append(
            {
                "id": fid,
                "title": args.title,
                "severity": args.severity,
                "target": args.target,
                "status": args.status,
                "timestamp": now_utc(),
            }
        )
        save_state(eng_dir, state)
        print(f"[OK] Recorded finding {fid}: [{args.severity}] {args.title}")
        return 0

    if args.cmd == "note":
        state.setdefault("notes", []).append({"timestamp": now_utc(), "text": args.text})
        save_state(eng_dir, state)
        print("[OK] Added session note to PROGRESS.md")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
