#!/usr/bin/env python3
"""dafny_hints.py — a MULTI-LINE-SAFE hint extractor, built to remove dafny_pairs.py's
single-line blocker.

THE BLOCKER THIS FILE EXISTS TO FIX
------------------------------------
dp.find_hints anchors on `^\\s*(kind)\\b.*$` and only accepts a clause that ends on the
SAME line it starts (line ends with `;`, `{`, or the next line starts a new clause).
Measured (this file, see __main__): on a 300-file random sample of the named corpus,
that whole-single-line requirement leaves 100 files (33.3%) with ZERO extractable
hints — the same order of magnitude as the previously reported 34/60 (56.7%).
Real Dafny invariants routinely wrap:

    invariant 0 <= low <= high <= a.Length &&
        x !in a[..low] && x !in a[high..]

    assert CorrectlyReadRange(buffer, tail, Write(x)) by {
      reveal CorrectlyReadRange();
    }

Neither is a single line, so dp.find_hints sees nothing there at all.

THE DESIGN: REFUSE, DON'T GUESS
--------------------------------
A clause's extent is only accepted when the code can prove, from bracket/brace depth
and a short, explicit set of continuation shapes, that lines i..j form the WHOLE
clause and nothing else. Every ambiguous shape is refused (dropped, not guessed):

  * `assert` (statement mode): ends at a `;` at bracket-depth 0, or — for
    `assert P by { ... }` — at the `}` that closes a brace which is immediately,
    provably preceded by the keyword `by` (checked by walking back over whitespace,
    across lines if needed; not "any brace at depth 0", which would also fire on an
    innocent `assert x in {1,2,3};` and misresolve it).
  * `invariant` / `decreases` / `modifies` / `reads` / `requires` / `ensures`
    (spec mode, never semicolon-terminated): extended line-by-line while paren/
    bracket depth is nonzero, or while the line ends with — or the next line
    opens with — a binary/logical continuation token (`&&`, `||`, `==>`, `::`,
    trailing `in`, a bare comma, ...). Stops the instant depth is balanced and the
    next line starts a new clause keyword or a lone `{`/`}`. Anything else at that
    boundary is refused.
  * A brace that opens with NOTHING else meaningful left on its line is refused
    outright, on sight, rather than tracked forward. That shape is what a glued-on
    loop/method body opener looks like (`... && Q {`) — chasing its matching `}`
    forward would walk the "clause" straight through the loop body and turn a
    single-hint deletion into wholesale mutilation of the file. A same-line set/map
    display (`{1,2,3}`) does not have this shape (it has content after `{` on the
    same line), so it is unaffected.
  * `calc { ... }` blocks are one more addressable kind: `calc`'s own grammar
    guarantees a `{` follows shortly and closes unambiguously, so brace-depth
    matching alone (no `by`-lookback needed) is safe there. Opt in via
    `include_calc=True`; it's off by default so kind-for-kind comparisons against
    the baseline stay apples-to-apples.

Comments and string/verbatim-string literals are masked to spaces (newlines and
length preserved) before ANY of the above runs, so a keyword or bracket inside a
comment or a string can never be mistaken for real syntax. Char literals (`'x'`)
are the one deliberate exception — see `mask_source`'s docstring for why, and what
that costs.

WHAT THIS FILE MEASURES, NOT ASSUMES
-------------------------------------
Run as `__main__` it reports, on real files pulled from the corpus, exactly the
numbers the brief asked for: hints-per-file before (dp) vs after (this module),
malformed-rate before vs after on real ablations, and single-hint pair yield
before vs after — against the standing baselines (1.53 pairs/verified file,
389/782 usable DafnyBench pairs). See the bottom of this file for the harness.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import dafny_verify as dv

DEFAULT_KINDS = ("invariant", "assert", "decreases")
ALL_SPEC_KINDS = ("invariant", "decreases", "ensures", "requires", "modifies", "reads")
STATEMENT_KINDS = ("assert",)

# A clause extent is refused, never guessed, past this many lines. Calc blocks get a
# larger allowance since a real multi-step calc can legitimately run long.
MAX_SPAN = 80
MAX_CALC_SPAN = 320


# ---------------------------------------------------------------------------
# MASKING — comments and strings become spaces (same length, same newlines) so
# every downstream scan (keyword match, bracket depth) only ever sees real code.
# ---------------------------------------------------------------------------

def mask_source(src: str) -> str:
    """Blank out comment bodies and string/verbatim-string interiors, in place,
    preserving every newline and the overall length so line numbers never shift.

    Char literals (`'x'`, `'\\n'`) are deliberately NOT masked as strings. Dafny
    identifiers may carry a trailing apostrophe (`x'`, `Node'` — a named Dafny
    convention for "the next state"), and that shape outnumbers genuine char
    literals by roughly 120 to 1 in this corpus (measured: 1231 files contain an
    apostrophe'd identifier vs 10 files that contain a bracket/semicolon INSIDE an
    actual char literal like `'{'`). Treating a bare `'` as a string-opener would
    corrupt bracket depth on the common case to fix the rare one, so it is left
    alone. The 10-file cost: a char literal holding a bracket or `;` can miscount
    depth there. Extent detection is written to REFUSE when depth never resolves
    (see MAX_SPAN), so that miscount's failure mode is a lost hint, never a
    corrupted excision — measured directly in the malformed-rate comparison below.
    """
    out = list(src)
    n = len(src)
    i = 0
    NORMAL, LINE, BLOCK, STR, VSTR = range(5)
    state = NORMAL
    while i < n:
        c = src[i]
        if state == NORMAL:
            if c == "/" and i + 1 < n and src[i + 1] == "/":
                out[i] = out[i + 1] = " "
                state = LINE
                i += 2
                continue
            if c == "/" and i + 1 < n and src[i + 1] == "*":
                out[i] = out[i + 1] = " "
                state = BLOCK
                i += 2
                continue
            if c == "@" and i + 1 < n and src[i + 1] == '"':
                out[i] = out[i + 1] = " "
                state = VSTR
                i += 2
                continue
            if c == '"':
                out[i] = " "
                state = STR
                i += 1
                continue
            i += 1
            continue
        if state == LINE:
            if c == "\n":
                state = NORMAL
                i += 1
                continue
            out[i] = " "
            i += 1
            continue
        if state == BLOCK:
            if c == "*" and i + 1 < n and src[i + 1] == "/":
                out[i] = out[i + 1] = " "
                state = NORMAL
                i += 2
                continue
            if c != "\n":
                out[i] = " "
            i += 1
            continue
        if state == STR:
            if c == "\\" and i + 1 < n and src[i + 1] != "\n":
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if c == '"':
                out[i] = " "
                state = NORMAL
                i += 1
                continue
            if c != "\n":
                out[i] = " "
            i += 1
            continue
        if state == VSTR:
            if c == '"' and i + 1 < n and src[i + 1] == '"':
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if c == '"':
                out[i] = " "
                state = NORMAL
                i += 1
                continue
            if c != "\n":
                out[i] = " "
            i += 1
            continue
    return "".join(out)


# ---------------------------------------------------------------------------
# CONTINUATION SHAPES — the only evidence allowed to extend a spec clause past a
# line boundary while paren/bracket depth is already back to zero.
# ---------------------------------------------------------------------------

_CONT_SUFFIXES = ("==>", "<==>", "<==", "&&", "||", "::", "=>", ":=", "==", "!=",
                  "<=", ">=", "+", "-", "*", "/", "%", "<", ">", ",", ":", "!", ".")
# NOTE: bare trailing "|" is deliberately EXCLUDED. It would read as a continuation
# (set-comprehension separator, `set x | P :: ...`), but `|expr|` cardinality bars
# are the overwhelmingly common case in Dafny specs (`invariant 0 <= i <= |a|`) and
# ALWAYS end a clause with a trailing "|". Treating that as "more to come" merged
# unrelated adjacent single-line invariants into one — measured: this one token
# was the entire reason an early version of this extractor UNDERcounted hints
# relative to dp.find_hints on real code. Dropping it fixed the regression (see
# module __main__ for the before/after).
_TRAILING_WORD_RE = re.compile(r"(?<![A-Za-z0-9_])(!?in|then|else)$")

# `then`/`else`/`case` are keyword continuations, not operator-symbol ones: a
# multi-line `if C then E1 else E2` or `match x case A => ... case B => ...`
# inside a spec expression can legitimately start its next line with one of
# these, with NO operator anywhere at the line boundary to signal it — measured:
# an early version corrupted exactly this shape (`if ... then ... \n else ...`),
# stopping the extent one line early and leaving a dangling `else` behind (see
# module __main__ for the malformed diagnostic this produced).
_LEAD_CONT_RE = re.compile(
    r"^\s*(==>|<==>|<==|&&|\|\||::|=>|:=|==|!=|<=|>=|!in\b|in\b|then\b|else\b|case\b|"
    r"[+\-*/%<>,:.|!])")

_KIND_RE = re.compile(r"^\s*(invariant|assert|decreases|ensures|requires|modifies|reads)\b")
_CALC_RE = re.compile(r"^\s*calc\b")


def _ends_with_continuation(mline: str) -> bool:
    s = mline.rstrip()
    if not s:
        return False
    if _TRAILING_WORD_RE.search(s):
        return True
    return any(s.endswith(suf) for suf in _CONT_SUFFIXES)


def _starts_with_continuation(mline: str) -> bool:
    return bool(_LEAD_CONT_RE.match(mline))


def _preceded_by_keyword(masked_lines, i, j, keyword) -> bool:
    """Does the token immediately before position j on line i (skipping whitespace,
    walking back across lines if needed) equal `keyword` at a word boundary?"""
    line = masked_lines[i]
    k = j - 1
    while True:
        while k >= 0 and line[k].isspace():
            k -= 1
        if k >= 0:
            end = k + 1
            start = k
            while start >= 0 and (line[start].isalnum() or line[start] == "_"):
                start -= 1
            start += 1
            token = line[start:end]
            boundary_ok = start == 0 or not (line[start - 1].isalnum() or line[start - 1] == "_")
            return token == keyword and boundary_ok
        i -= 1
        if i < 0:
            return False
        line = masked_lines[i]
        k = len(line) - 1


# ---------------------------------------------------------------------------
# EXTENT DETECTION
# ---------------------------------------------------------------------------

def _find_assert_extent(masked_lines, start):
    """Statement mode: ends at `;` at depth 0, or at the `}` closing a brace that is
    provably a `by { ... }` block (not just any brace at depth 0 — that would also
    fire on `assert x in {1,2,3};` and misresolve it). Returns 0-based end line, or
    None to refuse."""
    depth = 0
    by_block_base = None
    limit = min(start + MAX_SPAN, len(masked_lines))
    for i in range(start, limit):
        line = masked_lines[i]
        for j, c in enumerate(line):
            if by_block_base is None and depth == 0 and c == ";":
                return i if line[j + 1:].strip() == "" else None
            if c in "([{":
                if c == "{" and by_block_base is None and depth == 0 \
                        and _preceded_by_keyword(masked_lines, i, j, "by"):
                    by_block_base = depth
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth < 0:
                    return None
                if by_block_base is not None and depth == by_block_base and c == "}":
                    return i if line[j + 1:].strip() == "" else None
    return None


_DECREASES_STAR_RE = re.compile(r"^\s*decreases\s*\*\s*$")


def _find_spec_extent(masked_lines, start):
    """Spec mode (invariant/decreases/modifies/reads/requires/ensures): never
    semicolon-terminated (some styles DO add a trailing `;` for readability — that
    is harmless punctuation here, not a terminator, since nothing treats `;`
    specially in this mode). Extends across lines only while bracket depth is
    unbalanced or an explicit continuation token is present; stops the instant
    depth is 0 and the following line does not open with one too — regardless of
    what that following line otherwise contains, since it is never itself part of
    the accepted extent, only evidence for where the extent already ended. A brace
    that opens with nothing left on its line is refused outright rather than
    chased forward: that shape is a glued-on body opener, not a same-line set/map
    display, and walking to its match would swallow the loop/method body whole."""
    soft = 0   # () []
    brace = 0  # {}
    limit = min(start + MAX_SPAN, len(masked_lines))
    for i in range(start, limit):
        mline = masked_lines[i]
        for pos, c in enumerate(mline):
            if c in "([":
                soft += 1
            elif c in ")]":
                soft -= 1
                if soft < 0:
                    return None
            elif c == "{":
                if brace == 0 and mline[pos + 1:].strip() == "":
                    # Nothing else on the line after this brace: the shape of a
                    # glued-on body opener, not a same-line set/map display.
                    # Chasing its match would walk into the loop/method body.
                    return None
                brace += 1
            elif c == "}":
                brace -= 1
                if brace < 0:
                    return None
        if brace != 0 or soft != 0:
            continue
        # `decreases *` is Dafny's fixed idiom for "no termination proof"; its `*`
        # is a bare literal token, not a multiplication operator awaiting a right
        # operand, so it must NOT be read as "more to come" the way a genuine
        # trailing `*` (`invariant x == y *`) legitimately is.
        is_decreases_star = i == start and _DECREASES_STAR_RE.match(mline)
        if not is_decreases_star and _ends_with_continuation(mline):
            continue
        nxt = i + 1
        if nxt >= len(masked_lines):
            return i
        nxt_line = masked_lines[nxt]
        if nxt_line.strip() == "":
            return i
        if _starts_with_continuation(nxt_line):
            continue
        # Depth is balanced and neither side of this boundary reads as a
        # continuation: the clause is done. What the next line otherwise
        # contains — another clause, a lone brace, a whole one-line body
        # (`{ i := i + 1; }`), unrelated code — does not matter, because that
        # line is only ever consulted here, never included in the extent.
        return i
    return None


def _find_calc_extent(masked_lines, start):
    """calc's grammar guarantees a `{` follows shortly and is the block; plain
    brace-depth matching to its close is safe (no `by`-lookback needed)."""
    depth = 0
    opened = False
    limit = min(start + MAX_CALC_SPAN, len(masked_lines))
    for i in range(start, limit):
        for c in masked_lines[i]:
            if c == "{":
                depth += 1
                opened = True
            elif c == "}":
                depth -= 1
                if depth < 0:
                    return None
                if opened and depth == 0:
                    return i
    return None


def find_hints(src: str, kinds=DEFAULT_KINDS, include_calc: bool = False):
    """Multi-line-safe hints as (start_line, end_line, kind, text) — 0-based,
    inclusive on both ends, both endpoints wholly owned by the clause so the range
    is always safe to delete as a contiguous whole-line block.

    Deliberately does NOT skip past an accepted extent's interior: a `by { }` block
    (or a calc block) commonly contains its own nested `assert` statements, each of
    which is ALSO independently excisable — deleting just the inner line leaves the
    outer block intact, a strictly more minimal ablation than deleting the whole
    outer block. Every line is checked as its own candidate regardless of whether an
    enclosing extent already claimed it, so both the coarse outer hint and the finer
    nested ones are returned; a plain continuation line of a spec clause never
    starts with a clause keyword, so it never spuriously matches here anyway.
    Measured: an early version that skipped to `end + 1` silently dropped exactly
    this nested-assert case relative to dp.find_hints (112 of 300 sampled files) —
    see module __main__.
    """
    masked_lines = mask_source(src).splitlines()
    orig_lines = src.splitlines()
    out = []
    n = len(masked_lines)
    for i in range(n):
        mline = masked_lines[i]
        m = _KIND_RE.match(mline)
        if m and m.group(1) in kinds:
            kind = m.group(1)
            end = _find_assert_extent(masked_lines, i) if kind == "assert" \
                else _find_spec_extent(masked_lines, i)
            if end is not None:
                text = "\n".join(orig_lines[i:end + 1]).strip()
                out.append((i, end, kind, text))
                continue
        if include_calc and _CALC_RE.match(mline):
            end = _find_calc_extent(masked_lines, i)
            if end is not None:
                text = "\n".join(orig_lines[i:end + 1]).strip()
                out.append((i, end, "calc", text))
    return out


def count_candidates(src: str, kinds=DEFAULT_KINDS) -> int:
    """How many lines LOOK like a clause start (before extent resolution) — the
    denominator for a refusal rate: candidates seen vs hints actually accepted."""
    masked_lines = mask_source(src).splitlines()
    return sum(1 for line in masked_lines
               if (m := _KIND_RE.match(line)) and m.group(1) in kinds)


def excise(src: str, start: int, end: int) -> str:
    """Delete lines [start, end] (0-based, inclusive) whole. Mirrors dp.drop_line's
    convention exactly (splitlines + join + trailing newline) so excised variants
    are byte-shaped the same way the baseline's are."""
    lines = src.splitlines()
    return "\n".join(lines[:start] + lines[end + 1:]) + "\n"


