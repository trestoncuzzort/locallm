"""t/harness.py — the backend-independent part of running a t task.

One implementation of: task loading, the twin operators, the flake
discipline, and the flip rule (real VERIFIED and twin REFUTED, or the task
is refused). Lowering files supply only syntax; verdicts come only from
t.verifiers backends.

Twin operators (SPEC.md "The twins", v2 — the ladder below, tried in order):
  INVARIANT-DROP  (v1) — delete one invariant of one loop (pre-order).
  COLLAPSE-IF     (v0) — replace one `if` (pre-order) with its then-branch.
  NEGATE-COND          — swap one `if`'s branches, which is `not cond`.
  COMPARE-FLIP         — `<`<->`<=`, `>`<->`>=` in one executable expression.
  BOUNDARY-SWAP        — swap the operands of one order comparison.
  OFF-BY-ONE           — +/-1 on one literal, `at` index, or loop bound.
  WRONG-VAR            — one variable occurrence replaced by another one.
  DROP-GUARD           — drop one conjunct of an `if`/`while` condition.

Selection is derived from the body, never configured per task, and is
deterministic: operators in the fixed order above, sites within an operator in
the pre-order `collapse_first_if` already used, and the FIRST candidate with a
WITNESS wins. So the same task always yields the same twin, and the first two
rungs reproduce the v1 rule exactly wherever it was already load-bearing.

A witness is a measurement, not an assumption (t/interp.py; the house rule
applied to the harness itself). Measured over 1395 generated tasks from
fuzz_lower.py (7 seeds x 200), 129 twins — 9.2% — computed the same value
as the real program on every input tested: for those the "measured flip"
measured nothing, since no behavioural difference existed for a kernel to
detect. So:
  - a value-changing operator is accepted only with an input where the real
    body and the twin return different values (or the twin is undefined where
    the real body has a value);
  - INVARIANT-DROP, whose twin computes the SAME value by construction, is
    accepted only with a loop state the surviving invariants no longer cover
    (exit entailment or preservation).
No witness on any rung and the task is REFUSED — an unmeasurable twin is
reported as such rather than passed off as a flip.

The twin NEVER touches `requires`, `ensures`, `spec_funs`, or `decreases`:
the spec is the fixed instrument, the body (and its proof annotations) is
what gets broken.
"""
from __future__ import annotations

import json
from pathlib import Path

import interp
from verifiers import Outcome, flake_check

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

KNOWN_VERSIONS = (0, 1)


class SpecError(ValueError):
    """This file is not a t task. Raised instead of letting a
    SPEC-nonconforming task through: everything downstream — the twin
    ladder, the seven lowerings, the flip rule — reads a task assuming
    SPEC.md holds of it, and a kernel verdict on something t does not
    define measures nothing."""


def load(path: Path) -> dict:
    """The only door into a task. A file that reaches the kernels has been
    through fuzz_lower.check_wf, so the well-formedness rules the fuzzer
    has always enforced on GENERATED tasks are the same ones a committed
    task must pass. Measured 2026-09-05 on the pre-fix bytes: duplicate
    parameters, a return named after a parameter, and a task with no
    `requires` all loaded and COUNTED as flips.

    Every refusal the read and the parse can name leaves by SpecError,
    including the four that used to leave by traceback before the wrapper
    below could name a cause. Measured 2026-09-05: a file holding `not json`
    killed both drivers with json.JSONDecodeError; the file `[]` — valid
    JSON, not a task — with `AttributeError: 'list' object has no attribute
    'get'` on the version check; a UTF-16 file, which is what a Windows
    shell's `>` writes by default, with `UnicodeDecodeError: 'utf-8' codec
    can't decode byte 0xff in position 0` raised by read_text before json
    saw a character; and an otherwise-valid task carrying a 4301-digit
    integer literal with `ValueError: Exceeds the limit (4300 digits) for
    integer string conversion` raised by json's own scanner. A driver that
    catches SpecError caught none of the four, so one such file in tasks/
    cost the whole run. The limit, measured the same day: JSON nested deeply
    enough to exhaust the interpreter's recursion limit (5000 levels) raises
    RecursionError, which is not a ValueError and is not caught here."""
    try:
        task = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SpecError(f"{path.name}: not JSON ({e})") from e
    except (ValueError, OSError) as e:
        # What is left once the path is named but the bytes are not a t task
        # anyone can read: a decode failure (UnicodeDecodeError), json's
        # int-string conversion limit (a plain ValueError out of the
        # scanner), and a path that will not open (OSError).
        # UnicodeDecodeError and JSONDecodeError are both ValueError
        # subclasses, so the narrower clause above keeps its own message and
        # this one names the exception type for everything else.
        raise SpecError(f"{path.name}: not a readable t task "
                        f"({type(e).__name__}: {e})") from e
    if not isinstance(task, dict):
        raise SpecError(f"{path.name}: not a t task — the top-level value is "
                        f"a {type(task).__name__} and a task is an object")
    if task.get("t") not in KNOWN_VERSIONS:
        raise SpecError(f"{path.name}: not a t task I know "
                        f"(t={task.get('t')!r}, known: {KNOWN_VERSIONS})")
    # Deferred: fuzz_lower imports this module, so importing it at module
    # level is a cycle (the same one interp.py records).
    from fuzz_lower import check_wf                  # noqa: PLC0415
    try:
        errs = check_wf(task)
    except Exception as e:                           # noqa: BLE001
        # A shape check_wf reads without checking. Still a refusal that
        # names its cause, never a bare KeyError out of a loader.
        raise SpecError(f"{path.name}: not a well-formed t task "
                        f"({type(e).__name__}: {e})") from e
    if errs:
        raise SpecError(f"{path.name}: {errs[0]}")
    return task


