#!/usr/bin/env python3
"""dafny_pairs.py — turn ONE verified Dafny file into MANY preference pairs.

DafnyBench ships 782 (original, hints-stripped) pairs, of which we measured 389
usable. That ceiling exists only because someone stripped each program ONCE. The
verifier is the oracle for both halves of that operation, so there is no reason to
accept a fixed corpus: any file that verifies is a pair GENERATOR.

THE ABLATION IS SINGLE-HINT, AND THAT IS A DELIBERATE CHOICE
------------------------------------------------------------
Removing every hint at once (DafnyBench's `_no_hints`) produces at most one pair
per file, and it produces the EASIEST possible negative — the proof is missing so
much that failure says little about which piece mattered. Removing exactly ONE
hint at a time gives:

  * up to N pairs from a file with N hints, instead of 1;
  * a MINIMAL broken proof — the rejected side differs from the chosen side by a
    single line, so the preference signal isolates that line instead of rewarding
    "write more invariants";
  * a natural proof-repair triple for free: (broken source, the verifier's own
    diagnostic, the one line that fixes it).

WHY THE FLIP MUST BE MEASURED, NOT ASSUMED
------------------------------------------
Deleting a hint does NOT reliably break a proof. We measured this on DafnyBench:
210 of 782 stripped files (26.9%) still verify — Z3 finds the proof without the
hint. Those are `rejected_verified`, preference noise pointing the wrong way, and
a generator that assumed "hint removed => now fails" would mint them by the
thousand. So every candidate variant is VERIFIED, and only a genuine
verified -> refuted flip is kept.

Deleting a hint can also break the PARSE rather than the proof (63 of 782 on
DafnyBench). dafny_verify classifies that MALFORMED, and it is discarded: a
rejected that fails to parse teaches syntax, not proof.

CONSERVATIVE BY CONSTRUCTION: only hints that occupy a WHOLE SINGLE LINE are
candidates. A multi-line `invariant` continuation would need real parsing to
excise correctly, and guessing at it produces malformed variants that look like
findings. Refuse rather than guess — the yield is lower and every pair is real.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import dafny_verify as dv

# A hint is a line whose ENTIRE content is one proof annotation. Anchored at both
# ends on purpose: `assert` inside a larger expression, or an `invariant` sharing a
# line with code, is not safely removable by line deletion.
HINT_RE = re.compile(
    r"^\s*(?P<kind>invariant|assert|decreases|ensures|requires|modifies|reads)\b.*$")

# ensures/requires are NOT stripped by default: removing a postcondition usually makes
# the proof EASIER (often trivially vacuous), so the variant verifies and is discarded
# anyway — and where it does fail, the "fix" is to restate the spec, which is the
# spec-writing task, not the proof task. Kept in the regex so callers can opt in.
DEFAULT_KINDS = ("invariant", "assert", "decreases")


@dataclass
class Pair:
    source_path: str
    hint_kind: str
    hint_line: int          # 1-based line number removed
    hint_text: str
    chosen: str             # the original, verified
    rejected: str           # original minus one hint, genuinely refuted
    diagnostic: str         # the verifier's own complaint about `rejected`


def find_hints(src: str, kinds=DEFAULT_KINDS):
    """Whole-line proof annotations, as (0-based index, kind, text)."""
    out = []
    for i, line in enumerate(src.splitlines()):
        m = HINT_RE.match(line)
        if not m:
            continue
        if m.group("kind") not in kinds:
            continue
        # A clause continued on the next line cannot be removed by deleting this one.
        stripped = line.rstrip()
        if not (stripped.endswith(";") or stripped.endswith("{")
                or _next_line_starts_clause(src, i)):
            continue
        out.append((i, m.group("kind"), line.strip()))
    return out


def _next_line_starts_clause(src: str, i: int) -> bool:
    lines = src.splitlines()
    if i + 1 >= len(lines):
        return False
    nxt = lines[i + 1].lstrip()
    return bool(re.match(r"^(invariant|assert|decreases|ensures|requires|modifies|reads|\{|\})",
                         nxt))


def drop_line(src: str, idx: int) -> str:
    lines = src.splitlines()
    return "\n".join(lines[:idx] + lines[idx + 1:]) + "\n"


def pairs_from_file(path: Path, rlimit: int = dv.DEFAULT_RLIMIT,
                    max_variants: int | None = None) -> tuple[list, dict]:
    """Verify the original, then ablate one hint at a time. Returns (pairs, stats)."""
    stats = {"file": str(path), "hints": 0, "variants": 0, "pairs": 0, "base": ""}
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        stats["base"] = "unreadable"
        return [], stats

    base = dv.verify_source(src, rlimit=rlimit)
    stats["base"] = base.outcome
    # Only a REAL proof seeds pairs. A vacuous base would mint pairs whose `chosen`
    # proves nothing — the exact 20 poisoned pairs the DafnyBench run surfaced.
    if base.outcome != dv.Outcome.VERIFIED:
        return [], stats

    hints = find_hints(src)
    stats["hints"] = len(hints)
    if max_variants:
        hints = hints[:max_variants]

    pairs = []
    for idx, kind, text in hints:
        variant = drop_line(src, idx)
        r = dv.verify_source(variant, rlimit=rlimit)
        stats["variants"] += 1
        if r.outcome != dv.Outcome.REFUTED:
            continue                      # still verifies, or broke the parse — discard
        diag = "; ".join(d["message"] for d in r.diagnostics[:3])
        pairs.append(Pair(str(path), kind, idx + 1, text, src, variant, diag))
    stats["pairs"] = len(pairs)
    return pairs, stats


def generate(paths, rlimit: int = dv.DEFAULT_RLIMIT, workers: int = 12,
             max_variants: int | None = None):
    """Parallel over FILES (each file's variants run sequentially inside)."""
    def one(p):
        return pairs_from_file(Path(p), rlimit=rlimit, max_variants=max_variants)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, paths))
    pairs = [p for ps, _ in results for p in ps]
    stats = [s for _, s in results]
    return pairs, stats


