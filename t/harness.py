"""t/harness.py — the backend-independent part of running a t task.

One implementation of: task loading, the twin operators, the flake
discipline, and the flip rule (real VERIFIED and twin REFUTED, or the task
is refused). Lowering files supply only syntax; verdicts come only from
t.verifiers backends.

Twin operators (SPEC.md "The twins", v1):
  COLLAPSE-IF     (v0) — replace the first `if` (pre-order) with its then-branch.
  INVARIANT-DROP  (v1) — delete the FIRST invariant of the FIRST loop (pre-order)
                         that states any.
Selection is derived from the body, never configured per task: a body that
contains a loop with invariants gets INVARIANT-DROP; otherwise a body with an
`if` gets COLLAPSE-IF; a body with neither has no twin and the task is
refused. One deterministic rule, applied identically to every task, so "the
twin failed" always means the same thing for a given body shape.

The twin NEVER touches `requires`, `ensures`, `spec_funs`, or `decreases`:
the spec is the fixed instrument, the body (and its proof annotations) is
what gets broken.
"""
from __future__ import annotations

import json
from pathlib import Path

from verifiers import Outcome, flake_check

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

KNOWN_VERSIONS = (0, 1)


def load(path: Path) -> dict:
    task = json.loads(path.read_text(encoding="utf-8"))
    assert task.get("t") in KNOWN_VERSIONS, (
        f"{path.name}: not a t task I know (t={task.get('t')!r}, "
        f"known: {KNOWN_VERSIONS})")
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


def make_twin(body: list) -> tuple[list | None, str | None]:
    """Deterministic twin selection. Returns (twin_body, operator_name) or
    (None, None) when no operator applies (the task is then refused)."""
    if _has_invariant_loop(body):
        twin, _ = drop_first_invariant(body)
        return twin, "invariant-drop"
    twin, hit = collapse_first_if(body)
    if hit:
        return twin, "collapse-if"
    return None, None


def run_task(task_path: Path, lower, backend, suffix: str) -> bool:
    """lower(task, body) -> source text; backend is a t.verifiers module."""
    task = load(task_path)
    name = task["name"]
    OUT.mkdir(exist_ok=True)

    twin_body, op = make_twin(task["body"])
    if twin_body is None:
        print(f"  {name}: REFUSED — no `if` and no invariant to mutate, "
              f"twin undefined")
        return False

    real = OUT / f"{name}.{suffix}"
    real.write_text(lower(task, task["body"]), encoding="utf-8")
    twin = OUT / f"{name}_twin.{suffix}"
    twin.write_text(lower(task, twin_body), encoding="utf-8")

    r_real, agree_r = flake_check(backend.verify, real)
    r_twin, agree_t = flake_check(backend.verify, twin)
    if not (agree_r and agree_t):
        print(f"  {name}: REFUSED — verdicts flaked across runs")
        return False
    flip = (r_real.outcome == Outcome.VERIFIED
            and r_twin.outcome == Outcome.REFUTED)
    tag = (f"COUNTS  (real VERIFIED, {op} twin REFUTED)" if flip else
           f"REFUSED (real {r_real.outcome}, {op} twin {r_twin.outcome}"
           + (" — vacuous spec or dead annotation)"
              if r_twin.outcome == Outcome.VERIFIED else ")"))
    print(f"  {name}: {tag}")
    return flip


def run_all(argv: list[str], lower, backend, suffix: str) -> int:
    want = argv or sorted(p.stem for p in (HERE / "tasks").glob("*.json"))
    print(f"t -> {backend.version()}")
    ok = all(run_task(HERE / "tasks" / f"{w}.json", lower, backend, suffix)
             for w in want)
    return 0 if ok else 1