def collapse_first_if(body: list) -> tuple[list, bool]:
    """v0 twin operator, pre-order: the first `if` encountered is replaced by
    its then-branch. Descends into `while` bodies (v1) so a loop containing
    the only `if` is still mutable; v0 tasks (top-level `if`, no loops) get
    byte-identical behavior to the original v0 operator."""
    out, done = [], False
    for s in body:
        if not done and "if" in s:
            out.extend(s["if"]["then"])
            done = True
        elif not done and "while" in s:
            inner, hit = collapse_first_if(s["while"]["body"])
            if hit:
                w = dict(s["while"])
                w["body"] = inner
                s = {"while": w}
                done = True
            out.append(s)
        else:
            out.append(s)
    return out, done


def drop_first_invariant(body: list) -> tuple[list, bool]:
    """v1 twin operator, pre-order: the first `while` that states any
    invariant loses its FIRST invariant. Everything else is untouched."""
    out, done = [], False
    for s in body:
        if not done and "while" in s and s["while"].get("invariants"):
            w = dict(s["while"])
            w["invariants"] = w["invariants"][1:]
            out.append({"while": w})
            done = True
        elif not done and "while" in s:
            inner, hit = drop_first_invariant(s["while"]["body"])
            w = dict(s["while"])
            w["body"] = inner
            out.append({"while": w})
            done = hit
        elif not done and "if" in s:
            c = s["if"]
            then2, hit = drop_first_invariant(c["then"])
            if hit:
                out.append({"if": {"cond": c["cond"],
                                   "then": then2, "else": c["else"]}})
                done = True
            else:
                else2, hit2 = drop_first_invariant(c["else"])
                out.append({"if": {"cond": c["cond"],
                                   "then": c["then"], "else": else2}})
                done = hit2
        else:
            out.append(s)
    return out, done


def _has_invariant_loop(body: list) -> bool:
    for s in body:
        if "while" in s:
            if s["while"].get("invariants"):
                return True
            if _has_invariant_loop(s["while"]["body"]):
                return True
        elif "if" in s:
            if (_has_invariant_loop(s["if"]["then"])
                    or _has_invariant_loop(s["if"]["else"])):
                return True
    return False


# ---------------------------------------------------------------------------
# The mutation ladder. Sites are enumerated in the same pre-order
# collapse_first_if uses, so rung 1 site 0 IS drop_first_invariant and rung 2
# site 0 IS collapse_first_if; a task whose v1 twin already had a witness
# keeps that exact twin.
# ---------------------------------------------------------------------------

MAX_CANDIDATES = 400      # ladder budget per task; the search is otherwise
                          # unbounded in wrong-var, which is quadratic in the
                          # number of names in scope.

FLIP = {"<": "<=", "<=": "<", ">": ">=", ">=": ">"}
ORDER_OPS = ("<", "<=", ">", ">=")


def _copy(o):
    return json.loads(json.dumps(o))       # a t body is pure JSON