# ---------------------------------------------------------------------------
# PAIR GENERATION — same contract as dafny_pairs.pairs_from_file, swapped to the
# multi-line extractor. A pair is real only on a measured VERIFIED -> REFUTED flip.
# ---------------------------------------------------------------------------

@dataclass
class Pair:
    source_path: str
    hint_kind: str
    hint_line: int       # 1-based START line removed
    hint_end_line: int   # 1-based END line removed (equal to hint_line for single-line hints)
    hint_text: str
    chosen: str
    rejected: str
    diagnostic: str


def pairs_from_file(path, rlimit: int = dv.DEFAULT_RLIMIT, kinds=DEFAULT_KINDS,
                     include_calc: bool = False, max_variants: int | None = None):
    """Verify the original, then ablate one (possibly multi-line) hint at a time.
    Returns (pairs, stats). `stats['outcomes']` tallies EVERY variant's outcome, not
    just the REFUTED ones that become pairs, so a malformed rate can be computed
    without re-deriving it from the pairs list."""
    stats = {"file": str(path), "candidates": 0, "hints": 0, "variants": 0, "pairs": 0,
              "base": "", "outcomes": {}}
    try:
        src = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        stats["base"] = "unreadable"
        return [], stats

    base = dv.verify_source(src, rlimit=rlimit)
    stats["base"] = base.outcome
    stats["candidates"] = count_candidates(src, kinds=kinds)
    if base.outcome != dv.Outcome.VERIFIED:
        return [], stats

    hints = find_hints(src, kinds=kinds, include_calc=include_calc)
    stats["hints"] = len(hints)
    if max_variants:
        hints = hints[:max_variants]

    pairs = []
    tally = Counter()
    for start, end, kind, text in hints:
        variant = excise(src, start, end)
        r = dv.verify_source(variant, rlimit=rlimit)
        stats["variants"] += 1
        tally[r.outcome] += 1
        if r.outcome != dv.Outcome.REFUTED:
            continue
        diag = "; ".join(d["message"] for d in r.diagnostics[:3])
        pairs.append(Pair(str(path), kind, start + 1, end + 1, text, src, variant, diag))
    stats["outcomes"] = dict(tally)
    stats["pairs"] = len(pairs)
    return pairs, stats


