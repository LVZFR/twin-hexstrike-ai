#!/usr/bin/env python3
"""
show_target.py — print the current authorized HTB target scope, if set.

Usage:
    python3 show_target.py

Claude Code should run this at the start of every session (per CLAUDE.md)
before invoking any hexstrike-ai tool, and must not proceed against any
target other than what this prints. If it reports "NO TARGET SET",
Claude Code must stop and ask the user to run set_target.py first.
"""
import json
import sys
from pathlib import Path

TARGET_FILE = Path.home() / "hexstrike-ai" / ".current-target"


def main() -> int:
    if not TARGET_FILE.exists():
        print("NO TARGET SET")
        print(f"Run: python3 scripts/set_target.py <ip> [hostname] [machine_name]")
        return 1

    try:
        data = json.loads(TARGET_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"TARGET FILE CORRUPT: {e}")
        print(f"Fix or delete {TARGET_FILE} and re-run set_target.py")
        return 1

    print("CURRENT AUTHORIZED TARGET")
    print(f"  IP:           {data.get('target_ip', '(missing)')}")
    print(f"  Hostname:     {data.get('hostname') or '(none)'}")
    print(f"  Machine name: {data.get('machine_name') or '(none)'}")
    print(f"  Set at:       {data.get('set_at', '(unknown)')}")
    print()
    print("Scope is limited to the IP/hostname above ONLY. Do not act on")
    print("any other host, even if discovered during enumeration, without")
    print("the user updating this file first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
