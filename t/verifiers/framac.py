"""t.verifiers.framac — the sixth kernel: Frama-C/WP over ACSL contracts.

Pins: Frama-C 33.0 (Arsenic) + alt-ergo 2.4.3-free (NEVER opam's alt-ergo
2.6.x, which is non-commercial — the WS-7 licensing catch), via opam.

THE REFUTED DOCTRINE, decided after measurement: a false postcondition here
surfaces as Stepout/Timeout on the goal — the quantified VC yields no
countermodel from alt-ergo or plain Z3 (both measured 2026-08-31). That is
the same epistemic position as Dafny's rlimit and gnatprove's `medium`: the
deterministic budget IS the bar, and "unproved at the pinned budget" is what
REFUTED means operationally. The per-goal status lines ship in extras so the
countermodel refinement (why3's `counterexamples` prover configs exist; WP's
naming for them is the parked follow-up) can sharpen this later without
rewriting history. Outcome.TIMEOUT here means the WALL backstop only.

THE SEMANTIC DECISION: without -wp-rte, WP reasons about C integer
arithmetic mathematically — which is t v0's semantics, so -wp-rte is
deliberately absent. The machine-int arm (with -wp-rte and explicit range
obligations) is a later gate, same as Verus's exec/i64 arm.

-wp-cache none because a proof cache poisons flake_check — a cached verdict
re-measures nothing.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from . import Outcome, Result, sha256_file
from .discover import find, missing

FRAMAC = find("T_FRAMAC", ['frama-c'], [".opam/*/bin/frama-c"])
_FRAMAC_WHY = missing("framac", "T_FRAMAC", ['frama-c'], [".opam/*/bin/frama-c"])
DEFAULT_STEPS = 20_000
WALL_S = 240
BANNED = re.compile(r"\badmit\b|\bassumes\b|requires\s+\\false", re.IGNORECASE)


def version() -> str:
    p = subprocess.run([FRAMAC, "-version"], capture_output=True, text=True)
    return f"frama-c {p.stdout.strip()} / alt-ergo 2.4.3-free"


def verify(path: Path, budget: int = DEFAULT_STEPS) -> Result:
    src_hash = sha256_file(path)
    banned = BANNED.findall(path.read_text(encoding="utf-8"))
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            [FRAMAC, "-wp", "-wp-prover", "alt-ergo", "-wp-steps", str(budget),
             "-wp-cache", "none", str(path)],
            capture_output=True, text=True, timeout=WALL_S)
    except subprocess.TimeoutExpired:
        return Result("framac", version(), src_hash, Outcome.TIMEOUT,
                      wall_ms=int((time.monotonic() - t0) * 1000),
                      budget=f"wp-steps={budget}", error="wall backstop fired")
    wall = int((time.monotonic() - t0) * 1000)
    out = p.stdout + p.stderr
    m = re.search(r"Proved goals:\s+(\d+)\s*/\s*(\d+)", out)
    statuses = re.findall(r"^\s+(Qed|Alt-Ergo|Timeout|Stepout|Unknown|Failed)"
                          r":?\s+\d+", out, re.MULTILINE)

    if banned:
        outcome = Outcome.VACUOUS
    elif m is None:
        outcome = Outcome.MALFORMED     # WP never reached goal generation
    elif int(m.group(1)) == int(m.group(2)) and int(m.group(2)) > 0:
        outcome = Outcome.VERIFIED
    else:
        outcome = Outcome.REFUTED       # unproved at the pinned budget
    return Result("framac", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"wp-steps={budget}",
                  error="" if outcome != Outcome.TOOL_ERROR else out[-400:],
                  extras={"proved": m.group(0) if m else None,
                          "goal_statuses": statuses[:8],
                          "banned_tokens": banned[:5]})
