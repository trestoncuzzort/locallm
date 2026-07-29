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
from pathlib import Path

import forge
import screen_tasks
import venv_guard

HERE = Path(__file__).resolve().parent
SCREEN = HERE / "data" / "screen_results.jsonl"
NOMINEES = HERE / "data" / "ruler_nominees.json"
RULER = HERE / "data" / "ruler_confirmed.json"

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
    args = ap.parse_args()
    {"nominate": cmd_nominate, "confirm": cmd_confirm}[args.cmd](args)


if __name__ == "__main__":
    venv_guard.ensure(__file__, "pyarrow")
    main()
