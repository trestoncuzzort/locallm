#!/usr/bin/env python3
"""lower_lean.py — lower t v0 tasks to Lean 4; the fourth kernel.

THE PROOF-ASSISTANT DIFFERENCE, made concrete: the lowering emits three
things — the function, the theorem stating every ensures clause with the
return name replaced by the applied function, and a PROOF. v0's fragment is
linear integer arithmetic, so the proof is one uniform mechanical tactic:

    unfold <f>; first | (split <;> omega) | omega

`split` case-splits the body's `if`; the `first`-fallthrough exists because a
twin whose `if` was collapsed would otherwise fail on TACTIC SHAPE rather
than on truth — measured before this file was written: the naked tactic
failed the twin with "Could not split", a shape error that would mint fake
REFUTEDs; the fallthrough fails it with "omega could not prove the goal: a
possible counterexample…", a real one. Lean's Int is mathematical, so the
semantic line needs no defending here — it is the native reading.

Every file ends with `#print axioms <thm>`; the adapter audits the list.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                 # noqa: E402
from verifiers import lean as lean_backend     # noqa: E402

BIN_OPS = {"==": "=", "!=": "≠", "<": "<", "<=": "≤", ">": ">", ">=": "≥",
           "+": "+", "-": "-", "*": "*", "implies": "→"}
NARY_OPS = {"and": "∧", "or": "∨"}


def expr(e: dict, ret_subst: str | None) -> str:
    if "int" in e:
        n = e["int"]
        return f"({n} : Int)" if n >= 0 else f"(({n}) : Int)"
    if "var" in e:
        return ret_subst if ret_subst and e["var"] == expr.ret_name else e["var"]
    op, args = e["op"], [expr(a, ret_subst) for a in e.get("args", [])]
    if op == "neg":
        return f"(-{args[0]})"
    if op == "not":
        return f"(¬{args[0]})"
    if op in NARY_OPS:
        return "(" + f" {NARY_OPS[op]} ".join(args) + ")"
    if op in BIN_OPS:
        return f"({args[0]} {BIN_OPS[op]} {args[1]})"
    raise ValueError(f"t v0 has no operator {op!r}")


def body_expr(body: list, ret: str) -> str:
    if len(body) == 1 and "assign" in body[0]:
        name, e = body[0]["assign"]
        assert name == ret, f"assign to {name}, expected {ret}"
        return expr(e, None)
    if len(body) == 1 and "if" in body[0]:
        c = body[0]["if"]
        return (f"if {expr(c['cond'], None)} then {body_expr(c['then'], ret)} "
                f"else {body_expr(c['else'], ret)}")
    raise ValueError("t v0 -> lean: body not expressible as one expression")


def lower(task: dict, body: list) -> str:
    name, ret = task["name"], task["returns"][0]["name"]
    expr.ret_name = ret
    params = " ".join(f"({p['name']} : Int)" for p in task["params"])
    args = " ".join(p["name"] for p in task["params"])
    applied = f"({name}_t {args})"
    post = " ∧ ".join(expr(e, applied) for e in task["ensures"])
    pre = " ∧ ".join(expr(e, applied) for e in task.get("requires", []))
    hyp = f" (hpre : {pre})" if pre else ""
    return (
        f"def {name}_t {params} : Int := {body_expr(body, ret)}\n\n"
        f"theorem {name}_t_spec {params}{hyp} :\n"
        f"    {post} := by\n"
        f"  unfold {name}_t; first | (split <;> omega) | omega\n\n"
        f"#print axioms {name}_t_spec\n")


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, lean_backend, "lean"))