def _replace(body: list, path: tuple, new):
    """`body` with the subtree at `path` replaced; `body` is not mutated."""
    out = _copy(body)
    node = out
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = _copy(new)
    return out


def _splice(body: list, path: tuple, stmts: list):
    """`body` with the STATEMENT at `path` replaced by `stmts` in place."""
    out = _copy(body)
    node = out
    for k in path[:-1]:
        node = node[k]
    i = path[-1]
    node[i:i + 1] = _copy(stmts)
    return out


def _stmts(body: list, scope: list, prefix: tuple = ()):
    """Pre-order over statements — statement, then into `if` branches and
    `while` bodies — yielding (path, stmt, scope), where scope is the
    (name, type) pairs a substitution at that statement may use. A `var`
    statement is yielded BEFORE its own name enters scope: its initialiser
    cannot see it."""
    sc = list(scope)
    for i, s in enumerate(body):
        p = prefix + (i,)
        yield p, s, list(sc)
        if "var" in s:
            sc.append((s["var"]["name"], s["var"]["type"]))
        elif "if" in s:
            yield from _stmts(s["if"]["then"], sc, p + ("if", "then"))
            yield from _stmts(s["if"]["else"], sc, p + ("if", "else"))
        elif "while" in s:
            yield from _stmts(s["while"]["body"], sc, p + ("while", "body"))


def _exprs(body: list, scope: list):
    """Pre-order over the expressions a twin may break: `if`/`while`
    conditions, assignment right-hand sides, local initialisers. Never
    `invariants` or `decreases` — dropping an invariant is INVARIANT-DROP's
    job, and a rewritten `decreases` would break termination rather than the
    thing under test. Yields (path, expr, scope, kind)."""
    for p, s, sc in _stmts(body, scope):
        if "assign" in s:
            yield p + ("assign", 1), s["assign"][1], sc, "rhs"
        elif "var" in s:
            yield p + ("var", "init"), s["var"]["init"], sc, "init"
        elif "if" in s:
            yield p + ("if", "cond"), s["if"]["cond"], sc, "cond-if"
        elif "while" in s:
            yield p + ("while", "cond"), s["while"]["cond"], sc, "cond-while"


def _sub(e: dict, path: tuple):
    """Pre-order over an expression and its subexpressions."""
    yield path, e
    if "op" in e:
        for i, a in enumerate(e["args"]):
            yield from _sub(a, path + ("args", i))
    elif "ite" in e:
        for k in ("cond", "then", "else"):
            yield from _sub(e["ite"][k], path + ("ite", k))
    elif "forall" in e or "exists" in e:
        q = "forall" if "forall" in e else "exists"
        for k in ("lo", "hi", "body"):
            yield from _sub(e[q][k], path + (q, k))
    elif "call" in e:
        for i, a in enumerate(e["call"]["args"]):
            yield from _sub(a, path + ("call", "args", i))


def _c_collapse_if(body, scope):
    for p, s, _ in _stmts(body, scope):
        if "if" in s:
            yield _splice(body, p, s["if"]["then"])


def _c_negate_cond(body, scope):
    # `not cond` is realised as a branch swap: identical semantics, and it
    # introduces no operator a lowering may reject (fuzz_lower.py records
    # lower_rocq.py's cond_bool0 refusing a boolean connective in a v0
    # condition, so a literal `not` would turn a REFUTED cell into a
    # LOWER-ERROR one and lose the flip).
    for p, s, _ in _stmts(body, scope):
        if "if" in s:
            c = s["if"]
            yield _replace(body, p, {"if": {"cond": c["cond"],
                                            "then": c["else"],
                                            "else": c["then"]}})


def _c_compare_flip(body, scope):
    for path, e, _, _k in _exprs(body, scope):
        for sp, node in _sub(e, path):
            if node.get("op") in FLIP:
                yield _replace(body, sp, {"op": FLIP[node["op"]],
                                          "args": node["args"]})


def _c_boundary_swap(body, scope):
    for path, e, _, _k in _exprs(body, scope):
        for sp, node in _sub(e, path):
            if node.get("op") in ORDER_OPS:
                yield _replace(body, sp, {"op": node["op"],
                                          "args": node["args"][::-1]})