def generate(paths, rlimit: int = dv.DEFAULT_RLIMIT, workers: int = 8, kinds=DEFAULT_KINDS,
             include_calc: bool = False, max_variants: int | None = None):
    """Parallel over FILES (each file's variants run sequentially inside), capped at
    `workers` — shared box, keep it modest."""
    def one(p):
        return pairs_from_file(p, rlimit=rlimit, kinds=kinds,
                                include_calc=include_calc, max_variants=max_variants)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, paths))
    pairs = [p for ps, _ in results for p in ps]
    stats = [s for _, s in results]
    return pairs, stats


def write_jsonl(pairs, dest: Path):
    dest.write_text("\n".join(json.dumps(p.__dict__) for p in pairs), encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# __main__ — MEASURE, don't estimate. Every number printed below comes from a run
# that just happened, against the named 8-directory corpus (4,584 files) — NOT the
# ~120k .dfy files that a concurrent process was actively cloning into
# dafny-corpus/ under other directory names during this session (confirmed by
# directory mtimes of 18:09-18:11 today, vs the named 8 dirs' 16:57-17:30). Those
# are someone else's live, unreviewed, unreproducible input; scoping to the named
# 8 keeps every number here reproducible and comparable to the standing baselines.
# ---------------------------------------------------------------------------

CORPUS_ROOT = Path.home() / "dafny-corpus"
NAMED_DIRS = ("dafny-main", "DafnyBench", "dafny-synthesis", "libraries",
              "aws-cmpl", "aws-esdk", "evm-dafny", "reportgen")
GROUND_TRUTH = CORPUS_ROOT / "DafnyBench" / "DafnyBench" / "dataset" / "ground_truth"


def _named_corpus_files():
    out = []
    for d in NAMED_DIRS:
        out.extend((CORPUS_ROOT / d).rglob("*.dfy"))
    return sorted(out)


def _structural_comparison(files, dp_module):
    """No verification needed: pure text-level hints-per-file, dp vs this module."""
    dp_counts, my_counts = [], []
    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        dp_counts.append(len(dp_module.find_hints(src)))
        my_counts.append(len(find_hints(src, kinds=DEFAULT_KINDS)))
    n = len(dp_counts)
    zero_dp = sum(1 for c in dp_counts if c == 0)
    zero_my = sum(1 for c in my_counts if c == 0)
    return {
        "files": n,
        "dp_avg_hints_per_file": sum(dp_counts) / n if n else 0.0,
        "my_avg_hints_per_file": sum(my_counts) / n if n else 0.0,
        "dp_zero_hint_files": zero_dp,
        "my_zero_hint_files": zero_my,
        "dp_zero_hint_pct": 100.0 * zero_dp / n if n else 0.0,
        "my_zero_hint_pct": 100.0 * zero_my / n if n else 0.0,
        "dp_total_hints": sum(dp_counts),
        "my_total_hints": sum(my_counts),
    }


def _ablation_comparison(files, dp_module, rlimit, workers, max_variants):
    """Verification-heavy: single-hint ablation, dp vs this module, on the SAME
    files. Reports malformed rate and pairs-per-verified-file for each."""
    def run_dp(p):
        return dp_module.pairs_from_file(Path(p), rlimit=rlimit, max_variants=max_variants)

    def run_mine(p):
        return pairs_from_file(p, rlimit=rlimit, kinds=DEFAULT_KINDS, max_variants=max_variants)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        dp_results = list(ex.map(run_dp, files))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        my_results = list(ex.map(run_mine, files))

    def summarize(results, has_outcomes):
        stats = [s for _, s in results]
        pairs = [p for ps, _ in results for p in ps]
        verified_files = [s for s in stats if s["base"] == dv.Outcome.VERIFIED]
        total_variants = sum(s["variants"] for s in stats)
        total_hints = sum(s.get("hints", s.get("candidates", 0)) for s in verified_files)
        outcome_tally = Counter()
        if has_outcomes:
            for s in stats:
                outcome_tally.update(s.get("outcomes", {}))
        malformed = outcome_tally.get(dv.Outcome.MALFORMED, 0)
        return {
            "base_files": len(stats),
            "base_verified": len(verified_files),
            "total_hints_on_verified": total_hints,
            "total_variants": total_variants,
            "pairs": len(pairs),
            "pairs_per_verified_file": (len(pairs) / len(verified_files)) if verified_files else 0.0,
            "flip_rate_of_variants": (len(pairs) / total_variants) if total_variants else 0.0,
            "outcome_tally": dict(outcome_tally),
            "malformed_rate_of_variants": (malformed / total_variants) if total_variants and has_outcomes else None,
        }

    return {"dp_baseline": summarize(dp_results, has_outcomes=False),
            "mine": summarize(my_results, has_outcomes=True)}


if __name__ == "__main__":
    import argparse
    import importlib
    import sys
    import time

    ap = argparse.ArgumentParser(description="dafny_hints measurement harness")
    ap.add_argument("--structural-sample", type=int, default=300,
                     help="files sampled from the named 8-dir corpus for the (cheap, no-verify) hints-per-file comparison")
    ap.add_argument("--ablation-sample", type=int, default=150,
                     help="files sampled from DafnyBench ground_truth for the (verification-heavy) yield/malformed comparison")
    ap.add_argument("--max-variants", type=int, default=20,
                     help="cap on hint-ablation verifications per file, so one 100+-hint outlier can't dominate wall time")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rlimit", type=int, default=dv.DEFAULT_RLIMIT)
    ap.add_argument("--seed", type=int, default=20260827)
    args = ap.parse_args()

    dp = importlib.import_module("dafny_pairs")

    all_files = _named_corpus_files()
    print(f"[corpus] named 8-dir corpus: {len(all_files)} .dfy files "
          f"(dafny-main, DafnyBench, dafny-synthesis, libraries, aws-cmpl, aws-esdk, evm-dafny, reportgen)",
          file=sys.stderr)

    rng = random.Random(args.seed)
    struct_sample = rng.sample(all_files, min(args.structural_sample, len(all_files)))

    t0 = time.time()
    struct = _structural_comparison(struct_sample, dp)
    struct["wall_s"] = round(time.time() - t0, 2)
    struct["seed"] = args.seed
    print("\n=== STRUCTURAL: hints-per-file, dp.find_hints vs dafny_hints.find_hints ===")
    print(json.dumps(struct, indent=2))

    gt_files = sorted(GROUND_TRUTH.glob("*.dfy"))
    print(f"\n[corpus] DafnyBench ground_truth: {len(gt_files)} files "
          f"(the corpus the standing 1.53-pairs/389-of-782 baselines were measured on)",
          file=sys.stderr)
    rng2 = random.Random(args.seed + 1)
    abl_sample = rng2.sample(gt_files, min(args.ablation_sample, len(gt_files)))

    t0 = time.time()
    abl = _ablation_comparison(abl_sample, dp, rlimit=args.rlimit, workers=args.workers,
                                max_variants=args.max_variants)
    abl["wall_s"] = round(time.time() - t0, 2)
    abl["sample_size"] = len(abl_sample)
    abl["seed"] = args.seed + 1
    abl["max_variants_cap"] = args.max_variants
    print("\n=== ABLATION: single-hint yield + malformed rate, dp vs dafny_hints, same files ===")
    print(json.dumps(abl, indent=2))
