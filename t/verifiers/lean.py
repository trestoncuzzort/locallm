"""t.verifiers.lean — the fourth kernel, and the first proof assistant.

Shape difference, stated first: Lean has no SMT sidecar — "verified" means
THE KERNEL ACCEPTED A PROOF TERM. t's Lean lowering must therefore emit a
proof, and v0's fragment (linear integer arithmetic) makes that mechanical:
`omega` is a decision procedure for LIA living in core Lean, and its output
is still kernel-checked — the tactic is automation, never the authority.

Verdict classification (lean 4.33.1, measured on this machine 2026-08-31):
  banned token in SOURCE (sorry/admit/axiom/native_decide, or an in-file
    set_option maxHeartbeats overriding the CLI budget)     -> VACUOUS
  axiom audit line lists anything beyond
    {propext, Classical.choice, Quot.sound}  (esp. sorryAx) -> VACUOUS
  "omega could not prove" / "unsolved goals" / tactic-failed -> REFUTED
  "maxHeartbeats" deterministic-timeout message              -> TIMEOUT
  exit 0 with a clean axiom audit                            -> VERIFIED
  any other nonzero (parse/elaboration errors)               -> MALFORMED
REFUTED is tested before MALFORMED because proof failures also exit 1.

The generated file ends with `#print axioms <thm>`, so every verification
carries its own axiom audit — the dossier's `hasSorry`/allowlist gate, made
unavoidable rather than optional.

Budget: -DmaxHeartbeats, Lean's deterministic counter (the dossier's measured
trap — in-file set_option overrides the CLI — is why the denylist scan runs
BEFORE the kernel is consulted). Determinism is architectural; flake_check
re-measures it anyway because re-measuring is cheap.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from . import Outcome, Result, sha256_file
from .discover import find, missing

LEAN = find("T_LEAN_BIN", ['lean'], [".elan/bin/lean"])
_LEAN_WHY = missing("lean", "T_LEAN_BIN", ['lean'], [".elan/bin/lean"])
DEFAULT_HEARTBEATS = 400_000
WALL_S = 180
BANNED = re.compile(r"\b(sorry|admit|native_decide)\b|^\s*axiom\s"
                    r"|set_option\s+maxHeartbeats", re.MULTILINE)
AXIOM_ALLOW = {"propext", "Classical.choice", "Quot.sound"}
REFUTED_MARKS = ("omega could not prove", "unsolved goals", "failed")


def version() -> str:
    p = subprocess.run([str(LEAN), "--version"], capture_output=True, text=True)
    return p.stdout.strip().split(",")[0]


def verify(path: Path, budget: int = DEFAULT_HEARTBEATS) -> Result:
    src_hash = sha256_file(path)
    banned = BANNED.findall(path.read_text(encoding="utf-8"))
    t0 = time.monotonic()
    try:
        p = subprocess.run([str(LEAN), f"-DmaxHeartbeats={budget}", str(path)],
                           capture_output=True, text=True, timeout=WALL_S)
    except subprocess.TimeoutExpired:
        return Result("lean", version(), src_hash, Outcome.TIMEOUT,
                      wall_ms=int((time.monotonic() - t0) * 1000),
                      budget=f"heartbeats={budget}", error="wall backstop fired")
    wall = int((time.monotonic() - t0) * 1000)
    out = p.stdout + p.stderr
    ax = re.findall(r"depends on axioms: \[([^\]]*)\]", out)
    ax_used = {a.strip() for line in ax for a in line.split(",") if a.strip()}
    bad_axioms = ax_used - AXIOM_ALLOW

    if banned:
        outcome = Outcome.VACUOUS
    elif "maxHeartbeats" in out or "deterministic timeout" in out:
        outcome = Outcome.TIMEOUT
    elif p.returncode == 0:
        outcome = Outcome.VACUOUS if bad_axioms else Outcome.VERIFIED
    elif any(m in out for m in REFUTED_MARKS):
        outcome = Outcome.REFUTED
    else:
        outcome = Outcome.MALFORMED
    return Result("lean", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"heartbeats={budget}",
                  error="" if outcome != Outcome.TOOL_ERROR else out[-400:],
                  extras={"axioms": sorted(ax_used),
                          "banned_tokens": [b for b in banned if any(b)][:5]})