def _c_off_by_one(body, scope):
    for path, e, _, kind in _exprs(body, scope):
        for sp, node in _sub(e, path):
            if "int" in node:
                for d in (1, -1):
                    yield _replace(body, sp, {"int": node["int"] + d})
            elif node.get("op") == "at":
                for d in (1, -1):
                    yield _replace(body, sp + ("args", 1),
                                   {"op": "+", "args": [node["args"][1],
                                                        {"int": d}]})
            elif node.get("op") in ORDER_OPS and kind == "cond-while":
                # The loop bound: `i < len(s)` has no literal to move.
                for d in (1, -1):
                    yield _replace(body, sp + ("args", 1),
                                   {"op": "+", "args": [node["args"][1],
                                                        {"int": d}]})


def _c_wrong_var(body, scope):
    # Params and locals only, on BOTH sides of the substitution. The return
    # name is not a target: a body that reads it before its first assignment
    # is ill-formed rather than wrong, and a lowering rejects it instead of
    # refuting it, which loses the flip. It is not a source either — nor is a
    # quantifier's bound variable — because neither carries a declared type
    # here, and substituting across types would emit a twin no lowering can
    # even typecheck.
    for path, e, sc, _k in _exprs(body, scope):
        ty_of = dict(sc)
        for sp, node in _sub(e, path):
            if "var" in node and node["var"] in ty_of:
                ty = ty_of[node["var"]]
                for alt, alt_ty in sc:
                    if alt != node["var"] and alt_ty == ty:
                        yield _replace(body, sp, {"var": alt})


def _c_drop_guard(body, scope):
    for path, e, _, kind in _exprs(body, scope):
        if kind not in ("cond-if", "cond-while"):
            continue
        if e.get("op") != "and" or len(e["args"]) < 2:
            continue
        for k in range(len(e["args"])):
            rest = e["args"][:k] + e["args"][k + 1:]
            yield _replace(body, path,
                           rest[0] if len(rest) == 1
                           else {"op": "and", "args": rest})


EXTENSIONAL = (("collapse-if", _c_collapse_if),
               ("negate-cond", _c_negate_cond),
               ("compare-flip", _c_compare_flip),
               ("boundary-swap", _c_boundary_swap),
               ("off-by-one", _c_off_by_one),
               ("wrong-var", _c_wrong_var),
               ("drop-guard", _c_drop_guard))


def _invariant_candidates(task: dict):
    """(twin_body, loop, kept, names) per (loop, invariant) in pre-order.
    Candidate 0 is drop_first_invariant's twin. `names` is what a loop state
    ranges over: everything in scope at the loop, plus the return."""
    body = task["body"]
    scope = [(p["name"], p["type"]) for p in task["params"]]
    ret = task["returns"][0]
    for p, s, sc in _stmts(body, scope):
        if "while" not in s or not s["while"].get("invariants"):
            continue
        invs = s["while"]["invariants"]
        for j in range(len(invs)):
            kept = invs[:j] + invs[j + 1:]
            yield (_replace(body, p + ("while", "invariants"), kept),
                   s["while"], kept, sc + [(ret["name"], ret["type"])])


def _tag(op: str, k: int) -> str:
    return op if k == 0 else f"{op}#{k}"


def twin_for(task: dict) -> tuple[list | None, str | None, dict | None]:
    """Grounded twin selection: (twin_body, operator, witness), or
    (None, reason, None) when no rung of the ladder produced a witness."""
    n = 0
    for k, (twin, loop, kept, names) in enumerate(_invariant_candidates(task)):
        n += 1
        w = interp.invariant_witness(task, loop, kept, names)
        if w is not None:
            return twin, _tag("invariant-drop", k), w
    ref = interp.Reference(task)
    if not ref.points:
        # UNMEASURABLE, which is a different refusal from "the twin computes
        # the same thing" — and the two causes are worth telling apart.
        return None, ("no-input" if not ref.n_req else "real-undefined"), None
    # A witness that merely shows real and twin compute DIFFERENT values is
    # not grounds for expecting a refutation: a loose `ensures` can be
    # satisfied by both. Only a witness that FALSIFIES ensures entails that a
    # sound kernel must refute, which is what interp records in `_ens` and
    # what SPEC.md means by "the twin is REFUTED by the actual kernel".
    # Measured 2026-09-04: accepting on difference alone produced 88 cells
    # across all seven kernels whose twin came back VERIFIED, every one a
    # collapse-if, clustered by TASK rather than by kernel, which is the
    # signature of the twin being unrefutable rather than of seven adapters
    # being wrong. The ladder therefore prefers a refuting candidate and
    # falls back to a merely-differing one only when the whole ladder has
    # none, so the weakness is recorded in the tag instead of being silently
    # counted as a flip that failed.
    fallback = None
    for op, gen in EXTENSIONAL:
        for k, twin in enumerate(gen(task["body"], _scope(task))):
            n += 1
            if n > MAX_CANDIDATES:
                break
            w = ref.witness(twin)
            if w is None:
                continue
            if w.get("_ens") is True:
                return twin, _tag(op, k), w
            if fallback is None:
                fallback = (twin, _tag(op, k) + "+nonrefuting", w)
        if n > MAX_CANDIDATES:
            break
    if n > MAX_CANDIDATES and fallback is None:
        return None, "candidate-budget", None
    if fallback is not None:
        return fallback
    return None, ("no-witness" if n else "no-operator"), None


