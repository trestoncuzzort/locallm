#!/usr/bin/env python3
"""screen_tasks.py — import candidate tasks and screen them into a usable ruler.

The current held-out set is saturated: 6 of its 10 tasks scored a perfect 1.000 in
all 57 logged runs, so they carry no signal in either direction and only 4 tasks can
actually move. A task pinned at 1.0 or 0.0 contributes zero variance, which is why
the admission criterion is a BAND rather than a quality bar:

    admit a task only if the base model's pass rate sits in [0.2, 0.8]

That criterion is derived from the instrument's job, not eyeballed: outside the band
a task cannot register a change. It also doubles as a contamination filter — anything
the base model memorised in pretraining scores ~1.0 and is rejected automatically,
which is the weakness eval.py's own docstring concedes it cannot otherwise rule out.

HOW MANY TASKS THIS NEEDS: see the SIZING block below. The figures are deliberately
NOT restated in this docstring. They were superseded once already - section 54
re-derived the per-task sd from the admitted set rather than the old instrument and
the required count moved 5.16x - and three copies of the old numbers survived in
this file afterwards because each had to be found and edited by hand. One
definition, referenced everywhere that needs it.

SOURCE — AceCode-89K (TIGER-Lab), MIT licensed, bare `assert` test cases. Chosen over
KodCode-V1 deliberately: KodCode is CC BY-NC 4.0, and non-commercial rows cannot ship
from an MIT repo that publishes its dataset. Downloading is not redistributing, so
KodCode remains fine to screen against locally, but nothing derived from it may be
committed or published. See OPEN-ITEMS.md.

TWO STAGES, because precision is only worth paying for on survivors. Rejecting a task
stuck at 1.0 does not need n=100 — a handful of samples settles it. Stage 1 discards
the obvious ceiling/floor cases cheaply; stage 2 spends real samples only on what
survived. Same admissions, a fraction of the GPU time.

    python screen_tasks.py                     # default: 200 candidates
    python screen_tasks.py --candidates 400
    python screen_tasks.py --stage1 8 --stage2 40

Resumable: results append to data/screen_results.jsonl and already-screened ids are
skipped, so an interrupted overnight run picks up where it stopped. Honours the
council/STOP file like the other long-running jobs here.
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import re
import sys
import time
from pathlib import Path

import forge
import venv_guard

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "screen_results.jsonl"
STOP = HERE / "council" / "STOP"
ACECODE_GLOB = str(Path.home() / ".cache/huggingface/hub/datasets--TIGER-Lab--AceCode-89K"
                                 "/snapshots/*/data/*.parquet")

# One unique function called by every assert, or we cannot bind an entry point.
CALL = re.compile(r"\bassert\s+(?:not\s+)?([A-Za-z_]\w*)\s*\(")
BAND_LO, BAND_HI = 0.2, 0.8

# --------------------------------------------------------------------------
# SIZING - the single definition. Nothing else in this file restates a number.
#
# Derivation (section 54, re-derived from the 30 admitted pilot tasks, NOT from
# the old saturated instrument): mean p(1-p) over admitted = 0.2230, so per-task
# sd at N_SAMPLES=5 is 0.2108 against the old instrument's 0.0928 - a ratio of
# 2.27, so the required count scales 5.16x.
#
#   G_per_arm = 2*(z_.025 + z_.20)^2 * mean(p(1-p)) / delta^2,  T*k*N_SAMPLES = G
#
# POWER DEPENDS ON TOTAL GENERATIONS PER ARM, NOT ON TASK COUNT (council section
# 59, finding 2, verified). T=155/k=5, T=78/k=10 and T=39/k=20 have identical
# power. Task count is therefore a GENERALISATION decision, not a power decision:
# the formula estimates the change in mean pass rate ON THESE T TASKS. Claiming
# "the model improved at code generation" needs an extra tau^2/T heterogeneity
# term this omits. Pre-register which estimand is meant.
#
# CONDITIONAL, and the condition is unmet: every figure assumes run-to-run noise
# is pure sampling. That ratio (0.98) was measured on the OLD ten-task
# instrument. The new instrument's noise floor is UNMEASURED. If a systematic
# term of even 0.005 exists, the large-k rows below are void.
# --------------------------------------------------------------------------
N_SAMPLES = 5           # generations per eval run; must match eval.py:37
SIZING = {
    # delta_pp: generations per arm needed at 80% power, alpha=.05 two-sided
    3.0: 3889,
    5.0: 1400,
}
DEFAULT_DELTA_PP = 3.0
DEFAULT_K = 10          # eval runs per task; the cheaper shape from section 56


def tasks_needed(delta_pp: float = DEFAULT_DELTA_PP, k: int = DEFAULT_K) -> int:
    """Admitted tasks required to detect delta_pp at k eval runs of N_SAMPLES."""
    return -(-SIZING[delta_pp] // (k * N_SAMPLES))          # ceiling division


def wilson(c: int, n: int) -> tuple[float, float]:
    """95% Wilson interval - correct near 0 and 1, where normal approx is not."""
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def candidates(limit: int, seed: int, stratum: str | None = None) -> list[dict]:
    """Random sample, not the head of the file, so the admitted set is not an
    artifact of dataset ordering."""
    import pyarrow.parquet as pq
    files = sorted(glob.glob(ACECODE_GLOB))
    if not files:
        raise SystemExit(f"AceCode parquet not found at {ACECODE_GLOB}")
    rng = random.Random(seed)
    rows: list[dict] = []
    for f in files:
        t = pq.read_table(f, columns=["id", "source", "question", "test_cases"])
        rows.extend(t.to_pylist())
    if stratum:
        before = len(rows)
        rows = [r for r in rows if r.get("source") == stratum]
        print(f"[screen] stratum '{stratum}': {len(rows):,} of {before:,} rows eligible")
        if not rows:
            raise SystemExit(f"no rows with source={stratum!r}")
    rng.shuffle(rows)

    taken, out = 0, []
    reserved = {t.tid for t in forge.SEED_TASKS}
    import eval as ev
    reserved |= {t.tid for t in ev.HELD_OUT}
    for r in rows:
        if taken >= limit:
            break
        tcs = [str(x) for x in (r.get("test_cases") or [])]
        if not tcs or not all(x.strip().startswith("assert") for x in tcs):
            continue
        names = {m.group(1) for x in tcs if (m := CALL.search(x))}
        if len(names) != 1:
            continue
        entry = names.pop()
        body = "\n".join(tcs)
        if forge.BANNED.search(body) or forge.BANNED.search(r.get("question") or ""):
            continue
        tid = f"ace_{r['id']}"
        if tid in reserved:
            continue
        out.append({"tid": tid, "entry": entry, "prompt": r["question"], "tests": tcs})
        taken += 1
    return out


def as_task(c: dict) -> forge.Task:
    """AceCode asserts call the function by its own global name; forge's harness
    passes the (return-type-guarded) entry point into run_tests. Bind the name
    locally so the asserts run unchanged against the guarded function."""
    indented = "\n".join("    " + line.strip() for line in c["tests"])
    tests = f"def run_tests(_f):\n    {c['entry']} = _f\n{indented}\n"
    return forge.Task(c["tid"], c["prompt"], c["entry"], tests)


def rate(actor: forge.Actor, task: forge.Task, n: int, temp: float) -> tuple[int, int]:
    """Returns (passed, scored). A generation error is NOT a failed solution."""
    ok = scored = 0
    for _ in range(n):
        try:
            raw = actor.generate(task.prompt, forge.ACTOR_SYSTEM, temp)
        except Exception:  # noqa: BLE001
            continue
        scored += 1
        if forge.verify(forge.extract_code(raw), task).ok:
            ok += 1
    return ok, scored


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=int, default=200)
    ap.add_argument("--stage1", type=int, default=8, help="cheap ceiling/floor reject")
    ap.add_argument("--stage2", type=int, default=40, help="precision on survivors")
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--target", type=int, default=tasks_needed(),
                    help=f"stop once this many admitted (default {tasks_needed()} "
                         f"= detect {DEFAULT_DELTA_PP}pp at k={DEFAULT_K}; see SIZING)")
    ap.add_argument("--stratum", default=None,
                    help="restrict to one AceCode source stratum. 'oss' is MIT and is "
                         "the default choice on SUPPLY grounds - 25,862 eligible rows "
                         "against a draw of a few hundred. bigcode_python_fns descends "
                         "from a dataset whose own card states no licence and stays "
                         "excluded. evol is NOT unverified: council section 59 walked "
                         "it to Apache-2.0 (Magicoder-Evol-Instruct-110K <- "
                         "evol-codealpaca-v1 <- CodeAlpaca-20k CC-BY-4.0) and it is "
                         "publishable from an MIT repo with Apache section 4(b) "
                         "changed-file notices. It is excluded for supply and "
                         "single-licence simplicity, not provenance. Note both strata "
                         "are OpenAI-model-generated; that caveat does not "
                         "discriminate between them.")
    args = ap.parse_args()

    OUT.parent.mkdir(exist_ok=True)
    done = set()
    if OUT.exists():
        for line in OUT.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["tid"])
            except (json.JSONDecodeError, KeyError):
                pass
    admitted = sum(1 for line in (OUT.open(encoding="utf-8") if OUT.exists() else [])
                   if '"admitted": true' in line)

    cands = [c for c in candidates(args.candidates, args.seed, args.stratum)
             if c["tid"] not in done]
    print(f"[screen] {len(cands)} candidates to screen "
          f"({len(done)} already done, {admitted} admitted so far)")
    print(f"[screen] band [{BAND_LO}, {BAND_HI}] | stage1 n={args.stage1} "
          f"stage2 n={args.stage2} | target {args.target}")

    actor = forge.Actor(forge.OLLAMA_URL, forge.MODEL_NAME)
    t0 = time.time()
    for i, c in enumerate(cands, 1):
        if STOP.exists():
            print("[screen] STOP file present - halting cleanly.")
            break
        if admitted >= args.target:
            print(f"[screen] target of {args.target} admitted tasks reached.")
            break
        task = as_task(c)
        ok1, n1 = rate(actor, task, args.stage1, args.temp)
        rec = {"tid": c["tid"], "entry": c["entry"], "stage1": [ok1, n1]}
        if n1 == 0:
            rec |= {"admitted": False, "why": "no samples generated"}
        elif ok1 == 0 or ok1 == n1:
            # Pinned at floor or ceiling on the cheap stage: cannot carry signal.
            rec |= {"admitted": False,
                    "why": f"stage1 {ok1}/{n1} - at {'ceiling' if ok1 else 'floor'}"}
        else:
            ok2, n2 = rate(actor, task, args.stage2, args.temp)
            r = ok2 / n2 if n2 else 0.0
            lo, hi = wilson(ok2, n2)
            inside = BAND_LO <= r <= BAND_HI
            rec |= {"stage2": [ok2, n2], "rate": round(r, 4), "wilson95": [lo, hi],
                    "admitted": inside,
                    "why": "in band" if inside else f"rate {r:.2f} outside band"}
            if inside:
                rec["task"] = c            # keep everything needed to build the task
                admitted += 1
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        mins = (time.time() - t0) / 60
        print(f"  [{i}/{len(cands)}] {c['tid']:<28} {rec['why']:<34} "
              f"admitted={admitted} ({mins:.1f}m)")

    actor.release()
    print(f"\n[screen] done. {admitted} admitted -> {OUT}")
    for d in sorted(SIZING):
        print(f"[screen] detect {d}pp: needs {tasks_needed(d, DEFAULT_K)} tasks "
              f"at k={DEFAULT_K}, or {tasks_needed(d, 5)} at k=5 "
              f"({SIZING[d]:,} generations/arm either way)")
    print("[screen] all of the above assume run-to-run noise is pure sampling. "
          "The new instrument's noise floor is UNMEASURED - measure it before "
          "trusting any large-k row.")


if __name__ == "__main__":
    venv_guard.ensure(__file__, "pyarrow")
    main()
