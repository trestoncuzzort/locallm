#!/usr/bin/env python3
"""lower_rocq.py — lower t v0 tasks to the Rocq Prover; the fifth kernel.

Same proof-assistant contract as the Lean backend: emit the function, the
theorem, and a mechanical proof. Z is mathematical, so the semantic line is
native here too. The uniform proof for the v0 LIA fragment:

    intros; unfold <f>;
    repeat match goal with
    | |- context [?a <?  ?b] => destruct (Z.ltb_spec a b)
    | |- context [?a <=? ?b] => destruct (Z.leb_spec a b)
    | |- context [?a =?  ?b] => destruct (Z.eqb_spec a b)
    end; lia.

The `match goal` sweep destructs whatever boolean comparisons the lowered
body actually contains — a collapsed twin simply matches nothing and falls
straight to lia, whose honest failure ("Cannot find witness", measured) is a
refutation, never a shape error. Booleans in the body use <? / <=? / =?; the
spec side uses the propositional < / <= / =. Every file ends with
`Print Assumptions`, so the axiom audit ships inside the artifact.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                 # noqa: E402
from verifiers import rocq as rocq_backend     # noqa: E402

PROP_OPS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
            "+": "+", "-": "-", "*": "*"}
BOOL_CMP = {"<": "<?", "<=": "<=?", "==": "=?"}
NARY = {"and": "/\\", "or": "\\/"}

TACTIC = (
    "  intros; unfold {name}_t;\n"
    "  repeat match goal with\n"
    "  | |- context [?a <? ?b] => destruct (Z.ltb_spec a b)\n"
    "  | |- context [?a <=? ?b] => destruct (Z.leb_spec a b)\n"
    "  | |- context [?a =? ?b] => destruct (Z.eqb_spec a b)\n"
    "  end; lia.\n")


def prop(e: dict, ret_subst: str | None, ret_name: str) -> str:
    if "int" in e:
        return str(e["int"])
    if "var" in e:
        return ret_subst if ret_subst and e["var"] == ret_name else e["var"]
    op = e["op"]
    args = [prop(a, ret_subst, ret_name) for a in e.get("args", [])]
    if op == "neg":
        return f"(-{args[0]})"
    if op == "not":
        return f"(~ {args[0]})"
    if op == "implies":
        return f"({args[0]} -> {args[1]})"
    if op in NARY:
        return "(" + f" {NARY[op]} ".join(args) + ")"
    if op in PROP_OPS:
        return f"({args[0]} {PROP_OPS[op]} {args[1]})"
    raise ValueError(f"t v0 has no operator {op!r}")


def cond_bool(e: dict) -> str:
    op = e.get("op")
    if op in BOOL_CMP:
        a, b = (prop(x, None, "") for x in e["args"])
        return f"({a} {BOOL_CMP[op]} {b})"
    if op == ">":
        b, a = (prop(x, None, "") for x in e["args"])
        return f"({a} <? {b})"
    if op == ">=":
        b, a = (prop(x, None, "") for x in e["args"])
        return f"({a} <=? {b})"
    raise ValueError(f"t v0 -> rocq: no boolean form for condition {op!r}")


def body_expr(body: list, ret: str) -> str:
    if len(body) == 1 and "assign" in body[0]:
        name, e = body[0]["assign"]
        assert name == ret, f"assign to {name}, expected {ret}"
        return prop(e, None, "")
    if len(body) == 1 and "if" in body[0]:
        c = body[0]["if"]
        return (f"if {cond_bool(c['cond'])} then {body_expr(c['then'], ret)} "
                f"else {body_expr(c['else'], ret)}")
    raise ValueError("t v0 -> rocq: body not expressible as one expression")


def lower(task: dict, body: list) -> str:
    name, ret = task["name"], task["returns"][0]["name"]
    params = " ".join(p["name"] for p in task["params"])
    binder = " ".join(f"({p['name']} : Z)" for p in task["params"])
    applied = f"({name}_t {params})"
    post = " /\\ ".join(prop(e, applied, ret) for e in task["ensures"])
    pre = " /\\ ".join(prop(e, applied, ret) for e in task.get("requires", []))
    stmt = f"{pre} -> {post}" if pre else post
    return (
        "From Stdlib Require Import ZArith Lia.\n"
        "Open Scope Z_scope.\n\n"
        f"Definition {name}_t {binder} : Z := {body_expr(body, ret)}.\n\n"
        f"Theorem {name}_t_spec : forall {binder}, {stmt}.\n"
        "Proof.\n"
        + TACTIC.format(name=name) +
        "Qed.\n\n"
        f"Print Assumptions {name}_t_spec.\n")


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, rocq_backend, "v"))
