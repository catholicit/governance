#!/usr/bin/env python3
"""Turn Peribolos JSON logs (stdin) into a short human-readable change list.

Keeps Peribolos' own summary lines ("Set x as a admin of ...", "Removing ...")
plus warnings and errors; drops API call traces and read-only noise.
Exits 1 if Peribolos reported an error, so CI fails visibly.
"""
import json
import sys

NOISE = ("Skipping", "Finished syncing", "It doesn't look like", "Throttle(")
failed = False
changes = []
for line in sys.stdin:
    try:
        entry = json.loads(line)
    except ValueError:
        continue
    msg, level = entry.get("msg", ""), entry.get("level", "")
    if level in ("error", "fatal"):
        failed = True
        changes.append(f"GREŠKA: {msg} {entry.get('error', '')}".strip())
    elif level == "warning" and not msg.startswith(NOISE):
        changes.append(f"upozorenje: {msg}")
    elif "client" not in entry and not msg.startswith(NOISE):
        changes.append(msg)

print("\n".join(f"- {c}" for c in changes) if changes else "Bez promjena: organizacija odgovara org.yaml.")
sys.exit(1 if failed else 0)
