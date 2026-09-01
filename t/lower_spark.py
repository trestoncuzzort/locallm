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
  * seq            -> SPARK.Containers.Functional.Infinite_Sequences,
                      instantiated over Big_Integer (see THE SEQ MODEL).

VARIANTS: SPARK requires a Big_Integer Subprogram_Variant to be provably
nonnegative; t's decreases obligations only give >= 0 at the recursion/loop
step. Every variant is therefore wrapped (if D >= 0 then D else 0): still
well-founded, decreasing exactly when t's obligations hold, and measured to
prove where Big_Integers.Max blew the 20000-step budget.

THE SEQ MODEL, rewritten 2026-09-01 because the previous one was UNSOUND.
It was `type Seq is array (Positive range <>) of Big_Integer`, and an Ada
array index type is discrete and therefore bounded: S'Length <= Integer'Last
holds by typing, so the kernel was handed `len(s) <= 2^31-1` for free.
SPEC.md gives a seq only `len(s) >= 0`. MEASURED on the fuzzer's fz_p_seqlen
probe (ensures len(s) <= 2^31-1 with both branches live): spark VERIFIED it
while dafny, verus, lean, rocq and fstar REFUTED it — a false theorem, the
same disease as lower_framac.py's C int. The seq is now

    package Seqs is new SPARK.Containers.Functional.Infinite_Sequences
      (Element_Type => Big_Integer);

whose Length returns Big_Natural (no upper bound) and whose Get is indexed
by a Big_Integer position. Its private part is `pragma SPARK_Mode (Off)`, so
the prover sees the public axiomatization and nothing of the bounded
representation underneath: the emitted obligation is about sequences of
arbitrary mathematical length. len(s) >= 0 — SPEC.md's one seq assumption —
comes from Length's own Big_Natural result subtype, not from an assumption
this lowering writes.

