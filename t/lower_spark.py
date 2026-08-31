#!/usr/bin/env python3
"""lower_spark.py — lower t v0/v1 tasks to SPARK 2014; the third kernel.

THE SEMANTIC DECISION, same doctrine as the Verus backend: t integers are
mathematical. Ada's Integer is a machine type with overflow — lowering to it
would make `abs` unprovable at Integer'First and silently change what the
task means. Ada 2022's Big_Integer (Ada.Numerics.Big_Numbers.Big_Integers)
IS mathematical and gnatprove proves over it directly.

SHAPE (v1, measured 2026-08-31 on gnatprove FSF 16.1.0 before this rewrite):
GNAT's naming convention refuses a body in the single .ads file the t.spark
verifier writes (measured: "file can have only one compilation unit", "does
not contain unit (spec)", and pragma Source_File_Name is rejected under a
project). So EVERYTHING is a package spec of expression functions:

  * task body      -> one expression function F (statement lists are compiled
                      to expressions: assignments become substitution, `if`
                      becomes an if-expression merge of the branch outcomes);
  * while loops    -> one recursive helper function per loop, W_k over a
                      record of the in-scope mutable state; loop invariants
                      become W_k's Pre AND Post (plus `not cond` in Post),
                      the loop's decreases becomes W_k's Subprogram_Variant.
                      That is the standard Hoare package, stated to the
                      kernel rather than assumed: invariant-on-entry is the
                      call-site Pre check, preservation is the recursive
                      call's Pre check, exit knowledge is Post.
  * recursion      -> F is a recursive expression function; the task-level
                      decreases becomes F's Subprogram_Variant.
  * spec_funs      -> recursive expression functions with their own
                      Subprogram_Variant.
  * seq            -> type Seq is array (Positive range <>) of Big_Integer
                      (Positive index keeps 'Length within Integer, which
                      the range obligations below need).

VARIANTS: SPARK requires a Big_Integer Subprogram_Variant to be provably
nonnegative; t's decreases obligations only give >= 0 at the recursion/loop
step. Every variant is therefore wrapped (if D >= 0 then D else 0): still
well-founded, decreasing exactly when t's obligations hold, and measured to
prove where Big_Integers.Max blew the 20000-step budget.

QUANTIFIERS: SPARK quantified expressions range over discrete machine types
only, so a t quantifier over mathematical [lo, hi) is lowered as

    (for all K in Integer => (if lo <= K < hi then body else True))

(exists dually with `and then`) — the machine-representable slice of the
range. That is NOT the t quantifier when [lo, hi) escapes Integer, so per
SPEC.md ("bounded backends owe explicit range obligations") every clause
that contains quantifiers gets a hoisted leading obligation

    Integer'First <= lo and then hi <= Integer'Last + 1

conjoined in front (`bounds_ok`). Once bounds_ok is PROVED, machine slice
and t range coincide and the lowered clause is exactly the t clause; if it
cannot be proved the task is honestly refuted, never silently weakened.
bounds_ok is only sound where it is CHECKED before being assumed — ensures
and invariants. A quantifier in `requires` (pure assumption position), in a
quantifier bound that mentions an enclosing bound variable, under a partial
`at` in a bound, or in an executable/definitional position (bodies,
spec_fun bodies, loop conditions, decreases) is an explicit ABSTAIN.

DEFINEDNESS: `and`/`or`/`implies` lower to `and then`/`or else`/if-
expressions, so SPEC.md's left-to-right definedness contexts land exactly on
GNATprove's own RTE-checking contexts; `at` lowers to
S (S'First + To_Integer (I)) whose index/conversion checks ARE the t
definedness obligations — a lowering that silently totalized `at` would be
wrong, this one makes the kernel discharge it.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                   # noqa: E402
from verifiers import spark as spark_backend     # noqa: E402

TYPE = {"int": "Big_Integer", "bool": "Boolean", "seq": "Seq"}
CMP = {"==": "=", "!=": "/=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
ARITH = {"+": "+", "-": "-", "*": "*"}
NARY = {"and": "and then", "or": "or else"}
B_FIRST = "To_Big_Integer (Integer'First)"
B_LAST = "To_Big_Integer (Integer'Last)"


def cap(name: str) -> str:
    return name.capitalize()


# --- expression tree walks -------------------------------------------------

def _children(e: dict):
    if "op" in e:
        yield from e.get("args", [])
    elif "forall" in e or "exists" in e:
        q = e["forall"] if "forall" in e else e["exists"]
        yield q["lo"]
        yield q["hi"]
        yield q["body"]
    elif "ite" in e:
        yield e["ite"]["cond"]
        yield e["ite"]["then"]
        yield e["ite"]["else"]
    elif "call" in e:
        yield from e["call"]["args"]


def _walk(e: dict):
    yield e
    for c in _children(e):
        yield from _walk(c)


def has_quant(e: dict) -> bool:
    return any("forall" in n or "exists" in n for n in _walk(e))


def has_at(e: dict) -> bool:
    return any(n.get("op") == "at" for n in _walk(e))


def fvars(e: dict) -> set:
    return {n["var"] for n in _walk(e) if "var" in n}


def quant_bounds(e: dict) -> list:
    """Every quantifier's (lo, hi) in this clause, for the hoisted machine-
    range obligation. Abstains when hoisting would be unsound."""
    out = []

    def go(e: dict, active: frozenset):
        if "forall" in e or "exists" in e:
            q = e["forall"] if "forall" in e else e["exists"]
            for b in (q["lo"], q["hi"]):
                if fvars(b) & active:
                    raise NotImplementedError(
                        "spark: quantifier bound mentions an enclosing bound "
                        "variable; the machine-range obligation cannot be "
                        "hoisted to clause level")
                if has_at(b):
                    raise NotImplementedError(
                        "spark: partial `at` inside a quantifier bound; "
                        "hoisting the machine-range obligation would strip "
                        "its definedness guard")
            out.append((q["lo"], q["hi"]))
            go(q["lo"], active)
            go(q["hi"], active)
            go(q["body"], active | {q["var"]})
        else:
            for c in _children(e):
                go(c, active)

    go(e, frozenset())
    return out


class Lower:
    def __init__(self, task: dict):
        self.task = task
        self.helpers: list[str] = []   # emitted W_k record types + functions
        self.wcount = 0
        self.spec_fun_names = {sf["name"] for sf in task.get("spec_funs", [])}

    # --- expressions -------------------------------------------------------

    def expr(self, e: dict, sub: dict) -> str:
        if "int" in e:
            # Qualified: a bare literal fails resolution where both operands
            # of an operator are literal-bearing (measured: "expected type
            # universal integer" on count_matches), and the qualified form
            # keeps the Big_Integer literal aspect for arbitrary magnitude.
            return f"Big_Integer'({e['int']})"
        if "bool" in e:
            return "True" if e["bool"] else "False"
        if "var" in e:
            v = e["var"]
            if v not in sub:
                raise ValueError(f"unbound variable {v!r}")
            if sub[v] is None:
                raise ValueError(f"read of unassigned {v!r}")
            return sub[v]
        if "forall" in e or "exists" in e:
            q = e["forall"] if "forall" in e else e["exists"]
            v = cap(q["var"])
            lo, hi = self.expr(q["lo"], sub), self.expr(q["hi"], sub)
            guard = (f"To_Big_Integer ({v}) >= {lo} "
                     f"and then To_Big_Integer ({v}) < {hi}")
            body = self.expr(q["body"],
                             {**sub, q["var"]: f"To_Big_Integer ({v})"})
            if "forall" in e:
                return (f"(for all {v} in Integer => "
                        f"(if {guard} then {body} else True))")
            return f"(for some {v} in Integer => ({guard} and then {body}))"
        if "ite" in e:
            c = e["ite"]
            return (f"(if {self.expr(c['cond'], sub)} "
                    f"then {self.expr(c['then'], sub)} "
                    f"else {self.expr(c['else'], sub)})")
        if "call" in e:
            c = e["call"]
            fun = "F" if c["fun"] == self.task["name"] else cap(c["fun"])
            if c["fun"] != self.task["name"] \
                    and c["fun"] not in self.spec_fun_names:
                raise ValueError(f"call to unknown function {c['fun']!r}")
            args = [self.expr(a, sub) for a in c["args"]]
            return f"{fun} ({', '.join(args)})" if args else fun
        op = e["op"]
        args = [self.expr(a, sub) for a in e.get("args", [])]
        if op == "len":
            return f"To_Big_Integer ({args[0]}'Length)"
        if op == "at":
            s, i = args
            return f"{s} ({s}'First + To_Integer ({i}))"
        if op == "neg":
            return f"(-{args[0]})"
        if op == "not":
            return f"(not {args[0]})"
        if op == "implies":
            return f"(if {args[0]} then {args[1]} else True)"
        if op in NARY:
            return "(" + f" {NARY[op]} ".join(args) + ")"
        if op in CMP:
            return f"({args[0]} {CMP[op]} {args[1]})"
        if op in ARITH:
            return f"({args[0]} {ARITH[op]} {args[1]})"
        raise ValueError(f"t has no operator {op!r}")

    def no_quant(self, e: dict, where: str) -> None:
        if has_quant(e):
            raise NotImplementedError(
                f"spark: quantifier in {where}: the machine-Integer encoding "
                f"truncates the range there with no place to state the "
                f"bounds obligation")

    def clause(self, e: dict, sub: dict) -> str:
        """A requires/ensures/invariant item: hoisted machine-range
        obligations for every quantifier, then the clause itself."""
        parts = [f"({B_FIRST} <= {self.expr(lo, sub)} "
                 f"and then {self.expr(hi, sub)} <= {B_LAST} + 1)"
                 for lo, hi in quant_bounds(e)]
        parts.append(self.expr(e, sub))
        return " and then ".join(parts)

    def req_clause(self, e: dict, sub: dict) -> str:
        if has_quant(e):
            raise NotImplementedError(
                "spark: quantifier in requires is assumption-position; the "
                "machine-range obligation would be assumed, not checked — "
                "not conservative")
        return self.expr(e, sub)

    # --- statements --------------------------------------------------------

    def compile(self, stmts: list, env: dict, types: dict,
                psub: dict) -> dict:
        env, types = dict(env), dict(types)
        for s in stmts:
            if "assign" in s:
                v, e = s["assign"]
                if v not in env:
                    raise ValueError(f"assign to undeclared {v!r}")
                self.no_quant(e, "an executable body position")
                env[v] = self.expr(e, {**psub, **env})
            elif "var" in s:
                d = s["var"]
                self.no_quant(d["init"], "an executable body position")
                env[d["name"]] = self.expr(d["init"], {**psub, **env})
                types[d["name"]] = d["type"]
            elif "if" in s:
                c = s["if"]
                self.no_quant(c["cond"], "an executable body position")
                cond = self.expr(c["cond"], {**psub, **env})
                et = self.compile(c["then"], env, types, psub)
                ee = self.compile(c["else"], env, types, psub)
                for v in env:
                    if et[v] == ee[v]:
                        env[v] = et[v]
                    elif et[v] is None or ee[v] is None:
                        raise NotImplementedError(
                            f"spark: {v!r} assigned on only one branch of an "
                            f"`if` and read later; no join value")
                    else:
                        env[v] = f"(if {cond} then {et[v]} else {ee[v]})"
            elif "while" in s:
                env = self.lower_while(s["while"], env, types, psub)
            else:
                raise ValueError(f"unknown statement {sorted(s)!r}")
        return env

    def lower_while(self, w: dict, env: dict, types: dict,
                    psub: dict) -> dict:
        if "decreases" not in w:
            raise ValueError("while without a decreases clause")
        self.wcount += 1
        name, tname = f"W_{self.wcount}", f"W_{self.wcount}_State"
        state = list(env.keys())
        for v in state:
            if env[v] is None:
                raise NotImplementedError(
                    f"spark: loop reached with {v!r} unassigned; the state "
                    f"record has no value for it")
        tparams = self.task["params"]
        plist = [f"{cap(p['name'])} : {TYPE[p['type']]}" for p in tparams] \
            + [f"{cap(v)} : {TYPE[types[v]]}" for v in state]
        entry = {**psub, **{v: cap(v) for v in state}}
        result = {**psub,
                  **{v: f"{name}'Result.{cap(v)}" for v in state}}
        invs = w.get("invariants", [])
        pre = "\n       and then ".join(self.clause(i, entry) for i in invs)
        post_parts = [self.clause(i, result) for i in invs]
        self.no_quant(w["cond"], "a loop condition")
        post_parts.append(f"(not {self.expr(w['cond'], result)})")
        post = "\n       and then ".join(post_parts)
        self.no_quant(w["decreases"], "a decreases clause")
        d = self.expr(w["decreases"], entry)
        variant = f"(if {d} >= 0 then {d} else 0)"
        inner = {v: cap(v) for v in state}
        benv = self.compile(w["body"], inner, types, psub)
        cond = self.expr(w["cond"], {**psub, **inner})
        rec_args = [cap(p["name"]) for p in tparams] \
            + [benv[v] for v in state]
        agg = ", ".join(f"{cap(v)} => {cap(v)}" for v in state)
        sig = f"function {name} ({'; '.join(plist)}) return {tname}"
        aspects = []
        if pre:
            aspects.append(f"Pre  => {pre}")
        aspects.append(f"Post => {post}")
        aspects.append(f"Subprogram_Variant => (Decreases => {variant})")
        fields = "\n".join(f"      {cap(v)} : {TYPE[types[v]]};"
                           for v in state)
        self.helpers.append(
            f"   type {tname} is record\n{fields}\n   end record;\n"
            f"\n"
            f"   {sig}\n"
            f"   with\n     " + ",\n     ".join(aspects) + ";\n"
            f"\n"
            f"   {sig}\n"
            f"   is ((if {cond}\n"
            f"        then {name} ({', '.join(rec_args)})\n"
            f"        else {tname}'({agg})));\n")
        out_args = [cap(p["name"]) for p in tparams] \
            + [env[v] for v in state]
        call = f"{name} ({', '.join(out_args)})"
        return {v: f"{call}.{cap(v)}" for v in state}

    # --- spec_funs ---------------------------------------------------------

    def lower_spec_fun(self, sf: dict) -> str:
        sub = {p["name"]: cap(p["name"]) for p in sf["params"]}
        self.no_quant(sf["body"], "a spec_fun body (definitional position)")
        self.no_quant(sf["decreases"], "a decreases clause")
        d = self.expr(sf["decreases"], sub)
        plist = "; ".join(f"{cap(p['name'])} : {TYPE[p['type']]}"
                          for p in sf["params"])
        sig = f"function {cap(sf['name'])} ({plist}) return " \
              f"{TYPE[sf['result']]}"
        return (f"   {sig}\n"
                f"   with Subprogram_Variant => "
                f"(Decreases => (if {d} >= 0 then {d} else 0));\n"
                f"\n"
                f"   {sig} is\n"
                f"     ({self.expr(sf['body'], sub)});\n")


def lower(task: dict, body: list) -> str:
    L = Lower(task)
    ret = task["returns"][0]
    psub = {p["name"]: cap(p["name"]) for p in task["params"]}
    needs_seq = any(p["type"] == "seq" for p in task["params"]) or any(
        p["type"] == "seq"
        for sf in task.get("spec_funs", []) for p in sf["params"])

    spec_funs = [L.lower_spec_fun(sf) for sf in task.get("spec_funs", [])]

    env = L.compile(body, {ret["name"]: None}, {ret["name"]: ret["type"]},
                    psub)
    if env[ret["name"]] is None:
        raise ValueError(f"body never assigns {ret['name']!r}")
    final = env[ret["name"]]

    aspects = []
    reqs = [L.req_clause(e, psub) for e in task.get("requires", [])]
    if reqs:
        aspects.append("Pre  => " + "\n       and then ".join(reqs))
    post_sub = {**psub, ret["name"]: "F'Result"}
    aspects.append("Post => " + "\n       and then ".join(
        L.clause(e, post_sub) for e in task["ensures"]))
    if "decreases" in task:
        L.no_quant(task["decreases"], "a decreases clause")
        d = L.expr(task["decreases"], psub)
        aspects.append(f"Subprogram_Variant => "
                       f"(Decreases => (if {d} >= 0 then {d} else 0))")

    plist = "; ".join(f"{cap(p['name'])} : {TYPE[p['type']]}"
                      for p in task["params"])
    fsig = f"function F ({plist}) return {TYPE[ret['type']]}" if plist \
        else f"function F return {TYPE[ret['type']]}"
    pkg = f"T_{cap(task['name'])}"
    parts = [
        "pragma Ada_2022;",
        "with Ada.Numerics.Big_Numbers.Big_Integers;",
        "use  Ada.Numerics.Big_Numbers.Big_Integers;",
        f"package {pkg} with SPARK_Mode is",
        "",
    ]
    if needs_seq:
        parts += ["   type Seq is array (Positive range <>) of Big_Integer;",
                  ""]
    for sf in spec_funs:
        parts += [sf]
    for h in L.helpers:
        parts += [h]
    parts += [
        f"   {fsig}",
        "   with\n     " + ",\n     ".join(aspects) + ";",
        "",
        f"   {fsig} is",
        f"     ({final});",
        "",
        f"end {pkg};",
    ]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, spark_backend, "ads"))
