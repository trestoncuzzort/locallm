"""t.verifiers.verus — the second kernel.

Verdict mapping (Verus 0.2026.08.30, per the WS-7 dossier and measured here):
exit codes are 0/1 only, so the taxonomy comes from --output-json plus the
message stream: verification-results with errors == 0 -> VERIFIED; errors > 0
-> REFUTED, unless the resource-limit message fired -> TIMEOUT; no
verification-results at all (rustc rejected the file) -> MALFORMED.

Vacuity: `assume`, `admit`, and `external_body` verify anything at exit 0
(the dossier's headline hazard). t never emits them, and this adapter scans
the SOURCE for them anyway — defense against a future lowering bug, not
against t's own tasks. A hit is VACUOUS regardless of the solver's opinion.

Budget: --rlimit (solver resource multiplier), deterministic where wall-clock
is not — same doctrine as Dafny's. The bundled Z3 is used as shipped; the
release bundle pins it, and version() records the whole identity.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from . import Outcome, Result, sha256_file
from .discover import find, missing

VERUS = find("T_VERUS_BIN", ['verus'], [".local/verus/**/verus"])
_VERUS_WHY = missing("verus", "T_VERUS_BIN", ['verus'], [".local/verus/**/verus"])
DEFAULT_RLIMIT = 10
WALL_S = 120
BANNED = re.compile(r"\b(assume|admit|external_body)\b")


def version() -> str:
    if not VERUS:
        raise SystemExit(_VERUS_WHY)
    p = subprocess.run([str(VERUS), "--version"], capture_output=True, text=True)
    line = next((l for l in p.stdout.splitlines() if "Version" in l), "?")
    return f"verus {line.split(':', 1)[-1].strip()}"


def verify(path: Path, budget: int = DEFAULT_RLIMIT) -> Result:
    src_hash = sha256_file(path)
    banned = BANNED.findall(path.read_text(encoding="utf-8"))
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            [str(VERUS), "--output-json", "--rlimit", str(budget), str(path)],
            capture_output=True, text=True, timeout=WALL_S)
    except subprocess.TimeoutExpired:
        return Result("verus", version(), src_hash, Outcome.TIMEOUT,
                      wall_ms=int((time.monotonic() - t0) * 1000),
                      budget=f"rlimit={budget}", error="wall backstop fired")
    wall = int((time.monotonic() - t0) * 1000)
    vr = None
    try:
        doc = json.loads(p.stdout)
        vr = doc.get("verification-results")
    except (json.JSONDecodeError, AttributeError):
        pass

    if banned:
        outcome = Outcome.VACUOUS
    elif vr is None:
        outcome = Outcome.MALFORMED
    elif vr.get("errors", 1) == 0 and vr.get("success"):
        outcome = Outcome.VERIFIED
    elif "rlimit" in (p.stdout + p.stderr).lower() and "exceeded" in (p.stdout + p.stderr).lower():
        outcome = Outcome.TIMEOUT
    else:
        outcome = Outcome.REFUTED
    return Result("verus", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"rlimit={budget}",
                  error="" if outcome != Outcome.TOOL_ERROR else (p.stderr[-400:]),
                  extras={"verification_results": vr,
                          "banned_tokens": banned[:5]})
