#!/usr/bin/env python3
"""lower_framac.py — lower t v0+v1 tasks to ACSL-annotated C; the sixth kernel.

THE SEMANTIC LINE, corrected 2026-09-01 — the old one was WRONG, and the
error was a false theorem, not a wording slip. It read: "C's int is a machine
type, but WP WITHOUT -wp-rte reasons about the arithmetic mathematically — so
this lowering matches t's mathematical integers exactly." Only the
ARITHMETIC is mathematical without -wp-rte. The TYPING is not: WP's default
model constrains every C `int` with is_sint32, so `x <= 2^31-1` was granted
for free on every formal, every local and every seq element. SPEC.md says t
integers are mathematical and unbounded, so the emitted obligation was a
different, weaker theorem. MEASURED on the differential fuzzer: framac alone
VERIFIED fz_p_intwidth and fz_p_seqlen while six other kernels REFUTED them,
and an element-width probe (`ensures len(s) > 0 ==> s[0] <= 2^31-1`) proved
7/7 goals.

The fix is not in this file, and cannot be: ACSL's unbounded `integer` is a
LOGIC type, and Frama-C 33 rejects it for a ghost variable and for a ghost
function's parameters and result alike (both measured), so there is no C
program this lowering could emit whose program variables are unbounded. What
a C int MEANS to the prover is a model, and the model is a flag: the adapter
pins -wp-model Typed+nat (verifiers/framac.py, MODEL), WP's natural
arithmetic, under which a C integer carries no range hypothesis at all.
Everything below — `int` formals, `int` locals, `int *s` elements, the `int
s_n` length — is therefore a mathematical integer, and the ACSL side already
used `integer` for spec-level quantities and bound variables. The two files
are one instrument: this C read under the default model is a proof of
something t did not ask.

The -wp-rte machine-int arm remains a later gate, not a silent default.

v1 mapping (measured on frama-c 33.0 / alt-ergo 2.4.3-free, 2026-08-31):

  seq        -> `int *s` plus a fresh length parameter `s_n`, with emitted
                preconditions `s_n >= 0` and `\\valid_read(s + (0 .. s_n-1))`.
  forall/    -> `\\forall integer i; lo <= i < hi ==> body` (and the && form
  exists        for exists). Bound vars are ACSL `integer` — mathematical.
  while      -> `loop invariant` per invariant (order preserved — the twin
                depends on it), `loop assigns` (collected from the body),
                `loop variant` from the required decreases clause.
  spec_funs  -> recursive ACSL logic functions (`logic integer f(...) = ...`),
                with a `{L}` label parameter iff the fun reads a seq. WP does
                NOT check termination of recursive logic definitions (measured:
                `bad(n) = bad(n)+1` is accepted), so this lowering emits the
                decreases obligation itself: one `lemma f_terminates_k` per
                self-call, stating measure' >= 0 && measure' < measure under
                that call's path condition. Those lemmas are proof goals in
                the same file — unproved means REFUTED, not a shrug.
  recursion  -> a real recursive C function with an ACSL `decreases` clause;
                WP's variant PO at the call site is the termination proof
                (measured: `decreases 0` on factorial leaves the variant goal
                unproved).

DEFINEDNESS, honestly: `at` outside [0, len) is undefined in t. For
EXECUTABLE positions this lowering discharges it — every unconditionally
evaluated `at` in a statement gets a `/*@ assert 0 <= i < s_n; */` proof
obligation in front of the statement, and a conditionally evaluated `at` in
executable position is an explicit NotImplementedError (never silently
emitted as C UB). For SPEC positions (requires/ensures/invariants/spec_fun
bodies) WP's logic is total: an out-of-range s[i] denotes an UNCONSTRAINED
value under the memory model, so no proof can depend on any particular
out-of-range content — weaker than Dafny-style well-formedness checking,
stronger than totalizing to a fixed value. That gap is this backend's known
softness, recorded here rather than papered over.

Bodies lower to statements: locals are C locals, the return name is a local
returned at the end, `bool` is C int 0/1 (spec side renders bool vars as
`x != 0` and bool equality as `<==>`). Every function gets `assigns
\\nothing;` — it is provable (t bodies never write memory) and it is what
makes recursive calls modular.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                   # noqa: E402
from verifiers import framac as framac_backend   # noqa: E402

ARITH = {"+": "+", "-": "-", "*": "*"}
CMP = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


# ---------------------------------------------------------------- typing ----

def typ(e: dict, env: dict, funs: dict) -> str:
    """Type of an expression: 'int' | 'bool' | 'seq'."""
    if "int" in e:
        return "int"
    if "bool" in e:
        return "bool"
    if "var" in e:
        return env[e["var"]]
    if "forall" in e or "exists" in e:
        return "bool"
    if "ite" in e:
        return typ(e["ite"]["then"], env, funs)
    if "call" in e:
        return funs[e["call"]["fun"]]["result"]
    op = e["op"]
    if op in ("len", "at", "neg") or op in ARITH:
        return "int"
    return "bool"                                # cmp, and, or, not, implies


def seq_var(e: dict, env: dict) -> str:
    """A seq-position expression must be a seq-typed variable (v1: sequences
    are param-position values with no seq-valued operations)."""
    if "var" in e and env.get(e["var"]) == "seq":
        return e["var"]
    raise NotImplementedError(f"seq position holds non-variable {e!r}")


# ---------------------------------------------------------- ACSL (spec) -----

class Ctx:
    """Rendering context for ACSL: env (name->type), funs (spec_fun table +
    the task itself), ret (return name to render as \\result, or None), and
    label (the memory label attached to labeled logic-fun calls)."""
    def __init__(self, env, funs, ret=None, label="Here"):
        self.env, self.funs, self.ret, self.label = env, funs, ret, label

    def bind(self, name, ty):
        env2 = dict(self.env)
        env2[name] = ty
        return Ctx(env2, self.funs, self.ret, self.label)


def acsl_call(c: dict, ctx: Ctx) -> str:
    fun = c["fun"]
    info = ctx.funs[fun]
    if info.get("is_task"):
        raise NotImplementedError(
            "task self-call in spec position (v1 specs are anchored by "
            "spec_funs, never the task's own name)")
    parts = []
    for p, a in zip(info["params"], c["args"], strict=True):
        if p["type"] == "seq":
            s = seq_var(a, ctx.env)
            parts += [s, f"{s}_n"]
        else:
            parts.append(term(a, ctx))
    lab = f"{{{ctx.label}}}" if info["labeled"] else ""
    return f"{fun}{lab}({', '.join(parts)})"


def term(e: dict, ctx: Ctx) -> str:
    """ACSL term. int-typed terms are `integer`-valued; bool-typed terms are
    ACSL boolean terms (comparisons / && / || / ! coerce in term position —
    measured on the count spec_fun's guard)."""
    if "int" in e:
        return str(e["int"])
    if "bool" in e:
        return "\\true" if e["bool"] else "\\false"
    if "var" in e:
        n = e["var"]
        base = "\\result" if n == ctx.ret else n
        return f"({base} != 0)" if ctx.env[n] == "bool" else base
    if "ite" in e:
        i = e["ite"]
        return (f"(({term(i['cond'], ctx)}) ? ({term(i['then'], ctx)}) "
                f": ({term(i['else'], ctx)}))")
    if "call" in e:
        return acsl_call(e["call"], ctx)
    if "forall" in e or "exists" in e:
        raise NotImplementedError("quantifier in ACSL term position")
    op, args = e["op"], e.get("args", [])
    if op == "len":
        return f"{seq_var(args[0], ctx.env)}_n"
    if op == "at":
        return f"{seq_var(args[0], ctx.env)}[{term(args[1], ctx)}]"
    if op == "neg":
        return f"(-{term(args[0], ctx)})"
    if op == "not":
        return f"(!{term(args[0], ctx)})"
    if op == "implies":
        return f"((!({term(args[0], ctx)})) || ({term(args[1], ctx)}))"
    if op in ("and", "or"):
        glue = " && " if op == "and" else " || "
        return "(" + glue.join(term(a, ctx) for a in args) + ")"
    if op in ARITH or op in CMP:
        o = ARITH.get(op) or CMP[op]
        return f"({term(args[0], ctx)} {o} {term(args[1], ctx)})"
    raise ValueError(f"t has no operator {op!r}")


def pred(e: dict, ctx: Ctx) -> str:
    """ACSL predicate (for requires/ensures/invariants/asserts/lemmas)."""
    if "bool" in e:
        return "\\true" if e["bool"] else "\\false"
    if "var" in e:
        n = e["var"]
        base = "\\result" if n == ctx.ret else n
        return f"({base} != 0)"                  # bool-typed C variable
    if "forall" in e or "exists" in e:
        kind = "forall" if "forall" in e else "exists"
        q = e[kind]
        c2 = ctx.bind(q["var"], "int")
        rng = (f"({term(q['lo'], ctx)}) <= {q['var']} "
               f"&& {q['var']} < ({term(q['hi'], ctx)})")
        body = pred(q["body"], c2)
        glue = "==>" if kind == "forall" else "&&"
        return f"(\\{kind} integer {q['var']}; ({rng}) {glue} ({body}))"
    if "ite" in e:
        i = e["ite"]
        c = pred(i["cond"], ctx)
        return (f"((({c}) && ({pred(i['then'], ctx)})) "
                f"|| ((!({c})) && ({pred(i['else'], ctx)})))")
    if "call" in e:
        return f"({acsl_call(e['call'], ctx)} == \\true)"
    op, args = e["op"], e.get("args", [])
    if op == "not":
        return f"(!{pred(args[0], ctx)})"
    if op == "implies":
        return f"({pred(args[0], ctx)} ==> {pred(args[1], ctx)})"
    if op in ("and", "or"):
        glue = " && " if op == "and" else " || "
        return "(" + glue.join(pred(a, ctx) for a in args) + ")"
    if op in ("==", "!="):
        if typ(args[0], ctx.env, ctx.funs) == "bool":
            eq = f"({pred(args[0], ctx)} <==> {pred(args[1], ctx)})"
            return eq if op == "==" else f"(!{eq})"
        return f"({term(args[0], ctx)} {CMP[op]} {term(args[1], ctx)})"
    if op in CMP:
        return f"({term(args[0], ctx)} {CMP[op]} {term(args[1], ctx)})"
    raise ValueError(f"no predicate form for operator {op!r}")


# ------------------------------------------------------------- C (code) -----

def cexpr(e: dict, env: dict, funs: dict, task_name: str) -> str:
    if "int" in e:
        return str(e["int"])
    if "bool" in e:
        return "1" if e["bool"] else "0"
    if "var" in e:
        return e["var"]
    if "forall" in e or "exists" in e:
        raise NotImplementedError("bounded quantifier in executable position")
    if "ite" in e:
        i = e["ite"]
        return (f"(({cexpr(i['cond'], env, funs, task_name)}) "
                f"? ({cexpr(i['then'], env, funs, task_name)}) "
                f": ({cexpr(i['else'], env, funs, task_name)}))")
    if "call" in e:
        c = e["call"]
        if c["fun"] != task_name:
            raise NotImplementedError(
                "spec_fun call in executable position (ACSL logic functions "
                "are not executable)")
        parts = []
        for p, a in zip(funs[task_name]["params"], c["args"], strict=True):
            if p["type"] == "seq":
                s = seq_var(a, env)
                parts += [s, f"{s}_n"]
            else:
                parts.append(cexpr(a, env, funs, task_name))
        return f"{task_name}_t({', '.join(parts)})"
    op, args = e["op"], e.get("args", [])
    if op == "len":
        return f"{seq_var(args[0], env)}_n"
    if op == "at":
        return (f"{seq_var(args[0], env)}"
                f"[{cexpr(args[1], env, funs, task_name)}]")
    if op == "neg":
        return f"(-{cexpr(args[0], env, funs, task_name)})"
    if op == "not":
        return f"(!{cexpr(args[0], env, funs, task_name)})"
    if op == "implies":
        a, b = (cexpr(x, env, funs, task_name) for x in args)
        return f"((!({a})) || ({b}))"
    if op in ("and", "or"):
        glue = " && " if op == "and" else " || "
        return ("(" + glue.join(cexpr(a, env, funs, task_name)
                                for a in args) + ")")
    if op in ARITH or op in CMP:
        o = ARITH.get(op) or CMP[op]
        return (f"({cexpr(args[0], env, funs, task_name)} {o} "
                f"{cexpr(args[1], env, funs, task_name)})")
    raise ValueError(f"t has no operator {op!r}")


def code_ats(e: dict, env: dict, uncond: bool = True) -> list:
    """(seq, index-expr) pairs for every `at` in an executable expression.
    Unconditionally evaluated ats are returned (they get an assert);
    a conditionally evaluated at is refused — emitting it without a
    dischargeable guard would silently totalize `at` as C UB."""
    out = []
    if "ite" in e:
        i = e["ite"]
        out += code_ats(i["cond"], env, uncond)
        out += code_ats(i["then"], env, False)
        out += code_ats(i["else"], env, False)
        return out
    if "call" in e:
        for a in e["call"]["args"]:
            out += code_ats(a, env, uncond)
        return out
    if "op" not in e:
        return out
    op, args = e["op"], e.get("args", [])
    if op == "at":
        if not uncond:
            raise NotImplementedError(
                "conditionally evaluated `at` in executable position — "
                "definedness not dischargeable by a plain assert")
        out += code_ats(args[1], env, uncond)
        out.append((seq_var(args[0], env), args[1]))
        return out
    if op in ("and", "or"):
        out += code_ats(args[0], env, uncond)
        for a in args[1:]:
            out += code_ats(a, env, False)
        return out
    if op == "implies":
        out += code_ats(args[0], env, uncond)
        out += code_ats(args[1], env, False)
        return out
    for a in args:
        out += code_ats(a, env, uncond)
    return out


def at_asserts(e: dict, ctx: Ctx, indent: str) -> list:
    return [f"{indent}/*@ assert 0 <= ({term(ix, ctx)}) "
            f"&& ({term(ix, ctx)}) < {s}_n; */"
            for s, ix in code_ats(e, ctx.env)]


def assigned_names(body: list) -> tuple[list, list]:
    """(assign targets, locals declared) in order, recursively."""
    hit, dec = [], []
    for s in body:
        if "assign" in s:
            hit.append(s["assign"][0])
        elif "var" in s:
            dec.append(s["var"]["name"])
        elif "if" in s:
            for br in (s["if"]["then"], s["if"]["else"]):
                h, d = assigned_names(br)
                hit += h
                dec += d
        elif "while" in s:
            h, d = assigned_names(s["while"]["body"])
            hit += h
            dec += d
    return hit, dec


def stmts(body: list, ctx: Ctx, task_name: str, indent: str) -> list:
    out = []
    for s in body:
        if "assign" in s:
            name, e = s["assign"]
            assert name in ctx.env, f"assign to undeclared {name}"
            out += at_asserts(e, ctx, indent)
            out.append(f"{indent}{name} = "
                       f"{cexpr(e, ctx.env, ctx.funs, task_name)};")
        elif "var" in s:
            v = s["var"]
            out += at_asserts(v["init"], ctx, indent)
            ctx = ctx.bind(v["name"], v["type"])
            out.append(f"{indent}int {v['name']} = "
                       f"{cexpr(v['init'], ctx.env, ctx.funs, task_name)};")
        elif "if" in s:
            c = s["if"]
            out += at_asserts(c["cond"], ctx, indent)
            out.append(f"{indent}if "
                       f"({cexpr(c['cond'], ctx.env, ctx.funs, task_name)}) "
                       f"{{")
            out += stmts(c["then"], ctx, task_name, indent + "  ")
            out.append(f"{indent}}} else {{")
            out += stmts(c["else"], ctx, task_name, indent + "  ")
            out.append(f"{indent}}}")
        elif "while" in s:
            w = s["while"]
            if code_ats(w["cond"], ctx.env):
                raise NotImplementedError(
                    "`at` in a while condition — its per-iteration "
                    "definedness assert has no statement to precede")
            ann = [f"{indent}  loop invariant {pred(i, ctx)};"
                   for i in w.get("invariants", [])]
            hit, dec = assigned_names(w["body"])
            frame = [n for n in dict.fromkeys(hit) if n not in dec]
            ann.append(f"{indent}  loop assigns "
                       f"{', '.join(frame) if frame else chr(92) + 'nothing'};")
            ann.append(f"{indent}  loop variant ({term(w['decreases'], ctx)});")
            out.append(f"{indent}/*@")
            out += ann
            out.append(f"{indent}*/")
            out.append(f"{indent}while "
                       f"({cexpr(w['cond'], ctx.env, ctx.funs, task_name)}) "
                       f"{{")
            out += stmts(w["body"], ctx, task_name, indent + "  ")
            out.append(f"{indent}}}")
        else:
            raise ValueError(f"t has no statement {s!r}")
    return out


# ------------------------------------------------- spec_fun termination -----

def subst(e: dict, m: dict) -> dict:
    if "var" in e:
        return m.get(e["var"], e)
    if "int" in e or "bool" in e:
        return e
    if "ite" in e:
        i = e["ite"]
        return {"ite": {k: subst(i[k], m) for k in ("cond", "then", "else")}}
    if "call" in e:
        c = e["call"]
        return {"call": {"fun": c["fun"],
                         "args": [subst(a, m) for a in c["args"]]}}
    for kind in ("forall", "exists"):
        if kind in e:
            q = e[kind]
            m2 = {k: v for k, v in m.items() if k != q["var"]}
            return {kind: {"var": q["var"], "lo": subst(q["lo"], m),
                           "hi": subst(q["hi"], m),
                           "body": subst(q["body"], m2)}}
    return {"op": e["op"], "args": [subst(a, m) for a in e.get("args", [])]}


def self_calls(e: dict, fun: str, path: list) -> list:
    """(args, path-conditions) for every self-call, path tracked through the
    definedness-relevant branching structure (ite branches, and/or/implies
    short-circuit)."""
    out = []
    if "ite" in e:
        i = e["ite"]
        out += self_calls(i["cond"], fun, path)
        out += self_calls(i["then"], fun, path + [i["cond"]])
        out += self_calls(i["else"], fun,
                          path + [{"op": "not", "args": [i["cond"]]}])
        return out
    if "call" in e:
        c = e["call"]
        for a in c["args"]:
            out += self_calls(a, fun, path)
        if c["fun"] == fun:
            out.append((c["args"], path))
        return out
    for kind in ("forall", "exists"):
        if kind in e:
            q = e[kind]
            for sub in (q["lo"], q["hi"], q["body"]):
                out += self_calls(sub, fun, path)
            return out
    if "op" not in e:
        return out
    op, args = e["op"], e.get("args", [])
    if op in ("and", "or"):
        seen = []
        for a in args:
            out += self_calls(a, fun, path + seen)
            g = a if op == "and" else {"op": "not", "args": [a]}
            seen = seen + [g]
        return out
    if op == "implies":
        out += self_calls(args[0], fun, path)
        out += self_calls(args[1], fun, path + [args[0]])
        return out
    for a in args:
        out += self_calls(a, fun, path)
    return out


def spec_fun_acsl(f: dict, funs: dict) -> list:
    """The recursive logic definition plus its measured termination lemmas
    (WP does not check logic-function termination itself — see docstring)."""
    env = {p["name"]: p["type"] for p in f["params"]}
    labeled = funs[f["name"]]["labeled"]
    lab = "{L}" if labeled else ""
    sig = []
    for p in f["params"]:
        if p["type"] == "seq":
            sig += [f"int *{p['name']}", f"integer {p['name']}_n"]
        else:
            sig.append(f"integer {p['name']}")
    body_ctx = Ctx(env, funs, ret=None, label="L")
    res = {"int": "integer", "bool": "boolean"}[f["result"]]
    lines = [f"/*@ logic {res} {f['name']}{lab}({', '.join(sig)}) =",
             f"      {term(f['body'], body_ctx)};", "*/"]
    quant = ", ".join(
        (f"int *{p['name']}, integer {p['name']}_n"
         if p["type"] == "seq" else f"integer {p['name']}")
        for p in f["params"])
    for k, (args, path) in enumerate(self_calls(f["body"], f["name"], []), 1):
        m = {p["name"]: a for p, a in zip(f["params"], args, strict=True)}
        measure = term(f["decreases"], body_ctx)
        measure2 = term(subst(f["decreases"], m), body_ctx)
        concl = f"(({measure2}) >= 0 && ({measure2}) < ({measure}))"
        guard = " && ".join(f"({pred(p, body_ctx)})" for p in path)
        prop = f"({guard}) ==> {concl}" if guard else concl
        lines += [f"/*@ lemma {f['name']}_terminates_{k}{lab}:",
                  f"      \\forall {quant};",
                  f"      {prop};", "*/"]
    return lines


# -------------------------------------------------------------- lowering ----

def lower(task: dict, body: list) -> str:
    name, ret = task["name"], task["returns"][0]["name"]
    rett = task["returns"][0]["type"]
    env = {p["name"]: p["type"] for p in task["params"]}
    env[ret] = rett

    funs = {}
    for f in task.get("spec_funs", []):
        funs[f["name"]] = {
            "params": f["params"], "result": f["result"],
            "labeled": any(p["type"] == "seq" for p in f["params"]),
            "is_task": False}
    funs[name] = {"params": task["params"], "result": rett,
                  "labeled": False, "is_task": True}

    seqs = [p["name"] for p in task["params"] if p["type"] == "seq"]
    used = set()

    def names_in(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("var", "name", "fun") and isinstance(v, str):
                    used.add(v)
                names_in(v)
        elif isinstance(x, list):
            for v in x:
                names_in(v)
    names_in(task)
    names_in(body)
    for s in seqs:
        if f"{s}_n" in used:
            raise NotImplementedError(
                f"name {s}_n collides with the fresh length parameter "
                f"for seq {s}")

    header = []
    for f in task.get("spec_funs", []):
        header += spec_fun_acsl(f, funs)

    spec_ctx = Ctx(env, funs, ret=None, label="Here")
    post_ctx = Ctx(env, funs, ret=ret, label="Here")
    clauses = []
    for s in seqs:
        clauses.append(f"  requires {s}_n >= 0;")
        clauses.append(f"  requires \\valid_read({s} + (0 .. {s}_n - 1));")
    clauses += [f"  requires {pred(e, spec_ctx)};"
                for e in task.get("requires", [])]
    if "decreases" in task:
        clauses.append(f"  decreases ({term(task['decreases'], spec_ctx)});")
    clauses.append("  assigns \\nothing;")
    clauses += [f"  ensures {pred(e, post_ctx)};" for e in task["ensures"]]

    cparams = []
    for p in task["params"]:
        if p["type"] == "seq":
            cparams += [f"int *{p['name']}", f"int {p['name']}_n"]
        else:
            cparams.append(f"int {p['name']}")

    body_lines = stmts(body, Ctx(env, funs, ret=None, label="Here"),
                       name, "  ")
    return ("\n".join(header) + ("\n" if header else "")
            + "/*@\n" + "\n".join(clauses) + "\n*/\n"
            + f"int {name}_t({', '.join(cparams)}) {{\n"
            + f"  int {ret};\n"
            + "\n".join(body_lines) + "\n"
            + f"  return {ret};\n}}\n")


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, framac_backend, "c"))
