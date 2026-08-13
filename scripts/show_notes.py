#!/usr/bin/env python3
"""
show_notes.py — print the current objective and finding log for this
hexstrike-ai session (separate from .current-target, the IP scope file).

Usage:
    python3 show_notes.py

Claude Code should run this alongside show_target.py at the start of a
session, so it knows both WHERE it's allowed to act (scope) and WHAT the
current goal is (objective) without guessing.
"""
import json
from pathlib import Path

NOTES_FILE = Path.home() / "hexstrike-ai" / ".session-notes"


def main() -> int:
    if not NOTES_FILE.exists():
        print("NO OBJECTIVE SET")
        print('Run: python3 scripts/set_notes.py objective "<what you are trying to do>"')
        return 1

    try:
        data = json.loads(NOTES_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"NOTES FILE CORRUPT: {e}")
        return 1

    print("CURRENT OBJECTIVE")
    print(f"  {data.get('objective') or '(not set)'}")
    print()

    findings = data.get("findings", [])
    if findings:
        print(f"FINDINGS LOG ({len(findings)} entries)")
        for i, f in enumerate(findings, 1):
            print(f"  {i}. [{f.get('at', '?')}] {f.get('text', '')}")
    else:
        print("FINDINGS LOG (empty)")

    print()
    print(f"Last updated: {data.get('updated_at', '(unknown)')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
