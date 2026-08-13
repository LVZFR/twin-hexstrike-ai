#!/usr/bin/env python3
"""
hexstrike_console.py — main control console for HexStrike AI + Claude Code.

Run this ON THE KALI VM'S OWN DESKTOP (needs a display):

    cd ~/hexstrike-ai
    python3 scripts/hexstrike_console.py

This replaces manual `claude` CLI usage for routine recon: fill in the
target/objective, type an instruction, hit Send, and it invokes
`claude -p` (Claude Code's non-interactive print mode) in the background
with a scoped --allowedTools list so read-only recon tools (nmap, gobuster,
httpx, etc.) run without an interactive approval prompt, while anything
else (exploitation, file writes, credential attacks) still requires you
to explicitly type a command that allows it, or drop to a real `claude`
session yourself.

This tool does not talk to HTB's API and does not decide what is
"authorized" — it only records what you type into the Target/Objective
fields (same .current-target / .session-notes files set_target.py and
set_notes.py use) and passes your typed instruction to Claude Code
verbatim, prefixed with that scope context.
"""
import json
import queue
import subprocess
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

BASE = Path.home() / "hexstrike-ai"
TARGET_FILE = BASE / ".current-target"
NOTES_FILE = BASE / ".session-notes"
CLAUDE_BIN_CANDIDATES = [
    Path.home() / ".local" / "bin" / "claude",
    Path("/usr/local/bin/claude"),
]

# Read-only recon tools that auto-run without an interactive approval
# prompt when using `claude -p`. Exploitation/credential/file-write tools
# are deliberately excluded — those still need a manual `claude` session.
AUTO_APPROVED_TOOLS = [
    "nmap_scan",
    "nmap_advanced_scan",
    "rustscan_fast_scan",
    "masscan_high_speed",
    "httpx_probe",
    "katana_crawl",
    "gobuster_scan",
    "feroxbuster_scan",
    "dirsearch_scan",
    "dirb_scan",
    "ffuf_scan",
    "amass_scan",
    "subfinder_scan",
    "fierce_scan",
    "dnsenum_scan",
    "wafw00f_scan",
    "nuclei_scan",
    "nikto_scan",
    "arp_scan_discovery",
    "nbtscan_netbios",
    "enum4linux_scan",
    "enum4linux_ng_advanced",
    "smbmap_scan",
    "rpcclient_enumeration",
    "detect_technologies_ai",
    "analyze_target_intelligence",
    "checksec_analyze",
    "strings_extract",
    "server_health",
    "get_telemetry",
]

HELPER_SCRIPTS = [
    "Bash(python3 scripts/show_target.py)",
    "Bash(python3 scripts/show_notes.py)",
    "Bash(python3 scripts/set_notes.py *)",
]


def find_claude_bin() -> str:
    for c in CLAUDE_BIN_CANDIDATES:
        if c.exists():
            return str(c)
    return "claude"  # fall back to PATH


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


def save_target(target_ip, hostname, machine_name) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "target_ip": target_ip,
        "hostname": hostname or None,
        "machine_name": machine_name or None,
        "set_at": now,
        "note": (
            "Manually entered by the user via hexstrike_console.py. Not "
            "verified against any HTB API. Claude Code must treat this "
            "file, not its own inference, as the sole source of current "
            "scope."
        ),
    }
    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    TARGET_FILE.write_text(json.dumps(data, indent=2) + "\n")
    return data