def _scope(task: dict) -> list:
    return [(p["name"], p["type"]) for p in task["params"]]


_TWIN_CACHE: dict[str, tuple] = {}


def twin_cached(task: dict) -> tuple[list | None, str | None, dict | None]:
    """run_all.py/run_par.py ask for the same task's twin once per backend;
    the ladder is a search, so it runs once."""
    key = json.dumps(task, sort_keys=True)
    if key not in _TWIN_CACHE:
        _TWIN_CACHE[key] = twin_for(task)
    return _TWIN_CACHE[key]


def make_twin(body: list, task: dict | None = None
              ) -> tuple[list | None, str | None]:
    """Deterministic twin selection. Returns (twin_body, operator_name), or
    (None, reason) when no operator produced a witness.

    `task` is what makes the choice measurable — without params, requires and
    ensures there is nothing to run the twin on. A body-only call is the
    UNGROUNDED v1 rule, kept for callers that carry their own semantic
    instrument (fuzz_lower.py decides twin strength with its own interpreter
    and must keep selecting the twin whose strength it reports)."""
    if task is not None:
        twin, op, _ = twin_cached(task)
        return twin, op
    if _has_invariant_loop(body):
        twin, _ = drop_first_invariant(body)
        return twin, "invariant-drop"
    twin, hit = collapse_first_if(body)
    if hit:
        return twin, "collapse-if"
    return None, None


_NO_INPUT = ("the bounded search enumerated {n} and found none satisfying "
             "`requires`, so there is nothing to measure. That is the "
             "COVERAGE of the search and not a proof that no input "
             "satisfies `requires`: the domain is a ladder capped at "
             "interp.MAX_POINTS points in shell order, and a bounded "
             "search is sound for falsity, never for truth (interp.py).")

REFUSALS = {
    "no-operator": "no `if` and no invariant — nothing to mutate, so the "
                   "twin is undefined",
    "no-witness": "every mutation on the ladder computes what the real body "
                  "computes, on the whole bounded domain — nothing to measure",
    "no-input": _NO_INPUT.format(
        n=f"the domain, at most {interp.MAX_POINTS} points "
          f"(interp.MAX_POINTS),"),
    "real-undefined": "the real body returns no value on any input that "
                      "satisfies `requires` — nothing for a twin to differ "
                      "from",
    "candidate-budget": f"no witness within {MAX_CANDIDATES} candidates",
}


def refusal(reason: str, task: dict | None = None) -> str:
    """The refusal sentence, with the domain the search ACTUALLY
    enumerated counted where the refusal is about coverage. Re-walking
    the ladder costs nothing next to a kernel run and evaluates no body.
    run_all.py and run_par.py call this too; REFUSALS keeps the cap
    sentence for a caller with no task to count."""
    if reason == "no-input" and task is not None:
        n = sum(1 for _ in interp.domain(task, _scope(task)))
        return _NO_INPUT.format(n=f"{n} points of the domain")
    return REFUSALS[reason]


