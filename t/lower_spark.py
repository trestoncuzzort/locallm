#!/usr/bin/env python3
"""lower_spark.py — lower t v0 tasks to SPARK 2014; the third kernel.

THE SEMANTIC DECISION, same doctrine as the Verus backend: t v0 integers are
mathematical. Ada's Integer is a machine type with overflow — lowering to it
would make `abs` unprovable at Integer'First and silently change what the
task means. Ada 2022's Big_Integer (Ada.Numerics.Big_Numbers.Big_Integers)
IS mathematical and gnatprove proves over it directly — measured on this
machine before this file was written: abs over Big_Integer, all 11 checks
proved, plain integer literals accepted under pragma Ada_2022.

Shape: one package per task, one expression function F with a Post aspect;
ensures clauses reference the t return name, rewritten to F'Result here.
Bodies must be expressible as a single expression (the v0 limit the Verus
backend already states).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                   # noqa: E402
from verifiers import spark as spark_backend     # noqa: E402

BIN_OPS = {"==": "=", "!=": "/=", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
           "+": "+", "-": "-", "*": "*"}
NARY_OPS = {"and": "and then", "or": "or else"}


def expr(e: dict, ret: str) -> str:
    if "int" in e:
        return str(e["int"])
    if "var" in e:
        return "F'Result" if e["var"] == ret else e["var"].capitalize()
    op, args = e["op"], [expr(a, ret) for a in e.get("args", [])]
    if op == "neg":
        return f"(-{args[0]})"
    if op == "not":
        return f"(not {args[0]})"
    if op == "implies":
        return f"(if {args[0]} then {args[1]} else True)"
    if op in NARY_OPS:
        return "(" + f" {NARY_OPS[op]} ".join(args) + ")"
    if op in BIN_OPS:
        return f"({args[0]} {BIN_OPS[op]} {args[1]})"
    raise ValueError(f"t v0 has no operator {op!r}")


def body_expr(body: list, ret: str) -> str:
    if len(body) == 1 and "assign" in body[0]:
        name, e = body[0]["assign"]
        assert name == ret, f"assign to {name}, expected {ret}"
        return expr(e, ret=None)  # return name must not read as F'Result here
    if len(body) == 1 and "if" in body[0]:
        c = body[0]["if"]
        return (f"(if {expr(c['cond'], None)} then "
                f"{body_expr(c['then'], ret)} else {body_expr(c['else'], ret)})")
    raise ValueError("t v0 -> spark: body not expressible as one expression")


def lower(task: dict, body: list) -> str:
    ret = task["returns"][0]["name"]
    ps = "; ".join(f"{p['name'].capitalize()} : Big_Integer"
                   for p in task["params"])
    post = "\n     and then ".join(expr(e, ret) for e in task["ensures"])
    pre = " and then ".join(expr(e, ret) for e in task.get("requires", []))
    pre_aspect = f"     Pre  => {pre},\n" if pre else ""
    inner = body_expr(body, ret)
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1]
    return (
        "pragma Ada_2022;\n"
        "with Ada.Numerics.Big_Numbers.Big_Integers;\n"
        "use  Ada.Numerics.Big_Numbers.Big_Integers;\n"
        f"package T_{task['name'].capitalize()} with SPARK_Mode is\n"
        f"   function F ({ps}) return Big_Integer is\n"
        f"     ({inner})\n"
        "   with\n"
        f"{pre_aspect}"
        f"     Post => {post};\n"
        f"end T_{task['name'].capitalize()};\n")


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, spark_backend, "ads"))
