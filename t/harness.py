"""t/harness.py — the backend-independent part of running a t task.

One implementation of: task loading, the v0 twin operator (collapse the
body's first `if` to its then-branch), the flake discipline, and the flip
rule (real VERIFIED and twin REFUTED, or the task is refused). Lowering
files supply only syntax; verdicts come only from t.verifiers backends.
"""
from __future__ import annotations

import json
from pathlib import Path

from verifiers import Outcome, flake_check

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def load(path: Path) -> dict:
    task = json.loads(path.read_text(encoding="utf-8"))
    assert task.get("t") == 0, f"{path.name}: not a t v0 task"
    return task


def collapse_first_if(body: list) -> tuple[list, bool]:
    out, done = [], False
    for s in body:
        if not done and "if" in s:
            out.extend(s["if"]["then"])
            done = True
        else:
            out.append(s)
    return out, done


def run_task(task_path: Path, lower, backend, suffix: str) -> bool:
    """lower(task, body) -> source text; backend is a t.verifiers module."""
    task = load(task_path)
    name = task["name"]
    OUT.mkdir(exist_ok=True)

    real = OUT / f"{name}.{suffix}"
    real.write_text(lower(task, task["body"]), encoding="utf-8")
    twin_body, mutated = collapse_first_if(task["body"])
    if not mutated:
        print(f"  {name}: REFUSED — no `if` to collapse, v0 twin undefined")
        return False
    twin = OUT / f"{name}.twin.{suffix}"
    twin.write_text(lower(task, twin_body), encoding="utf-8")

    r_real, agree_r = flake_check(backend.verify, real)
    r_twin, agree_t = flake_check(backend.verify, twin)
    if not (agree_r and agree_t):
        print(f"  {name}: REFUSED — verdicts flaked across runs")
        return False
    flip = (r_real.outcome == Outcome.VERIFIED
            and r_twin.outcome == Outcome.REFUTED)
    tag = ("COUNTS  (real VERIFIED, twin REFUTED)" if flip else
           f"REFUSED (real {r_real.outcome}, twin {r_twin.outcome}"
           + (" — vacuous spec)" if r_twin.outcome == Outcome.VERIFIED else ")"))
    print(f"  {name}: {tag}")
    return flip


def run_all(argv: list[str], lower, backend, suffix: str) -> int:
    want = argv or sorted(p.stem for p in (HERE / "tasks").glob("*.json"))
    print(f"t v0 -> {backend.version()}")
    ok = all(run_task(HERE / "tasks" / f"{w}.json", lower, backend, suffix)
             for w in want)
    return 0 if ok else 1