def write_jsonl(pairs, dest: Path):
    dest.write_text("\n".join(json.dumps(p.__dict__) for p in pairs), encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# SUBSET ABLATION — and the reason it is MINIMAL subsets, not all subsets.
#
# Single-hint ablation yields <=N pairs from N hints and measured 1.53 pairs per
# verified file. The obvious extension is "remove every subset", but 2^N is both
# unaffordable (one verification each) and WRONG: if dropping {A} already breaks
# the proof, then dropping {A,B} breaks it too, trivially. That superset is a
# STRICTLY EASIER negative — more is missing, so the preference signal is weaker
# and the pair teaches less. Minting it would inflate the count while diluting the
# data, which is the same self-deception the ruler's saturation failure was.
#
# The valuable object is the MINIMAL BREAKING SUBSET: a set of hints whose removal
# refutes the proof, but every proper subset of which still verifies. That is the
# smallest possible perturbation to the chosen side, i.e. the hardest negative.
#
# So this searches by increasing size and prunes:
#   k=1  every hint alone. Flips -> minimal. Non-flips -> SURVIVORS.
#   k>=2 combinations drawn ONLY from survivors (so no singleton break is inside),
#        skipping any candidate that is a superset of an already-found minimal set.
#
# This is also exactly where the DafnyBench loss goes. 210 of 782 stripped files
# (26.9%) still verified — Z3 did not need the hint. Those hints are precisely the
# SURVIVORS here, and combinations of them are where the new pairs come from: a
# hint that is redundant alone is often load-bearing together with another.
# ---------------------------------------------------------------------------

from itertools import combinations


def drop_lines(src: str, idxs) -> str:
    keep = set(range(len(src.splitlines()))) - set(idxs)
    lines = src.splitlines()
    return "\n".join(lines[i] for i in sorted(keep)) + "\n"


def subset_pairs_from_file(path: Path, rlimit: int = dv.DEFAULT_RLIMIT,
                           max_k: int = 3, budget: int = 60):
    """Minimal breaking subsets, breadth-first with superset pruning.

    `budget` caps verifications PER FILE — a file with 12 hints would otherwise cost
    12 + 66 + 220 at k<=3. Bounded work is reported, never silently truncated: the
    stats carry `budget_hit` so a capped file is visible rather than looking complete.
    """
    stats = {"file": str(path), "hints": 0, "variants": 0, "pairs": 0,
             "base": "", "survivors": 0, "budget_hit": False}
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        stats["base"] = "unreadable"
        return [], stats

    base = dv.verify_source(src, rlimit=rlimit)
    stats["base"] = base.outcome
    if base.outcome != dv.Outcome.VERIFIED:
        return [], stats

    hints = find_hints(src)
    stats["hints"] = len(hints)
    if not hints:
        return [], stats

    by_idx = {h[0]: h for h in hints}
    spent = 0
    minimal: list[frozenset] = []
    pairs: list[Pair] = []

    def try_subset(idxs) -> bool:
        nonlocal spent
        variant = drop_lines(src, idxs)
        r = dv.verify_source(variant, rlimit=rlimit)
        spent += 1
        if r.outcome != dv.Outcome.REFUTED:
            return False
        diag = "; ".join(d["message"] for d in r.diagnostics[:3])
        kinds = "+".join(by_idx[i][1] for i in sorted(idxs))
        text = " | ".join(by_idx[i][2] for i in sorted(idxs))
        pairs.append(Pair(str(path), kinds, sorted(idxs)[0], text, src, variant, diag))
        return True

    # k = 1
    survivors = []
    for idx, _kind, _text in hints:
        if spent >= budget:
            stats["budget_hit"] = True
            break
        if try_subset([idx]):
            minimal.append(frozenset([idx]))
        else:
            survivors.append(idx)
    stats["survivors"] = len(survivors)

    # k >= 2, survivors only, pruning supersets of known minimal sets
    for k in range(2, max_k + 1):
        if spent >= budget:
            stats["budget_hit"] = True
            break
        for combo in combinations(survivors, k):
            if spent >= budget:
                stats["budget_hit"] = True
                break
            cs = frozenset(combo)
            if any(m <= cs for m in minimal):
                continue
            if try_subset(list(combo)):
                minimal.append(cs)

    stats["variants"] = spent
    stats["pairs"] = len(pairs)
    return pairs, stats


def generate_subsets(paths, rlimit: int = dv.DEFAULT_RLIMIT, workers: int = 12,
                     max_k: int = 3, budget: int = 60):
    def one(p):
        return subset_pairs_from_file(Path(p), rlimit=rlimit, max_k=max_k, budget=budget)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, paths))
    return [p for ps, _ in results for p in ps], [s for _, s in results]
