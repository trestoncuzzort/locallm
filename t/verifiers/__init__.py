"""t.verifiers — one Outcome, many kernels.

Every backend module in this package exposes the same two functions:

    version() -> str                      # exact pinned toolchain identity
    verify(path, budget=None) -> Result   # one file, one verdict

The Outcome taxonomy is dafny_verify.py's, unchanged, because it was measured
there and the reasons transfer: a MALFORMED rejected-half teaches syntax, not
proof; a VACUOUS pass is the spec weakened out from under the theorem; a
TIMEOUT is not knowledge; and TOOL_ERROR is never evidence of anything.

flake_check() is the noise-floor discipline: no single verdict is trusted for
a witness until the same file returns the same outcome n times. Backends with
an SMT solver underneath (Dafny, Verus, SPARK, Frama-C) need this; the
kernel-checked backends (Lean, Rocq, Agda) are architecturally deterministic
and may pass n=1, but saying so is the dossier's claim and re-measuring it
here is cheap, so the default is n=3 for everyone.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path


def safe_text(p: Path) -> str:
    """Decode a source file for regex scanning WITHOUT crashing on non-UTF8.

    Wave-1 audit (2026-08-31) crashed six of seven adapters with an
    unhandled UnicodeDecodeError: each read the source with
    `path.read_text(encoding="utf-8")` before invoking its kernel, so a
    probe of random bytes killed the adapter instead of scoring MALFORMED.
    errors="replace" keeps every real byte position intact for the ban
    regexes (a replacement char never spuriously matches a keyword) while
    guaranteeing a str. The verdict hash still binds to raw bytes via
    sha256_file — this function is for scanning, never for hashing."""
    return p.read_bytes().decode("utf-8", errors="replace")


class Outcome:
    VERIFIED = "verified"      # a real proof, and only this is ok=True
    VACUOUS = "vacuous"        # accepted, but for the wrong reason — never a win
    REFUTED = "refuted"        # the honest "this is wrong"
    MALFORMED = "malformed"    # does not parse/resolve; NOT a proof failure
    TIMEOUT = "timeout"        # budget exhausted; we do NOT know it is wrong
    # The solver stopped WITHOUT exhausting the budget and WITHOUT a
    # countermodel. Added by measurement (2026-09-01, gnatprove FSF 16.1.0):
    # gnatprove's per-unit .spark audit carries exactly three unproved_status
    # values — "limit", "gave_up", "unknown" — and abs_twin.ads/max_twin.ads
    # report "gave_up" after Z3 spent 1 step of 20000. Folding that into
    # TIMEOUT would assert a budget exhaustion the kernel's own record denies;
    # folding it into REFUTED is the bug this outcome exists to make
    # unrepresentable. ok=False, exactly like TIMEOUT: not knowledge.
    UNPROVED = "unproved"
    TOOL_ERROR = "tool_error"  # anything else; never counted as evidence


@dataclass
class Result:
    backend: str
    backend_version: str
    source_sha256: str
    outcome: str
    ok: bool = False           # True ONLY for Outcome.VERIFIED
    exit_code: int = -1
    wall_ms: int = 0
    budget: str = ""           # the deterministic bound used, backend dialect
    error: str = ""
    extras: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flake_check(verify_fn, path: Path, n: int = 3):
    """Run verify n times; return (Result, agreed). Disagreement returns the
    LAST result with agreed=False — the caller must refuse the witness, not
    pick a favorite run."""
    results = [verify_fn(path) for _ in range(n)]
    outcomes = {r.outcome for r in results}
    return results[-1], len(outcomes) == 1
