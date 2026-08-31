"""t.verifiers.rocq — the fifth kernel: the Rocq Prover (né Coq).

Kernel-checked like Lean, solverless like Lean — determinism is
architectural. The pin is homebrew's rocq 9.2.0 (same upstream release the
dossier named via opam; the opam route's rocq-stdlib.9.2.0 does not exist,
which the install attempt measured the hard way).

Verdict classification (rocq/coqc 9.2.0, measured on this machine
2026-08-31):
  banned token in SOURCE (Admitted / Axiom / admit)          -> VACUOUS
  "Print Assumptions" output lacking
      "Closed under the global context"                       -> VACUOUS
  "Tactic failure" / "Cannot find witness" / "Unable to
      unify" / "unsolved"                                     -> REFUTED
      (lia's honest can't-prove is "Cannot find witness")
  "Syntax error" / "was not found" / "Illegal"                -> MALFORMED
  wall backstop                                               -> TIMEOUT
  exit 0 with the Closed line                                 -> VERIFIED
REFUTED markers are tested before MALFORMED; both exit nonzero.

Every generated file ends with `Print Assumptions <thm>.` so the axiom audit
is part of the artifact, not an optional second pass. No deterministic
resource flag exists at the CLI; the wall backstop is honest about being a
backstop, and flake_check re-measures the architectural determinism claim.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import Outcome, Result, sha256_file

COQC = os.environ.get("T_COQC", "coqc")
WALL_S = 180
BANNED = re.compile(r"\bAdmitted\b|\baxiom\b|^\s*Axiom\s|\badmit\b",
                    re.IGNORECASE | re.MULTILINE)
REFUTED_MARKS = ("Tactic failure", "Cannot find witness", "Unable to unify",
                 "unsolved")
MALFORMED_MARKS = ("Syntax error", "was not found", "Illegal", "Unknown")


def version() -> str:
    p = subprocess.run([COQC, "--version"], capture_output=True, text=True)
    return p.stdout.strip().splitlines()[0]


def verify(path: Path, budget: int = 0) -> Result:
    if not shutil.which(COQC):
        raise SystemExit("t.verifiers.rocq: no coqc on PATH")
    src_hash = sha256_file(path)
    src_text = path.read_text(encoding="utf-8")
    banned = BANNED.findall(src_text)
    t0 = time.monotonic()
    # coqc derives a module name from the basename and rejects dots, so the
    # harness's *.twin.v files would be MALFORMED for filename reasons — the
    # same trap GNAT's naming convention set, in Rocq costume. The adapter
    # owns the on-disk name; the witness hash binds to the SOURCE bytes.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="t-rocq-") as td:
        unit = Path(td) / "t_unit.v"
        unit.write_text(src_text, encoding="utf-8")
        try:
            p = subprocess.run([COQC, "t_unit.v"], capture_output=True,
                               text=True, timeout=WALL_S, cwd=td)
        except subprocess.TimeoutExpired:
            return Result("rocq", version(), src_hash, Outcome.TIMEOUT,
                          wall_ms=int((time.monotonic() - t0) * 1000),
                          budget="wall backstop only", error="backstop fired")
    wall = int((time.monotonic() - t0) * 1000)
    out = p.stdout + p.stderr
    closed = "Closed under the global context" in out

    if banned:
        outcome = Outcome.VACUOUS
    elif p.returncode == 0:
        outcome = Outcome.VERIFIED if closed else Outcome.VACUOUS
    elif any(m in out for m in REFUTED_MARKS):
        outcome = Outcome.REFUTED
    elif any(m in out for m in MALFORMED_MARKS):
        outcome = Outcome.MALFORMED
    else:
        outcome = Outcome.MALFORMED
    return Result("rocq", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget="wall backstop only",
                  error="" if outcome != Outcome.TOOL_ERROR else out[-400:],
                  extras={"assumptions_closed": closed,
                          "banned_tokens": banned[:5]})
