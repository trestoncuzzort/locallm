#!/usr/bin/env python3
"""lower_rocq.py — lower t tasks (v0 and v1) to the Rocq Prover; the fifth kernel.

v0 (`"t": 0`, frozen): unchanged from the original lowering — function,
theorem, and the uniform destruct-then-lia proof. abs/max keep their measured
behavior byte-for-byte in structure.

v1 (`"t": 1`) opens the three gates for this backend:

  MODEL. `seq` is lowered to the function+length pair (s : Z -> Z) (s_len : Z)
  with the hypothesis 0 <= s_len added to every statement in which s is in
  scope. v1 seq is opaque (param-position only; just `len` and `at`), so a
  finite sequence and such a pair are observationally identical: `at` is only
  ever *defined* inside [0, len), and every definedness obligation is emitted
  as its own lemma (Dafny-style well-formedness, discharged by the kernel,
  never silently totalized away — the `<name>_def_k` lemmas below).

  LOOPS. A while loop becomes a structural Fixpoint over nat fuel on the
  tuple of mutable state, plus one lemma proved by induction on fuel: if the
  invariants hold and `decreases < Z.of_nat fuel`, the loop's output satisfies
  the invariants and the negated guard. The fuel account needs no separate
  nonnegativity argument: with fuel 0 the hypothesis says decreases < 0, and
  the guard must then be false or the task's own decreases-nonnegative
  obligation is violated — both discharged by the same engine. The theorem
  runs the loop at fuel S (Z.to_nat decreases0), always sufficient.

  RECURSION. spec_funs and self-recursive bodies become fuel Fixpoints with a
  wrapper at fuel S (Z.to_nat measure). Per spec_fun the generator emits a
  fuel-irrelevance lemma (any fuel above the declared measure computes the
  same value — this IS the termination theorem for the declared measure) and
  the defining-equation lemma used for rewriting. A self-recursive task gets
  a fuel-indexed spec lemma by induction on fuel; the induction hypothesis is
  exactly the modular contract of the self-call (callee requires proved at the
  call site by lia, callee ensures assumed), and the fuel bound is exactly the
  decreases obligation.

  PROOFS. One engine, generic over every task: invertible structural steps,
  deterministic saturation (merge seq-application arguments lia proves equal;
  resolve implications with leaf-provable antecedents; instantiate
  forall-hypotheses at seq-application arguments — E-matching lite), guarded
  case splits (lia-undecidable antecedents; equality of two seq-application
  arguments), then a shallow goal-directed search (witnesses, disjuncts,
  f_equal, backward chaining). Every discharge ends in the kernel: lia,
  assumption, congruence. A goal the engine cannot close fails with
  "Tactic failure: unsolved t verification condition", which the adapter
  classifies REFUTED — the honest can't-prove, never a shape error.

Every file ends with `Print Assumptions`, so the axiom audit ships inside the
artifact. No Admitted, no Axiom — the adapter bans the tokens outright.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                                 # noqa: E402
from verifiers import rocq as rocq_backend     # noqa: E402

# --------------------------------------------------------------------------
# v0 path — frozen; identical to the original lowering.
# --------------------------------------------------------------------------

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


def prop0(e: dict, ret_subst: str | None, ret_name: str) -> str:
    if "int" in e:
        return str(e["int"])
    if "var" in e:
        return ret_subst if ret_subst and e["var"] == ret_name else e["var"]
    op = e["op"]
    args = [prop0(a, ret_subst, ret_name) for a in e.get("args", [])]
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


def cond_bool0(e: dict) -> str:
    op = e.get("op")
    if op in BOOL_CMP:
        a, b = (prop0(x, None, "") for x in e["args"])
        return f"({a} {BOOL_CMP[op]} {b})"
    if op == ">":
        b, a = (prop0(x, None, "") for x in e["args"])
        return f"({a} <? {b})"
    if op == ">=":
        b, a = (prop0(x, None, "") for x in e["args"])
        return f"({a} <=? {b})"
    raise ValueError(f"t v0 -> rocq: no boolean form for condition {op!r}")


def body_expr0(body: list, ret: str) -> str:
    if len(body) == 1 and "assign" in body[0]:
        name, e = body[0]["assign"]
        assert name == ret, f"assign to {name}, expected {ret}"
        return prop0(e, None, "")
    if len(body) == 1 and "if" in body[0]:
        c = body[0]["if"]
        return (f"if {cond_bool0(c['cond'])} then {body_expr0(c['then'], ret)} "
                f"else {body_expr0(c['else'], ret)}")
    raise ValueError("t v0 -> rocq: body not expressible as one expression")


def lower_v0(task: dict, body: list) -> str:
    name, ret = task["name"], task["returns"][0]["name"]
    params = " ".join(p["name"] for p in task["params"])
    binder = " ".join(f"({p['name']} : Z)" for p in task["params"])
    applied = f"({name}_t {params})"
    post = " /\\ ".join(prop0(e, applied, ret) for e in task["ensures"])
    pre = " /\\ ".join(prop0(e, applied, ret) for e in task.get("requires", []))
    stmt = f"{pre} -> {post}" if pre else post
    return (
        "From Stdlib Require Import ZArith Lia.\n"
        "Open Scope Z_scope.\n\n"
        f"Definition {name}_t {binder} : Z := {body_expr0(body, ret)}.\n\n"
        f"Theorem {name}_t_spec : forall {binder}, {stmt}.\n"
        "Proof.\n"
        + TACTIC.format(name=name) +
        "Qed.\n\n"
        f"Print Assumptions {name}_t_spec.\n")


# --------------------------------------------------------------------------
# v1 — shared tactic prelude (validated piece by piece against coqc 9.2
# before this generator existed; see the session's proto files).
# --------------------------------------------------------------------------

PRELUDE = r"""(* persistent resolution marker: survives destruction of what it records *)
Inductive t_done (P : Prop) : Prop := t_done_intro : t_done P.

Ltac t_leaf := solve [ lia | assumption | congruence | discriminate | (exfalso; lia) ].

(* succeeds iff some hypothesis has exactly type T *)
Ltac t_have T := match goal with H2 : ?T2 |- _ => constr_eq T T2 end.

