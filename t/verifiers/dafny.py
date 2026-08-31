"""t.verifiers.dafny — the first kernel, exit codes measured not assumed.

Mapping (dafny 4.11.0, measured in dafny_verify.py and re-relied-on here):
    0 -> VERIFIED only when the verifier's own tally shows >= 1 obligation
         discharged and no contradictory-assumptions warning and no banned
         source token; otherwise VACUOUS / MALFORMED / TOOL_ERROR (below)
    2 -> MALFORMED (parse/resolution)
    4 -> REFUTED
Wall timeout -> TIMEOUT; anything else -> TOOL_ERROR.

The deterministic budget is Z3's resource limit (--resource-limit), because
wall-clock is nondeterministic and rlimit is not — dafny_verify.py's finding,
inherited whole. Vacuity is surfaced with --warn-contradictory-assumptions:
measured there, `ensures true` and unsatisfiable requires verify instantly at
exit 0, and only the warning tells you.

Positive evidence (Wave-1 audit, 2026-08-31): exit 0 alone is NOT proof.
Measured on dafny 4.11.0, an empty file and a comments-only file both exit 0
printing "0 verified, 0 errors", and the old exit-0-is-VERIFIED rule scored
them VERIFIED. VERIFIED therefore requires the verifier's finish line
("Dafny program verifier finished with N verified, M errors") with N >= 1 and
M == 0. That tally is dafny's own stdout and `dafny verify` never executes
user code, so the source cannot print or suppress it; exit 0 with the line
absent is TOOL_ERROR, exit 0 with N == 0 is MALFORMED (zero obligations
discharged is not a proof). This check is the guarantee: even a ban token the
regex misses cannot conjure a discharged obligation out of "0 verified".

Ban regex (second line, same audit): opaque + lemma {:axiom} / assume
{:axiom} admits a false fact that --warn-contradictory-assumptions cannot see
(probes h7/h8/h9/h11 all exited 0 with "N verified" for a false theorem), and
{:verify false} / {:extern} / @Axiom / {:only} are stopped today only
incidentally, by warnings-as-errors at exit 2. Also measured: `include` pulls
a false axiom in from a file this scan never reads — the e6 probe exits 0
with "2 verified, 0 errors" and no ban token in the included-from file — so
`include` is banned outright. The regex bans the ENTIRE {:...} and @Attr
pragma surfaces (honest lowerings emit no attribute of any kind), plus the
keywords assume/axiom/opaque/reveal/extern/include, case-insensitively
(@Axiom is capitalized; `{ : axiom }` is a measured parse error but the
tolerant form costs nothing). The scan text is NFKC-normalized safe_text:
NFKC folds fullwidth homoglyph spellings back to ASCII, and a keyword dafny
itself acts on is necessarily ASCII, so the raw bytes cannot hide one.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

from . import Outcome, Result, safe_text, sha256_file
from .discover import find, missing

DAFNY = find("T_DAFNY", ["dafny"], [".local/dafny/dafny"])
_DAFNY_WHY = missing("dafny", "T_DAFNY", ["dafny"], [".local/dafny/dafny"])

DEFAULT_RLIMIT = 500_000   # Z3 resource units; deterministic where seconds are not
WALL_S = 120               # hang backstop only, never the verdict

# Source tokens that can admit an unproved fact or skip/outsource an
# obligation (measured per docstring). Honest lower_dafny.py output contains
# no attributes, no @-forms, no strings, no comments, and none of these words.
BANNED_RE = re.compile(
    r"\{\s*:\s*\w+"                 # every {:attr} pragma ({:axiom}, {:verify false}, {:extern}, {:only}, ...)
    r"|@\s*[A-Za-z_]\w*"            # every 4.10+ @Attribute form (@Axiom, @Verify(false), ...)
    r"|\binclude\b"                 # imports source this scan never sees (e6: exit 0, "2 verified")
    r"|\bassume\w*"                 # assume statement, assume {:axiom}, {:assume_concurrent}
    r"|\b(?:axiom|opaque|reveal|extern)\b",
    re.IGNORECASE)

# Dafny 4.11.0's own tally line, printed exactly once per run (measured):
#   "Dafny program verifier finished with 1 verified, 0 errors"
FINISH_RE = re.compile(r"finished with (\d+) verified, (\d+) error")


def version() -> str:
    if not DAFNY:
        raise SystemExit(_DAFNY_WHY)
    p = subprocess.run([DAFNY, "--version"], capture_output=True, text=True)
    return f"dafny {p.stdout.strip()}"


def verify(path: Path, budget: int = DEFAULT_RLIMIT) -> Result:
    if not DAFNY:
        raise SystemExit(_DAFNY_WHY)
    src_hash = sha256_file(path)
    # safe_text, not read_text: Wave-1's non-UTF8 probes crashed the scan.
    # NFKC folds homoglyph spellings; sha256 above still binds raw bytes.
    src = unicodedata.normalize("NFKC", safe_text(path))
    banned = sorted({m.group(0) for m in BANNED_RE.finditer(src)})
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
    fin = FINISH_RE.search(out)
    n_verified = int(fin.group(1)) if fin else -1
    n_errors = int(fin.group(2)) if fin else -1
    err = ""
    if p.returncode == 0:
        if banned:
            # dafny accepted it, but only because a banned construct admitted
            # or skipped the obligation — never a win.
            outcome = Outcome.VACUOUS
        elif fin is None:
            # exit 0 without the verifier's own tally is not evidence.
            outcome = Outcome.TOOL_ERROR
            err = "exit 0 but no 'N verified, M errors' line: " + out[-300:]
        elif n_verified < 1 or n_errors != 0:
            # "0 verified, 0 errors" at exit 0: measured for empty and
            # comments-only files. Nothing was proved.
            outcome = Outcome.MALFORMED
        elif vac:
            outcome = Outcome.VACUOUS
        else:
            outcome = Outcome.VERIFIED
    elif p.returncode == 2:
        outcome = Outcome.MALFORMED
    elif p.returncode == 4:
        # Z3 resource exhaustion also surfaces at exit 4; "out of resource"
        # in the text is a budget verdict, not a refutation.
        outcome = (Outcome.TIMEOUT if "out of resource" in out.lower()
                   else Outcome.REFUTED)
    else:
        outcome = Outcome.TOOL_ERROR
        err = out[-400:]
    return Result("dafny", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"rlimit={budget}",
                  error=err,
                  extras={"vacuity_warnings": vac[:5],
                          "banned_tokens": banned[:8],
                          "verified_count": n_verified,
                          "error_count": n_errors})
