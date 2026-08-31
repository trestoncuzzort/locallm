#!/usr/bin/env python3
"""Screen the SQL domain against the base model. The second instance, run for real.

WHY THIS LIVES AT THE ROOT AND NOT UNDER domains/. Everything in domains/ is
forbidden to import forge (see domains/__init__.py) so the prompt contract had to
be written twice and diffed. This runner is the INTEGRATION point -- the place
where a domain meets the generator -- so it is allowed to import both, and it is
the honest place for the seam to be visible.

It reuses forge.Actor rather than writing a second Ollama client, because the
"one helper, two copies" failure has been paid for twice in this repo already
(venv_guard, sections 65/67). That reuse immediately produced a finding: see
NUM_CTX below.

NO GREEDY ANCHOR. forge.run_task samples `1 greedy + K-1 at GEN_TEMP` and the
estimand that produces has been open since section 76. This draws every candidate
at the same temperature, so the per-task rate is a clean Bernoulli p_i under one
sampler and nothing here needs the greedy correction.

    python run_sql_screen.py --k 8
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import forge                      # for Actor and the Ollama config ONLY
from domains.sql import SQL_SYSTEM, SqlVerifier, TASKS
from domains.sql import harness, runtime

OUT = Path(__file__).with_name("data") / "sql_screen.jsonl"
# Per-run detail is overwritten; the SUMMARY of every run is appended here and
# never rewritten. One run is a nomination, not a measurement -- build_ruler.py's
# own docstring says admission at n=40 has se ~= 0.077, and this screen's k=8 has
# se ~= 0.177 at p=0.5, which is wider than half the band. Replicates accumulate
# so that instability is visible instead of being re-discovered each time.
HISTORY = Path(__file__).with_name("data") / "sql_screen_history.jsonl"
BAND_LO, BAND_HI = 0.2, 0.8


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=8, help="candidates per task")
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--model", default=forge.MODEL_NAME)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    actor = forge.Actor(forge.OLLAMA_URL, args.model)
    verifier = SqlVerifier()
    ident = runtime.identity()

    # THE RECEIPT. Ground truth here is a function of the reference query, the
    # fixture bytes and the ENGINE, and the rates are a function of the SAMPLER.
    # All four go in the header or two runs of this file are not comparable --
    # which is section 71's lesson arriving in a domain with no interpreter.
    receipt = {
        "kind": "sql_screen_receipt",
        "engine": ident,
        "model": args.model,
        "sampler": {"temperature": args.temp, "k": args.k,
                    "greedy_anchor": False,
                    "num_ctx": 2048},
        "n_tasks": len(TASKS),
        "fixture_sha256": TASKS[0].fixture_sha256,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(json.dumps(receipt, indent=2))
    print()

    rows, t0 = [], time.perf_counter()
    out_path = Path(args.out)
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt) + "\n")
        for i, task in enumerate(TASKS, 1):
            prompt = harness.user_prompt(task.prompt, task.fixture)
            scores, exact, unjudgeable, errors = [], 0, 0, {}
            for _ in range(args.k):
                try:
                    reply = actor.generate(prompt, SQL_SYSTEM, args.temp)
                except Exception as e:                       # noqa: BLE001
                    unjudgeable += 1
                    errors[f"generation failed: {e.__class__.__name__}"] = \
                        errors.get(f"generation failed: {e.__class__.__name__}", 0) + 1
                    continue
                s = verifier.score(reply, task)
                if not s.judgeable:
                    unjudgeable += 1
                    continue
                scores.append(s.reward)
                exact += int(s.exact)
                if s.error:
                    key = s.denied or s.error.split(":")[0]
                    errors[key] = errors.get(key, 0) + 1

            n = len(scores)
            rate = exact / n if n else 0.0
            mean = statistics.fmean(scores) if scores else 0.0
            partial = sum(1 for x in scores if 0.0 < x < 1.0)
            row = {"tid": task.tid, "task_sha256": task.task_sha256,
                   "ordered": task.ordered, "note": task.note,
                   "n_judged": n, "n_unjudgeable": unjudgeable,
                   "exact_rate": round(rate, 4),
                   "mean_reward": round(mean, 4),
                   "n_partial": partial,
                   "scores": [round(x, 4) for x in scores],
                   "errors": errors}
            rows.append(row)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            band = "IN " if BAND_LO <= rate <= BAND_HI else "out"
            print(f"[{i:2d}/{len(TASKS)}] {task.tid:26s} "
                  f"exact {rate:5.2f} [{band}]  mean {mean:5.3f}  "
                  f"partial {partial}/{n}  {task.note[:34]}")

    actor.release()
    dt = time.perf_counter() - t0

    print()
    print("=" * 78)
    in_band = [r for r in rows if BAND_LO <= r["exact_rate"] <= BAND_HI]
    floor = [r for r in rows if r["exact_rate"] == 0.0]
    ceil = [r for r in rows if r["exact_rate"] == 1.0]
    all_scores = [x for r in rows for x in r["scores"]]
    graded = [x for x in all_scores if 0.0 < x < 1.0]
    print(f"tasks in [{BAND_LO}, {BAND_HI}] on EXACT match : "
          f"{len(in_band)}/{len(rows)}   {[r['tid'] for r in in_band]}")
    print(f"tasks at the floor (0.00)                : {len(floor)}  "
          f"{[r['tid'] for r in floor]}")
    print(f"tasks at the ceiling (1.00)              : {len(ceil)}  "
          f"{[r['tid'] for r in ceil]}")
    print(f"mean exact rate over tasks               : "
          f"{statistics.fmean(r['exact_rate'] for r in rows):.4f}")
    print(f"mean SCALAR reward over tasks            : "
          f"{statistics.fmean(r['mean_reward'] for r in rows):.4f}")
    print(f"candidates scored strictly between 0 & 1 : "
          f"{len(graded)}/{len(all_scores)} "
          f"({len(graded)/max(len(all_scores),1):.1%})")
    print(f"unjudgeable (timeout / generation error) : "
          f"{sum(r['n_unjudgeable'] for r in rows)}")
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            **receipt,
            "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "seconds": round(dt, 1),
            "exact_rate_by_tid": {r["tid"]: r["exact_rate"] for r in rows},
            "mean_reward_by_tid": {r["tid"]: r["mean_reward"] for r in rows},
            "in_band": [r["tid"] for r in in_band],
            "mean_exact_rate": round(
                statistics.fmean(r["exact_rate"] for r in rows), 4),
            "mean_scalar_reward": round(
                statistics.fmean(r["mean_reward"] for r in rows), 4),
            "graded_share": round(len(graded) / max(len(all_scores), 1), 4),
        }) + "\n")
    print(f"wrote {out_path}   ({dt:.0f}s)")
    print(f"appended a run summary to {HISTORY.name} "
          f"({sum(1 for _ in HISTORY.open(encoding='utf-8'))} run(s) banked)")
    rescued = [r["tid"] for r in rows
               if r["exact_rate"] == 0.0 and r["mean_reward"] > 0.0]
    print()
    print(f"tasks DEAD on exact match but alive on the scalar : "
          f"{len(rescued)}/{len(floor)}  {rescued}")
    print("That last line is the whole case for a scalar reward, and it is a "
          "smaller case\nthan expected: a wrong query usually groups or joins "
          "differently and returns a\nrow set disjoint from the answer key, so "
          "it scores 0.0 anyway. Overlap is a\ngraded metric over an outcome "
          "space that is nearly bimodal. What it buys is\nthat a task at the "
          "floor still produces a gradient.")


if __name__ == "__main__":
    main()
