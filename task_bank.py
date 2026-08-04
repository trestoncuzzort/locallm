#!/usr/bin/env python3
"""task_bank.py — build a forge.Task from a screened-candidate payload dict.

Extracted from screen_tasks.py (codex review fold on the repo-hygiene branch)
so that code needing ONLY the task-building logic — verify_dataset.py's
published copy, in particular — does not have to import screen_tasks.py to
get it. screen_tasks.py is the private overnight-screening loop: it owns the
STOP-file path used to halt that loop, sizing/noise-floor internals, and
other references that must never leave this machine, so it can never be
added to a publish whitelist. Splitting the one function outside code
actually needs off of it closes that gap without touching what screen_tasks.py
does privately.

screen_tasks.py now imports `as_task` from here — this is the one
implementation, not a second copy under a different name.

Zero forbidden terms, by construction: this file exists so that it can ship.
"""
from __future__ import annotations

import forge


def as_task(c: dict) -> forge.Task:
    """AceCode asserts call the function by its own global name; forge's harness
    passes the (return-type-guarded) entry point into run_tests. Bind the name
    locally so the asserts run unchanged against the guarded function."""
    indented = "\n".join("    " + line.strip() for line in c["tests"])
    tests = f"def run_tests(_f):\n    {c['entry']} = _f\n{indented}\n"
    return forge.Task(c["tid"], c["prompt"], c["entry"], tests)