def counts_as_flip(op: str) -> bool:
    """Does a REFUTED twin under this operator COUNT as the flip SPEC.md
    defines? ONE rule, one implementation: run_task, run_all.py and
    run_par.py all ask here.

    The TAG is the whole answer, because twin_for is the one place that
    decides. It returns a candidate only on a witness that entails a sound
    kernel must refute — one falsifying `ensures`, or, for INVARIANT-DROP,
    a loop state the surviving invariants no longer cover (interp returns
    only exit-entailment and preservation states) — and it marks
    `+nonrefuting` the fallback it takes when NO rung of the ladder
    falsifies `ensures`. Such a twin computes a different value, but a
    kernel refuting it is refuting it for a reason the measurement did not
    predict, and counting that as a flip credits the discipline with a
    detection it did not make.

    This used to re-derive that verdict from the witness's `_kind`/`_ens`
    while both drivers read the tag, which is one rule with two
    implementations and two ways to drift. Measured 2026-09-05: the two
    agreed on every twin of the 11 committed tasks and on all 1029 twins of
    five 200-task fuzz corpora (seeds 1-5, 43 of them tagged), so the tag is
    kept and the derivation is a comment."""
    return not op.endswith("+nonrefuting")


def witness(w: dict | None) -> str:
    """One line naming the input (or loop state) that makes the twin a
    measurement — the thing a REFUTED verdict is a verdict ABOUT."""
    if not w:
        return "none"
    kind = w.get("_kind")
    ins = ", ".join(f"{k}={v}" for k, v in w.items() if not k.startswith("_"))
    if kind in ("exit", "preservation"):
        return f"{kind} at {ins}"
    return f"{ins} -> real {w.get('_real')}, twin {w.get('_twin')}"


def run_task(task_path: Path, lower, backend, suffix: str,
             written: dict[Path, str] | None = None) -> bool:
    """lower(task, body, witness=None) -> source text; backend is a
    t.verifiers module. The twin call passes the measured witness so
    a lowering may use it; the real call never does.

    THE IDENTITY IS THE TASK NAME. `task["name"]` is an Id by SPEC.md's
    grammar and the name every lowering embeds as the module, crate or unit
    of what it emits, so out/<name>.<suffix> and out/<name>_twin.<suffix>
    name the artifact the way the source inside it names itself. The file's
    STEM was tried as the identity and is not one: any legal filename can be
    a stem, and measured 2026-09-05 one reached the kernels as a filename —
    abs.json copied to zzW2_abs.v1.json emitted out/zzW2_abs.v1.fst carrying
    `module Abs`, which F* refuses BY NAME (Error 141, "Expected module
    zzW2_abs.v1", exit 1, while the same bytes named Abs.fst verify).

    ONE ARTIFACT, ONE WRITER. `written` maps an out/ path to the task FILE
    that wrote it, for a whole run; a caller measuring one task can leave it
    None and gets a fresh empty map, which nothing can collide with. Two
    task files holding the same `name`, or names `x` and `x_twin` (both
    Ids), claim the same two paths. Measured 2026-09-05 before this map
    existed, on a pair of task files that claimed one twin path:
    `lower_dafny.py` printed COUNTS for both and exited 0, while the first
    task's twin artifact ended the run holding the second task's REAL
    lowering — a correct program standing where the broken one belongs, and
    the only artifact a reader has. run_all.py and run_par.py refuse that
    shape as a PATH-COLLISION cell; this is the single-kernel path's half of
    the same rule. No rename and no per-task directory: a collision is a
    defect in the task SET, and the author who named the tasks is the one
    who can fix it."""
    task = load(task_path)
    name = task["name"]
    written = {} if written is None else written
    OUT.mkdir(exist_ok=True)

    twin_body, op, w = twin_cached(task)
    if twin_body is None:
        print(f"  {name}: REFUSED — {refusal(op, task)}")
        return False

    real = OUT / f"{name}.{suffix}"
    twin = OUT / f"{name}_twin.{suffix}"
    clash = next((p for p in (real, twin) if p in written), None)
    if clash is not None:
        # NEITHER file is written. What is on disk is what an earlier task's
        # verdict was measured on, and this task has no artifact of its own
        # to be measured on.
        print(f"  {name} ({task_path.name}): PATH-COLLISION — out/{clash.name} "
              f"is also written by {written[clash]}")
        return False
    real.write_text(lower(task, task["body"]), encoding="utf-8",
                    newline="\n")
    twin.write_text(lower(task, twin_body, witness=w), encoding="utf-8",
                    newline="\n")
    written[real] = written[twin] = task_path.name

    r_real, agree_r = flake_check(backend.verify, real)
    r_twin, agree_t = flake_check(backend.verify, twin)
    if not (agree_r and agree_t):
        print(f"  {name}: REFUSED — verdicts flaked across runs")
        return False
    refuted = (r_real.outcome == Outcome.VERIFIED
               and r_twin.outcome == Outcome.REFUTED)
    flip = refuted and counts_as_flip(op)
    if flip:
        tag = (f"COUNTS  (real VERIFIED, {op} twin REFUTED, "
               f"witness {witness(w)})")
    elif refuted:
        # The kernel refuted a twin the witness does not convict. Whatever
        # it found, the measurement did not predict it, so it is not this
        # discipline's flip.
        tag = (f"REFUSED (real {r_real.outcome}, {op} twin REFUTED — "
               f"witness does not falsify ensures; refuted for another "
               f"reason, not counted)")
    elif r_twin.outcome == Outcome.VERIFIED and counts_as_flip(op):
        # A twin known to be broken, accepted anyway: SPEC.md's vacuous
        # spec, or an obligation the kernel re-derives.
        tag = (f"REFUSED (real {r_real.outcome}, {op} twin {r_twin.outcome}"
               f" — vacuous spec: the twin is broken on {witness(w)} and "
               f"the kernel accepted it anyway)")
    elif r_twin.outcome == Outcome.VERIFIED:
        # NOT AN ACCUSATION. A +nonrefuting twin breaks nothing the spec
        # states — both programs satisfy `ensures` — so VERIFIED is the
        # correct verdict and says nothing about the spec's teeth, which is
        # the whole reason the tag exists (SPEC.md, "+nonrefuting").
        # Measured 2026-09-05 on a loose task (requires 1<=x, x<=2; ensures
        # r <= 10-x; body r := 0): the off-by-one twin r := 1 satisfies the
        # spec too, dafny VERIFIED it, and this line called it a vacuous
        # spec whose twin the kernel had accepted anyway. False on both
        # counts.
        tag = (f"REFUSED (real {r_real.outcome}, {op} twin {r_twin.outcome}"
               f" — the twin differs on {witness(w)} but does not falsify "
               f"`ensures`, so VERIFIED is correct and says nothing about "
               f"the spec's teeth)")
    else:
        tag = f"REFUSED (real {r_real.outcome}, {op} twin {r_twin.outcome})"
    print(f"  {name}: {tag}")
    return flip


