#!/usr/bin/env python3
"""
set_notes.py — record the current objective/goal and running findings for
this hexstrike-ai session, separate from the IP scope (.current-target).

Usage:
    python3 set_notes.py objective "<text>"
    python3 set_notes.py add-finding "<text>"
    python3 set_notes.py clear

Examples:
    python3 set_notes.py objective "Get user.txt and root.txt on Cohort"
    python3 set_notes.py add-finding "nmap: 22/ssh, 80/http->https redirect, 443/nginx, cert CN=cohort.htb"
    python3 set_notes.py add-finding "gobuster on https://cohort.htb found /admin (403)"

This does not talk to HTB's API and does not know what the "real"
objective is — it only records what you tell it. Use show_notes.py to
review the current objective and finding log, e.g. at the start of a new
Claude Code session or after stepping away from the machine.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

NOTES_FILE = Path.home() / "hexstrike-ai" / ".session-notes"


def load() -> dict:
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"objective": None, "findings": [], "updated_at": None}


def save(data: dict) -> None:
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTES_FILE.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    action = sys.argv[1]
    data = load()

    if action == "objective":
        if len(sys.argv) < 3:
            print("Usage: set_notes.py objective \"<text>\"")
            return 1
        data["objective"] = sys.argv[2]
        save(data)
        print(f"Objective set: {data['objective']}")

    elif action == "add-finding":
        if len(sys.argv) < 3:
            print("Usage: set_notes.py add-finding \"<text>\"")
            return 1
        entry = {
            "text": sys.argv[2],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        data.setdefault("findings", []).append(entry)
        save(data)
        print(f"Finding added ({len(data['findings'])} total)")

    elif action == "clear":
        NOTES_FILE.unlink(missing_ok=True)
        print("Session notes cleared.")

    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