def save_objective(objective: str) -> None:
    data = load_notes()
    data["objective"] = objective
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    NOTES_FILE.write_text(json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------------------- theme --

BG = "#0b0f0d"
PANEL = "#0f1712"
FG = "#39ff88"
FG_DIM = "#1f8a4a"
ACCENT = "#00e0ff"
WARN = "#ff5f5f"
FONT_MONO = ("Courier New", 10)
FONT_MONO_BOLD = ("Courier New", 10, "bold")
FONT_TITLE = ("Courier New", 15, "bold")


class HexStrikeConsole(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HEXSTRIKE // CONTROL CONSOLE")
        self.geometry("980x760")
        self.minsize(860, 640)
        self.configure(bg=BG)

        self._proc = None
        self._out_queue: "queue.Queue[str]" = queue.Queue()
        self._claude_bin = find_claude_bin()

        self._build_style()
        self._build_layout()
        self._load_state()
        self._poll_queue()

    # -------------------------------------------------------- styling --
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure(
            "TLabel", background=BG, foreground=FG, font=FONT_MONO
        )
        style.configure(
            "Panel.TLabel", background=PANEL, foreground=FG, font=FONT_MONO
        )
        style.configure(
            "Title.TLabel",
            background=BG,
            foreground=ACCENT,
            font=FONT_TITLE,
        )
        style.configure(
            "TEntry",
            fieldbackground="#06110a",
            foreground=FG,
            insertcolor=FG,
        )

    # --------------------------------------------------------- layout --
    def _build_layout(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(
            header,
            text="◤ HEXSTRIKE // CONTROL CONSOLE ◢",
            bg=BG,
            fg=ACCENT,
            font=FONT_TITLE,
        ).pack(side="left")
        self._status_led = tk.Label(
            header, text="● OFFLINE", bg=BG, fg=WARN, font=FONT_MONO_BOLD
        )
        self._status_led.pack(side="right")

        # --- scope panel ---
        scope = tk.LabelFrame(
            self,
            text=" TARGET SCOPE ",
            bg=PANEL,
            fg=FG,
            font=FONT_MONO_BOLD,
            labelanchor="nw",
            bd=1,
            relief="solid",
        )
        scope.pack(fill="x", padx=14, pady=6)

        self._entries = {}
        grid = tk.Frame(scope, bg=PANEL)
        grid.pack(fill="x", padx=10, pady=8)
        for i, (label, key, width) in enumerate(
            [
                ("TARGET IP", "target_ip", 18),
                ("HOSTNAME", "hostname", 22),
                ("MACHINE", "machine_name", 18),
            ]
        ):
            tk.Label(
                grid, text=label, bg=PANEL, fg=FG_DIM, font=FONT_MONO
            ).grid(row=0, column=i * 2, sticky="w", padx=(0 if i == 0 else 12, 4))
            e = tk.Entry(
                grid,
                width=width,
                bg="#06110a",
                fg=FG,
                insertbackground=FG,
                font=FONT_MONO,
                relief="flat",
                highlightthickness=1,
                highlightbackground=FG_DIM,
                highlightcolor=ACCENT,
            )
            e.grid(row=0, column=i * 2 + 1, sticky="w")
            self._entries[key] = e

        obj_row = tk.Frame(scope, bg=PANEL)
        obj_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(
            obj_row, text="OBJECTIVE", bg=PANEL, fg=FG_DIM, font=FONT_MONO
        ).pack(side="left")
        self._objective_entry = tk.Entry(
            obj_row,
            bg="#06110a",
            fg=FG,
            insertbackground=FG,
            font=FONT_MONO,
            relief="flat",
            highlightthickness=1,
            highlightbackground=FG_DIM,
            highlightcolor=ACCENT,
        )
        self._objective_entry.pack(side="left", fill="x", expand=True, padx=8)

        btn_row = tk.Frame(scope, bg=PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        self._make_button(
            btn_row, "SAVE SCOPE", self.on_save_scope, bg="#0d3d21"
        ).pack(side="left")
        self._make_button(
            btn_row, "RELOAD", self.on_reload, bg="#12232c"
        ).pack(side="left", padx=6)

        # --- console output ---
        console_frame = tk.LabelFrame(
            self,
            text=" CLAUDE CODE OUTPUT ",
            bg=PANEL,
            fg=FG,
            font=FONT_MONO_BOLD,
            labelanchor="nw",
            bd=1,
            relief="solid",
        )
        console_frame.pack(fill="both", expand=True, padx=14, pady=6)
        self._console = scrolledtext.ScrolledText(
            console_frame,
            bg="#04090a",
            fg=FG,
            insertbackground=FG,
            font=FONT_MONO,
            relief="flat",
            wrap="word",
        )
        self._console.pack(fill="both", expand=True, padx=6, pady=6)
        self._console.configure(state="disabled")
        self._console.tag_configure("warn", foreground=WARN)
        self._console.tag_configure("accent", foreground=ACCENT)
        self._console.tag_configure("dim", foreground=FG_DIM)

        # --- prompt input ---
        prompt_frame = tk.Frame(self, bg=BG)
        prompt_frame.pack(fill="x", padx=14, pady=(0, 6))
        tk.Label(
            prompt_frame, text=">>>", bg=BG, fg=ACCENT, font=FONT_MONO_BOLD
        ).pack(side="left")
        self._prompt_entry = tk.Entry(
            prompt_frame,
            bg="#06110a",
            fg=FG,
            insertbackground=FG,
            font=FONT_MONO,
            relief="flat",
            highlightthickness=1,
            highlightbackground=FG_DIM,
            highlightcolor=ACCENT,
        )
        self._prompt_entry.pack(side="left", fill="x", expand=True, padx=8)
        self._prompt_entry.bind("<Return>", lambda _e: self.on_send())

        self._send_btn = self._make_button(
            prompt_frame, "SEND ▶", self.on_send, bg="#0d3d21", width=10
        )
        self._send_btn.pack(side="left")

        # --- footer / auto-approved tools note ---
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(
            footer,
            text=(
                f"Auto-approved (read-only recon): "
                f"{', '.join(AUTO_APPROVED_TOOLS[:6])}, "
                f"+{len(AUTO_APPROVED_TOOLS) - 6} more. "
                f"Anything else prompts inside a manual `claude` session."
            ),
            bg=BG,
            fg=FG_DIM,
            font=("Courier New", 8),
            wraplength=940,
            justify="left",
        ).pack(anchor="w")

    def _make_button(self, parent, text, command, bg="#12232c", width=14):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=FG,
            activebackground="#1c5c33",
            activeforeground=FG,
            font=FONT_MONO_BOLD,
            relief="flat",
            width=width,
            highlightthickness=1,
            highlightbackground=FG_DIM,
            padx=6,
            pady=4,
        )

    # ---------------------------------------------------------- state --
    def _load_state(self):
        t = load_target()
        for key in ("target_ip", "hostname", "machine_name"):
            self._entries[key].delete(0, tk.END)
            self._entries[key].insert(0, t.get(key) or "")

        n = load_notes()
        self._objective_entry.delete(0, tk.END)
        self._objective_entry.insert(0, n.get("objective") or "")

        self._log(
            f"[console] loaded scope: "
            f"{t.get('target_ip') or '(none set)'} "
            f"({t.get('hostname') or 'no hostname'})",
            "dim",
        )
        self._set_status(bool(t.get("target_ip")))

    def _set_status(self, has_target: bool):
        if has_target:
            self._status_led.configure(text="● SCOPE LOCKED", fg=FG)
        else:
            self._status_led.configure(text="● NO TARGET", fg=WARN)

    # -------------------------------------------------------- actions --
    def on_save_scope(self):
        target_ip = self._entries["target_ip"].get().strip()
        hostname = self._entries["hostname"].get().strip()
        machine_name = self._entries["machine_name"].get().strip()
        objective = self._objective_entry.get().strip()

        if not target_ip:
            messagebox.showerror("Missing field", "Target IP is required.")
            return

        save_target(target_ip, hostname, machine_name)
        if objective:
            save_objective(objective)

        self._log(f"[console] scope saved: {target_ip} ({hostname or '-'})", "accent")
        self._set_status(True)

    def on_reload(self):
        self._load_state()

    def on_send(self):
        if self._proc is not None:
            messagebox.showinfo(
                "Busy", "Claude Code is already running. Wait for it to finish."
            )
            return

        target = load_target()
        if not target.get("target_ip"):
            messagebox.showerror(
                "No target", "Save a target IP in TARGET SCOPE before sending."
            )
            return

        instruction = self._prompt_entry.get().strip()
        if not instruction:
            return
        self._prompt_entry.delete(0, tk.END)

        full_prompt = (
            f"Read CLAUDE.md in this project directory first, then run "
            f"`python3 scripts/show_target.py` and "
            f"`python3 scripts/show_notes.py` to confirm the current "
            f"authorized target and objective before doing anything else. "
            f"Follow every rule in CLAUDE.md, including the automatic "
            f"findings-logging instructions and the scope boundary. "
            f"Current authorized target: {target.get('target_ip')} "
            f"(hostname: {target.get('hostname') or 'n/a'}, "
            f"machine: {target.get('machine_name') or 'n/a'}). "
            f"This is an HTB lab machine explicitly spawned by the account "
            f"owner for authorized practice. Stay within this target only. "
            f"Task: {instruction}"
        )

        self._log(f">>> {instruction}", "accent")
        self._run_claude(full_prompt)

    def _run_claude(self, prompt: str):
        allowed = [f"mcp__hexstrike-ai__{t}" for t in AUTO_APPROVED_TOOLS] + HELPER_SCRIPTS
        cmd = [
            self._claude_bin,
            "-p",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            *allowed,
            prompt,
        ]

        self._send_btn.configure(state="disabled", text="RUNNING…")
        self._status_led.configure(text="● RUNNING", fg=ACCENT)

        def worker():
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(BASE),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                self._proc = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    self._out_queue.put(line.rstrip("\n"))
                proc.wait()
                self._out_queue.put(f"__DONE__{proc.returncode}")
            except FileNotFoundError:
                self._out_queue.put(
                    "__DONE__-1: claude binary not found — check "
                    "CLAUDE_BIN_CANDIDATES in this script"
                )
            except Exception as e:  # noqa: BLE001
                self._out_queue.put(f"__DONE__-1: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                line = self._out_queue.get_nowait()
                if line.startswith("__DONE__"):
                    self._proc = None
                    self._send_btn.configure(state="normal", text="SEND ▶")
                    self._set_status(True)
                    self._log(f"[console] done ({line[8:]})", "dim")
                else:
                    self._log(line)
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _log(self, text: str, tag: str | None = None):
        self._console.configure(state="normal")
        if tag:
            self._console.insert(tk.END, text + "\n", tag)
        else:
            self._console.insert(tk.END, text + "\n")
        self._console.see(tk.END)
        self._console.configure(state="disabled")


if __name__ == "__main__":
    HexStrikeConsole().mainloop()