(* succeeds iff t is a Z numeral literal *)
Ltac t_numeral t :=
  lazymatch t with
  | Z0 => idtac
  | Zpos _ => idtac
  | Zneg _ => idtac
  | _ => fail
  end.

(* replace u with v everywhere, provided lia proves them equal, oriented so a
   numeral is never the term being replaced *)
Ltac t_merge a b :=
  first
  [ tryif (t_numeral b) then fail else idtac; replace b with a in * by lia
  | tryif (t_numeral a) then fail else idtac; replace a with b in * by lia
  ].

(* invertible structural steps *)
Ltac t_inv1 :=
  match goal with
  | H : False |- _ => destruct H
  | H : _ /\ _ |- _ => destruct H
  | H : exists _, _ |- _ => destruct H
  | H : _ <-> _ |- _ => destruct H
  | H : _ \/ _ |- _ => destruct H
  | |- _ /\ _ => split
  | |- _ <-> _ => split
  | |- forall _, _ => intro
  | |- _ -> _ => intro
  | |- not _ => intro
  | |- context [?a <? ?b] => destruct (Z.ltb_spec a b)
  | |- context [?a <=? ?b] => destruct (Z.leb_spec a b)
  | |- context [?a =? ?b] => destruct (Z.eqb_spec a b)
  | |- context [Bool.eqb ?a ?b] => destruct (Bool.eqb_spec a b)
  | |- context [orb _ _] => progress (cbn [orb andb negb])
  | |- context [andb _ _] => progress (cbn [orb andb negb])
  | |- context [negb _] => progress (cbn [orb andb negb])
  | |- context [if true then _ else _] => progress (cbn [orb andb negb])
  | |- context [if false then _ else _] => progress (cbn [orb andb negb])
  | _ => progress subst
  end.

