"""Interleaved replication driver — 40 replicates per arm, ALTERNATING.

WHY INTERLEAVE. The original run scored the trained arm as one continuous block
(16:51-19:22) and the null arm as the next (19:24-20:50). Any drift in the
machine, the server, or the harness over those four hours is therefore aliased
with the arm: a difference between arms and a difference between time-blocks are
the same measurement. The zero-compute diagnostics named this as a confound it
could not remove from the banked rows.

Alternating the arms replicate-by-replicate breaks that aliasing. Session drift
becomes common-mode across both arms instead of loading onto one, so the paired
difference is protected from it. Nothing else about the measurement changes: same
frozen ruler, same pinned verifier, same generation budget per replicate.

Each round calls ruler_noise.cmd_measure with --runs set to the round number, and
the resume logic inside it banks exactly one more replicate for that model. That
is deliberate: the fingerprint check and the drift-abort in cmd_measure run per
replicate, so a mid-run edit to the verifier aborts here exactly as it would in a
straight run.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
# Windows layout is Scripts/python.exe, POSIX is bin/python. The hardcoded Windows
# path made subprocess.Popen raise FileNotFoundError on Linux before any round ran.
PY = REPO / ".venv-train" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

ARMS = ["llama3-forged-rep", "llama3-forged-null-rep"]  # Aug 4/5 default


def one(model: str, upto: int) -> int:
    """Bank one more replicate for `model` by asking for `upto` total."""
    cmd = [str(PY), "ruler_noise.py", "measure", "--runs", str(upto), "--model", model]
    p = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    tail = (p.stdout or "").strip().splitlines()[-3:]
    for ln in tail:
        print(f"    {ln}", flush=True)
    if p.returncode != 0:
        print(f"    !! exit {p.returncode}", flush=True)
        err = (p.stderr or "").strip().splitlines()[-5:]
        for ln in err:
            print(f"    !! {ln}", flush=True)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=40)
    # F6 scores three arms (null, healthy, random) and optionally a fourth (0.5x random).
    # nargs=2 refused them outright; the driver loop below already iterates over any number.
    ap.add_argument("--arms", nargs="+", metavar="TAG", default=None,
                     help="model tags to interleave, 2 or more; "
                          f"default is the Aug 4/5 pair {ARMS}")
    args = ap.parse_args()
    arms = args.arms or ARMS

    t0 = time.time()
    for r in range(1, args.rounds + 1):
        for model in arms:
            el = (time.time() - t0) / 60
            print(f"[round {r}/{args.rounds}] {model}  (+{el:.1f} min)", flush=True)
            rc = one(model, r)
            if rc != 0:
                print(f"ABORTING at round {r}, {model} — see output above", flush=True)
                return rc
    print(f"\nDONE: {args.rounds} replicates per arm in {(time.time()-t0)/60:.1f} min",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