def run_all(argv: list[str], lower, backend, suffix: str) -> int:
    """Every named task (or all of tasks/) through ONE kernel — what
    `python lower_<kernel>.py` runs.

    EVERY TASK IS MEASURED, AND A REFUSED FILE IS ONE FILE. Two ways this
    path used to lose the rest of a run, both measured 2026-09-05: a
    nonconforming file ended it in a traceback, since nothing here caught
    the SpecError load raises; and `all(<generator>)` stopped at the first
    False, so a probe task whose twin the kernel verified printed one
    REFUSED line and `abs`, named after it on the same command line, was
    never lowered at all. The drivers' rule holds here too — one file's
    refusal must not silence every other measurement in the run.

    ONE `written` map for the whole run, threaded through run_task, so the
    second task to claim an out/ path is refused instead of overwriting the
    first task's measured twin with its own real source (the measurement is
    under run_task; run_all.py and run_par.py hold the same map for the
    cross-kernel matrix). The argv names below are FILE stems, because that
    is what a command line can name; the artifacts they produce are named
    after the TASK each file holds."""
    want = argv or sorted(p.stem for p in (HERE / "tasks").glob("*.json"))
    print(f"t -> {backend.version()}")
    ok = True
    written: dict[Path, str] = {}     # artifact path -> the task FILE that wrote it
    for w in want:
        try:
            ok = run_task(HERE / "tasks" / f"{w}.json",
                          lower, backend, suffix, written) and ok
        except SpecError as e:
            print(f"  {w}: REFUSED — {e}")
            ok = False
        except NotImplementedError as e:
            # The lowering declined the task — an identifier its adapter's
            # cheat scan would misread (ident_guard.py), or a construct it
            # cannot express. The cross-kernel runners record this as an
            # ABSTAIN cell; measured 2026-09-05, this path let it out as a
            # traceback, and `abs`, named after such a task on the same
            # command line, was never lowered.
            print(f"  {w}: ABSTAIN — {e}")
            ok = False
    return 0 if ok else 1
