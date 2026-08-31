"""Probe for one claim: the trace recovers training signal that pairs discard.

THE CLAIM. Section 86 measured that 66% of task attempts "teach nothing". That
is a statement about DPO, not about the data -- a task whose candidates ALL pass
produces no preference pair and is counted as teaching nothing, while being
several verified-correct programs.

These tests fail if that stops being true, i.e. if the views ever collapse back
to what pairs alone would have given. Synthetic rows only; no model, no
verifier, no repo file read or written.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import traces as T


def row(tid, code, ok, *, timed_out=False, runtime=1.0):
    return {"schema": T.SCHEMA, "tid": tid, "prompt": f"solve {tid}",
            "entry": tid, "raw": f"```python\n{code}\n```", "code": code,
            "ok": ok, "reward": 1.0 if ok else 0.0, "error": "" if ok else "boom",
            "runtime_ms": runtime, "timed_out": timed_out, "temp": 0.8,
            "model": "test", "verifier": {}, "ts": ""}


def test_all_candidates_passing_teaches_dpo_nothing_and_sft_everything():
    """The headline case. Four correct programs, no preference pair possible."""
    rows = [row("t1", f"def t1():\n    return {i}", True) for i in range(4)]
    assert T.derive_dpo(rows) == [], "a pair needs a failure; there is none"
    sft = T.derive_sft(rows)
    assert len(sft) == 4, f"expected 4 supervised rows, got {len(sft)}"
    kto = T.derive_kto(rows)
    assert len(kto) == 4 and all(r["label"] for r in kto), kto


def test_all_candidates_failing_still_teaches_kto():
    """The other end: nothing passed, so SFT and DPO get nothing, KTO gets
    four negatives. Failure is signal for a method that takes labels."""
    rows = [row("t2", f"def t2():\n    return {i}", False) for i in range(4)]
    assert T.derive_sft(rows) == []
    assert T.derive_dpo(rows) == []
    kto = T.derive_kto(rows)
    assert len(kto) == 4 and not any(r["label"] for r in kto), kto


def test_mixed_task_produces_all_three_views():
    rows = [row("t3", "def t3():\n    return 1", True),
            row("t3", "def t3():\n    return 2", False),
            row("t3", "def t3():\n    return 3", False)]
    assert len(T.derive_sft(rows)) == 1
    assert len(T.derive_kto(rows)) == 3
    assert len(T.derive_dpo(rows)) == 2, "best passer against each failure"


def test_a_timeout_is_not_a_wrong_answer():
    """The pipeline's existing rule, re-derived rather than re-invented: a
    timed-out candidate must never become the rejected half."""
    rows = [row("t4", "def t4():\n    return 1", True),
            row("t4", "def t4():\n    while True: pass", False, timed_out=True)]
    assert T.derive_dpo(rows) == [], "a timeout became a preference signal"


def test_views_do_not_consume_the_trace():
    """A view is a pure function. Running one must not change the trace, or
    'rebuild it differently later' stops being possible."""
    rows = [row("t5", "def t5():\n    return 1", True),
            row("t5", "def t5():\n    return 2", False)]
    before = [dict(r) for r in rows]
    T.derive_sft(rows); T.derive_kto(rows); T.derive_dpo(rows)
    assert rows == before, "a derivation mutated the trace"


def test_yield_report_shows_the_ratio_that_motivates_this():
    """Two tasks: one all-passing, one mixed. DPO sees only the mixed one."""
    rows = ([row("a", f"def a():\n    return {i}", True) for i in range(4)]
            + [row("b", "def b():\n    return 1", True),
               row("b", "def b():\n    return 2", False)])
    rep = T.yield_report(rows)
    assert rep["candidates"] == 6 and rep["tasks"] == 2
    assert rep["sft_rows"] == 5, rep
    assert rep["kto_rows"] == 6, rep
    assert rep["dpo_pairs"] == 1, rep
    assert rep["sft_rows"] > rep["dpo_pairs"], "the whole argument, in one line"


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails.append(name); print(f"FAIL {name}: {e}")
    print(f"\n{len(fails)} failed")
    raise SystemExit(1 if fails else 0)
