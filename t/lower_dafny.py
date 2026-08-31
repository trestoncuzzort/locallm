#!/usr/bin/env python3
"""lower_dafny.py — lower t v0 tasks to Dafny, verify both the task and its
broken twin, and refuse anything that does not flip.

    python3 t/lower_dafny.py            # all of t/tasks/*.json
    python3 t/lower_dafny.py abs        # one task

The verdict is Dafny's, never this file's. Exit codes are the measured ones
from dafny_verify.py (dafny 4.11.0): 0 verified, 2 parse/resolution, 4
verification failed. A task COUNTS only when the real lowering exits 0 and the
twin exits 4 — dafny_pairs.py's measured-flip rule. Everything else is refused
with the reason printed: twin-verifies means the spec is vacuous; real-fails
means the task is wrong; twin-malformed means the mutation broke syntax rather
than meaning and the witness would be about parsing, not proof.

Stdlib only, same reason as dataset_gate.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from verifiers import Outcome, flake_check          # noqa: E402
from verifiers import dafny as dafny_backend        # noqa: E402

OUT = HERE / "out"

BIN_OPS = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
           "+": "+", "-": "-", "*": "*", "implies": "==>"}
NARY_OPS = {"and": "&&", "or": "||"}


def expr(e: dict) -> str:
    if "int" in e:
        return str(e["int"])
    if "var" in e:
        return e["var"]
    op, args = e["op"], [expr(a) for a in e.get("args", [])]
    if op == "neg":
        return f"(-{args[0]})"
    if op == "not":
        return f"(!{args[0]})"
    if op in NARY_OPS:
        return "(" + f" {NARY_OPS[op]} ".join(args) + ")"
    if op in BIN_OPS:
        return f"({args[0]} {BIN_OPS[op]} {args[1]})"
    raise ValueError(f"t v0 has no operator {op!r}")


def stmts(body: list, indent: str) -> str:
    out = []
    for s in body:
        if "assign" in s:
            name, e = s["assign"]
            out.append(f"{indent}{name} := {expr(e)};")
        elif "if" in s:
            c = s["if"]
            out.append(f"{indent}if {expr(c['cond'])} {{")
            out.append(stmts(c["then"], indent + "  "))
            out.append(f"{indent}}} else {{")
            out.append(stmts(c["else"], indent + "  "))
            out.append(f"{indent}}}")
        else:
            raise ValueError(f"t v0 has no statement {s!r}")
    return "\n".join(out)


def lower(task: dict, body: list) -> str:

    ps = ", ".join(f"{p['name']}: int" for p in task["params"])
    r = task["returns"][0]["name"]
    lines = [f"method {task['name'].capitalize()}({ps}) returns ({r}: int)"]
    for e in task.get("requires", []):
        lines.append(f"  requires {expr(e)}")
    for e in task["ensures"]:
        lines.append(f"  ensures {expr(e)}")
    lines.append("{")
    lines.append(stmts(body, "  "))
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import harness
    raise SystemExit(harness.run_all(sys.argv[1:], lower, dafny_backend, "dfy"))
