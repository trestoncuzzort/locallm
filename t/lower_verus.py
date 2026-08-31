#!/usr/bin/env python3
"""lower_verus.py — lower t v0 tasks to Verus; the second kernel.

THE SEMANTIC DECISION, made with a witness rather than by silence: t v0
integers are mathematical integers. Verus's `int` type IS mathematical, but
only in ghost/proof code — executable code uses machine ints with overflow
obligations. So v0 lowers to `proof fn`, which preserves t's semantics
exactly; the exec/i64 arm (with explicit range obligations) is a later gate,
opened when t grows machine-int types. Choosing exec now would silently
change what a t task MEANS between Dafny (int = mathematical) and Verus —
exactly the class of cross-backend semantic drift t exists to surface, not
commit.

Body lowering: Verus proof fns are expression-oriented, so the v0 statement
shape (assigns to the return name, if/else) is converted to an expression.
Bodies that do not fit (multiple sequential assigns) are refused — an honest
v0 limit, not a bug.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                   # noqa: E402
from verifiers import verus as verus_backend     # noqa: E402

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


def body_expr(body: list, ret: str) -> str:
    """Statement body -> Verus expression, or refuse."""
    if len(body) == 1 and "assign" in body[0]:
        name, e = body[0]["assign"]
        assert name == ret, f"assign to {name}, expected {ret}"
        return expr(e)
    if len(body) == 1 and "if" in body[0]:
        c = body[0]["if"]
        return (f"if {expr(c['cond'])} {{ {body_expr(c['then'], ret)} }}"
                f" else {{ {body_expr(c['else'], ret)} }}")
    raise ValueError("t v0 -> verus: body not expressible as one expression")


def lower(task: dict, body: list) -> str:
    ps = ", ".join(f"{p['name']}: int" for p in task["params"])
    r = task["returns"][0]["name"]
    ensures = ",\n        ".join(expr(e) for e in task["ensures"])
    requires = ",\n        ".join(expr(e) for e in task.get("requires", []))
    req = f"    requires\n        {requires}\n" if requires else ""
    return (
        "use vstd::prelude::*;\n\nverus! {\n\n"
        f"proof fn {task['name']}({ps}) -> (r: int)\n"
        f"{req}    ensures\n        {ensures},\n"
        "{\n"
        f"    {body_expr(body, r)}\n"
        "}\n\n} // verus!\n\nfn main() {}\n")


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, verus_backend, "rs"))
