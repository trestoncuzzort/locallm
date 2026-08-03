#!/usr/bin/env python3
"""trace.py — the immutable record, and the training views derived from it.

THE CHANGE THIS MAKES. Until now a pair was the primary artifact: run_task
sampled K candidates, emitted at most ONE (chosen, rejected) pair, and threw the
rest away. Section 86 measured the cost -- 66% of task attempts teach nothing,
and only 16.9% of paid-for generations reach a training row.

That number is a fact about DPO, not about the data. A task where all four
candidates PASS yields no preference pair at all, and is recorded as teaching
nothing. It is four verified-correct programs. As SFT rows it teaches four
times; as KTO positives it teaches four times. The generations were already
bought and the verifier already ran.

So the trace is primary and every training file is a VIEW over it:

    candidates --> trace.jsonl --> derive_sft()   --> supervised rows
                               --> derive_kto()   --> labelled rows
                               --> derive_dpo()   --> preference pairs

WHY THIS ORDER AND NOT THE OTHER. A view can always be rebuilt from the trace;
a trace cannot be rebuilt from a view. Emitting pairs first destroys the
information that any other method would have needed, which is what makes
"try KTO instead" cost a full regeneration today instead of a function call.
Adopted as sponsor item 3; this is that item.

WHAT A TRACE ROW IS. One candidate, one verdict, and everything needed to
re-derive the verdict: which task, which model, what sampler, which verifier.
Rows are APPEND-ONLY and never edited -- a corrected verdict is a new row, so
the history of what was believed stays readable.

WHAT THIS FILE DOES NOT DO. It does not train anything, it does not talk to a
model, and it does not decide which method is best. It is stdlib-only so the
derivations can be tested without a GPU.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA = 1
HERE = Path(__file__).resolve().parent
TRACE = HERE / "data" / "trace.jsonl"


@dataclass
class TraceRow:
    """One candidate, as it was actually produced and judged."""
    schema: int
    tid: str                 # which task
    prompt: str              # what was asked
    entry: str               # the function the tests call
    raw: str                 # verbatim model emission, before extraction
    code: str                # extracted code, exactly what was executed
    ok: bool                 # THE VERDICT: did the hidden tests pass
    reward: float            # scalar reward; 1.0/0.0 today, room for partial
    error: str = ""          # failure text when ok is False
    runtime_ms: float = 0.0
    timed_out: bool = False
    temp: float = 0.0        # sampler settings, because they change the draw
    model: str = ""
    verifier: dict = field(default_factory=dict)   # interpreter + file hashes
    ts: str = ""


def append(rows: list[TraceRow], path: Path = TRACE) -> int:
    """Append rows. Never rewrites; the file only grows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    return len(rows)


def load(path: Path = TRACE) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# THE VIEWS. Each is a pure function of the trace: same trace, same rows, every
# time. None of them mutate or consume the trace.
# ---------------------------------------------------------------------------
def derive_sft(rows: list[dict], dedup: bool = True) -> list[dict]:
    """Verified-correct programs, as supervised examples.

    The widest view: every candidate that PASSED is usable, with no need for a
    matching failure. This is what turns an all-candidates-passed task from
    "teaches nothing" into K training rows.

    Research seed 01 calls verified-positive SFT the cleanest first downstream
    comparison, for the reason visible here -- it needs the fewest assumptions.
    A row is included because a program was executed and its tests passed.
    """
    seen: set[tuple[str, str]] = set()
    out = []
    for r in rows:
        if not r.get("ok"):
            continue
        key = (r["tid"], r["code"].strip())
        if dedup and key in seen:
            continue
        seen.add(key)
        out.append({"prompt": r["prompt"], "completion": r["raw"],
                    "meta": {"tid": r["tid"], "reward": r.get("reward", 1.0),
                             "source": "sft"}})
    return out


def derive_kto(rows: list[dict], dedup: bool = True) -> list[dict]:
    """Every candidate, labelled desirable or not.

    KTO needs a LABEL, not a pair, which is the point of including it: a task
    that produced only failures contributes nothing to DPO and contributes real
    negative signal here. Nothing is discarded for lacking a partner.
    """
    seen: set[tuple[str, str]] = set()
    out = []
    for r in rows:
        code = (r.get("code") or "").strip()
        if not code:
            continue
        key = (r["tid"], code)
        if dedup and key in seen:
            continue
        seen.add(key)
        out.append({"prompt": r["prompt"], "completion": r["raw"],
                    "label": bool(r.get("ok")),
                    "meta": {"tid": r["tid"], "source": "kto"}})
    return out


def derive_dpo(rows: list[dict], per_task_cap: int | None = None) -> list[dict]:
    """Preference pairs: a passing candidate against a demonstrably failing one.

    The narrowest view, and deliberately the same rule the pipeline already
    used: `rejected` must be WRONG, never merely slow or unmeasured, and never
    a timeout -- a timeout is not a wrong answer. Reproducing that rule here
    rather than inventing a new one keeps this a re-derivation of the existing
    dataset instead of a second, differently-shaped one.

    Emitting every winner against every loser would inflate the count without
    adding information, so pairs are built per task from the best passer
    against each distinct failure, then capped.
    """
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_task[r["tid"]].append(r)

    out = []
    for tid, rs in by_task.items():
        passing = [r for r in rs if r.get("ok")]
        failing = [r for r in rs
                   if not r.get("ok") and not r.get("timed_out")
                   and (r.get("code") or "").strip()]
        if not passing or not failing:
            continue
        best = min(passing, key=lambda r: (r.get("runtime_ms", 0.0),
                                           len(r.get("code") or "")))
        seen: set[str] = set()
        made = 0
        for f in sorted(failing, key=lambda r: len(r.get("code") or "")):
            code = f["code"].strip()
            if code == best["code"].strip() or code in seen:
                continue
            seen.add(code)
            out.append({"prompt": best["prompt"], "chosen": best["raw"],
                        "rejected": f["raw"],
                        "meta": {"tid": tid, "reason": "correctness",
                                 "source": "dpo"}})
            made += 1
            if per_task_cap and made >= per_task_cap:
                break
    return out


VIEWS = {"sft": derive_sft, "kto": derive_kto, "dpo": derive_dpo}


def yield_report(rows: list[dict]) -> dict:
    """How many training rows each method gets from the SAME trace.

    The number this project keeps arguing about. Reported rather than asserted,
    because "SFT gets more rows" is only interesting with the ratio attached.
    """
    tasks = {r["tid"] for r in rows}
    solved = {r["tid"] for r in rows if r.get("ok")}
    return {
        "candidates": len(rows),
        "tasks": len(tasks),
        "tasks_solved": len(solved),
        "sft_rows": len(derive_sft(rows)),
        "kto_rows": len(derive_kto(rows)),
        "dpo_pairs": len(derive_dpo(rows)),
    }


if __name__ == "__main__":
    rows = load()
    if not rows:
        raise SystemExit(f"no trace at {TRACE}. Nothing has written one yet.")
    rep = yield_report(rows)
    print(f"trace: {rep['candidates']} candidates over {rep['tasks']} tasks "
          f"({rep['tasks_solved']} solved)")
    for k in ("sft_rows", "kto_rows", "dpo_pairs"):
        print(f"  {k:12} {rep[k]}")
