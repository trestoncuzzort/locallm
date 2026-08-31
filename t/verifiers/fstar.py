"""t.verifiers.fstar — the seventh kernel: F*.

Verdict mapping (F* 2026.08.30 / bundled Z3 4.13.3, measured 2026-08-31 on
ubuntu-box in the install audit, re-relied-on here; tactic-admit rows
re-measured 2026-08-31 in the Wave-1 hole-closing pass):
  exit 0 + success line + >=1 Query-stats row    -> VERIFIED (ban scan clean)
  banned token in SOURCE (admit/assume/magic/expect_failure families,
      option pragmas, warn_error — substring, raw + NFKC)  -> VACUOUS
  diagnostic number 296 at ANY level             -> VACUOUS  (a tactic
      admitted a goal — tadmit/admit_all/tadmit_t land here)
  Error number 335                               -> VACUOUS  (admit()/assume
      term/unsafe_coerce/admit_smt_queries/lax — all measured as 335)
  exit 0 + success line + ZERO Query-stats rows  -> MALFORMED (zero
      discharged obligations is not a proof)
  Error number 19, solver reason canceled/
      resource-limits on any attempt line        -> TIMEOUT  (rlimit verdict)
  Error number 19 otherwise                      -> REFUTED
  Error number 168 (syntax) / 72 (resolution)    -> MALFORMED
  Error number 129 (missing input file)          -> TOOL_ERROR
  any other Error number                         -> MALFORMED (the typechecker
      rejected the shape before/around proof; never a refutation)
  nonzero exit with no parseable Error JSON      -> TOOL_ERROR
  wall backstop                                  -> TIMEOUT

Exit codes are 0/1 only (measured: every failure class exits 1), so
classification comes from the NDJSON diagnostics `--message_format json`
puts on stderr — one object per line, {"msg":[...],"level","range",
"number","ctx"} — never from the exit code beyond "0 = clean". On failing
runs even the progress lines land on stderr, so parsing skips non-JSON
lines. A timeout and a refutation share number 19 and are split by message
text, exactly as measured.

Measured traps this adapter owns:
  * `assume val` verifies at exit 0 UNDER --report_assumes error (measured
    on both a magic-value assume val and an axiom-shaped one) — hence the
    lexical ban on the assume/admit/magic families in the SOURCE,
    verus-style, on top of the flag. A hit is VACUOUS regardless of the
    solver's opinion.
  * TACTIC ADMITS (Wave-1 hole, closed 2026-08-31). `assert P by (tadmit())`
    — likewise admit_all(), tadmit_t, and FStar.Tactics.tadmit — closed the
    goal at the tactic engine: exit 0, success line, --report_assumes
    silent, and the old \\b-bounded ban blind to `tadmit` (word chars on
    both sides). Three measured layers close it:
      1. the ban is SUBSTRING matching, so tadmit/admit_all/tadmit_t/_admit/
         admit_ and every other identifier embedding a family name is hit;
      2. the engine's own per-goal report — "Tactics admitted goal.",
         number 296, ctx "While running primitive tadmit_t" — is scanned at
         EVERY level and is VACUOUS on sight, so an admit primitive reached
         by a name no lexical scan can see (reflection, concatenated
         strings) still cannot verify;
      3. --warn_error @296 on the command line promotes 296 to a hard error
         (measured: exit 1). A file pragma `--warn_error -296` was measured
         to silence 296 entirely AND to override the CLI promotion — which
         is why every option pragma (#set/#push/#pop/#reset-options,
         #restart-solver) and the token warn_error are themselves banned:
         the honest lowering emits no pragma of any kind, and a working
         demotion must spell the pragma in plain ASCII for F* to parse it,
         so the substring scan cannot be evaded by the encoding tricks that
         work on identifiers.
  * POSITIVE OBLIGATION EVIDENCE: --query_stats prints one "Query-stats"
    row per discharged SMT query (measured on stdout at exit 0). VERIFIED
    additionally requires at least one such row: an empty module, a
    comments-only file, or any run that discharged zero obligations is
    MALFORMED even at exit 0 with the success line — file-accepted is not
    proof-discharged. (A row is not per-goal attribution — an admitted VC
    still produces a trivial query, measured — so rows gate the zero case
    while layers 1–3 gate the admit case.)
  * `[@@expect_failure]` (the skeptic's catch, 2026-08-31) makes F* accept
    a file whose only theorem is FALSE: checked-to-fail, silently dropped,
    exit 0. Banned by substring, expect_lax_failure explicitly included
    (\\bexpect_failure\\b never matched it).
  * Unicode: the scan runs over the raw decode AND its NFKC normalization,
    so fullwidth/compatibility spellings of a banned name are hit. Cross-
    script homoglyphs (Cyrillic а in `аdmit`) survive NFKC, but F*'s ASCII
    lexer rejects them — measured number 168 on both homoglyph probes — so
    they end MALFORMED, never VERIFIED. Comment/string mentions of banned
    words DO fire the ban (measured on the overfire probes): scanning raw
    text is the conservative direction — a hidden live token can never
    slip through a comment-stripper this adapter does not have.
  * Non-UTF8 bytes (Wave-1 crash, closed 2026-08-31): the scan decodes via
    safe_text (errors=replace) and the scratch copy is written as RAW
    BYTES, so F* judges the same bytes the hash binds to; the measured
    result on the non-UTF8 probe is a lexer error -> MALFORMED, no
    exception.
  * --report_assumes error composed with --cache_off fails EVERY file
    (number 335 on Prims.fst unsafe_coerce) — never composed here. Instead
    every verify runs in a fresh scratch directory, so no .checked cache
    can leak between runs (F*'s cache trap, ROADMAP 7.2). The scratch file
    is named after the source's own `module` line because F* binds module
    name to file name; the witness hash binds to the SOURCE bytes.
  * A user-code `unsafe_coerce` body was measured as Error 335 under
    --report_assumes error -> VACUOUS via the 335 row, no ban entry needed.
  * A missing input file is number 129 at exit 1 — TOOL_ERROR, never
    MALFORMED.

Budget is --z3rlimit (deterministic solver resource units — the same
doctrine as Dafny's and Verus's rlimit rows); --z3seed and --z3version are
pinned. Two identical failing runs at the pinned seed were measured
byte-identical on stderr, so flake_check re-measures a determinism claim
rather than hoping for one.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path

from . import Outcome, Result, safe_text, sha256_file
from .discover import find, missing

_GLOBS = [".local/fstar/fstar/bin/fstar.exe", ".local/fstar/**/bin/fstar.exe"]
FSTAR = find("T_FSTAR", ["fstar.exe", "fstar"], _GLOBS)
_FSTAR_WHY = missing("fstar", "T_FSTAR", ["fstar.exe", "fstar"], _GLOBS)

DEFAULT_RLIMIT = 50        # z3rlimit units; every t task + twin fits (measured)
Z3_VERSION = "4.13.3"      # the bundled default among the three shipped; pinned
Z3_SEED = 42
WALL_S = 120               # hang backstop only, never the verdict

# Substring families, deliberately unbounded (no \b): tadmit, admit_all,
# tadmit_t, _admit, admit_, expect_lax_failure and every embedding are hits.
# The pragma rows exist because a file pragma can demote diagnostic 296 out
# of existence (measured) and the honest lowering emits no pragmas at all.
BANNED = re.compile(
    r"admit|assume|magic|expect_(?:lax_)?failure"
    r"|#\s*(?:set|push|pop|reset)-options|#\s*restart-solver|warn_error")
_MODULE = re.compile(r"^\s*module\s+([A-Za-z0-9_.']+)", re.MULTILINE)
_OK_LINE = "All verification conditions discharged successfully"
_QUERY = re.compile(r"\bQuery-stats\b")
TACTIC_ADMIT_NUM = 296     # "Tactics admitted goal." — measured on tadmit
# Under --query_stats every error-19 msg carries per-attempt reason lines
# ("unknown because canceled (rlimit=1; ...)" at rlimit exhaustion,
# "unknown because (incomplete quantifiers) (rlimit=50; ...)" at a real
# refutation — both measured 2026-08-31) PLUS a fixed advisory Note whose
# prose contains the literal words "timed out", 'canceled' and 'resource
# limits reached'. So the timeout/refutation split reads ONLY the reason
# lines — a whole-message "timed out" scan misclassified the false-baseline
# probe as TIMEOUT the moment --query_stats went on.
_UNKNOWN = re.compile(r"unknown because (.*?) ?\(rlimit=")


def _rlimit_timeout(msg: str) -> bool:
    reasons = _UNKNOWN.findall(msg)
    if reasons:
        return any("canceled" in r or "resource" in r or "timeout" in r
                   for r in reasons)
    # no solver reason lines (a 19 not shaped by --query_stats): the old
    # measured discriminator, with the advisory Note cut away first
    return "timed out" in msg.split("Note:")[0]


def version() -> str:
    if not FSTAR:
        raise SystemExit(_FSTAR_WHY)
    p = subprocess.run([FSTAR, "--version"], capture_output=True, text=True)
    return " / ".join(l.strip() for l in p.stdout.strip().splitlines())


def verify(path: Path, budget: int = DEFAULT_RLIMIT) -> Result:
    if not FSTAR:
        raise SystemExit(_FSTAR_WHY)
    src_hash = sha256_file(path)
    raw = path.read_bytes()
    src_text = safe_text(path)
    banned = sorted(set(BANNED.findall(src_text))
                    | set(BANNED.findall(unicodedata.normalize("NFKC",
                                                               src_text))))
    m = _MODULE.search(src_text)
    fname = (m.group(1) + ".fst") if m else "T_unit.fst"
    bud = f"z3rlimit={budget} z3seed={Z3_SEED} z3={Z3_VERSION}"
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="t-fstar-") as td:
        # raw bytes, not the decoded scan text: F* must judge exactly the
        # bytes src_hash binds to (non-UTF8 then fails ITS lexer -> MALFORMED)
        (Path(td) / fname).write_bytes(raw)
        try:
            p = subprocess.run(
                [FSTAR, "--message_format", "json",
                 "--z3version", Z3_VERSION, "--z3seed", str(Z3_SEED),
                 "--z3rlimit", str(budget), "--report_assumes", "error",
                 "--warn_error", f"@{TACTIC_ADMIT_NUM}", "--query_stats",
                 fname],
                capture_output=True, text=True, timeout=WALL_S, cwd=td)
        except subprocess.TimeoutExpired:
            return Result("fstar", version(), src_hash, Outcome.TIMEOUT,
                          wall_ms=int((time.monotonic() - t0) * 1000),
                          budget=bud, error="wall backstop fired")
    wall = int((time.monotonic() - t0) * 1000)

    errs: list[tuple[int, str]] = []
    admitted = False           # diagnostic 296 at ANY level, error or not
    for line in p.stderr.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue                       # progress lines share stderr on failure
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("number") == TACTIC_ADMIT_NUM:
            admitted = True
        if d.get("level") == "Error":
            errs.append((d.get("number", -1), " ".join(d.get("msg") or [])))
    nums = {n for n, _ in errs}
    queries = len(_QUERY.findall(p.stdout)) + len(_QUERY.findall(p.stderr))

    if banned:
        outcome = Outcome.VACUOUS
    elif admitted:
        # the engine itself said a tactic closed a goal without proof; this
        # holds even if a missed spelling got the admit primitive executed
        outcome = Outcome.VACUOUS
    elif p.returncode == 0:
        if _OK_LINE not in p.stdout:
            # exit 0 was measured clean-only; the stdout line is a witness
            outcome = Outcome.TOOL_ERROR
        elif queries == 0:
            # accepted, but zero obligations were discharged — not a proof
            outcome = Outcome.MALFORMED
        else:
            outcome = Outcome.VERIFIED
    elif 335 in nums:
        outcome = Outcome.VACUOUS
    elif any(n == 19 and _rlimit_timeout(msg) for n, msg in errs):
        # a run the budget muddied is never counted as a refutation
        outcome = Outcome.TIMEOUT
    elif 19 in nums:
        outcome = Outcome.REFUTED
    elif nums & {168, 72}:
        outcome = Outcome.MALFORMED
    elif 129 in nums:
        outcome = Outcome.TOOL_ERROR
    elif errs:
        outcome = Outcome.MALFORMED
    else:
        outcome = Outcome.TOOL_ERROR
    return Result("fstar", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=bud,
                  error=("" if outcome != Outcome.TOOL_ERROR
                         else (p.stderr + p.stdout)[-400:]),
                  extras={"errors": [(n, msg[:200]) for n, msg in errs[:5]],
                          "banned_tokens": banned[:5],
                          "tactic_admitted": admitted,
                          "queries": queries})
