#!/usr/bin/env python3
"""build_ruler.py — turn a screened band into a held-out ruler that can actually move.

WHY THIS EXISTS. eval.py's HELD_OUT bank is spent, measured (section 64): base
pass@20 == pass@5 == pass@3 == 0.9000 exactly, six tasks at 20/20, `rotate` at
0/20. Nine of ten tasks are solvable and the base already sits at 0.87 pass@1, so
the entire measurable range of that instrument is THREE percentage points against
a corrected MDE of ~2.6pp. A held-out null measured on it was never evidence
about training.

The replacement is drawn from the screened oss band, where admission requires the
base model's pass rate to sit inside [BAND_LO, BAND_HI] — i.e. every task can
move in both directions by construction.

TWO THINGS THIS FILE IS CAREFUL ABOUT, both from council section 62:

1. SELECTION ON NOISE (leftover-risk 6, and section 50 finding 5 before it).
   The screen admits on a stage-2 estimate at n=40, where se ~= 0.077 at p=0.5.
   Tasks measured at 0.22 or 0.78 include some whose TRUE rate is outside the
   band; freezing those straight into a ruler imports the selection error and
   they behave as partial floor/ceiling tasks at eval time. So admission here is
   a NOMINATION, not a decision: `confirm` re-measures every nominee at a higher
   n and keeps only those still in band. Regression to the mean is expected and
   is the point.

2. POOL DISJOINTNESS. The same screened pool is the natural source for training
   prompts. If a task can land in both, the ruler stops being held out. The split
   here is deterministic (sha256 of tid) so it is reproducible and so a later
   training draw can take the complement without coordination.

Run:
    python build_ruler.py nominate                 # CPU only, from screen results
    python build_ruler.py confirm --n 60           # GPU: re-measure nominees
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import forge
import screen_tasks
import venv_guard

HERE = Path(__file__).resolve().parent
SCREEN = HERE / "data" / "screen_results.jsonl"
NOMINEES = HERE / "data" / "ruler_nominees.json"
RULER = HERE / "data" / "ruler_confirmed.json"
FROZEN = HERE / "data" / "ruler_frozen.json"
NOISE = HERE / "data" / "ruler_noise.jsonl"

# Fraction of the admitted band reserved for the RULER. The rest is the training
# pool. Ruler-first because the ruler is currently the binding constraint
# (section 64); revisit when it is not.
RULER_SHARE = 0.5


def split_side(tid: str) -> str:
    """Deterministic, reproducible, and independent of draw order or count.

    Hashing the tid means a task's side never changes when the pool grows, so a
    later training draw can take the complement without re-running this.
    """
    h = int(hashlib.sha256(tid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ruler" if h < RULER_SHARE else "train"


def load_admitted() -> list[dict]:
    if not SCREEN.exists():
        raise SystemExit(f"no screen results at {SCREEN}; run screen_tasks.py first")
    rows = [json.loads(l) for l in SCREEN.open(encoding="utf-8")]
    return [r for r in rows if r.get("admitted")]


def cmd_nominate(args: argparse.Namespace) -> None:
    admitted = load_admitted()
    ruler = [r for r in admitted if split_side(r["tid"]) == "ruler"]
    train = [r for r in admitted if split_side(r["tid"]) == "train"]

    print(f"admitted in band : {len(admitted)}")
    print(f"  -> ruler side  : {len(ruler)}")
    print(f"  -> train side  : {len(train)}   (complement, reserved, not used here)")

    # Distance from the band edge, as a selection-on-noise risk flag. A task
    # admitted at 0.21 is far likelier to fall out on re-measurement than one at
    # 0.50. This does NOT filter — confirm() decides — it just makes the risk
    # visible before any GPU time is spent.
    mid = (screen_tasks.BAND_LO + screen_tasks.BAND_HI) / 2
    edge = [r for r in ruler if abs(r["rate"] - mid) > 0.25]
    print(f"\nnominees within {screen_tasks.BAND_LO}-{screen_tasks.BAND_HI}, "
          f"{len(edge)} of {len(ruler)} sit >0.25 from band centre {mid} "
          f"(most likely to regress out on re-measurement)")

    NOMINEES.parent.mkdir(exist_ok=True)
    NOMINEES.write_text(json.dumps(
        {"ruler_nominees": [r["tid"] for r in ruler],
         "train_reserved": [r["tid"] for r in train],
         "band": [screen_tasks.BAND_LO, screen_tasks.BAND_HI],
         "ruler_share": RULER_SHARE,
         "screen_rates": {r["tid"]: r["rate"] for r in ruler}},
        indent=2), encoding="utf-8")
    print(f"\nwrote {NOMINEES}")
    print("NOMINATED, NOT CONFIRMED. These rates are stage-2 estimates at n=40 "
          "and have not survived a second measurement yet.")


def cmd_confirm(args: argparse.Namespace) -> None:
    if not NOMINEES.exists():
        raise SystemExit(f"run `nominate` first; {NOMINEES} missing")
    spec = json.loads(NOMINEES.read_text(encoding="utf-8"))
    want = set(spec["ruler_nominees"])

    # Rebuild full task objects (prompt/entry/tests) from the same draw the
    # screen used, so a nominee's identity is its tid and nothing is re-derived.
    pool = {c["tid"]: c for c in screen_tasks.candidates(args.draw, args.seed, "oss")}
    missing = want - pool.keys()
    if missing:
        print(f"[!] {len(missing)} nominees not in a draw of {args.draw}; "
              f"raise --draw. Missing e.g. {sorted(missing)[:3]}")
    tasks = [screen_tasks.as_task(pool[t]) for t in sorted(want & pool.keys())]
    print(f"re-measuring {len(tasks)} nominees at n={args.n} "
          f"(screen used n=40; se falls ~{(40/args.n)**0.5:.2f}x)\n")

    actor = forge.Actor(forge.OLLAMA_URL, args.model)
    kept, dropped = [], []
    for t in tasks:
        c, n = screen_tasks.rate(actor, t, args.n, args.temp)
        p = c / n if n else 0.0
        lo, hi = screen_tasks.wilson(c, n)
        was = spec["screen_rates"].get(t.tid)
        inband = screen_tasks.BAND_LO <= p <= screen_tasks.BAND_HI
        (kept if inband else dropped).append(
            {"tid": t.tid, "screen_rate": was, "confirmed_rate": round(p, 4),
             "n": n, "wilson95": [round(lo, 4), round(hi, 4)]})
        print(f"  {t.tid:<20} screen {was:.2f} -> confirmed {p:.2f} "
              f"[{lo:.2f},{hi:.2f}]  {'KEEP' if inband else 'DROP (regressed out)'}")
    actor.release()

    print(f"\nkept {len(kept)} / dropped {len(dropped)}")
    if dropped:
        moved = sum(abs(d["confirmed_rate"] - d["screen_rate"]) for d in dropped) / len(dropped)
        print(f"dropped nominees moved {moved:.3f} on average — that is the "
              f"selection-on-noise the screen's n=40 could not resolve, made visible")
    RULER.write_text(json.dumps(
        {"model": args.model, "n": args.n, "temp": args.temp,
         "band": spec["band"], "kept": kept, "dropped": dropped}, indent=2),
        encoding="utf-8")
    print(f"wrote {RULER}")
    print("\nThis is a CONFIRMED BAND, not yet a frozen ruler. Freezing means "
          "pinning these tids and never screening against them again.")


def verify_frozen() -> dict:
    """THE FREEZE GATE. Returns the frozen spec only if the tasks on disk still
    hash to it; raises otherwise.

    Council activation #17 finding F2: `freeze` wrote ruler_set_sha256 and NOTHING
    read it. A hash nobody checks is a comment. This is the same "parse, don't
    validate" shape dataset_gate.load_verified already uses for training data --
    make the checked thing the only way to obtain what you need, so the check
    cannot be skipped by forgetting a line.

    It recomputes each task's hash from the stored screen payload, so a silently
    edited prompt or test body fails here rather than quietly changing what the
    ruler measures.
    """
    if not FROZEN.exists():
        raise SystemExit(
            f"{FROZEN.name} missing - the ruler is not frozen. Run: "
            f"python build_ruler.py freeze")
    spec = json.loads(FROZEN.read_text(encoding="utf-8"))

    payloads = {}
    for line in SCREEN.open(encoding="utf-8"):
        r = json.loads(line)
        if r.get("admitted") and r.get("task"):
            payloads[r["tid"]] = r["task"]

    def sha(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(p.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    problems = []
    for tid, rec in spec["ruler"].items():
        c = payloads.get(tid)
        if c is None:
            problems.append(f"{tid}: no stored payload")
            continue
        body = "\n".join(str(x) for x in c["tests"])
        if sha(c["prompt"], c["entry"], body) != rec["task_sha256"]:
            problems.append(f"{tid}: task bytes changed since freezing")
    if problems:
        raise SystemExit(
            "FROZEN RULER GATE: the ruler on disk is not the ruler that was "
            "frozen.\n  " + "\n  ".join(problems[:8]) +
            "\n  Measuring against it would compare to a different instrument.")

    recomputed = sha(*[f"{t}:{spec['ruler'][t]['task_sha256']}"
                       for t in sorted(spec["ruler"])])
    if recomputed != spec["ruler_set_sha256"]:
        raise SystemExit(
            f"FROZEN RULER GATE: set hash mismatch.\n"
            f"  recorded   {spec['ruler_set_sha256']}\n"
            f"  recomputed {recomputed}\n"
            f"  The task list itself was edited after freezing.")
    return spec


def cmd_freeze(args: argparse.Namespace) -> None:
    """Pin the ruler and declare the training split in ONE act.

    Section 70 deferred this deliberately and said why: freezing is irreversible
    in the sense that matters (a task that has been looked at cannot be
    un-looked-at), and it must happen in the same act as declaring the training
    split so the disjointness is recorded once rather than asserted twice.

    IT PINS THE TASKS, NOT ONLY THE TIDS. A tid is a pointer; if the payload it
    points at can change, nothing is frozen. Commit a7fa36b learned this on the
    dataset receipt ("the receipt now pins the verifier, not only the data") and
    it applies with more force here, because the tests ARE the reward signal. So
    every task's prompt, entry point and test body are hashed individually and
    the set gets a hash of its own.

    THE FOUR DROPPED NOMINEES GO NOWHERE, on purpose. They sit on the ruler side
    of split_side() but failed confirmation, so they are excluded from the ruler.
    Moving them to training would be the obvious tidy-up and it would break the
    one property the sha256 split exists for: that a later training draw can take
    the complement with NO coordination and no exception list. An exception list
    is a second source of truth about who is on which side. They are recorded as
    excluded-from-both with the reason attached.
    """
    if FROZEN.exists() and not args.force:
        raise SystemExit(
            f"{FROZEN} already exists. Freezing twice silently is how a ruler "
            f"quietly changes identity; pass --force only if you mean to replace "
            f"it, and say so in the channel.")
    if not RULER.exists():
        raise SystemExit(f"run `confirm` first; {RULER} missing")
    spec = json.loads(RULER.read_text(encoding="utf-8"))
    nom = json.loads(NOMINEES.read_text(encoding="utf-8"))

    kept = {k["tid"]: k for k in spec["kept"]}
    dropped = {d["tid"]: d for d in spec["dropped"]}
    train = list(nom["train_reserved"])

    payloads = {}
    for line in SCREEN.open(encoding="utf-8"):
        r = json.loads(line)
        if r.get("admitted") and r.get("task"):
            payloads[r["tid"]] = r["task"]

    # ---- the checks, all of them fatal ---------------------------------
    problems = []
    missing = sorted(set(kept) - set(payloads))
    if missing:
        problems.append(f"{len(missing)} ruler tids have no stored payload: {missing[:5]}")
    overlap = sorted(set(kept) & set(train))
    if overlap:
        problems.append(f"ruler and training pool OVERLAP on {overlap}")
    misside = sorted(t for t in kept if split_side(t) != "ruler")
    if misside:
        problems.append(f"{len(misside)} ruler tids hash to the train side: {misside[:5]}")
    mistrain = sorted(t for t in train if split_side(t) != "train")
    if mistrain:
        problems.append(f"{len(mistrain)} training tids hash to the ruler side: {mistrain[:5]}")
    import eval as ev
    reserved = {t.tid for t in forge.SEED_TASKS} | {t.tid for t in ev.HELD_OUT}
    clash = sorted((set(kept) | set(train)) & reserved)
    if clash:
        problems.append(f"tids collide with SEED_TASKS/HELD_OUT: {clash}")
    if problems:
        for p in problems:
            print(f"[!] {p}")
        raise SystemExit("refusing to freeze an inconsistent ruler")

    # ---- what the band's numbers rest on, said out loud ----------------
    # confirm measured pure temp 0.8; eval.py scores 1 greedy + 4 at 0.8. The
    # band has to hold under the instrument that will actually be used.
    # NO SAMPLE-DEPENDENT MEASUREMENTS GO IN HERE. An earlier version recorded a
    # per-task eval_instrument_rate averaged over whatever replicates existed at
    # freeze time, which meant the FROZEN artifact went stale the moment another
    # replicate was banked -- it said 3 tasks were out of band at n=10 and 4 at
    # n=40. Council activation #17 named the fix: a frozen file should contain
    # only what is actually frozen. Measured rates live in the analysis artifacts
    # (council/ruler_noise_analysis_*.txt), which are dated and re-derivable.
    # confirmed_rate stays because it is ADMISSION PROVENANCE - the number that
    # decided membership - not a live measurement of the instrument.
    #
    # WHAT IS LEFT HERE IS A WARNING, NOT A WRITE, AND ITS CONDITION IS NOW
    # SPELLED OUT. Council #18 (section 82, F3) found the line below attached to
    # a bare `else:` that bound to `if problems:` above -- the comment block does
    # not end a suite, so the `if NOISE.exists():` head removed by the section-77
    # edit left its `else` bound to the nearest preceding `if`. It therefore
    # fired on every SUCCESSFUL freeze, announcing that ruler_noise.jsonl was
    # missing while the file sat on disk at 209,606 bytes. A red warning printed
    # on a green path is section 79's rule inverted: the next person believes the
    # text over the mark.
    if not NOISE.exists():
        print(f"[!] {NOISE.name} absent - the band is confirmed only under the "
              f"SCREEN's sampler. Nothing has measured it under the eval "
              f"instrument, so how it behaves there is unknown.")

    def sha(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(p.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    tasks = {}
    for t in sorted(kept):
        c = payloads[t]
        body = "\n".join(str(x) for x in c["tests"])
        tasks[t] = {
            "entry": c["entry"],
            "prompt_sha256": sha(c["prompt"]),
            "tests_sha256": sha(body),
            "task_sha256": sha(c["prompt"], c["entry"], body),
            "confirmed_rate": kept[t]["confirmed_rate"],
            "confirmed_n": kept[t]["n"],
            "wilson95": kept[t]["wilson95"],
        }
    set_sha = sha(*[f"{t}:{tasks[t]['task_sha256']}" for t in sorted(tasks)])

    FROZEN.write_text(json.dumps({
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": spec["model"],
        "band": spec["band"],
        "ruler_set_sha256": set_sha,
        "n_ruler": len(tasks),
        "ruler": tasks,
        "training_pool": sorted(train),
        "n_training_pool": len(train),
        "excluded_from_both": {
            t: {"reason": "nominated to the ruler side by split_side(), then "
                          "regressed out of band on confirmation; NOT moved to "
                          "training because the sha256 split must stay the only "
                          "source of truth about sides",
                "screen_rate": dropped[t]["screen_rate"],
                "confirmed_rate": dropped[t]["confirmed_rate"]}
            for t in sorted(dropped)},
        "split": {"function": "sha256(tid)[:8] / 0xFFFFFFFF < RULER_SHARE",
                  "ruler_share": RULER_SHARE},
        "checks_passed": [
            "every ruler tid has a stored task payload",
            "ruler and training pool are disjoint",
            "every ruler tid hashes to the ruler side",
            "every training tid hashes to the train side",
            "no tid collides with forge.SEED_TASKS or eval.HELD_OUT",
        ],
        "measured_rates_live_where":
            "council/ruler_noise_analysis_*.txt - sample-dependent figures are "
            "deliberately NOT frozen here (council #17): an eval-instrument rate "
            "averaged over whatever replicates existed at freeze time goes stale "
            "the moment another is banked.",
    }, indent=2), encoding="utf-8")

    print(f"\nFROZEN {len(tasks)} ruler tasks -> {FROZEN}")
    print(f"  ruler set sha256      {set_sha}")
    print(f"  training pool         {len(train)} tids (disjoint by construction)")
    print(f"  excluded from both    {len(dropped)} dropped nominees")
    for p in json.loads(FROZEN.read_text(encoding="utf-8"))["checks_passed"]:
        print(f"  [ok] {p}")
    print("\nThis ruler is now pinned, and the pin is ENFORCED: "
          "build_ruler.verify_frozen() re-hashes every task from its stored "
          "payload and runs before anything measures against it. Nothing may "
          "screen against these tids again, and the training pool above is the "
          "only side new prompts may be drawn from.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("nominate")
    c = sub.add_parser("confirm")
    c.add_argument("--n", type=int, default=60, help="samples per task; > the screen's 40")
    c.add_argument("--temp", type=float, default=0.8)
    c.add_argument("--draw", type=int, default=500, help="must cover the screened draw")
    c.add_argument("--seed", type=int, default=1337, help="must match the screen's seed")
    c.add_argument("--model", default=forge.MODEL_NAME)
    f = sub.add_parser("freeze")
    f.add_argument("--force", action="store_true",
                   help="replace an existing frozen ruler; say so in the channel")
    args = ap.parse_args()
    {"nominate": cmd_nominate, "confirm": cmd_confirm,
     "freeze": cmd_freeze}[args.cmd](args)


if __name__ == "__main__":
    venv_guard.ensure(__file__, "pyarrow")
    main()
