#!/usr/bin/env python3
"""lower_framac.py — lower t v0 tasks to ACSL-annotated C; the sixth kernel.

The semantic line, stated where it can be seen: C's int is a machine type,
but WP WITHOUT -wp-rte reasons about the arithmetic mathematically — so this
lowering matches t v0's mathematical integers exactly, and the -wp-rte
machine-int arm is a later gate, not a silent default. The adapter pins that
flag choice; this file only emits the C.

Bodies lower to statements (C is happy with them): assign-to-return becomes
`return`, if stays if. ACSL operators: && || ! ==>, \result for the return
name.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                   # noqa: E402
from verifiers import framac as framac_backend   # noqa: E402

BIN_OPS = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
           "+": "+", "-": "-", "*": "*", "implies": "==>"}
NARY_OPS = {"and": "&&", "or": "||"}


def expr(e: dict, ret: str | None) -> str:
    if "int" in e:
        return str(e["int"])
    if "var" in e:
        return "\\result" if ret and e["var"] == ret else e["var"]
    op, args = e["op"], [expr(a, ret) for a in e.get("args", [])]
    if op == "neg":
        return f"(-{args[0]})"
    if op == "not":
        return f"(!{args[0]})"
    if op in NARY_OPS:
        return "(" + f" {NARY_OPS[op]} ".join(args) + ")"
    if op in BIN_OPS:
        return f"({args[0]} {BIN_OPS[op]} {args[1]})"
    raise ValueError(f"t v0 has no operator {op!r}")


def stmts(body: list, ret: str, indent: str) -> str:
    out = []
    for s in body:
        if "assign" in s:
            name, e = s["assign"]
            assert name == ret, f"assign to {name}, expected {ret}"
            out.append(f"{indent}return {expr(e, None)};")
        elif "if" in s:
            c = s["if"]
            out.append(f"{indent}if {expr(c['cond'], None)} {{")
            out.append(stmts(c["then"], ret, indent + "  "))
            out.append(f"{indent}}} else {{")
            out.append(stmts(c["else"], ret, indent + "  "))
            out.append(f"{indent}}}")
        else:
            raise ValueError(f"t v0 has no statement {s!r}")
    return "\n".join(out)


def lower(task: dict, body: list) -> str:
    name, ret = task["name"], task["returns"][0]["name"]
    params = ", ".join(f"int {p['name']}" for p in task["params"])
    clauses = [f"  ensures {expr(e, ret)};" for e in task["ensures"]]
    clauses = [f"  requires {expr(e, None)};"
               for e in task.get("requires", [])] + clauses
    return ("/*@\n" + "\n".join(clauses) + "\n*/\n"
            f"int {name}_t({params}) {{\n"
            + stmts(body, ret, "  ") + "\n}\n")


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, framac_backend, "c"))
