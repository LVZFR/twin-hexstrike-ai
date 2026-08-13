#!/usr/bin/env python3
"""
set_target.py — update the current authorized HTB target for this
hexstrike-ai / Claude Code project.

Usage:
    python3 set_target.py <target_ip> [hostname] [machine_name]

Example:
    python3 set_target.py 10.129.244.174 cohort.htb Cohort

This writes ~/hexstrike-ai/.current-target (a small JSON file) which
CLAUDE.md instructs Claude Code to read at the start of every session
via `python3 scripts/show_target.py`. It does NOT talk to the HTB API —
you must copy the IP/hostname/machine name from your own HTB dashboard.
Nothing here confirms authorization on HTB's behalf; it only records
what you tell it, so Claude Code has one unambiguous, current scope
statement instead of a stale/edited-by-hand block in CLAUDE.md.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TARGET_FILE = Path.home() / "hexstrike-ai" / ".current-target"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    target_ip = sys.argv[1]
    hostname = sys.argv[2] if len(sys.argv) > 2 else None
    machine_name = sys.argv[3] if len(sys.argv) > 3 else None

    data = {
        "target_ip": target_ip,
        "hostname": hostname,
        "machine_name": machine_name,
        "set_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Manually entered by the user from their own HTB dashboard. "
            "Not verified against any HTB API. Claude Code must treat "
            "this file, not its own inference, as the sole source of "
            "current scope."
        ),
    }

    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    TARGET_FILE.write_text(json.dumps(data, indent=2) + "\n")

    print(f"Target scope updated: {TARGET_FILE}")
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