(* deterministic saturation steps *)
Ltac t_sat1 :=
  match goal with
  (* merge var-headed application args that lia proves equal *)
  | H : context [?f ?a] |- context [?f ?b] =>
      is_var f; tryif (constr_eq a b) then fail else idtac; t_merge a b
  | H1 : context [?f ?a], H2 : context [?f ?b] |- _ =>
      is_var f; tryif (constr_eq a b) then fail else idtac; t_merge a b
  | |- context [?f ?a] =>
      is_var f;
      match goal with
      | |- context [?g ?b] =>
          constr_eq f g;
          tryif (constr_eq a b) then fail else idtac; t_merge a b
      end
  (* merge two Z variables lia proves equal: aligns nonlinear atoms (e.g.
     i'*(i'+1) with n*(n+1) once i' = n) that no linear step can relate *)
  | x : Z, y : Z |- _ =>
      tryif (constr_eq x y) then fail else idtac;
      replace x with y in * by lia
  (* resolve an implication whose antecedent is leaf-provable; keep H, pose B,
     and mark the implication done so re-destruction cannot re-fire it *)
  | H : ?A -> ?B |- _ =>
      tryif (t_have constr:(t_done (A -> B))) then fail else idtac;
      let D := fresh "D" in
      assert (D : A) by t_leaf;
      pose proof (t_done_intro (A -> B));
      pose proof (H D); clear D
  (* instantiate forall-hyps at args of var-headed applications (E-matching
     lite: the relevant terms are the indices at which a seq is inspected) *)
  | H : forall _ : Z, _ |- context [?f ?x] =>
      is_var f;
      let I := constr:(H x) in
      let T := type of I in
      tryif (t_have T) then fail else idtac;
      pose proof I
  | H : forall _ : Z, _, H2 : context [?f ?x] |- _ =>
      is_var f;
      let I := constr:(H x) in
      let T := type of I in
      tryif (t_have T) then fail else idtac;
      pose proof I
  end.

(* case-splitting saturation steps (kept last; each is presence-guarded) *)
Ltac t_split1 :=
  match goal with
  (* decide an arithmetic antecedent that lia cannot settle outright *)
  | H : ?A -> ?B |- _ =>
      tryif (t_have constr:(t_done (A -> B))) then fail else idtac;
      tryif (t_have constr:(~ A)) then fail else idtac;
      pose proof (t_done_intro (A -> B));
      let D := fresh "D" in
      assert (D : A \/ ~ A) by lia;
      destruct D as [D|D]; [ pose proof (H D); clear D | idtac ]
  (* decide equality of two var-headed application args (seq congruence);
     on the equal branch eliminate the variable side, never a numeral *)
  | H1 : context [?f ?a], H2 : context [?f ?b] |- _ =>
      is_var f;
      tryif (constr_eq a b) then fail else idtac;
      tryif (t_have constr:(a <> b)) then fail else idtac;
      tryif (t_have constr:(b <> a)) then fail else idtac;
      tryif (assert (a = b) by lia) then fail else idtac;
      tryif (assert (a <> b) by lia) then fail else idtac;
      let D := fresh "D" in
      assert (D : a = b \/ a <> b) by lia;
      destruct D as [D|D];
      [ first [ (is_var b; rewrite <- D in * ) | (is_var a; rewrite D in * ) | idtac ]
      | idtac ]
  | H1 : context [?f ?a] |- context [?f ?b] =>
      is_var f;
      tryif (constr_eq a b) then fail else idtac;
      tryif (t_have constr:(a <> b)) then fail else idtac;
      tryif (t_have constr:(b <> a)) then fail else idtac;
      tryif (assert (a = b) by lia) then fail else idtac;
      tryif (assert (a <> b) by lia) then fail else idtac;
      let D := fresh "D" in
      assert (D : a = b \/ a <> b) by lia;
      destruct D as [D|D];
      [ first [ (is_var b; rewrite <- D in * ) | (is_var a; rewrite D in * ) | idtac ]
      | idtac ]
  | |- context [?f ?a] =>
      is_var f;
      match goal with
      | |- context [?g ?b] =>
          constr_eq f g;
          tryif (constr_eq a b) then fail else idtac;
          tryif (t_have constr:(a <> b)) then fail else idtac;
          tryif (t_have constr:(b <> a)) then fail else idtac;
          tryif (assert (a = b) by lia) then fail else idtac;
          tryif (assert (a <> b) by lia) then fail else idtac;
          let D := fresh "D" in
          assert (D : a = b \/ a <> b) by lia;
          destruct D as [D|D];
          [ first [ (is_var b; rewrite <- D in * ) | (is_var a; rewrite D in * ) | idtac ]
          | idtac ]
      end
  end.

(* the leading lia closes contradictory contexts before the merge rules can
   see them — with False in scope lia proves any equality, and an equality
   merge under False would replace terms back and forth forever *)
Ltac t_base := repeat (first [ solve [ lia ] | t_inv1 | t_sat1 | t_split1 ]).

(* goal-directed shallow search *)
Ltac t_go n :=
  t_base;
  first
  [ t_leaf
  | lazymatch n with
    | O => fail
    | S ?m =>
      first
      [ lazymatch goal with
        | |- exists _ : Z, _ =>
            first [ exists 0; t_go m
                  | multimatch goal with x : Z |- _ => exists x; t_go m end ]
        end
      | lazymatch goal with
        | |- _ \/ _ => first [ left; t_go m | right; t_go m ]
        end
      | lazymatch goal with
        | |- _ = _ => progress f_equal; t_go m
        end
      | multimatch goal with
        | H : _ |- _ => solve [ apply H; t_go m ]
        end
      ]
    end
  ].

Ltac t_vc0 := solve [ t_go 6%nat ].

Ltac t_sweep :=
  repeat (match goal with
          | |- context [?a <? ?b] => destruct (Z.ltb_spec a b)
          | |- context [?a <=? ?b] => destruct (Z.leb_spec a b)
          | |- context [?a =? ?b] => destruct (Z.eqb_spec a b)
          | |- context [Bool.eqb ?a ?b] => destruct (Bool.eqb_spec a b)
          | _ => progress (cbn [orb andb negb])
          end).
"""

# emitted after the spec_fun section, since t_eqs names their equation lemmas
POST_SF = r"""Ltac t_dis := first [ solve [ t_vc0 ] | solve [ t_eqs; t_vc0 ] ]
              || fail "unsolved t verification condition".
Ltac t_side := first [ assumption | solve [ lia ]
                     | solve [ t_vc0 ] | solve [ t_eqs; t_vc0 ] ].
"""

RESERVED = {"at", "in", "fun", "if", "then", "else", "let", "forall", "exists",
            "match", "with", "end", "fix", "Prop", "Set", "Type", "fuel", "fu",
            "s_len"}


def _ck(name: str) -> str:
    if name in RESERVED or name.endswith("_len") or name.startswith("sf_"):
        raise NotImplementedError(
            f"rocq lowering: identifier {name!r} collides with the lowering's "
            f"namespace")
    return name


class Ctx:
    """Expression lowering context for one task."""

    def __init__(self, task: dict):
        self.task = task
        self.tys: dict[str, str] = {}
        for p in task["params"]:
            self.tys[_ck(p["name"])] = p["type"]
        for r in task["returns"]:
            self.tys[_ck(r["name"])] = r["type"]
        self.sfres: dict[str, str] = {}
        self.sfparams: dict[str, list] = {}
        for sf in task.get("spec_funs", []):
            self.sfres[sf["name"]] = sf["result"]
            self.sfparams[sf["name"]] = sf["params"]
        self.sfres[task["name"]] = task["returns"][0]["type"]
        self.sfparams[task["name"]] = task["params"]
        # how to render a call to `fun`: fname -> prefix string; the callee's
        # args are appended. Defaults set by the shapes.
        self.callpre: dict[str, str] = {
            f: f"sf_{f}" for f in self.sfres if f != task["name"]}

    def ty(self, e: dict, local: dict[str, str]) -> str:
        if "int" in e:
            return "int"
        if "bool" in e:
            return "bool"
        if "var" in e:
            return local.get(e["var"]) or self.tys[e["var"]]
        if "forall" in e or "exists" in e:
            return "bool"
        if "ite" in e:
            return self.ty(e["ite"]["then"], local)
        if "call" in e:
            return self.sfres[e["call"]["fun"]]
        op = e["op"]
        if op in ("+", "-", "*", "neg", "len", "at"):
            return "int"
        return "bool"

    # -- rendering helpers ------------------------------------------------
    def seq_fn(self, e: dict, env: dict) -> tuple[str, str]:
        assert "var" in e, "t v1: seq values are parameters, not expressions"
        v = e["var"]
        assert (self.tys.get(v) == "seq"), f"{v} is not a seq"
        return v, f"{v}_len"

    def call(self, e: dict, env: dict, local: dict) -> str:
        c = e["call"]
        f, args = c["fun"], c["args"]
        parts = [self.callpre[f]]
        for formal, a in zip(self.sfparams[f], args, strict=True):
            if formal["type"] == "seq":
                fn, ln = self.seq_fn(a, env)
                parts += [fn, ln]
            elif formal["type"] == "bool":
                parts.append(self.bx(a, env, local))
            else:
                parts.append(self.zx(a, env, local))
        return "(" + " ".join(parts) + ")"

    def zx(self, e: dict, env: dict, local: dict) -> str:
        if "int" in e:
            n = e["int"]
            return f"({n})" if n < 0 else str(n)
        if "var" in e:
            return env.get(e["var"], e["var"])
        if "ite" in e:
            c = e["ite"]
            return (f"(if {self.bx(c['cond'], env, local)} "
                    f"then {self.zx(c['then'], env, local)} "
                    f"else {self.zx(c['else'], env, local)})")
        if "call" in e:
            return self.call(e, env, local)
        op = e.get("op")
        if op == "len":
            return self.seq_fn(e["args"][0], env)[1]
        if op == "at":
            fn, _ = self.seq_fn(e["args"][0], env)
            return f"({fn} {self.zx(e['args'][1], env, local)})"
        if op == "neg":
            return f"(- {self.zx(e['args'][0], env, local)})"
        if op in ("+", "-", "*"):
            a, b = (self.zx(x, env, local) for x in e["args"])
            return f"({a} {op} {b})"
        raise ValueError(f"t v1 -> rocq: not an int expression: {op!r}")

    def bx(self, e: dict, env: dict, local: dict) -> str:
        if "bool" in e:
            return "true" if e["bool"] else "false"
        if "var" in e:
            return env.get(e["var"], e["var"])
        if "ite" in e:
            c = e["ite"]
            return (f"(if {self.bx(c['cond'], env, local)} "
                    f"then {self.bx(c['then'], env, local)} "
                    f"else {self.bx(c['else'], env, local)})")
        if "call" in e:
            return self.call(e, env, local)
        if "forall" in e or "exists" in e:
            raise NotImplementedError(
                "rocq lowering: a quantifier in computational position has no "
                "decidable lowering here")
        op = e["op"]
        if op in ("<", "<="):
            a, b = (self.zx(x, env, local) for x in e["args"])
            return f"({a} {'<?' if op == '<' else '<=?'} {b})"
        if op in (">", ">="):
            a, b = (self.zx(x, env, local) for x in e["args"])
            return f"({b} {'<?' if op == '>' else '<=?'} {a})"
        if op in ("==", "!="):
            t = self.ty(e["args"][0], local)
            if t == "bool":
                a, b = (self.bx(x, env, local) for x in e["args"])
                core = f"(Bool.eqb {a} {b})"
            else:
                a, b = (self.zx(x, env, local) for x in e["args"])
                core = f"({a} =? {b})"
            return core if op == "==" else f"(negb {core})"
        if op == "not":
            return f"(negb {self.bx(e['args'][0], env, local)})"
        if op == "and":
            return "(" + " && ".join(self.bx(x, env, local)
                                     for x in e["args"]) + ")%bool"
        if op == "or":
            return "(" + " || ".join(self.bx(x, env, local)
                                     for x in e["args"]) + ")%bool"
        if op == "implies":
            a, b = (self.bx(x, env, local) for x in e["args"])
            return f"((negb {a}) || {b})%bool"
        raise ValueError(f"t v1 -> rocq: not a bool expression: {op!r}")

    def prop(self, e: dict, env: dict, local: dict | None = None) -> str:
        local = local or {}
        if "bool" in e:
            return "True" if e["bool"] else "False"
        if "var" in e:
            t = local.get(e["var"]) or self.tys[e["var"]]
            term = env.get(e["var"], e["var"])
            return f"({term} = true)" if t == "bool" else term
        if "forall" in e or "exists" in e:
            q = e.get("forall") or e.get("exists")
            v = q["var"]
            lo = self.zx(q["lo"], env, local)
            hi = self.zx(q["hi"], env, local)
            # the bound variable shadows anything outside it: strip it from
            # the substitution env so no outer term leaks under the binder
            env2 = {k: t for k, t in env.items() if k != v}
            local2 = dict(local, **{v: "int"})
            body = self.prop(q["body"], env2, local2)
            if "forall" in e:
                return f"(forall {v} : Z, {lo} <= {v} < {hi} -> {body})"
            return f"(exists {v} : Z, {lo} <= {v} < {hi} /\\ {body})"
        if "ite" in e:
            c = e["ite"]
            cp = self.prop(c["cond"], env, local)
            return (f"(({cp} /\\ {self.prop(c['then'], env, local)}) "
                    f"\\/ (~ {cp} /\\ {self.prop(c['else'], env, local)}))")
        if "call" in e:
            return f"({self.call(e, env, local)} = true)"
        op = e["op"]
        if op == "not":
            return f"(~ {self.prop(e['args'][0], env, local)})"
        if op == "and":
            return "(" + " /\\ ".join(self.prop(x, env, local)
                                      for x in e["args"]) + ")"
        if op == "or":
            return "(" + " \\/ ".join(self.prop(x, env, local)
                                      for x in e["args"]) + ")"
        if op == "implies":
            a, b = (self.prop(x, env, local) for x in e["args"])
            return f"({a} -> {b})"
        if op in ("==", "!="):
            t = self.ty(e["args"][0], local)
            if t == "bool":
                a, b = (self.prop(x, env, local) for x in e["args"])
                return (f"({a} <-> {b})" if op == "=="
                        else f"(~ ({a} <-> {b}))")
            a, b = (self.zx(x, env, local) for x in e["args"])
            return f"({a} = {b})" if op == "==" else f"({a} <> {b})"
        if op in ("<", "<=", ">", ">="):
            a, b = (self.zx(x, env, local) for x in e["args"])
            return f"({a} {op} {b})"
        raise ValueError(f"t v1 -> rocq: not a spec expression: {op!r}")

    # -- definedness obligations ------------------------------------------
    def defs(self, e: dict, ctx: list[str], binders: list[str],
             acc: list, env: dict, local: dict) -> None:
        """Collect (binders, hyps, idx, len) for every `at` in e, honoring the
        SPEC's left-to-right / taken-branch definedness rules."""
        if "int" in e or "bool" in e or "var" in e:
            return
        if "forall" in e or "exists" in e:
            q = e.get("forall") or e.get("exists")
            v = q["var"]
            self.defs(q["lo"], ctx, binders, acc, env, local)
            self.defs(q["hi"], ctx, binders, acc, env, local)
            lo = self.zx(q["lo"], env, local)
            hi = self.zx(q["hi"], env, local)
            env2 = {k: t for k, t in env.items() if k != v}
            local2 = dict(local, **{v: "int"})
            self.defs(q["body"], ctx + [f"({lo} <= {v} < {hi})"],
                      binders + [f"({v} : Z)"], acc, env2, local2)
            return
        if "ite" in e:
            c = e["ite"]
            self.defs(c["cond"], ctx, binders, acc, env, local)
            cp = self.prop(c["cond"], env, local)
            self.defs(c["then"], ctx + [cp], binders, acc, env, local)
            self.defs(c["else"], ctx + [f"(~ {cp})"], binders, acc, env, local)
            return
        if "call" in e:
            for a in e["call"]["args"]:
                self.defs(a, ctx, binders, acc, env, local)
            return
        op = e["op"]
        if op == "at":
            self.defs(e["args"][1], ctx, binders, acc, env, local)
            fn, ln = self.seq_fn(e["args"][0], env)
            acc.append((list(binders), list(ctx),
                        self.zx(e["args"][1], env, local), ln))
            return
        if op == "len":
            return
        if op in ("and", "or"):
            path = list(ctx)
            for a in e["args"]:
                self.defs(a, path, binders, acc, env, local)
                p = self.prop(a, env, local)
                path = path + ([p] if op == "and" else [f"(~ {p})"])
            return
        if op == "implies":
            a, b = e["args"]
            self.defs(a, ctx, binders, acc, env, local)
            self.defs(b, ctx + [self.prop(a, env, local)], binders, acc,
                      env, local)
            return
        for a in e.get("args", []):
            self.defs(a, ctx, binders, acc, env, local)


# --------------------------------------------------------------------------
# statement-level symbolic execution
# --------------------------------------------------------------------------

def has_self_call(node, name: str) -> bool:
    if isinstance(node, dict):
        if "call" in node and node["call"].get("fun") == name:
            return True
        return any(has_self_call(v, name) for v in node.values())
    if isinstance(node, list):
        return any(has_self_call(v, name) for v in node)
    return False


def find_while(body: list):
    """Return (prefix, while_stmt, suffix) if exactly one top-level while and
    none nested anywhere else; (body, None, []) if no while at all."""
    def any_while(stmts):
        for s in stmts:
            if "while" in s:
                return True
            if "if" in s and (any_while(s["if"]["then"])
                              or any_while(s["if"]["else"])):
                return True
        return False

    idxs = [k for k, s in enumerate(body) if "while" in s]
    for s in body:
        if "if" in s and (any_while(s["if"]["then"])
                          or any_while(s["if"]["else"])):
            raise NotImplementedError(
                "rocq lowering: a loop under a conditional is not lowered yet")
    if not idxs:
        return body, None, []
    if len(idxs) > 1:
        raise NotImplementedError(
            "rocq lowering: more than one loop per body is not lowered yet")
    k = idxs[0]
    w = body[k]["while"]
    if any_while(w["body"]):
        raise NotImplementedError(
            "rocq lowering: nested loops are not lowered yet")
    return body[:k], w, body[k + 1:]


def exec_straight(cx: Ctx, stmts: list, env: dict, local: dict,
                  defs_ctx: list[str] | None, defs_binders: list[str],
                  acc: list) -> dict:
    """Symbolic execution of straight-line + if statements. env maps mutable
    var -> term; local maps locals -> type (also recorded in cx.tys). When
    defs_ctx is not None, definedness obligations are collected along the
    path conditions."""
    env = dict(env)
    for s in stmts:
        if "assign" in s:
            v, e = s["assign"]
            assert v in env, f"assign to undeclared {v}"
            t = local.get(v) or cx.tys[v]
            if defs_ctx is not None:
                cx.defs(e, defs_ctx, defs_binders, acc, env, local)
            env[v] = (cx.bx(e, env, local) if t == "bool"
                      else cx.zx(e, env, local))
        elif "var" in s:
            d = s["var"]
            v = _ck(d["name"])
            assert v not in cx.tys and v not in local, f"redeclared {v}"
            local[v] = d["type"]
            cx.tys[v] = d["type"]
            if defs_ctx is not None:
                cx.defs(d["init"], defs_ctx, defs_binders, acc, env, local)
            env[v] = (cx.bx(d["init"], env, local) if d["type"] == "bool"
                      else cx.zx(d["init"], env, local))
        elif "if" in s:
            c = s["if"]
            if defs_ctx is not None:
                cx.defs(c["cond"], defs_ctx, defs_binders, acc, env, local)
            cp = cx.prop(c["cond"], env, local)
            cb = cx.bx(c["cond"], env, local)
            env_t = exec_straight(
                cx, c["then"], env, local,
                None if defs_ctx is None else defs_ctx + [cp],
                defs_binders, acc)
            env_e = exec_straight(
                cx, c["else"], env, local,
                None if defs_ctx is None else defs_ctx + [f"(~ {cp})"],
                defs_binders, acc)
            for v in env:
                if env_t.get(v, env[v]) != env_e.get(v, env[v]):
                    env[v] = (f"(if {cb} then {env_t[v]} else {env_e[v]})")
                else:
                    env[v] = env_t.get(v, env[v])
        elif "while" in s:
            raise AssertionError("while must be split out before exec")
        else:
            raise ValueError(f"t v1 -> rocq: no statement {list(s)!r}")
    return env


# --------------------------------------------------------------------------
# v1 code generation
# --------------------------------------------------------------------------

def param_binders(cx: Ctx) -> tuple[str, str]:
    """(binder text, arg text) with seq expanded to fn+len."""
    bs, args = [], []
    for p in cx.task["params"]:
        v = p["name"]
        if p["type"] == "seq":
            bs.append(f"({v} : Z -> Z) ({v}_len : Z)")
            args += [v, f"{v}_len"]
        elif p["type"] == "bool":
            bs.append(f"({v} : bool)")
            args.append(v)
        else:
            bs.append(f"({v} : Z)")
            args.append(v)
    return " ".join(bs), " ".join(args)


def len_hyps(cx: Ctx) -> list[str]:
    return [f"(0 <= {p['name']}_len)" for p in cx.task["params"]
            if p["type"] == "seq"]


def rty(t: str) -> str:
    return "bool" if t == "bool" else "Z"


def emit_def_lemmas(cx: Ctx, name: str, obls: list, extra_binders: str = "",
                    counter: list | None = None) -> str:
    out = []
    counter = counter if counter is not None else [0]
    pb, _ = param_binders(cx)
    for binders, hyps, idx, ln in obls:
        counter[0] += 1
        k = counter[0]
        allb = " ".join(x for x in [pb, extra_binders, " ".join(binders)] if x)
        hs = len_hyps(cx) + hyps
        hyp_txt = "".join(f"  {h} ->\n" for h in hs)
        out.append(
            f"Lemma {name}_def_{k} : forall {allb},\n{hyp_txt}"
            f"  (0 <= {idx} < {ln}).\n"
            f"Proof. intros. t_dis. Qed.\n")
    return "\n".join(out)


def emit_spec_funs(cx: Ctx) -> str:
    """Fuel fixpoint + wrapper + irrelevance + equation lemma per spec_fun,
    plus t_eqs. Also collects definedness lemmas for spec_fun bodies."""
    task = cx.task
    chunks = []
    eqs = []
    counter = [0]
    for sf in task.get("spec_funs", []):
        f = sf["name"]
        res = rty(sf["result"])
        default = "false" if sf["result"] == "bool" else "0"
        # binders for the spec_fun's own params
        bs, args = [], []
        sf_tys = {}
        for p in sf["params"]:
            v = p["name"]
            sf_tys[v] = p["type"]
            if p["type"] == "seq":
                bs.append(f"({v} : Z -> Z) ({v}_len : Z)")
                args += [v, f"{v}_len"]
            else:
                bs.append(f"({v} : {rty(p['type'])})")
                args.append(v)
        btxt, atxt = " ".join(bs), " ".join(args)

        # body lowering: inside the fixpoint, self-calls use fuel `fu`
        saved_tys = dict(cx.tys)
        cx.tys.update(sf_tys)
        saved_pre = dict(cx.callpre)
        cx.callpre[f] = f"sf_{f}_fuel fu"
        body_fuel = (cx.bx(sf["body"], {}, {}) if sf["result"] == "bool"
                     else cx.zx(sf["body"], {}, {}))
        cx.callpre[f] = f"sf_{f}"
        body_plain = (cx.bx(sf["body"], {}, {}) if sf["result"] == "bool"
                      else cx.zx(sf["body"], {}, {}))
        measure = cx.zx(sf["decreases"], {}, {})
        sf_lens = [f"(0 <= {p['name']}_len)" for p in sf["params"]
                   if p["type"] == "seq"]

        # definedness obligations of the spec_fun body under its own path
        # conditions; the lemmas are emitted later, once t_dis exists
        obls: list = []
        cx.defs(sf["body"], [], [], obls, {}, {})
        cx._sf_obls = getattr(cx, "_sf_obls", [])
        for binders, hyps, idx, ln in obls:
            cx._sf_obls.append((f, btxt, sf_lens, binders, hyps, idx, ln))

        chunks.append(f"""Fixpoint sf_{f}_fuel (fuel : nat) {btxt} : {res} :=
  match fuel with
  | O => {default}
  | S fu => {body_fuel}
  end.

Definition sf_{f} {btxt} : {res} :=
  sf_{f}_fuel (S (Z.to_nat {measure})) {atxt}.

Lemma sf_{f}_fuel_irrel :
  forall (fuel fuel' : nat) {btxt},
  (Z.to_nat {measure} < fuel)%nat -> (Z.to_nat {measure} < fuel')%nat ->
  sf_{f}_fuel fuel {atxt} = sf_{f}_fuel fuel' {atxt}.
Proof.
  induction fuel as [|fu IH]; intros fuel' {atxt} Hf Hf'; [ lia | ].
  destruct fuel' as [|fu']; [ lia | ].
  simpl; t_sweep;
  repeat first [ reflexivity
               | solve [ lia ]
               | solve [ apply IH; lia ]
               | f_equal ].
  all: fail "unsolved t verification condition".
Qed.

Lemma sf_{f}_eq :
  forall {btxt},
  sf_{f} {atxt} = {body_plain}.
Proof.
  intros; unfold sf_{f} at 1; simpl; t_sweep;
  repeat first [ reflexivity
               | solve [ lia ]
               | solve [ unfold sf_{f}; apply sf_{f}_fuel_irrel; lia ]
               | f_equal ].
  all: fail "unsolved t verification condition".
Qed.
""")
        eqs.append(f"sf_{f}_eq")
        cx.tys = saved_tys
        cx.callpre = saved_pre
        cx.callpre[f] = f"sf_{f}"

    if eqs:
        eq_tac = " ".join(f"try rewrite {e};" for e in eqs)
        chunks.append(f"Ltac t_eqs := {eq_tac} idtac.\n")
    else:
        chunks.append("Ltac t_eqs := idtac.\n")
    return "\n".join(chunks)


def emit_sf_def_lemmas(cx: Ctx, counter: list) -> str:
    """Definedness lemmas for spec_fun bodies (emitted after t_dis exists)."""
    out = []
    for f, btxt, sf_lens, binders, hyps, idx, ln in getattr(cx, "_sf_obls", []):
        counter[0] += 1
        k = counter[0]
        allb = " ".join(x for x in [btxt, " ".join(binders)] if x)
        hs = sf_lens + hyps
        hyp_txt = "".join(f"  {h} ->\n" for h in hs)
        out.append(
            f"Lemma {cx.task['name']}_def_{k} : forall {allb},\n{hyp_txt}"
            f"  (0 <= {idx} < {ln}).\n"
            f"Proof. intros. t_dis. Qed.\n")
    return "\n".join(out)


def spec_def_obls(cx: Ctx) -> tuple[list, list]:
    """Definedness obligations for requires and ensures (r universally
    quantified). Returns (req_obls, ens_obls)."""
    task = cx.task
    req_obls: list = []
    ctx: list[str] = []
    for e in task.get("requires", []):
        cx.defs(e, list(ctx), [], req_obls, {}, {})
        ctx.append(cx.prop(e, {}))
    ens_obls: list = []
    ectx = list(ctx)
    for e in task["ensures"]:
        cx.defs(e, list(ectx), [], ens_obls, {}, {})
        ectx.append(cx.prop(e, {}))
    return req_obls, ens_obls


def ensures_text(cx: Ctx, ret_term: str) -> str:
    task = cx.task
    ret = task["returns"][0]["name"]
    env = {ret: ret_term}
    return " /\\ ".join(cx.prop(e, env) for e in task["ensures"])


def requires_arrows(cx: Ctx) -> str:
    return "".join(f"  {cx.prop(e, {})} ->\n"
                   for e in cx.task.get("requires", []))


def lens_arrows(cx: Ctx) -> str:
    return "".join(f"  {h} ->\n" for h in len_hyps(cx))


def header() -> str:
    return ("From Stdlib Require Import ZArith Bool Lia.\n"
            "Open Scope Z_scope.\n\n" + PRELUDE + "\n")


def lower_v1(task: dict, body: list) -> str:
    cx = Ctx(task)
    name = task["name"]
    ret = task["returns"][0]["name"]
    ret_t = task["returns"][0]["type"]
    pb, pargs = param_binders(cx)

    prefix, w, suffix = find_while(body)
    selfrec = has_self_call(body, name)
    if w is not None and selfrec:
        raise NotImplementedError(
            "rocq lowering: a body that both loops and self-recurses is not "
            "lowered yet")

    parts = [header()]
    parts.append(emit_spec_funs(cx))
    parts.append(POST_SF + "\n")

    counter = [0]
    parts.append(emit_sf_def_lemmas(cx, counter))
    req_obls, ens_obls = spec_def_obls(cx)
    parts.append(emit_def_lemmas(cx, name, req_obls, counter=counter))
    rb = f"({ret} : {rty(ret_t)})"
    parts.append(emit_def_lemmas(cx, name, ens_obls, extra_binders=rb,
                                 counter=counter))

    if w is not None:
        parts.append(gen_loop(cx, prefix, w, suffix, counter))
    elif selfrec:
        parts.append(gen_rec(cx, body))
    else:
        parts.append(gen_plain(cx, body, counter))

    parts.append(f"\nPrint Assumptions {name}_t_spec.\n")
    return "\n".join(p for p in parts if p)


def gen_plain(cx: Ctx, body: list, counter: list) -> str:
    """Straight-line/if body, no loop, no self-call."""
    task = cx.task
    name = task["name"]
    ret = task["returns"][0]["name"]
    ret_t = task["returns"][0]["type"]
    pb, pargs = param_binders(cx)

    local: dict[str, str] = {}
    env0 = {ret: None}
    obls: list = []
    reqs = [cx.prop(e, {}) for e in task.get("requires", [])]
    env0[ret] = "false" if ret_t == "bool" else "0"
    env = exec_straight(cx, body, env0, local, list(reqs), [], obls)
    expr = env[ret]
    def_txt = emit_def_lemmas(cx, name, obls, counter=counter)

    ens = ensures_text(cx, f"({name}_t {pargs})")
    return f"""{def_txt}
Definition {name}_t {pb} : {rty(ret_t)} := {expr}.

Theorem {name}_t_spec :
  forall {pb},
{lens_arrows(cx)}{requires_arrows(cx)}  {ens}.
Proof.
  intros.
  unfold {name}_t.
  t_dis.
Qed.
"""


def gen_loop(cx: Ctx, prefix: list, w: dict, suffix: list,
             counter: list) -> str:
    task = cx.task
    name = task["name"]
    ret = task["returns"][0]["name"]
    ret_t = task["returns"][0]["type"]
    pb, pargs = param_binders(cx)
    reqs = [cx.prop(e, {}) for e in task.get("requires", [])]

    # prefix symbolic execution (definedness under requires)
    local: dict[str, str] = {}
    obls: list = []
    env0 = {ret: "false" if ret_t == "bool" else "0"}
    env_pre = exec_straight(cx, prefix, env0, local, list(reqs), [], obls)

    # state variables: return + locals declared in the prefix, in order
    svars = [ret] + [s["var"]["name"] for s in prefix if "var" in s]
    stys = {v: (local.get(v) or cx.tys[v]) for v in svars}
    id_env = {v: v for v in svars}

    guard_b = cx.bx(w["cond"], id_env, local)
    guard_p = cx.prop(w["cond"], id_env, local)
    dec = cx.zx(w["decreases"], id_env, local)
    invs = [cx.prop(e, id_env, local) for e in w.get("invariants", [])]

    # invariant definedness: each invariant assumes requires + earlier ones
    inv_ctx = list(reqs)
    sb = " ".join(f"({v} : {rty(stys[v])})" for v in svars)
    for e in w.get("invariants", []):
        iob: list = []
        cx.defs(e, list(inv_ctx), [], iob, id_env, local)
        obls += [(b, h, i, l) for (b, h, i, l) in iob]
        inv_ctx.append(cx.prop(e, id_env, local))
    # guard + decreases definedness under requires + invariants
    gob: list = []
    cx.defs(w["cond"], list(inv_ctx), [], gob, id_env, local)
    cx.defs(w["decreases"], list(inv_ctx), [], gob, id_env, local)
    obls += gob
    # loop body: definedness under requires + invariants + guard
    body_ctx = inv_ctx + [guard_p]
    step_env = exec_straight(cx, w["body"], id_env, dict(local),
                             list(body_ctx), [], obls)
    step_terms = " ".join(step_env[v] for v in svars)

    # suffix (after the loop): requires + invariants + ~guard
    post_ctx = inv_ctx + [f"(~ {guard_p})"]
    env_post = exec_straight(cx, suffix, id_env, dict(local),
                             list(post_ctx), [], obls)
    result_term = env_post[ret]

    # the state-var definedness lemmas quantify over the state
    def_txt = emit_def_lemmas(cx, name, obls, extra_binders=sb,
                              counter=counter)

    tup_ty = "(" + " * ".join(rty(stys[v]) for v in svars) + ")%type"
    tup = "(" + ", ".join(svars) + ")"
    primed = [v + "'" for v in svars]
    tup_p = "(" + ", ".join(primed) + ")"
    pat_p = primed[0]
    for v in primed[1:]:
        pat_p = f"[{pat_p} {v}]" if pat_p.startswith("[") else f"[{pat_p} {v}]"
    # left-nested destruct pattern: [[a b] c]
    pat_p = primed[0]
    for v in primed[1:]:
        pat_p = f"[{pat_p} {v}]"
    sb_p = " ".join(f"({v}' : {rty(stys[v])})" for v in svars)
    penv = {v: v + "'" for v in svars}
    invs_p = [cx.prop(e, penv, local) for e in w.get("invariants", [])]
    guard_pp = cx.prop(w["cond"], penv, local)
    dec0 = cx.zx(w["decreases"],
                 {**{v: env_pre[v] for v in svars}}, local)
    init_terms = " ".join(env_pre[v] for v in svars)

    lens = len_hyps(cx)
    n_lens, n_reqs, n_invs = len(lens), len(reqs), len(invs)
    hyp_names = ([f"Hl{k+1}" for k in range(n_lens)]
                 + [f"Hreq{k+1}" for k in range(n_reqs)]
                 + ["Hfuel"] + [f"Hinv{k+1}" for k in range(n_invs)])
    lemma_hyps = "".join(f"  {h} ->\n" for h in lens + reqs)
    inv_hyps = "".join(f"  {p} ->\n" for p in invs)
    concl = " /\\ ".join(invs_p + [f"(~ {guard_pp})"])

    ens = ensures_text(cx, f"({name}_t {pargs})")
    state_names = " ".join(svars)
    primed_names = " ".join(primed)
    param_names = pargs

    ini_asserts = "".join(
        f"  assert (Hini{k+1} : {cx.prop(e, {v: env_pre[v] for v in svars}, local)}) by t_dis.\n"
        for k, e in enumerate(w.get("invariants", [])))
    pose_args = " ".join(
        ["(S (Z.to_nat {d}))".format(d=dec0), param_names, init_terms,
         primed_names]
        + [f"Hl{k+1}" for k in range(n_lens)]
        + [f"Hreq{k+1}" for k in range(n_reqs)]
        + ["Hfb"]
        + [f"Hini{k+1}" for k in range(n_invs)]
        + ["Heq"])

    return f"""{def_txt}
Fixpoint {name}_loop (fuel : nat) {pb} {sb} : {tup_ty} :=
  match fuel with
  | O => {tup}
  | S fu =>
      if {guard_b}
      then {name}_loop fu {pargs} {step_terms}
      else {tup}
  end.

Definition {name}_t {pb} : {rty(ret_t)} :=
  let '{tup} := {name}_loop (S (Z.to_nat {dec0})) {pargs} {init_terms}
  in {result_term}.

Lemma {name}_loop_spec :
  forall (fuel : nat) {pb} {sb} {sb_p},
{lemma_hyps}  {dec} < Z.of_nat fuel ->
{inv_hyps}  {name}_loop fuel {pargs} {state_names} = {tup_p} ->
  ({concl}).
Proof.
  induction fuel as [|fu IH];
  intros {param_names} {state_names} {primed_names} {' '.join(hyp_names)};
  simpl; t_sweep;
  first [ solve [ apply IH; t_side ]
        | (let Heq := fresh "Heq" in
           intro Heq; inversion Heq; subst; clear Heq; t_dis)
        | fail 1 "unsolved t verification condition" ].
Qed.

Theorem {name}_t_spec :
  forall {pb},
{lens_arrows(cx)}{requires_arrows(cx)}  {ens}.
Proof.
  intros {param_names} {' '.join(f'Hl{k+1}' for k in range(n_lens))} {' '.join(f'Hreq{k+1}' for k in range(n_reqs))}.
  unfold {name}_t.
  destruct ({name}_loop (S (Z.to_nat {dec0})) {pargs} {init_terms})
    as {pat_p} eqn:Heq.
  cbn beta iota.
  assert (Hfb : {dec0} < Z.of_nat (S (Z.to_nat {dec0}))) by lia.
{ini_asserts}  pose proof ({name}_loop_spec {pose_args}) as Hout.
  clear Hfb Heq {' '.join(f'Hini{k+1}' for k in range(n_invs))}.
  t_dis.
Qed.
"""


def gen_rec(cx: Ctx, body: list) -> str:
    task = cx.task
    name = task["name"]
    ret = task["returns"][0]["name"]
    ret_t = task["returns"][0]["type"]
    pb, pargs = param_binders(cx)
    default = "false" if ret_t == "bool" else "0"
    assert "decreases" in task, "self-recursive task without decreases"
    measure = cx.zx(task["decreases"], {}, {})

    reqs = [cx.prop(e, {}) for e in task.get("requires", [])]
    local: dict[str, str] = {}
    obls: list = []

    # fuel body: self-calls become {name}_fuel fu
    cx.callpre[name] = f"{name}_fuel fu"
    env0 = {ret: default}
    env = exec_straight(cx, body, env0, local, list(reqs), [], obls)
    body_fuel = env[ret]
    del cx.callpre[name]

    lens = len_hyps(cx)
    n_lens, n_reqs = len(lens), len(reqs)
    lens_reqs = "".join(f"  {h} ->\n" for h in lens + reqs)
    ens_fuel = ensures_text(cx, f"({name}_fuel fuel {pargs})")
    ens = ensures_text(cx, f"({name}_t {pargs})")
    eq_lines = "".join(f"  try rewrite sf_{sf['name']}_eq.\n"
                       for sf in task.get("spec_funs", []))
    hyps = " ".join([f"Hl{k+1}" for k in range(n_lens)]
                    + [f"Hreq{k+1}" for k in range(n_reqs)])

    return f"""Fixpoint {name}_fuel (fuel : nat) {pb} : {rty(ret_t)} :=
  match fuel with
  | O => {default}
  | S fu => {body_fuel}
  end.

Definition {name}_t {pb} : {rty(ret_t)} :=
  {name}_fuel (S (Z.to_nat {measure})) {pargs}.

Lemma {name}_fuel_spec :
  forall (fuel : nat) {pb},
  (Z.to_nat {measure} < fuel)%nat ->
{lens_reqs}  {ens_fuel}.
Proof.
  induction fuel as [|fu IH]; intros {pargs} Hf {hyps};
  [ exfalso; lia | ].
  simpl.
{eq_lines}  t_sweep;
  repeat first [ reflexivity
               | solve [ lia ]
               | solve [ apply IH; lia ]
               | (lazymatch goal with |- _ /\\ _ => split end)
               | f_equal ].
  all: fail "unsolved t verification condition".
Qed.

Theorem {name}_t_spec :
  forall {pb},
{lens_arrows(cx)}{requires_arrows(cx)}  {ens}.
Proof.
  intros.
  unfold {name}_t.
  apply ({name}_fuel_spec (S (Z.to_nat {measure})));
  first [ lia | assumption ].
Qed.
"""


def lower(task: dict, body: list) -> str:
    if task.get("t") == 0:
        return lower_v0(task, body)
    return lower_v1(task, body)


if __name__ == "__main__":
    raise SystemExit(harness.run_all(sys.argv[1:], lower, rocq_backend, "v"))
