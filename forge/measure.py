#!/usr/bin/env python3
"""measure.py — NIGHT 1: measurement before any training.

Two things, no gradients, local Ollama only:

  1. NOISE FLOOR — run the ruler (eval.py) 3x on the UNCHANGED baseline. The
     aggregate pass@1 wobbles run-to-run at temp>0; that wobble is the smallest
     delta a future training run must beat to mean anything. Never reported before.

  2. FRONTIER RESOLUTION — 0/5 is not 0. Sample the frontier tasks at high n
     (rotate n=100, rle n=50, temp 1.0) with a Wilson 95% CI. Outcomes:
       rotate > 0/100  -> it is SELF-lane (higher K reaches it); the external-
                          reference premise for it dissolves. STOP and report.
       rotate 0/100    -> a zero-background detector: >=5/100 after training would
                          be decisive. Sets up NIGHT 2's pre-registered experiment.

Writes data/night1_measurement.json and appends the frontier probes to
data/eval_history.jsonl. Reuses eval.HELD_OUT + forge so ground truth is identical.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import eval as ev
import forge

NOISE_RUNS   = 3
FRONTIER = {"rotate": 100, "rle": 50}
FRONTIER_TEMP = 1.0
OUT = forge.OUT_DIR


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI for a binomial pass rate."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - m) / d, 4), round((c + m) / d, 4))


def noise_floor() -> dict:
    print(f"[1/2] noise floor: {NOISE_RUNS} baseline eval runs...")
    runs = []
    for i in range(NOISE_RUNS):
        print(f"  run {i + 1}/{NOISE_RUNS}")
        r = ev.evaluate(forge.MODEL_NAME)
        if not r:
            return {"error": "eval failed (Ollama down or model missing)"}
        runs.append(r["aggregate"])
    p1 = [r["pass@1"] for r in runs]
    p3 = [r["pass@3"] for r in runs]
    mean = sum(p1) / len(p1)
    std = (sum((x - mean) ** 2 for x in p1) / len(p1)) ** 0.5
    return {
        "runs": runs,
        "pass@1_values": p1, "pass@3_values": p3,
        "pass@1_mean": round(mean, 4),
        "pass@1_std": round(std, 4),
        "pass@1_range": round(max(p1) - min(p1), 4),
        "note": "a future training delta below ~pass@1_range is indistinguishable from noise",
    }


def frontier() -> dict:
    print("[2/2] frontier resolution...")
    tasks = {t.tid: t for t in ev.HELD_OUT}
    actor = forge.Actor(forge.OLLAMA_URL, forge.MODEL_NAME)
    out = {}
    for tid, n in FRONTIER.items():
        task = tasks[tid]
        # Same defect as eval.py: a transport failure is not a failed solution.
        # Rate is over samples actually scored, and the shortfall is reported.
        c = scored = errors = 0
        for j in range(n):
            try:
                code = forge.extract_code(
                    actor.generate(task.prompt, forge.ACTOR_SYSTEM, FRONTIER_TEMP))
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            scored += 1
            if forge.verify(code, task).ok:
                c += 1
        if scored == 0:
            out[tid] = {"passes": 0, "n": 0, "requested": n, "gen_errors": errors,
                        "rate": None, "wilson95": None, "lane": "UNMEASURED"}
            print(f"  {tid}: UNMEASURED - all {n} samples failed to generate")
            continue
        lo, hi = wilson(c, scored)
        out[tid] = {"passes": c, "n": scored, "requested": n, "gen_errors": errors,
                    "rate": round(c / scored, 4), "wilson95": [lo, hi],
                    "lane": "self (>0)" if c > 0 else "candidate 0-mass"}
        flag = f"  [{errors} gen error(s)]" if errors else ""
        print(f"  {tid}: {c}/{scored}  rate={c/scored:.3f}  95%CI=[{lo},{hi}]{flag}")
    actor.release()
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    result = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": forge.MODEL_NAME}
    result["noise_floor"] = noise_floor()
    result["frontier"] = frontier()
    result["wall_clock_s"] = round(time.time() - t0, 1)

    (OUT / "night1_measurement.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False))
    with (OUT / "eval_history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": result["ts"], "kind": "night1_frontier",
                            "frontier": result["frontier"]}, ensure_ascii=False) + "\n")

    print("\n=== NIGHT 1 SUMMARY ===")
    nf = result["noise_floor"]
    print(f"noise floor pass@1: {nf.get('pass@1_values')} "
          f"(range {nf.get('pass@1_range')}, std {nf.get('pass@1_std')})")
    rot = result["frontier"].get("rotate", {})
    verdict = ("rotate is SELF-lane -> reroute (no external reference needed)"
               if rot.get("passes", 0) > 0
               else "rotate is candidate 0-mass -> zero-background detector for NIGHT 2")
    print(f"VERDICT: {verdict}")
    print(f"wrote {OUT / 'night1_measurement.json'}  ({result['wall_clock_s']}s)")


if __name__ == "__main__":
    main()
