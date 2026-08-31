#!/usr/bin/env python3
"""lower_lean.py — lower t tasks (v0 and v1) to Lean 4; the proof-assistant kernel.

THE PROOF-ASSISTANT DIFFERENCE, made concrete: the lowering emits functions,
theorems stating every ensures clause with the return name replaced by the
applied function, and PROOFS. Lean has no SMT sidecar — every verdict is the
kernel accepting (or rejecting) a proof term. The automation used is real and
kernel-checked: `omega` (linear integer arithmetic) and `grind` (congruence +
E-matching + case splits + linear arith, in core Lean since 4.22). No proof
term is hand-plumbed per task; every tactic script below is derived from the
BODY SHAPE by one rule, identically for every task:

  SIMPLE     (no loop, no self-call — all v0 tasks, and collapse-if twins
              whose recursion collapsed away): one function, one theorem,
              `unfold; grind`. The v0 lesson is kept: every script is a
              `first | ... | grind [f]` so a twin whose shape no longer fits
              the primary script fails on TRUTH (grind reasoning about the
              unfolded body), never on tactic shape.
  RECURSIVE  (body self-calls): the function takes the conjoined `requires`
              as a hypothesis argument — Lean-native partial functions — and
              every self-call discharges the callee's requires with a real
              `by omega/grind` proof; `termination_by (decreases).toNat`
              carries the t termination obligation. The theorem is itself
              recursive: it binds its own induction hypothesis as a `have`
              guarded by t's decreases obligation (0 <= smaller < current),
              then unfolds one step, splits the branches, and grinds — the
              IH is the modular contract of every smaller call.
              (fun_induction was measured and refused: grind cannot bridge
              the dependent requires-proof argument across arithmetic
              normalization — gcd's `a - b` leaf never met its induction
              hypothesis.)
  LOOP       (body contains one top-level while): the loop becomes a
              tail-recursive function over the mutable state; the invariants
              become hypotheses of a recursive helper theorem — the induction
              hypothesis is literally the invariant list. Guard-true steps
              re-enter the lemma at the symbolically-updated state (invariant
              preservation, by grind); guard-false discharges the ensures
              from invariants + ¬guard (by grind). Merged if-updates are
              pre-`split` so grind reasons per-branch — measured: without the
              split, grind loses the existential-invariant preservation of
              seq_max in cutsat case explosions.

DEFINEDNESS IS NOT SILENTLY TOTALIZED. `at` is lowered to the total
`s[i.toNat]!` for computation, and the SPEC.md definedness obligations are
emitted as separate _wf theorems, one per non-trivially-defined clause /
program point, each proved under exactly the context SPEC.md grants it
(earlier requires; requires + earlier ensures; earlier invariants;
invariants + guard for the loop body, with short-circuit and taken-branch
rules built into the D() calculus below). A file only verifies if its
definedness obligations also prove.

Existential-invariant establishment gets one generic heuristic: if plain
grind fails, retry with the range's lower endpoint as witness (`exact ⟨lo,
by grind⟩`) — needed because Int-literal toNat indices normalize away the
E-matching pattern grind would use to find the witness itself (measured on
seq_max's `∃ j ∈ [0,1)` at r = s[0]).

Every file ends with `#print axioms` per theorem; the adapter audits the list.

ABSTAIN policy: shapes this lowering cannot express honestly raise
NotImplementedError with the reason (multiple/nested loops, a loop plus
self-recursion, quantifiers in computational position). A recorded absence,
never a faked proof.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                 # noqa: E402
from verifiers import lean as lean_backend     # noqa: E402

CMP_OPS = {"<": "<", "<=": "≤", ">": ">", ">=": "≥"}
ARITH_OPS = {"+", "-", "*"}


def _collect_names(x, out: set) -> None:
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("var", "fun", "name") and isinstance(v, str):
                out.add(v)
            elif k == "assign":
                out.add(v[0])
                _collect_names(v[1], out)
            else:
                _collect_names(v, out)
    elif isinstance(x, list):
        for v in x:
            _collect_names(v, out)


class Lower:
    """One instance per (task, body) pair. Everything derives from the JSON."""

    def __init__(self, task: dict, body: list):
        self.task, self.body = task, body
        self.name = task["name"]
        self.ret = task["returns"][0]["name"]
        self.rett = task["returns"][0]["type"]
        self.types: dict[str, str] = {p["name"]: p["type"]
                                      for p in task["params"]}
        self.types[self.ret] = self.rett
        self.sfuns = {f["name"]: f for f in task.get("spec_funs", [])}
        self.used: set[str] = {self.name}
        _collect_names(task, self.used)
        _collect_names(body, self.used)
        self.fresh_n = 0
        self.hyp_n = 0
        self.ga = ("" if not self.sfuns else
                   " [" + ", ".join(f"{f}_s" for f in self.sfuns) + "]")

    # ---------- naming ----------

    def fresh(self, base: str) -> str:
        while True:
            self.fresh_n += 1
            cand = f"{base}_{self.fresh_n}"
            if cand not in self.used:
                self.used.add(cand)
                return cand

    def fresh_hyp(self) -> str:
        self.hyp_n += 1
        return f"_h{self.hyp_n}"

    # ---------- sorts ----------

    def sort(self, e: dict, types: dict) -> str:
        if "int" in e:
            return "int"
        if "bool" in e:
            return "bool"
        if "var" in e:
            return types[e["var"]]
        if "forall" in e or "exists" in e:
            return "bool"
        if "ite" in e:
            return self.sort(e["ite"]["then"], types)
        if "call" in e:
            f = e["call"]["fun"]
            if f == self.name:
                return self.rett
            return self.sfuns[f]["result"]
        op = e["op"]
        if op in ARITH_OPS or op in ("neg", "len", "at"):
            return "int"
        return "bool"

    # ---------- expressions ----------

    def term(self, e: dict, env: dict, types: dict, dep: bool = False) -> str:
        """Computational (term-level) lowering. `env` substitutes names;
        `dep` makes ite dependent (named hypothesis) so nested requires /
        termination proofs see the branch condition."""
        if "int" in e:
            n = e["int"]
            return f"({n} : Int)" if n >= 0 else f"(({n}) : Int)"
        if "bool" in e:
            return "true" if e["bool"] else "false"
        if "var" in e:
            return env.get(e["var"], e["var"])
        if "ite" in e:
            c = e["ite"]
            cp = self.prop(c["cond"], env, types)
            t = self.term(c["then"], env, types, dep)
            f = self.term(c["else"], env, types, dep)
            if dep:
                return f"(if {self.fresh_hyp()} : {cp} then {t} else {f})"
            return f"(if {cp} then {t} else {f})"
        if "call" in e:
            c = e["call"]
            args = " ".join(self.term(a, env, types, dep) for a in c["args"])
            if c["fun"] == self.name:
                pre = " (by first | omega | grind)" if self.task.get(
                    "requires") else ""
                return f"({self.name}_t {args}{pre})"
            return f"({c['fun']}_s {args})"
        if "forall" in e or "exists" in e:
            raise NotImplementedError(
                "bounded quantifier in computational position "
                "is not lowered for lean")
        op = e["op"]
        if op == "len":
            s = self.term(e["args"][0], env, types, dep)
            return f"((({s}).length : Int))"
        if op == "at":
            s = self.term(e["args"][0], env, types, dep)
            i = self.term(e["args"][1], env, types, dep)
            return f"({s}[({i}).toNat]!)"
        if op == "neg":
            return f"(-{self.term(e['args'][0], env, types, dep)})"
        if op in ARITH_OPS:
            a, b = (self.term(x, env, types, dep) for x in e["args"])
            return f"({a} {op} {b})"
        raise NotImplementedError(
            f"boolean operator {op!r} in computational position "
            "is not lowered for lean")

    def prop(self, e: dict, env: dict, types: dict) -> str:
        """Spec (Prop-level) lowering."""
        if "bool" in e:
            return "True" if e["bool"] else "False"
        if "var" in e:
            v = env.get(e["var"], e["var"])
            assert types[e["var"]] == "bool", f"int var {e['var']} as Prop"
            return f"({v} = true)"
        if "forall" in e:
            q = e["forall"]
            b = self.fresh(q["var"])
            lo = self.term(q["lo"], env, types)
            hi = self.term(q["hi"], env, types)
            body = self.prop(q["body"], {**env, q["var"]: b},
                             {**types, q["var"]: "int"})
            return f"(∀ ({b} : Int), {lo} ≤ {b} → {b} < {hi} → {body})"
        if "exists" in e:
            q = e["exists"]
            b = self.fresh(q["var"])
            lo = self.term(q["lo"], env, types)
            hi = self.term(q["hi"], env, types)
            body = self.prop(q["body"], {**env, q["var"]: b},
                             {**types, q["var"]: "int"})
            return f"(∃ ({b} : Int), {lo} ≤ {b} ∧ {b} < {hi} ∧ {body})"
        if "ite" in e:
            c = e["ite"]
            cp = self.prop(c["cond"], env, types)
            t = self.prop(c["then"], env, types)
            f = self.prop(c["else"], env, types)
            return f"(({cp} → {t}) ∧ (¬{cp} → {f}))"
        if "call" in e:
            return f"({self.term(e, env, types)} = true)"
        op = e["op"]
        if op in ("==", "!="):
            a, b = e["args"]
            if self.sort(a, types) == "bool":
                pa, pb = self.prop(a, env, types), self.prop(b, env, types)
                core = f"({pa} ↔ {pb})"
            else:
                ta, tb = self.term(a, env, types), self.term(b, env, types)
                core = (f"({ta} = {tb})" if op == "=="
                        else f"({ta} ≠ {tb})")
                return core
            return core if op == "==" else f"(¬{core})"
        if op in CMP_OPS:
            a, b = (self.term(x, env, types) for x in e["args"])
            return f"({a} {CMP_OPS[op]} {b})"
        if op == "not":
            return f"(¬{self.prop(e['args'][0], env, types)})"
        if op == "implies":
            p, q = (self.prop(x, env, types) for x in e["args"])
            return f"({p} → {q})"
        if op in ("and", "or"):
            j = " ∧ " if op == "and" else " ∨ "
            return "(" + j.join(self.prop(x, env, types)
                                for x in e["args"]) + ")"
        raise NotImplementedError(f"operator {op!r} in spec position "
                                  "is not lowered for lean")

    # ---------- definedness (SPEC.md "Definedness", as a calculus) ----------

    @staticmethod
    def _conj(parts: list) -> str | None:
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else "(" + " ∧ ".join(parts) + ")"

    def dcond(self, e: dict, env: dict, types: dict) -> str | None:
        """The proposition under which e is defined; None means True.
        Encodes left-to-right short-circuit for and/or/implies, taken-branch
        for ite, per-element for quantifier bodies, and 0 <= i < len for at."""
        if "int" in e or "bool" in e or "var" in e:
            return None
        guard = lambda p, d: None if d is None else f"({p} → {d})"  # noqa: E731
        if "ite" in e:
            c = e["ite"]
            cp = self.prop(c["cond"], env, types)
            return self._conj([
                self.dcond(c["cond"], env, types),
                guard(cp, self.dcond(c["then"], env, types)),
                guard(f"¬{cp}", self.dcond(c["else"], env, types))])
        if "forall" in e or "exists" in e:
            q = e["forall"] if "forall" in e else e["exists"]
            b = self.fresh(q["var"])
            env2 = {**env, q["var"]: b}
            types2 = {**types, q["var"]: "int"}
            lo = self.term(q["lo"], env, types)
            hi = self.term(q["hi"], env, types)
            db = self.dcond(q["body"], env2, types2)
            parts = [self.dcond(q["lo"], env, types),
                     self.dcond(q["hi"], env, types)]
            if db is not None:
                parts.append(f"(∀ ({b} : Int), {lo} ≤ {b} → {b} < {hi} "
                             f"→ {db})")
            return self._conj(parts)
        if "call" in e:
            return self._conj([self.dcond(a, env, types)
                               for a in e["call"]["args"]])
        op = e["op"]
        if op == "at":
            s, i = e["args"]
            it = self.term(i, env, types)
            ln = f"((({self.term(s, env, types)}).length : Int))"
            return self._conj([
                self.dcond(s, env, types), self.dcond(i, env, types),
                f"(((0 : Int) ≤ {it}) ∧ ({it} < {ln}))"])
        if op in ("and", "or"):
            def chain(args):
                if not args:
                    return None
                head, rest = args[0], args[1:]
                dh = self.dcond(head, env, types)
                dr = chain(rest)
                p = self.prop(head, env, types)
                if op == "or":
                    p = f"¬{p}"
                return self._conj([dh, guard(p, dr)])
            return chain(list(e["args"]))
        if op == "implies":
            p, q = e["args"]
            return self._conj([
                self.dcond(p, env, types),
                guard(self.prop(p, env, types),
                      self.dcond(q, env, types))])
        # strict ops: not, neg, len, arithmetic, comparisons, == / !=
        return self._conj([self.dcond(a, env, types)
                           for a in e.get("args", [])])

    # ---------- statements ----------

    def sym(self, stmts: list, env: dict, types: dict,
            keys: list[str]) -> tuple[dict, list]:
        """Forward symbolic execution of a loop-free statement list.
        Returns (updated env over `keys`, definedness obligations, each
        already guarded by its path condition)."""
        obs: list = []
        env = dict(env)
        for s in stmts:
            if "assign" in s:
                x, e = s["assign"]
                obs.append(self.dcond(e, env, types))
                env[x] = self.term(e, env, types)
            elif "var" in s:
                d = s["var"]
                types[d["name"]] = d["type"]
                obs.append(self.dcond(d["init"], env, types))
                env[d["name"]] = self.term(d["init"], env, types)
            elif "if" in s:
                c = s["if"]
                obs.append(self.dcond(c["cond"], env, types))
                cp = self.prop(c["cond"], env, types)
                env_t, obs_t = self.sym(c["then"], env, types, keys)
                env_e, obs_e = self.sym(c["else"], env, types, keys)
                obs += [f"({cp} → {o})" for o in obs_t if o is not None]
                obs += [f"(¬{cp} → {o})" for o in obs_e if o is not None]
                for k in set(env_t) | set(env_e):
                    t, f = env_t.get(k, k), env_e.get(k, k)
                    env[k] = t if t == f else f"(if {cp} then {t} else {f})"
            elif "while" in s:
                raise NotImplementedError(
                    "nested / multiple loops are not lowered for lean")
            else:
                raise NotImplementedError(f"statement {list(s)} unknown")
        return env, [o for o in obs if o is not None]

    def to_expr(self, stmts: list, env: dict, types: dict) -> tuple[str, list]:
        """Loop-free body -> one expression computing the return value,
        with dependent ifs (branch hypotheses feed the requires/termination
        side proofs of self-calls). Returns (expr, definedness obligations)."""
        if not stmts:
            raise NotImplementedError(
                "a path that assigns nothing is not lowered for lean")
        s, rest = stmts[0], stmts[1:]
        if "if" in s and not rest:
            c = s["if"]
            ob0 = self.dcond(c["cond"], env, types)
            cp = self.prop(c["cond"], env, types)
            te, obs_t = self.to_expr(c["then"], env, types)
            fe, obs_e = self.to_expr(c["else"], env, types)
            obs = ([ob0] if ob0 else []) \
                + [f"({cp} → {o})" for o in obs_t] \
                + [f"(¬{cp} → {o})" for o in obs_e]
            return (f"(if {self.fresh_hyp()} : {cp} then {te} else {fe})",
                    obs)
        if "assign" in s:
            x, e = s["assign"]
            ob = self.dcond(e, env, types)
            obs = [ob] if ob else []
            if not rest:
                if x != self.ret:
                    raise NotImplementedError(
                        f"body path ends assigning {x!r}, not the return")
                return self.term(e, env, types, dep=True), obs
            t = self.term(e, env, types, dep=True)
            env2 = {k: v for k, v in env.items() if k != x}
            re_, obs_r = self.to_expr(rest, env2, types)
            return f"(let {x} := {t};\n  {re_})", obs + obs_r
        if "var" in s:
            d = s["var"]
            types[d["name"]] = d["type"]
            ob = self.dcond(d["init"], env, types)
            t = self.term(d["init"], env, types, dep=True)
            env2 = {k: v for k, v in env.items() if k != d["name"]}
            re_, obs_r = self.to_expr(rest, env2, types)
            return (f"(let {d['name']} := {t};\n  {re_})",
                    ([ob] if ob else []) + obs_r)
        raise NotImplementedError(
            "statements after a branch are not lowered for lean")

    # ---------- shared pieces ----------

    def lean_type(self, t: str) -> str:
        return {"int": "Int", "bool": "Bool", "seq": "List Int"}[t]

    def binders(self, names_types: list[tuple[str, str]]) -> str:
        return " ".join(f"({n} : {self.lean_type(t)})"
                        for n, t in names_types)

    def _has(self, x, key: str, val=None) -> bool:
        if isinstance(x, dict):
            if key in x and (val is None or x[key] == val):
                if key != "call" or val is None or x["call"]["fun"] == val:
                    return True
            if key == "call" and "call" in x and (
                    val is None or x["call"]["fun"] == val):
                return True
            return any(self._has(v, key, val) for v in x.values())
        if isinstance(x, list):
            return any(self._has(v, key, val) for v in x)
        return False

    def _self_calls(self, x) -> bool:
        if isinstance(x, dict):
            if "call" in x and isinstance(x["call"], dict) \
                    and x["call"].get("fun") == self.name:
                return True
            return any(self._self_calls(v) for v in x.values())
        if isinstance(x, list):
            return any(self._self_calls(v) for v in x)
        return False

    def pre_props(self) -> list[str]:
        return [self.prop(r, {}, self.types)
                for r in self.task.get("requires", [])]

    def pre_conj(self) -> str:
        return " ∧ ".join(self.pre_props())

    def post_conj(self, applied: str) -> str:
        env = {self.ret: applied}
        return "\n    ∧ ".join(self.prop(e, env, self.types)
                               for e in self.task["ensures"])

    # ---------- spec_funs ----------

    def emit_sfuns(self) -> tuple[str, list[tuple[str, str]]]:
        out, thms = [], []
        for f in self.task.get("spec_funs", []):
            ptypes = {p["name"]: p["type"] for p in f["params"]}
            pb = self.binders([(p["name"], p["type"]) for p in f["params"]])
            body = self.term(f["body"], {}, dict(ptypes), dep=True)
            rec = self._self_calls_named(f["body"], f["name"])
            out.append(f"def {f['name']}_s {pb} : "
                       f"{self.lean_type(f['result'])} :=\n  {body}")
            if rec:
                dec = self.term(f["decreases"], {}, dict(ptypes))
                out.append(f"termination_by ({dec}).toNat")
                out.append("decreasing_by all_goals (first | omega | grind)")
            out.append("")
            d = self.dcond(f["body"], {}, dict(ptypes))
            if d is not None:
                tname = f"{f['name']}_s_wf"
                out.append(f"theorem {tname} {pb} :\n    {d} := by\n"
                           f"  grind{self.ga}\n")
                thms.append((tname, "definedness of spec_fun "
                             + f["name"]))
        return "\n".join(out), thms

    @staticmethod
    def _self_calls_named(x, name: str) -> bool:
        if isinstance(x, dict):
            if "call" in x and isinstance(x["call"], dict) \
                    and x["call"].get("fun") == name:
                return True
            return any(Lower._self_calls_named(v, name) for v in x.values())
        if isinstance(x, list):
            return any(Lower._self_calls_named(v, name) for v in x)
        return False

    # ---------- clause-level definedness theorems ----------

    def emit_clause_wfs(self) -> tuple[str, list[tuple[str, str]]]:
        out, thms, k = [], [], 0
        params_nt = [(p["name"], p["type"]) for p in self.task["params"]]
        reqs = self.task.get("requires", [])
        for i, r in enumerate(reqs):
            d = self.dcond(r, {}, self.types)
            if d is None:
                continue
            k += 1
            hyps = "".join(f"{self.prop(x, {}, self.types)} → "
                           for x in reqs[:i])
            out.append(f"theorem {self.name}_t_wf{k} "
                       f"{self.binders(params_nt)} :\n    {hyps}{d} := by\n"
                       f"  grind{self.ga}\n")
            thms.append((f"{self.name}_t_wf{k}", f"definedness of requires "
                         f"clause {i + 1}"))
        ens = self.task["ensures"]
        eb = params_nt + [(self.ret, self.rett)]
        for i, e in enumerate(ens):
            d = self.dcond(e, {}, self.types)
            if d is None:
                continue
            k += 1
            hyps = "".join(f"{p} → " for p in self.pre_props())
            hyps += "".join(f"{self.prop(x, {}, self.types)} → "
                            for x in ens[:i])
            out.append(f"theorem {self.name}_t_wf{k} "
                       f"{self.binders(eb)} :\n    {hyps}{d} := by\n"
                       f"  grind{self.ga}\n")
            thms.append((f"{self.name}_t_wf{k}", f"definedness of ensures "
                         f"clause {i + 1}"))
        return "\n".join(out), thms, k

    # ---------- the three shapes ----------

    def lower(self) -> str:
        header = (f"-- t task {self.name!r} -> lean4, generated by "
                  f"lower_lean.py; every verdict is the kernel's.\n")
        sf_src, sf_thms = self.emit_sfuns()
        wf_src, wf_thms, wf_k = self.emit_clause_wfs()
        body = self.body
        n_while = sum(1 for s in body if "while" in s)
        deep_while = self._has([s for s in body if "while" not in s],
                               "while")
        if n_while > 1 or deep_while:
            raise NotImplementedError(
                "only a single top-level loop is lowered for lean")
        if n_while == 1:
            if self._self_calls(body):
                raise NotImplementedError(
                    "a loop combined with self-recursion is not lowered "
                    "for lean")
            main = self.lower_loop(wf_k)
        elif self._self_calls(body):
            main = self.lower_rec()
        else:
            main = self.lower_simple()
        src, thms = main
        prints = "\n".join(
            f"#print axioms {t}" for t, _ in
            sf_thms + wf_thms + thms)
        parts = [header]
        if sf_src.strip():
            parts.append(sf_src)
        if wf_src.strip():
            parts.append(wf_src)
        parts.append(src)
        parts.append(prints + "\n")
        return "\n".join(parts)

    # SIMPLE: v0 straight-line + if bodies, and de-recursed twins.
    def lower_simple(self) -> tuple[str, list]:
        expr, obs = self.to_expr(self.body, {}, dict(self.types))
        params_nt = [(p["name"], p["type"]) for p in self.task["params"]]
        pb = self.binders(params_nt)
        pnames = " ".join(n for n, _ in params_nt)
        out = [f"def {self.name}_t {pb} : {self.lean_type(self.rett)} :=\n"
               f"  {expr}\n"]
        thms = []
        ob = self._conj(obs)
        if ob is not None:
            hyps = "".join(f"{p} → " for p in self.pre_props())
            out.append(f"theorem {self.name}_t_wfbody {pb} :\n"
                       f"    {hyps}{ob} := by\n  grind{self.ga}\n")
            thms.append((f"{self.name}_t_wfbody", "body definedness"))
        applied = f"({self.name}_t {pnames})"
        hpre = (f" (hpre : {self.pre_conj()})"
                if self.task.get("requires") else "")
        out.append(
            f"theorem {self.name}_t_spec {pb}{hpre} :\n"
            f"    {self.post_conj(applied)} := by\n"
            f"  first\n"
            f"  | (unfold {self.name}_t\n"
            f"     grind{self.ga})\n"
            f"  | grind [{self.name}_t"
            + (", " + ", ".join(f"{f}_s" for f in self.sfuns)
               if self.sfuns else "") + "]\n")
        thms.append((f"{self.name}_t_spec", "the contract"))
        return "\n".join(out), thms

    # RECURSIVE: body self-calls; requires becomes a hypothesis argument.
    def lower_rec(self) -> tuple[str, list]:
        if "decreases" not in self.task:
            raise NotImplementedError(
                "self-recursive body without a task decreases measure")
        expr, obs = self.to_expr(self.body, {}, dict(self.types))
        params_nt = [(p["name"], p["type"]) for p in self.task["params"]]
        pb = self.binders(params_nt)
        pnames = " ".join(n for n, _ in params_nt)
        has_pre = bool(self.task.get("requires"))
        hpre_def = f" (hpre : {self.pre_conj()})" if has_pre else ""
        dec = self.term(self.task["decreases"], {}, dict(self.types))
        out = [f"def {self.name}_t {pb}{hpre_def} : "
               f"{self.lean_type(self.rett)} :=\n  {expr}\n"
               f"termination_by ({dec}).toNat\n"
               f"decreasing_by all_goals (first | omega | grind)\n"]
        thms = []
        ob = self._conj(obs)
        if ob is not None:
            hyps = "".join(f"{p} → " for p in self.pre_props())
            out.append(f"theorem {self.name}_t_wfbody {pb} :\n"
                       f"    {hyps}{ob} := by\n  grind{self.ga}\n")
            thms.append((f"{self.name}_t_wfbody", "body definedness"))
        applied = (f"({self.name}_t {pnames} hpre)" if has_pre
                   else f"({self.name}_t {pnames})")
        hpre_thm = f" (hpre : {self.pre_conj()})" if has_pre else ""
        # the induction hypothesis, stated as a measure-guarded `have`: the
        # modular contract of every smaller call. (fun_induction is not used:
        # measured on gcd, grind cannot bridge the dependent proof argument
        # across arithmetic normalization; `simp only [self]` is not usable
        # inside a WF-recursive proof — the self-reference is a raw fixpoint
        # hypothesis. The guard is t's own decreases obligation: >= 0 and
        # strictly smaller.)
        primed = {p["name"]: self.fresh(p["name"])
                  for p in self.task["params"]}
        penv = dict(primed)
        pparams = " ".join(
            f"({primed[p['name']]} : {self.lean_type(p['type'])})"
            for p in self.task["params"])
        dec_p = self.term(self.task["decreases"], penv, dict(self.types))
        pre_p = " ∧ ".join(self.prop(r, penv, self.types)
                           for r in self.task.get("requires", []))
        hp = self.fresh("hpre") if has_pre else ""
        applied_p = (f"({self.name}_t {' '.join(primed.values())} {hp})"
                     if has_pre else
                     f"({self.name}_t {' '.join(primed.values())})")
        penv_post = {**penv, self.ret: applied_p}
        post_p = " ∧ ".join(self.prop(e, penv_post, self.types)
                            for e in self.task["ensures"])
        hyp_p = f" ({hp} : {pre_p})" if has_pre else ""
        fun_args = " ".join(primed.values()) + (f" {hp}" if has_pre else "")
        out.append(
            f"theorem {self.name}_t_spec {pb}{hpre_thm} :\n"
            f"    {self.post_conj(applied)} := by\n"
            f"  have _ih : ∀ {pparams}{hyp_p},\n"
            f"      (((0 : Int) ≤ ({dec_p})) ∧ (({dec_p}) < ({dec}))) →\n"
            f"      {post_p} :=\n"
            f"    fun {fun_args} _hm => {self.name}_t_spec {fun_args}\n"
            f"  rw [{self.name}_t.eq_def]\n"
            f"  repeat split\n"
            f"  all_goals grind{self.ga}\n"
            f"termination_by ({dec}).toNat\n"
            f"decreasing_by all_goals (first | omega | grind)\n")
        thms.append((f"{self.name}_t_spec", "the contract"))
        return "\n".join(out), thms

    # LOOP: one top-level while; invariants become the hypotheses of a
    # recursive helper theorem (the induction hypothesis, literally).
    def lower_loop(self, wf_k: int) -> tuple[str, list]:
        body = self.body
        idx = next(i for i, s in enumerate(body) if "while" in s)
        prefix, w, suffix = body[:idx], body[idx]["while"], body[idx + 1:]
        types = dict(self.types)
        params_nt = [(p["name"], p["type"]) for p in self.task["params"]]
        pnames = " ".join(n for n, _ in params_nt)

        # state = return var + every local declared before the loop
        state = [self.ret] + [s["var"]["name"] for s in prefix if "var" in s]
        env0, obs_pre = self.sym(prefix, {}, types, state)
        for v in state:
            if v not in env0:
                raise NotImplementedError(
                    f"state var {v!r} uninitialized before the loop")
        state_nt = [(v, types[v]) for v in state]
        sb = self.binders(state_nt)
        snames = " ".join(state)
        pb = self.binders(params_nt)

        invs = w.get("invariants", [])
        guard_p = self.prop(w["cond"], {}, types)
        guard_d = self.dcond(w["cond"], {}, types)
        env_b, obs_body = self.sym(w["body"], {}, dict(types), state)
        rec_args = " ".join(env_b.get(v, v) for v in state)
        dec = self.term(w["decreases"], {}, types)
        dec_d = self.dcond(w["decreases"], {}, types)
        if suffix:
            env_s, obs_suf = self.sym(suffix, {}, dict(types), state)
            result = env_s.get(self.ret, self.ret)
        else:
            obs_suf, result = [], self.ret

        out = [f"def {self.name}_t_loop {pb} {sb} : "
               f"{self.lean_type(self.rett)} :=\n"
               f"  if _hg : {guard_p} then\n"
               f"    {self.name}_t_loop {pnames} {rec_args}\n"
               f"  else {result}\n"
               f"termination_by ({dec}).toNat\n"
               f"decreasing_by all_goals (first | omega | grind)\n"]
        init_args = " ".join(env0[v] for v in state)
        out.append(f"def {self.name}_t {pb} : "
                   f"{self.lean_type(self.rett)} :=\n"
                   f"  {self.name}_t_loop {pnames} {init_args}\n")
        thms = []

        # program-point definedness: (context) -> obligations
        pre_hyps = self.pre_props()
        inv_props = [self.prop(iv, {}, types) for iv in invs]
        wfs = []
        for i, iv in enumerate(invs):
            d = self.dcond(iv, {}, types)
            if d is not None:
                wfs.append((pre_hyps + inv_props[:i], d,
                            f"definedness of invariant {i + 1}"))
        if guard_d is not None:
            wfs.append((pre_hyps + inv_props, guard_d,
                        "definedness of the loop guard"))
        if dec_d is not None:
            wfs.append((pre_hyps + inv_props + [guard_p], dec_d,
                        "definedness of the loop decreases"))
        ob = self._conj(obs_body)
        if ob is not None:
            wfs.append((pre_hyps + inv_props + [guard_p], ob,
                        "definedness of the loop body"))
        ob = self._conj(obs_pre)
        if ob is not None:
            wfs.append((pre_hyps, ob, "definedness before the loop"))
        ob = self._conj(obs_suf)
        if ob is not None:
            wfs.append((pre_hyps + inv_props + [f"(¬{guard_p})"], ob,
                        "definedness after the loop"))
        for hyps, obg, why in wfs:
            wf_k += 1
            binders = pb + (" " + sb if "before the loop" not in why
                            else "")
            chain = "".join(f"{h} → " for h in hyps)
            out.append(f"theorem {self.name}_t_wf{wf_k} {binders} :\n"
                       f"    {chain}{obg} := by\n  grind{self.ga}\n")
            thms.append((f"{self.name}_t_wf{wf_k}", why))

        # the helper lemma: invariants in, ensures-of-loop-value out
        has_pre = bool(pre_hyps)
        hpre = f"\n    (hpre : {self.pre_conj()})" if has_pre else ""
        hinvs = "".join(f"\n    (hinv{i + 1} : {p})"
                        for i, p in enumerate(inv_props))
        applied_loop = f"({self.name}_t_loop {pnames} {snames})"
        out.append(
            f"theorem {self.name}_t_loop_spec {pb} {sb}{hpre}{hinvs} :\n"
            f"    {self.post_conj(applied_loop)} := by\n"
            f"  rw [{self.name}_t_loop.eq_def]\n"
            f"  split\n"
            f"  · repeat split\n"
            f"    all_goals (apply {self.name}_t_loop_spec <;> "
            f"grind{self.ga})\n"
            f"  · grind{self.ga}\n"
            f"termination_by ({dec}).toNat\n"
            f"decreasing_by all_goals (first | omega | grind)\n")
        thms.append((f"{self.name}_t_loop_spec",
                     "invariants -> ensures, by induction on the loop"))

        # the contract: initial state satisfies the invariants
        init_pfs = []
        if has_pre:
            init_pfs.append("hpre")
        for iv in invs:
            if "exists" in iv:
                lo0 = self.term(iv["exists"]["lo"], env0, types)
                init_pfs.append(f"(by first | grind{self.ga} | "
                                f"exact ⟨{lo0}, by grind{self.ga}⟩)")
            else:
                init_pfs.append(f"(by grind{self.ga})")
        hpre_thm = f" (hpre : {self.pre_conj()})" if has_pre else ""
        applied = f"({self.name}_t {pnames})"
        out.append(
            f"theorem {self.name}_t_spec {pb}{hpre_thm} :\n"
            f"    {self.post_conj(applied)} := by\n"
            f"  first\n"
            f"  | (unfold {self.name}_t\n"
            f"     exact {self.name}_t_loop_spec {pnames} {init_args}\n"
            f"       " + " ".join(init_pfs) + ")\n"
            f"  | grind [{self.name}_t, {self.name}_t_loop"
            + (", " + ", ".join(f"{f}_s" for f in self.sfuns)
               if self.sfuns else "") + "]\n")
        thms.append((f"{self.name}_t_spec", "the contract"))
        return "\n".join(out), thms


def lower(task: dict, body: list) -> str:
    return Lower(task, body).lower()


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, lean_backend,
                                     "lean"))
