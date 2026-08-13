# HexStrike AI — Claude Code Project Instructions

This project runs HexStrike AI (an MCP-connected pentesting tool server) via
Claude Code. Read this file fully before running any tool against a target.

## Current Authorized Scope

Scope is **not** hardcoded in this file. At the start of every session, run:

```bash
python3 scripts/show_target.py
python3 scripts/show_notes.py
```

`show_target.py` prints the current target IP/hostname from `.current-target`,
a small JSON file the user updates themselves (from their own HTB dashboard)
via:

```bash
python3 scripts/set_target.py <target_ip> [hostname] [machine_name]
```

`show_notes.py` prints the current **objective** (what the user is trying to
achieve on that target — e.g. "get user.txt," "find the initial foothold")
and a running findings log, from `.session-notes`, updated via:

```bash
python3 scripts/set_notes.py objective "<what you are trying to do>"
python3 scripts/set_notes.py add-finding "<what a tool run revealed>"
```

These are two separate concerns: `.current-target` says WHERE Claude Code
is allowed to act, `.session-notes` says WHAT the user is currently trying
to accomplish there. Neither implies the other — always check both.

If `show_target.py` prints `NO TARGET SET`, **stop and ask the user** to run
`set_target.py` before touching any hexstrike-ai tool. Never infer, guess,
or reuse a target from a previous session or from conversation memory —
always re-check the file, since HTB machine IPs change on every respawn.

If `show_notes.py` prints `NO OBJECTIVE SET`, ask the user what they're
trying to achieve before running exploratory tools, rather than assuming
"scan everything" is the goal.

None of these scripts talk to HTB's API. They only record what the user
tells you, from their own dashboard/observations. This is not proof of
authorization — it is a deliberate, explicit record so Claude Code has one
unambiguous scope and goal statement instead of guessing.

## Standing Rules

1. **Scope is absolute.** Every hexstrike-ai tool call must target only the
   IP/hostname reported by `scripts/show_target.py`. If a scan result
   reveals a related host (subdomain, redirect, pivot target, adjacent IP),
   do not act on it — report it and wait for the user to confirm it's in
   scope, then have them run `set_target.py` again if it changes.

2. **No blanket auto-approval.** Never configure `alwaysAllow` for
   hexstrike-ai tools in this or any Claude Code config. Every tool
   invocation should be visible and approvable per-call. This project's
   `claude mcp add` entry intentionally leaves `alwaysAllow` empty — do not
   change that.

3. **No destructive or state-changing actions without explicit ask.**
   Enumeration, scanning, and read-only recon (nmap, gobuster, nikto,
   directory brute-force, etc.) are fine within scope. Exploitation,
   credential brute-forcing, file uploads, and anything that could alter
   the target's state require the user's explicit go-ahead for that
   specific action, not a general "go ahead."

4. **Report findings honestly.** State exactly what a tool returned — open
   ports, service versions, response codes. Do not infer a vulnerability
   exists without evidence from an actual tool run. Do not claim an
   exploit worked without verifying its actual output/return code.

5. **This is a personal, isolated Kali VM used for authorized practice
   only.** Never suggest or run anything against production systems, other
   people's infrastructure, or any IP outside the current scope file.

6. **HexStrike server stays localhost-only.** The server listens on
   127.0.0.1:8888 (see `hexstrike_server.py`, `API_HOST` env var). Do not
   change this to 0.0.0.0 or otherwise expose it beyond localhost — its
   `/api/command` and file-operation endpoints are unauthenticated.

## Typical Session Flow

1. Run `python3 scripts/show_target.py`. If no target is set, ask the user
   to run `set_target.py` with the current HTB machine IP.
2. Enumerate using hexstrike-ai tools (nmap, httpx, gobuster, etc.), one
   approved tool call at a time, targeting only the confirmed scope.
3. Report findings clearly — open ports, services, versions, any web
   content discovered.
4. User decides next steps (deeper enumeration, manual investigation,
   attempting a specific exploit) and explicitly asks for it.

## Automatic Findings Logging

After every hexstrike-ai tool call that returns a notable result — an open
port, a detected service/version, a discovered URL/endpoint, a
vulnerability indicator, a credential, a flag, or any other concrete
artifact — log it immediately with:

```bash
python3 scripts/set_notes.py add-finding "<concise, factual summary of what the tool actually returned>"
```

Rules for what counts as "notable" and how to phrase it:

- Log the actual result, not your interpretation of what it might mean.
  Good: `"nmap: 22/tcp open ssh OpenSSH 9.6p1, 80/tcp open http nginx 1.24.0"`
  Bad:  `"the server looks vulnerable to something"`
- One finding per tool call is usually enough — summarize concisely rather
  than pasting raw multi-line tool output.
- Skip logging when a tool call returns nothing new (e.g. a repeat scan
  confirming an already-logged port) — don't spam duplicate entries.
- Never log secrets, credentials, or flag contents in plaintext if the user
  has asked you to keep them out of the log — ask if unsure, since this
  file is stored on disk and may end up in version control history if the
  user later chooses to remove it from `.gitignore`.
- This logging is in addition to, not instead of, reporting the finding to
  the user directly in your response.

This keeps `.session-notes` (viewable via `show_notes.py` or the GUI's
Findings Log) building itself as you work, instead of relying on the user
to manually transcribe every result.

## Useful Commands

```bash
# Show current authorized target and objective
python3 scripts/show_target.py
python3 scripts/show_notes.py

# Update target (run this yourself each time you spawn/respawn a machine)
python3 scripts/set_target.py <ip> [hostname] [machine_name]

# Set/update the current objective and log findings as you go
python3 scripts/set_notes.py objective "<what you are trying to do>"
python3 scripts/set_notes.py add-finding "<what a tool run revealed>"

# Check hexstrike-ai server health and detected tools
curl -sS http://127.0.0.1:8888/health

# Verify MCP connection
claude mcp list

# Confirm target resolves (if hostname added to /etc/hosts)
getent hosts <target-hostname>
```
