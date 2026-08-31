"""t.verifiers.verus — the second kernel.

Verdict mapping (Verus 0.2026.08.30.b432e82, per the WS-7 dossier and
measured here): exit codes are 0/1 only, so the taxonomy comes from
--output-json plus the message stream. VERIFIED demands POSITIVE evidence,
all four at once: verification-results present, errors == 0 with success,
verified >= 1, and at least one `ensures` clause outside comments/strings.
The Wave-1 audit (2026-08-31) measured success=true with verified=0 for an
empty verus!{} block, a spec-only file, and a #[verifier::external] theorem
— all three scored VERIFIED under the old errors==0 test. verified counts
only functions whose obligations the solver actually discharged, so
verified >= 1 is the obligation evidence; the ensures scan closes the
remaining trivial pass (exec fn with no ensures: verified=1, zero theorems).

Vacuity: `assume`, `admit`, and the external family verify anything at exit
0 (the dossier's headline hazard). t never emits them; the adapter scans the
SOURCE anyway — defense against a lowering bug, not against t's own tasks.
The ban is prefix-matched (`assume\\w*` etc.) because Wave-1's
\\b-delimited exact words missed assume_specification and
#[verifier::external] ('_' is a word char, and `external` was not listed) —
both passed `ensures false` as VERIFIED. `requires false` is the same
hazard from the other side (measured VERIFIED, Wave-1 h_reqfalse): any
ensures follows from it, so it is VACUOUS by scan, solver unconsulted.
The scans are deliberately asymmetric about inert text:
  - ban + requires-false run on the RAW decoded source (a hit in a comment
    or string over-flags to VACUOUS — fails closed; stripping first would
    let a stripper bug hide a live assume behind a `"//"` string);
  - the positive ensures scan runs on comment/string-STRIPPED source (a
    stripper bug can only hide a real ensures, which scores MALFORMED —
    fails closed; raw text would let `// ensures` fake the evidence).
Ban matching also folds NFKC + common Cyrillic homoglyphs + zero-width
chars: a look-alike `аssume` is not the Verus builtin (rustc rejects the
identifier, so verified>=1 already refuses the file); folding upgrades that
refusal to VACUOUS.

TIMEOUT: the Wave-1 sniff (`"rlimit" and "exceeded" anywhere in output)
was source-spoofable — a comment `// rlimit exceeded` is quoted verbatim in
the diagnostic gutter, flipping a REFUTED into TIMEOUT (measured,
c_rlimitword). The check is now anchored to the tool's own header line
(`error:`/`note:` at column 0 — gutter-quoted source always carries a
`N | ` prefix), uses the exact phrase embedded in the rust_verify binary
(": Resource limit (rlimit) exceeded"), and additionally requires
errors > 0 in verification-results (a compile_error! spoof fails rustc with
errors == 0 and stays MALFORMED).

Budget: --rlimit (solver resource multiplier), deterministic where
wall-clock is not — same doctrine as Dafny's. The bundled Z3 is used as
shipped; the release bundle pins it, and version() records the identity.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
from pathlib import Path

from . import Outcome, Result, safe_text, sha256_file
from .discover import find, missing

VERUS = find("T_VERUS_BIN", ['verus'], [".local/verus/**/verus"])
_VERUS_WHY = missing("verus", "T_VERUS_BIN", ['verus'], [".local/verus/**/verus"])
DEFAULT_RLIMIT = 10
WALL_S = 120

# Prefix-matched ban families: assume, assume_specification, admit, external,
# external_body, external_fn_specification, external_type_specification, and
# any future *_specification aspect spelled with these stems. Left \b is
# sound: the live constructs sit after '::', '(', '[', or whitespace, all
# non-word chars.
BANNED = re.compile(r"\b(?:assume|admit|external)\w*")

# requires-false: scan from `requires` up to the next clause keyword or
# block/statement delimiter for a bare `false` token. Stops at '{', so a
# `false` hidden behind an ite inside a requires clause escapes this regex —
# accepted residual: so does `requires 0 == 1`, and no regex decides
# satisfiability; the twin flip is the harness-level backstop.
_REQ_FALSE = re.compile(
    r"\brequires\b(?:(?!\bensures\b|\bdecreases\b|\brecommends\b|[{;])[\s\S])*?"
    r"\bfalse\b")

_ENSURES = re.compile(r"\bensures\b")

# Anchored to column 0 and to the exact phrase in the rust_verify binary;
# requires errors > 0 at the call site (see module docstring).
_RLIMIT_DIAG = re.compile(
    r"^(?:error|note)(?:\[[^\]]*\])?: .*Resource limit \(rlimit\) exceeded",
    re.M)

# Cyrillic/Greek/Armenian codepoints that render as a-z (the confusables
# actually seen evading keyword scans; NFKC does not fold these).
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ѕ": "s", "ј": "j", "ԛ": "q", "ԝ": "w", "ɑ": "a", "ν": "v",
    "υ": "u", "ο": "o", "ⅰ": "i", "ⅼ": "l", "ⅾ": "d", "ⅿ": "m"})
_ZERO_WIDTH = dict.fromkeys(
    (0x200b, 0x200c, 0x200d, 0x2060, 0xfeff, 0x00ad))


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s.translate(_ZERO_WIDTH)) \
        .translate(_HOMOGLYPHS)


def _ban_hits(text: str) -> list[str]:
    hits = BANNED.findall(text)
    for h in BANNED.findall(_fold(text)):
        if h not in hits:
            hits.append(h)
    return hits


def _strip_inert(s: str) -> str:
    """Blank out //-comments, nested /* */ comments, "..." strings, and
    r/r#..# raw strings so the positive `ensures` scan cannot be satisfied
    from inert text. Mis-lexing fails closed: over-stripping can only hide a
    real ensures (scores MALFORMED, never VERIFIED). Char literals are not
    lexed — one codepoint cannot spell a keyword, and a '"' char literal at
    worst opens a phantom string, which again only over-strips. t's lowering
    emits exactly one comment (`// verus!`) and no string/char literals."""
    out: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = s.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and nxt == "*":
            depth, i = 1, i + 2
            while i < n and depth:
                if s.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif s.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            out.append(" ")
        elif c == '"':
            i += 1
            while i < n and s[i] != '"':
                i += 2 if s[i] == "\\" else 1
            i += 1
            out.append(" ")
        elif (c == "r" and nxt in ('"', "#")
              and (i == 0 or not (s[i - 1].isalnum() or s[i - 1] == "_"))):
            j = i + 1
            hashes = 0
            while j < n and s[j] == "#":
                hashes, j = hashes + 1, j + 1
            if j < n and s[j] == '"':
                close = '"' + "#" * hashes
                k = s.find(close, j + 1)
                i = n if k < 0 else k + len(close)
                out.append(" ")
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def version() -> str:
    if not VERUS:
        raise SystemExit(_VERUS_WHY)
    p = subprocess.run([str(VERUS), "--version"], capture_output=True, text=True)
    line = next((l for l in p.stdout.splitlines() if "Version" in l), "?")
    return f"verus {line.split(':', 1)[-1].strip()}"


def verify(path: Path, budget: int = DEFAULT_RLIMIT) -> Result:
    src_hash = sha256_file(path)
    # safe_text, not read_text: a non-UTF8 probe killed this adapter with an
    # unhandled UnicodeDecodeError in Wave-1 (j_nonutf8, j_random).
    text = safe_text(path)
    banned = _ban_hits(text)
    req_false = _REQ_FALSE.search(text) is not None
    has_theorem = _ENSURES.search(_strip_inert(text)) is not None
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

    errors = vr.get("errors", 0) if isinstance(vr, dict) else 0
    verified = vr.get("verified", 0) if isinstance(vr, dict) else 0
    if not isinstance(verified, int) or isinstance(verified, bool):
        verified = 0

    if banned:
        outcome = Outcome.VACUOUS
    elif req_false:
        outcome = Outcome.VACUOUS
    elif vr is None:
        outcome = Outcome.MALFORMED
    elif (vr.get("errors", 1) == 0 and vr.get("success")
          and verified >= 1 and has_theorem):
        outcome = Outcome.VERIFIED
    elif _RLIMIT_DIAG.search(p.stderr) and errors > 0:
        outcome = Outcome.TIMEOUT
    elif errors > 0:
        # REFUTED requires the solver itself to have rejected a proof: the
        # verification-results errors count is the only evidence accepted.
        outcome = Outcome.REFUTED
    else:
        # vr exists but nothing was refuted and the positive-evidence gate
        # did not open: rustc rejected the file before verification, OR the
        # run discharged zero obligations (verified == 0: empty verus block,
        # spec-only file, external-annotated theorem — all measured
        # success=true in Wave-1), OR no ensures survives outside
        # comments/strings (zero stated theorems). MALFORMED, never REFUTED
        # and never VERIFIED. The first repair here matched "error[" in
        # stderr, and the 2026-08-31 Dell install audit measured it vacuous:
        # the dotted-name diagnostic is a bare "error: invalid character '.'
        # in crate name" with no [E####] bracket, so <name>.twin.rs still
        # flipped verdicts on its filename alone. Classifying from the
        # solver's own counts closes every message-shape variant at once.
        outcome = Outcome.MALFORMED
    return Result("verus", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"rlimit={budget}",
                  error="" if outcome != Outcome.TOOL_ERROR else (p.stderr[-400:]),
                  extras={"verification_results": vr,
                          "banned_tokens": banned[:5],
                          "requires_false": req_false,
                          "has_ensures": has_theorem,
                          "verified_count": verified})
