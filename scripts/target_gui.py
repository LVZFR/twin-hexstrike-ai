#!/usr/bin/env python3
"""
target_gui.py — simple Tkinter form to set the current HTB target scope
and objective for this hexstrike-ai / Claude Code project.

Run this ON THE KALI VM'S OWN DESKTOP (not over plain SSH — it needs a
display). From a terminal in the VM's GUI session:

    cd ~/hexstrike-ai
    python3 scripts/target_gui.py

Fields map directly to the same files set_target.py / set_notes.py use:
    .current-target  -> target IP, hostname, machine name
    .session-notes    -> objective, findings log

Submitting the form overwrites .current-target and updates .session-notes
exactly the same way the CLI scripts do — this is just a friendlier way
to fill them in. Nothing here talks to HTB's API; it only records what
you type, same as before.
"""
import json
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, scrolledtext

BASE = Path.home() / "hexstrike-ai"
TARGET_FILE = BASE / ".current-target"
NOTES_FILE = BASE / ".session-notes"


def load_target() -> dict:
    if TARGET_FILE.exists():
        try:
            return json.loads(TARGET_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def load_notes() -> dict:
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"objective": None, "findings": []}


class TargetForm(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HexStrike AI — Target & Objective")
        self.geometry("640x560")
        self.resizable(False, False)

        pad = {"padx": 10, "pady": 4}

        tk.Label(self, text="Current Authorized Target", font=("", 13, "bold")).pack(
            anchor="w", **pad
        )

        self._entries = {}
        for label, key in [
            ("Target IP *", "target_ip"),
            ("Hostname (e.g. cohort.htb)", "hostname"),
            ("Machine name (e.g. Cohort)", "machine_name"),
        ]:
            row = tk.Frame(self)
            row.pack(fill="x", **pad)
            tk.Label(row, text=label, width=22, anchor="w").pack(side="left")
            entry = tk.Entry(row, width=45)
            entry.pack(side="left", fill="x", expand=True)
            self._entries[key] = entry

        tk.Label(self, text="Current Objective", font=("", 13, "bold")).pack(
            anchor="w", **pad
        )
        row = tk.Frame(self)
        row.pack(fill="x", **pad)
        tk.Label(row, text="Objective *", width=22, anchor="w").pack(side="left")
        self._objective_entry = tk.Entry(row, width=45)
        self._objective_entry.pack(side="left", fill="x", expand=True)

        tk.Label(self, text="Add Finding (optional, appended on submit)").pack(
            anchor="w", **pad
        )
        self._finding_entry = tk.Entry(self, width=70)
        self._finding_entry.pack(fill="x", **pad)

        tk.Label(self, text="Findings Log (read-only)", font=("", 11, "bold")).pack(
            anchor="w", **pad
        )
        self._findings_box = scrolledtext.ScrolledText(
            self, width=76, height=14, state="disabled"
        )
        self._findings_box.pack(fill="both", expand=True, **pad)

        btn_row = tk.Frame(self)
        btn_row.pack(fill="x", **pad)
        tk.Button(btn_row, text="Submit", command=self.on_submit, width=15).pack(
            side="left"
        )
        tk.Button(
            btn_row, text="Refresh", command=self.load_current, width=15
        ).pack(side="left", padx=6)
        tk.Button(
            btn_row, text="Clear Objective/Findings", command=self.on_clear, width=22
        ).pack(side="right")

        self._status = tk.Label(self, text="", fg="green")
        self._status.pack(anchor="w", **pad)

        self.load_current()

    def load_current(self):
        t = load_target()
        self._entries["target_ip"].delete(0, tk.END)
        self._entries["target_ip"].insert(0, t.get("target_ip") or "")
        self._entries["hostname"].delete(0, tk.END)
        self._entries["hostname"].insert(0, t.get("hostname") or "")
        self._entries["machine_name"].delete(0, tk.END)
        self._entries["machine_name"].insert(0, t.get("machine_name") or "")

        n = load_notes()
        self._objective_entry.delete(0, tk.END)
        self._objective_entry.insert(0, n.get("objective") or "")

        self._findings_box.configure(state="normal")
        self._findings_box.delete("1.0", tk.END)
        for i, f in enumerate(n.get("findings", []), 1):
            self._findings_box.insert(
                tk.END, f"{i}. [{f.get('at', '?')}] {f.get('text', '')}\n"
            )
        self._findings_box.configure(state="disabled")

        self._status.configure(text="Loaded current state.", fg="blue")

    def on_submit(self):
        target_ip = self._entries["target_ip"].get().strip()
        hostname = self._entries["hostname"].get().strip() or None
        machine_name = self._entries["machine_name"].get().strip() or None
        objective = self._objective_entry.get().strip()
        finding = self._finding_entry.get().strip()

        if not target_ip:
            messagebox.showerror("Missing field", "Target IP is required.")
            return
        if not objective:
            messagebox.showerror("Missing field", "Objective is required.")
            return

        now = datetime.now(timezone.utc).isoformat()

        target_data = {
            "target_ip": target_ip,
            "hostname": hostname,
            "machine_name": machine_name,
            "set_at": now,
            "note": (
                "Manually entered by the user via target_gui.py. Not "
                "verified against any HTB API. Claude Code must treat "
                "this file, not its own inference, as the sole source "
                "of current scope."
            ),
        }
        TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        TARGET_FILE.write_text(json.dumps(target_data, indent=2) + "\n")

        notes_data = load_notes()
        notes_data["objective"] = objective
        if finding:
            notes_data.setdefault("findings", []).append(
                {"text": finding, "at": now}
            )
        notes_data["updated_at"] = now
        NOTES_FILE.write_text(json.dumps(notes_data, indent=2) + "\n")

        self._finding_entry.delete(0, tk.END)
        self.load_current()
        self._status.configure(
            text=f"Saved at {now}. Claude Code will read this on next check.",
            fg="green",
        )

    def on_clear(self):
        if not messagebox.askyesno(
            "Confirm", "Clear the objective and findings log? Target IP is kept."
        ):
            return
        NOTES_FILE.unlink(missing_ok=True)
        self.load_current()
        self._status.configure(text="Objective and findings cleared.", fg="orange")


if __name__ == "__main__":
    TargetForm().mainloop()
