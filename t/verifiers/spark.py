"""t.verifiers.spark — the third kernel: GNATprove (SPARK 2014, Why3 + Z3).

Verdicts are classified from TEXT, because gnatprove was MEASURED (2026-08-31,
FSF 16.1.0-1 aarch64-darwin) to exit 0 for a full proof, for an unproved
postcondition, and for a file that does not even parse — the dossier's
warning, confirmed on this machine before this adapter was written:
    "Success: all checks proved"      -> VERIFIED
    any "medium:" or "high:" line     -> REFUTED
    any "error:" line                 -> MALFORMED (checked BEFORE medium/high;
                                          a broken file can produce both)
    wall backstop                     -> TIMEOUT
    none of the above                 -> TOOL_ERROR
The gave-up-vs-countermodel refinement (per-unit .spark JSON) is deferred to
the dossier's probe-matrix step; at t v0 task sizes Z3 answers instantly.

Budget: --steps, gnatprove's explicitly machine-independent deterministic
bound. Prover pinned to the bundled Z3 with --prover=z3. Vacuity analogue:
`pragma Assume`, `SPARK_Mode => Off`, and Import aspects prove anything —
t never emits them; the adapter rules VACUOUS on sight anyway.

gnatprove requires a project; each verify runs in a scratch dir with a
two-line .gpr beside a copy of the source. The hash in the Result is the
SOURCE file's, so witnesses bind to t's artifact, not the scaffolding.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import Outcome, Result, sha256_file

GNATPROVE = Path(os.environ.get(
    "T_GNATPROVE",
    Path.home() / ".local" / "gnatprove" / "gnatprove-aarch64-darwin-16.1.0-1"
    / "bin" / "gnatprove"))
DEFAULT_STEPS = 20_000
WALL_S = 180
BANNED = re.compile(r"pragma\s+Assume|SPARK_Mode\s*=>\s*Off|with\s+Import",
                    re.IGNORECASE)
GPR = "project T_Work is\n   for Source_Dirs use (\".\");\nend T_Work;\n"


def version() -> str:
    p = subprocess.run([str(GNATPROVE), "--version"],
                       capture_output=True, text=True)
    first = p.stdout.strip().splitlines()
    return "gnatprove " + " / ".join(first[:2])


def verify(path: Path, budget: int = DEFAULT_STEPS) -> Result:
    src_hash = sha256_file(path)
    banned = BANNED.findall(path.read_text(encoding="utf-8"))
    t0 = time.monotonic()
    src_text = path.read_text(encoding="utf-8")
    m = re.search(r"package\s+(\w+)", src_text)
    unit = (m.group(1).lower() if m else "t_unit") + ".ads"
    with tempfile.TemporaryDirectory(prefix="t-spark-") as td:
        work = Path(td)
        (work / "t_work.gpr").write_text(GPR, encoding="utf-8")
        # GNAT's naming convention demands file name == unit name; deriving it
        # here keeps harness filenames free (twins live in *.twin.ads outside).
        (work / unit).write_text(src_text, encoding="utf-8")
        try:
            p = subprocess.run(
                [str(GNATPROVE), "-P", "t_work.gpr", "--steps", str(budget),
                 "--prover=z3", "--quiet"],
                capture_output=True, text=True, timeout=WALL_S, cwd=work)
        except subprocess.TimeoutExpired:
            return Result("spark", version(), src_hash, Outcome.TIMEOUT,
                          wall_ms=int((time.monotonic() - t0) * 1000),
                          budget=f"steps={budget}", error="wall backstop fired")
    wall = int((time.monotonic() - t0) * 1000)
    out = p.stdout + p.stderr
    if banned:
        outcome = Outcome.VACUOUS
    elif re.search(r"^.*\berror\b", out, re.MULTILINE):
        outcome = Outcome.MALFORMED
    elif re.search(r"^\s*\S+:\d+:\d+: (medium|high):", out, re.MULTILINE) \
            or "medium:" in out or "high:" in out:
        outcome = Outcome.REFUTED
    elif p.returncode == 0:
        # --quiet suppresses the Success banner; exit 0 with no diagnostics
        # above IS the all-proved state (measured: unproved always prints).
        outcome = Outcome.VERIFIED
    else:
        outcome = Outcome.TOOL_ERROR
    return Result("spark", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"steps={budget}",
                  error="" if outcome != Outcome.TOOL_ERROR else out[-400:],
                  extras={"banned_tokens": banned[:5]})