QUANTIFIERS: SPARK quantified expressions range over a discrete type or over
a type carrying the Iterable aspect, and Ada's discrete types are all
bounded. t quantifies over mathematical [lo, hi), so the range is lowered as
an Iterable record whose CURSOR IS Big_Integer:

    type T_Range is record Lo, Hi : Big_Integer; end record
      with Iterable => (First => R_First, Has_Element => R_Has,
                        Next  => R_Next);
    (for all K in T_Range'(lo, hi) => body)      -- `for some` for exists

gnatprove quantifies over the cursor type under R_Has, so this IS t's
quantifier over [lo, hi) with no machine slice and no bound to hoist.
MEASURED (2026-09-01, gnatprove FSF 16.1.0): `for all K in T_Range'(0, N) =>
K <= Integer'Last` with N unconstrained goes `medium: postcondition might
fail` — the range is genuinely unbounded — while all_nonneg, contains,
count_matches, linear_search and seq_max still prove. This replaces the
previous `for all K in Integer` encoding and the hoisted `bounds_ok`
obligation it owed, and with them the four ABSTAIN paths that existed only
because a bounds obligation had nowhere sound to sit (quantifier in
requires, in a bound mentioning an enclosing bound variable, under a partial
`at` in a bound, in an executable/definitional position).

DEFINEDNESS: `and`/`or`/`implies` lower to `and then`/`or else`/if-
expressions, so SPEC.md's left-to-right definedness contexts land exactly on
GNATprove's own RTE-checking contexts; `at` lowers to `Elem (S, I)`, whose
own precondition `0 <= I and then I < Len (S)` is exactly t's definedness
side condition and is discharged by the kernel at every use. (Seqs.Get is
total in the shipped non-defensive SPARKlib build — reading out of range
yields an unconstrained value — so the obligation must be, and is, stated on
the wrapper rather than borrowed from the library.)
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

# Every Ada name this file puts in the emitted package. A t identifier that
# capitalizes onto one of them would be captured silently, so lower() refuses
# instead (the W_k helpers are checked separately, by count).
RESERVED = frozenset((
    "F", "Seq", "Seqs", "Len", "Elem", "T_Range", "R_First", "R_Has",
    "R_Next", "Big_Integer", "Boolean"))

SEQ_PREAMBLE = """\
   package Seqs is new SPARK.Containers.Functional.Infinite_Sequences
     (Element_Type => Big_Integer);
   subtype Seq is Seqs.Sequence;

   --  len(s): Big_Natural, so `len(s) >= 0` (SPEC.md's one seq assumption)
   --  is the library's result subtype and nothing bounds it above.
   function Len (S : Seq) return Big_Integer is (Seqs.Length (S));

   --  at(s, i): the Pre IS SPEC.md's definedness side condition, discharged
   --  by the kernel at every use. Seqs.Get is total in the shipped
   --  non-defensive SPARKlib build, so it cannot be borrowed from there.
   function Elem (S : Seq; I : Big_Integer) return Big_Integer is
     (Seqs.Get (S, I + Big_Integer'(1)))
   with Pre => I >= Big_Integer'(0) and then I < Len (S);
"""

# A t quantifier ranges over mathematical [lo, hi). Ada's discrete types are
# all bounded, so the range is a cursor-iterable whose cursor is Big_Integer;
# gnatprove quantifies over the cursor type under R_Has. R_Next's V is unused
# (flow reports UNUSED_VARIABLE at severity "warning", which the adapter's
# audit tolerates); writing a V-dependent body to silence it would put an
# arm in the iteration model that nothing measures.
RANGE_PREAMBLE = """\
   type T_Range is record
      Lo : Big_Integer;
      Hi : Big_Integer;
   end record
   with Iterable => (First       => R_First,
                     Has_Element => R_Has,
                     Next        => R_Next);

   function R_First (V : T_Range) return Big_Integer is (V.Lo);
   function R_Has (V : T_Range; C : Big_Integer) return Boolean is
     (C >= V.Lo and then C < V.Hi);
   function R_Next (V : T_Range; C : Big_Integer) return Big_Integer is
     (C + Big_Integer'(1));
"""


def cap(name: str) -> str:
    return name.capitalize()


# --- name capture ----------------------------------------------------------

def bound_names(task: dict, body: list) -> set:
    """Every t identifier the emitted package will capitalize into an Ada
    name: params, returns, locals, spec_fun names and their params, and
    quantifier bound variables."""
    out = set()

    def go(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("var", "name", "fun") and isinstance(v, str):
                    out.add(v)
                elif k in ("forall", "exists") and isinstance(v, dict):
                    out.add(v.get("var"))
                go(v)
        elif isinstance(x, list):
            for v in x:
                go(v)

    go(task)
    go(body)
    return {n for n in out if isinstance(n, str)}


class Lower:
    def __init__(self, task: dict):
        self.task = task
        self.helpers: list[str] = []   # emitted W_k record types + functions
        self.wcount = 0
        self.needs_range = False       # set by the first lowered quantifier
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
            self.needs_range = True
            q = e["forall"] if "forall" in e else e["exists"]
            v = cap(q["var"])
            lo, hi = self.expr(q["lo"], sub), self.expr(q["hi"], sub)
            # The cursor IS the mathematical bound variable: T_Range's cursor
            # type is Big_Integer, so [lo, hi) is not sliced to a machine type
            # and there is no range obligation to owe (see the header).
            body = self.expr(q["body"], {**sub, q["var"]: v})
            kind = "for all" if "forall" in e else "for some"
            return f"({kind} {v} in T_Range'({lo}, {hi}) => {body})"
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
            return f"Len ({args[0]})"
        if op == "at":
            s, i = args
            return f"Elem ({s}, {i})"
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

    # clause() and req_clause() are gone with the machine-Integer quantifier
    # encoding they served: T_Range carries no bounds obligation to hoist, so
    # every position (requires included) is just expr(). The four ABSTAIN
    # paths that guarded the hoist are gone with it — see the header.

    # --- statements --------------------------------------------------------

    def compile(self, stmts: list, env: dict, types: dict,
                psub: dict) -> dict:
        env, types = dict(env), dict(types)
        for s in stmts:
            if "assign" in s:
                v, e = s["assign"]
                if v not in env:
                    raise ValueError(f"assign to undeclared {v!r}")
                env[v] = self.expr(e, {**psub, **env})
            elif "var" in s:
                d = s["var"]
                env[d["name"]] = self.expr(d["init"], {**psub, **env})
                types[d["name"]] = d["type"]
            elif "if" in s:
                c = s["if"]
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
        pre = "\n       and then ".join(self.expr(i, entry) for i in invs)
        post_parts = [self.expr(i, result) for i in invs]
        post_parts.append(f"(not {self.expr(w['cond'], result)})")
        post = "\n       and then ".join(post_parts)
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

    # The seq and range preambles put fixed Ada names in scope; a t
    # identifier capitalizing onto one of them would be captured silently,
    # which is a wrong answer rather than a missing one.
    clash = sorted(n for n in bound_names(task, body) if cap(n) in RESERVED)
    if clash:
        raise NotImplementedError(
            f"spark: t name(s) {clash} collide with the emitted package's own "
            f"names ({sorted(RESERVED)})")

    spec_funs = [L.lower_spec_fun(sf) for sf in task.get("spec_funs", [])]

    env = L.compile(body, {ret["name"]: None}, {ret["name"]: ret["type"]},
                    psub)
    if env[ret["name"]] is None:
        raise ValueError(f"body never assigns {ret['name']!r}")
    final = env[ret["name"]]

    aspects = []
    reqs = [L.expr(e, psub) for e in task.get("requires", [])]
    if reqs:
        aspects.append("Pre  => " + "\n       and then ".join(reqs))
    post_sub = {**psub, ret["name"]: "F'Result"}
    aspects.append("Post => " + "\n       and then ".join(
        L.expr(e, post_sub) for e in task["ensures"]))
    if "decreases" in task:
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
    ]
    if needs_seq:
        parts += ["with SPARK.Containers.Functional.Infinite_Sequences;"]
    parts += [f"package {pkg} with SPARK_Mode is", ""]
    if needs_seq:
        parts += [SEQ_PREAMBLE]
    if L.needs_range:
        parts += [RANGE_PREAMBLE]
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
