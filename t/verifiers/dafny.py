"""t.verifiers.dafny — the first kernel, exit codes measured not assumed.

Mapping (dafny 4.11.0, measured in dafny_verify.py and re-relied-on here):
    0 -> VERIFIED (unless a contradictory-assumptions warning fired -> VACUOUS)
    2 -> MALFORMED (parse/resolution)
    4 -> REFUTED
Wall timeout -> TIMEOUT; anything else -> TOOL_ERROR.

The deterministic budget is Z3's resource limit (--resource-limit), because
wall-clock is nondeterministic and rlimit is not — dafny_verify.py's finding,
inherited whole. Vacuity is surfaced with --warn-contradictory-assumptions:
measured there, `ensures true` and unsatisfiable requires verify instantly at
exit 0, and only the warning tells you.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from . import Outcome, Result, sha256_file
from .discover import find, missing

DAFNY = find("T_DAFNY", ["dafny"], [".local/dafny/dafny"])
_DAFNY_WHY = missing("dafny", "T_DAFNY", ["dafny"], [".local/dafny/dafny"])

DEFAULT_RLIMIT = 500_000   # Z3 resource units; deterministic where seconds are not
WALL_S = 120               # hang backstop only, never the verdict


def version() -> str:
    if not DAFNY:
        raise SystemExit(_DAFNY_WHY)
    p = subprocess.run([DAFNY, "--version"], capture_output=True, text=True)
    return f"dafny {p.stdout.strip()}"


def verify(path: Path, budget: int = DEFAULT_RLIMIT) -> Result:
    if not DAFNY:
        raise SystemExit(_DAFNY_WHY)
    src_hash = sha256_file(path)
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            [DAFNY, "verify", "--resource-limit", str(budget),
             "--warn-contradictory-assumptions", str(path)],
            capture_output=True, text=True, timeout=WALL_S)
    except subprocess.TimeoutExpired:
        return Result("dafny", version(), src_hash, Outcome.TIMEOUT,
                      wall_ms=int((time.monotonic() - t0) * 1000),
                      budget=f"rlimit={budget}", error="wall backstop fired")
    wall = int((time.monotonic() - t0) * 1000)
    out = p.stdout + p.stderr
    vac = [l for l in out.splitlines() if "contradictory assumption" in l.lower()]
    if p.returncode == 0:
        outcome = Outcome.VACUOUS if vac else Outcome.VERIFIED
    elif p.returncode == 2:
        outcome = Outcome.MALFORMED
    elif p.returncode == 4:
        # Z3 resource exhaustion also surfaces at exit 4; "out of resource"
        # in the text is a budget verdict, not a refutation.
        outcome = (Outcome.TIMEOUT if "out of resource" in out.lower()
                   else Outcome.REFUTED)
    else:
        outcome = Outcome.TOOL_ERROR
    return Result("dafny", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"rlimit={budget}",
                  error="" if p.returncode in (0, 2, 4) else out[-400:],
                  extras={"vacuity_warnings": vac[:5]})
