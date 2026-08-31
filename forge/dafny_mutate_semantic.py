#!/usr/bin/env python3
"""dafny_mutate_semantic.py — NEAR-MISS negatives via semantic mutation, not deletion.

dafny_pairs.py's ablation deletes a whole hint line. That is an easy negative: the
model can learn "rejected = something is missing" without ever engaging with what
the hint actually SAID. This module does the harder thing: perturb one spec clause
in a way that PRESERVES its shape (same clause, same identifiers, one operator or
one constant changed) so the rejected side is a program that looks almost right and
is provably wrong. That is the negative worth paying for.

THE CONTRACT IS THE SAME GATE AS dafny_pairs.py, ENFORCED THE SAME WAY
------------------------------------------------------------------------
  base   must be dv.Outcome.VERIFIED   (never VACUOUS — see dv.spec_strength's own
         warning: seed only from a real proof)
  mutant must be dv.Outcome.REFUTED    (a mutant that still verifies is preference
         noise pointing the wrong way; a mutant that is MALFORMED teaches syntax,
         not proof, and must be counted, never silently dropped — rule 2/4 of the
         project brief)

CONSERVATIVE BY THE SAME CONSTRUCTION dafny_pairs.py USES: only whole-single-line
spec clauses (`invariant` / `ensures` / `requires` / `decreases`) are mutated, and
every mutation is a REGEX SUBSTITUTION within that one line — never a multi-line
rewrite, never a guess at intent. A mutation that fails to match its pattern
produces no candidate at all. This keeps "still PARSES" true by construction for
every operator except in the small number of cases the malformed-rate column
below reports.

OPERATORS (each is its own named, independently measured category; the module
must report yield AND malformed rate per operator, not a pooled average that
could hide one broken operator inside five working ones):

  bound_tighten     <=->/>=->    e.g. `i <= n` -> `i < n`   ("weaken the bound" in
                     the brief's own words — narrowing what the loop invariant
                     claims can break maintenance at the boundary the loop
                     actually reaches, which is a different failure mode from
                     bound_loosen below even though the edit looks similar)
  bound_loosen      <->/> -> >=  e.g. `i < n` -> `i <= n`   (the reverse edit —
                     "strengthen [an already-tight bound] until it no longer
                     holds": widening a strict inequality can admit a boundary
                     value the proof does not actually cover)
  constant_shift    integer literal k -> k+1 and k-1, on invariant/ensures/
                     requires lines (decreases handled separately below so each
                     operator's stats stay uncontaminated by the other clause
                     kind)
  decreases_perturb same shift, restricted to `decreases` lines, plus a lone
                     `+`/`-` flip when the expression has exactly one — this is
                     the one operator that targets termination instead of
                     partial correctness, so it is kept separate on purpose
  quantifier_narrow  `lo <= v < hi` / `lo <= v <= hi` inside a forall's range
                     antecedent -> shrink the range by one at whichever end is
                     present (hi down, or lo up)
  conjunct_to_true   one `&&`-joined conjunct (top-level, paren-balanced split)
                     replaced by the literal `true`, leaving the rest of the
                     clause intact — a partial version of dafny_pairs' deletion,
                     scoped to a fragment of a line instead of the whole line

WHAT THIS DOES NOT COVER (stated so silence cannot be read as coverage — rule 4)
  * Multi-line clauses are invisible to CLAUSE_RE by construction, same refusal
    dafny_pairs.py makes for the same reason: guessing at a continuation risks
    minting malformed variants that look like findings.
  * conjunct_to_true only sees `&&` joined at the TOP level of the line's own
    paren nesting; a conjunct buried inside a function call or a nested forall
    is not reachable and is silently skipped, not attempted.
  * A file with none of these four clause kinds, or none containing a relational
    operator / literal / forall-range / `&&`, yields zero candidates. That is
    reported as `candidates: 0` in per-file stats, exactly like dafny_pairs.py's
    own zero-hint files — it is not this module failing quietly.
  * This is single-mutation ablation, the same deliberate scope limit
    dafny_pairs.py documents for single-hint deletion: one clause, one edit, one
    verification. It does not compose two operators in the same variant.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import dafny_verify as dv

# Whole-line spec clause, anchored at both ends exactly like dafny_pairs.HINT_RE —
# a clause sharing its line with other code, or continued onto the next line, is
# not safely rewritable in place and is refused rather than guessed at.
CLAUSE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<kind>invariant|ensures|requires|decreases)\b(?P<rest>.*)$")

_INT_RE = re.compile(r"(?<![\w.])(\d+)(?![\w.])")

# lo <= v < hi   or   lo <= v <= hi   inside a forall's range antecedent.
#
# MEASURED AND FIXED: an earlier version let lo/hi include `(` and `)`, meaning
# a function-call bound (`i < length(l)`) could match. The lookahead that ends
# hi stops at a literal `)`, and with parens in hi's own charset the lazy
# match can stop AT THE FIRST `)` it meets — including one that belongs to the
# call inside hi, before hi's own `(` is balanced. That produced
# `length(l - 1)` instead of the intended `length(l) - 1`: the `- 1` landed
# inside the call's argument, not after the call, and Dafny correctly refused
# it as a type error (`length` expects a sequence, not `l - 1`). Measured on a
# 40-file sample: this was quantifier_narrow's one malformed case (1/43).
# Fixed the conservative way, not by trying to balance parens in a regex:
# hi/lo simply EXCLUDE `(` and `)`, so a paren'd bound fails to match at all
# and produces no candidate — refuse rather than risk a wrong edit that still
# happens to look balanced.
_QRANGE_RE = re.compile(
    r"(?P<lo>[\w+\-.\s]+?)\s*(?P<oplo><=|<)\s*(?P<var>\w+)\s*(?P<ophi><=|<)\s*(?P<hi>[\w+\-.\s]+?)(?=\s*(==>|&&|\)|$))")


@dataclass
class Mutation:
    source_path: str
    operator: str
    line_idx: int          # 1-based, the line that was rewritten
    original_line: str
    mutated_line: str
    chosen: str             # the original, verified
    rejected: str            # original with ONE clause rewritten, genuinely refuted
    diagnostic: str          # the verifier's own complaint about `rejected`


def _clause_lines(src: str):
    """(0-based idx, kind, indent, rest-after-kind) for whole-line clauses only."""
    out = []
    lines = src.splitlines()
    for i, line in enumerate(lines):
        m = CLAUSE_RE.match(line)
        if not m:
            continue
        stripped = line.rstrip()
        # Same continuation guard as dafny_pairs.find_hints: only touch a clause
        # that is NOT continued onto the next line, so the rewritten line stays
        # syntactically self-contained.
        nxt = lines[i + 1].lstrip() if i + 1 < len(lines) else ""
        continued = bool(re.match(
            r"^(invariant|assert|decreases|ensures|requires|modifies|reads|&&|\|\|)", nxt))
        if not (stripped.endswith(";") or stripped.endswith("{") or not continued):
            continue
        out.append((i, m.group("kind"), m.group("indent"), m.group("rest")))
    return out


def _split_top_level(rest: str, sep: str) -> list[tuple[int, int]]:
    """Byte spans of `sep`-joined top-level segments, paren/bracket balanced."""
    spans, depth, start = [], 0, 0
    i, n, L = 0, len(rest), len(sep)
    while i < n:
        c = rest[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and rest[i:i + L] == sep:
            spans.append((start, i))
            start = i + L
            i += L
            continue
        i += 1
    spans.append((start, n))
    return spans


# ---------------------------------------------------------------------------
# Operator A/B: relational tighten / loosen on invariant|ensures|requires lines
# (decreases lines are excluded here — decreases_perturb owns that clause kind
# so each operator's yield/malformed stats stay attributable to one edit shape).
# ---------------------------------------------------------------------------
_TIGHTEN = {"<=": "<", ">=": ">"}
_LOOSEN = {"<": "<=", ">": ">="}

# MEASURED AND FIXED: a naive `rest.find("<=")` / `rest.find("<")` substring
# search cannot tell a real relational operator from the same characters
# appearing inside one of Dafny's longer arrow tokens (`==>`, `<==`, `<==>`,
# iff/implies). A first pass guarded only the single-char `<`/`>` scan against
# a neighboring `=`; that missed the two-char `<=` scan entirely, so
# bound_tighten turned `Less(x,y) <==> ...` into `Less(x,y) <=> ...` — an
# invalid token, "this operator chain cannot continue" — on a 40-file sample.
# Fixed the general way: tokenize the whole line against EVERY operator that
# shares a prefix with the ones we mutate, longest alternative first, so the
# regex engine — not ad hoc lookaround — decides whether a `<` at some column
# belongs to a lone `<`, a `<=`, or is swallowed into `<==`/`<==>`. We only
# emit a mutation when the token matched at that position is a bare key in
# `mapping`; a token that resolved to an arrow is never a candidate.
_OP_TOKEN_RE = re.compile(r"<==>|<==|==>|<=|>=|==|!=|<|>")


def _relop_variants(rest: str, mapping: dict) -> list[tuple[str, str]]:
    """Every single-occurrence swap of an operator in `mapping`, one at a time,
    identified by tokenizing `rest` rather than by substring search."""
    out = []
    for m in _OP_TOKEN_RE.finditer(rest):
        tok = m.group()
        if tok not in mapping:
            continue
        j = m.start()
        new_rest = rest[:j] + mapping[tok] + rest[m.end():]
        out.append((new_rest, f"{tok}->{mapping[tok]} at col {j}"))
    return out


def op_bound_tighten(kind, indent, rest):
    if kind == "decreases":
        return []
    return [(indent + kind + new, desc) for new, desc in _relop_variants(rest, _TIGHTEN)]


def op_bound_loosen(kind, indent, rest):
    if kind == "decreases":
        return []
    return [(indent + kind + new, desc) for new, desc in _relop_variants(rest, _LOOSEN)]


# ---------------------------------------------------------------------------
# Operator C: constant_shift — invariant/ensures/requires only.
# Operator D: decreases_perturb — decreases only (shift + lone +/- flip).
# ---------------------------------------------------------------------------
def _constant_shift_variants(rest: str) -> list[tuple[str, str]]:
    out = []
    for m in _INT_RE.finditer(rest):
        val = int(m.group(1))
        for delta in (1, -1):
            newval = val + delta
            if newval < 0:
                continue
            new_rest = rest[:m.start()] + str(newval) + rest[m.end():]
            out.append((new_rest, f"{val}->{newval} at col {m.start()}"))
    return out


def op_constant_shift(kind, indent, rest):
    if kind == "decreases":
        return []
    return [(indent + kind + new, desc) for new, desc in _constant_shift_variants(rest)]


def op_decreases_perturb(kind, indent, rest):
    if kind != "decreases":
        return []
    variants = [(new, desc) for new, desc in _constant_shift_variants(rest)]
    # A lone top-level +/- (exactly one occurrence) flipped: `n - i` -> `n + i`.
    ops_found = [i for i, c in enumerate(rest) if c in "+-"]
    if len(ops_found) == 1:
        i = ops_found[0]
        flipped = "-" if rest[i] == "+" else "+"
        new_rest = rest[:i] + flipped + rest[i + 1:]
        variants.append((new_rest, f"{rest[i]}->{flipped} at col {i}"))
    return [(indent + kind + new, desc) for new, desc in variants]


# ---------------------------------------------------------------------------
# Operator E: quantifier_narrow — shrink a `lo <= v < hi` / `lo <= v <= hi`
# range inside a forall antecedent by one at whichever end exists.
# ---------------------------------------------------------------------------
def op_quantifier_narrow(kind, indent, rest):
    """Shrink a `lo <= v < hi` / `lo <= v <= hi` range by one at whichever end
    exists. Edits are made INSIDE the matched lo/hi subgroup spans only — never
    by rebuilding the lo..hi region from stripped parts — so whitespace outside
    the literal that actually changes is left untouched. (An earlier version
    reassembled the whole span from `.strip()`ed pieces and silently ate the
    space after `::`, turning `:: 0 <=` into `::0 <=`; cosmetic in Dafny's
    whitespace-insensitive grammar, but a needless second edit riding along
    with the intended one.)"""
    if "forall" not in rest:
        return []
    out = []
    for m in _QRANGE_RE.finditer(rest):
        hi_raw, lo_raw = m.group("hi"), m.group("lo")
        hi, lo = hi_raw.strip(), lo_raw.strip()

        if re.fullmatch(r"\d+", hi):
            new_hi = str(max(0, int(hi) - 1))
            new_frag = hi_raw.replace(hi, new_hi, 1)
        else:
            # Non-literal bound (`|result|`, `n-1`, a variable): append the
            # perturbation rather than guess at precedence. Safe without parens
            # — hi sits after the last comparison operator, so `- 1` here only
            # changes the arithmetic value being compared, not what's compared.
            new_hi = None
            new_frag = hi_raw + " - 1"
        a, b = m.span("hi")
        out.append((rest[:a] + new_frag + rest[b:], f"narrow hi {hi}->{new_hi or (hi + ' - 1')}"))

        if re.fullmatch(r"\d+", lo):
            new_lo = str(int(lo) + 1)
            new_frag_lo = lo_raw.replace(lo, new_lo, 1)
            a, b = m.span("lo")
            out.append((rest[:a] + new_frag_lo + rest[b:], f"narrow lo {lo}->{new_lo}"))
        # Non-literal lo is left alone: "narrow the lo end" only has an obvious,
        # low-risk single-token edit when lo is a bare integer; a non-literal lo
        # is skipped rather than guessed at, same refusal-over-guessing rule as
        # everywhere else in this module.
    return [(indent + kind + new, desc) for new, desc in out]


# ---------------------------------------------------------------------------
# Operator F: conjunct_to_true — one top-level && conjunct replaced by `true`.
# ---------------------------------------------------------------------------
def op_conjunct_to_true(kind, indent, rest):
    """Replace one top-level `&&` conjunct with `true`.

    MEASURED AND FIXED: an earlier version fired on any line with a top-level
    `&&`, including quantifier lines (`forall i,j :: 0<=i<a.Length && 0<=j<b.Length
    ==> ...`). On a 40-file DafnyBench sample that version's malformed rate was
    29% (9/31), and every failure traced to quantifier/binder entanglement, two
    distinct ways:
      1. `_split_top_level`'s first span runs from column 0, so when a quantifier
         binder precedes the first `&&` (`forall x :: maxValue(tree,x) && ...`),
         that whole span — binder declaration included — gets replaced by `true`,
         UNBINDING every later use of `x` (`unresolved identifier`).
      2. Even a LATER conjunct that contains no binder can still be the only
         place Dafny infers an untyped bound variable's type in a multi-variable
         quantifier (`forall i,j :: 0<=i<a.Length && 0<=j<b.Length ==> ...`) —
         replacing it produced "type of bound variable 'j' could not be
         determined", not a semantic near-miss.
    A SECOND round on dafny-synthesis (30 files) found the same family again in
    a form `forall`/`exists` doesn't cover: a `set`/`map` COMPREHENSION, whose
    `|...|` delimiters `_split_top_level` has no concept of at all (it only
    balances `([{`). `ensures count == |set i:int | 0<=i<|a| && P && Q|` has its
    `&&`s INSIDE the comprehension's own outer `|...|` pair; replacing either
    the first span (which then carries the `| set i:int | ...` opener away
    with it) or the last (which carries the closing `|` away with it) leaves an
    unbalanced pipe — "rbrace expected" / "verticalbar expected", 2/10 on that
    sample. Simple pipe-parity counting can't fix this cheaply: a comprehension
    ("outer open ... outer close", 2 pipes that don't close until line's end)
    and a plain cardinality `|a|` (2 pipes that close immediately) are the same
    parity at any given `&&`, so counting pipes can't tell "between two closed
    `|x|`s" from "still inside a comprehension's still-open one" without
    actually parsing.
    Distinguishing a load-bearing-for-typing/-delimiting conjunct from a
    load-bearing-for-proof one needs real binder/type analysis this module
    deliberately does not do (the same refuse-rather-than-guess line
    dafny_verify.py's body-extraction and dafny_pairs.py's line-anchoring both
    draw). So instead of guessing: conjunct_to_true refuses any line containing
    `forall`/`exists`, or a `set`/`map`/`iset`/`imap` comprehension binder,
    outright. That is conservative by construction, at the cost of yield on
    binder-heavy lines — those lines remain reachable through bound_tighten,
    bound_loosen, constant_shift, and quantifier_narrow instead, which mutate a
    single operator or literal and never remove a span that could hold a binder
    or a delimiter.
    """
    if re.search(r"\b(forall|exists)\b", rest):
        return []
    if re.search(r"\b(set|map|iset|imap)\b\s+\w+\s*(:\s*[\w<>,.\[\]]+)?\s*\|", rest):
        return []
    spans = _split_top_level(rest, "&&")
    if len(spans) < 2:
        return []
    out = []
    for a, b in spans:
        frag = rest[a:b]
        if not frag.strip() or frag.strip() == "true":
            continue
        new_rest = rest[:a] + frag.replace(frag.strip(), "true", 1) + rest[b:]
        out.append((new_rest, f"conjunct '{frag.strip()}' -> true"))
    return [(indent + kind + new, desc) for new, desc in out]


OPERATORS = {
    "bound_tighten": op_bound_tighten,
    "bound_loosen": op_bound_loosen,
    "constant_shift": op_constant_shift,
    "decreases_perturb": op_decreases_perturb,
    "quantifier_narrow": op_quantifier_narrow,
    "conjunct_to_true": op_conjunct_to_true,
}


def find_mutations(src: str, operators=None, per_line_cap: int = 4):
    """All (line_idx0, operator_name, orig_line, mutated_line, desc) candidates.

    `per_line_cap` bounds how many variants ONE operator may emit for a SINGLE
    clause line — a line with a dozen integer literals should not alone dominate
    constant_shift's stats. Capped, not silently truncated: candidates beyond the
    cap are simply never generated (deterministic: first `per_line_cap` in the
    operator's own scan order), which is disclosed here in the docstring rather
    than left to be discovered.
    """
    operators = operators or OPERATORS
    lines = src.splitlines()
    out = []
    for idx, kind, indent, rest in _clause_lines(src):
        for op_name, fn in operators.items():
            try:
                variants = fn(kind, indent, rest)
            except Exception:
                continue
            for new_line, desc in variants[:per_line_cap]:
                if new_line == lines[idx]:
                    continue
                out.append((idx, op_name, lines[idx], new_line, desc))
    return out


def apply_mutation(src: str, line_idx: int, mutated_line: str) -> str:
    lines = src.splitlines()
    lines[line_idx] = mutated_line
    return "\n".join(lines) + "\n"


def mutations_from_file(path: Path, rlimit: int = dv.DEFAULT_RLIMIT,
                        per_line_cap: int = 4, max_candidates: int | None = None):
    """Verify the original, then try each single-clause mutation. Returns
    (pairs, stats). `stats` breaks every candidate down by operator so a broken
    operator cannot hide inside a pooled total (rule 2/4 of the brief)."""
    stats = {
        "file": str(path), "base": "", "candidates": 0, "pairs": 0,
        "by_operator": {op: {"candidates": 0, "refuted": 0, "verified_noise": 0,
                              "malformed": 0, "vacuous_noise": 0, "other": 0}
                         for op in OPERATORS},
    }
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        stats["base"] = "unreadable"
        return [], stats

    base = dv.verify_source(src, rlimit=rlimit)
    stats["base"] = base.outcome
    # Seed ONLY from a real proof — a vacuous base mints pairs whose `chosen` side
    # proves nothing, the same refusal dv.pair_verdict and dafny_pairs both make.
    if base.outcome != dv.Outcome.VERIFIED:
        return [], stats

    candidates = find_mutations(src, per_line_cap=per_line_cap)
    if max_candidates:
        candidates = candidates[:max_candidates]
    stats["candidates"] = len(candidates)

    pairs = []
    for idx, op_name, orig_line, mutated_line, desc in candidates:
        variant = apply_mutation(src, idx, mutated_line)
        r = dv.verify_source(variant, rlimit=rlimit)
        bucket = stats["by_operator"][op_name]
        bucket["candidates"] += 1
        if r.outcome == dv.Outcome.REFUTED:
            bucket["refuted"] += 1
            diag = "; ".join(d["message"] for d in r.diagnostics[:3])
            pairs.append(Mutation(str(path), op_name, idx + 1, orig_line, mutated_line,
                                  src, variant, diag))
        elif r.outcome == dv.Outcome.MALFORMED:
            bucket["malformed"] += 1
        elif r.outcome == dv.Outcome.VERIFIED:
            bucket["verified_noise"] += 1
        elif r.outcome == dv.Outcome.VACUOUS:
            bucket["vacuous_noise"] += 1
        else:
            bucket["other"] += 1
    stats["pairs"] = len(pairs)
    return pairs, stats


def generate(paths, rlimit: int = dv.DEFAULT_RLIMIT, workers: int = 8,
            per_line_cap: int = 4, max_candidates: int | None = None):
    """Parallel over FILES (each file's candidates run sequentially inside, same
    shape as dafny_pairs.generate). Shared box: keep `workers` <= 8 (rule 5)."""
    def one(p):
        return mutations_from_file(Path(p), rlimit=rlimit, per_line_cap=per_line_cap,
                                   max_candidates=max_candidates)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, paths))
    pairs = [p for ps, _ in results for p in ps]
    stats = [s for _, s in results]
    return pairs, stats


def aggregate_operator_stats(stats: list[dict]) -> dict:
    """Sum by_operator across files, plus derived yield/malformed rates. This is
    the number the brief asks for: yield per operator AND malformed rate per
    operator, so a broken operator is visible on its own line, not averaged away."""
    totals = {op: {"candidates": 0, "refuted": 0, "verified_noise": 0,
                    "malformed": 0, "vacuous_noise": 0, "other": 0}
              for op in OPERATORS}
    for s in stats:
        for op, b in s.get("by_operator", {}).items():
            for k, v in b.items():
                totals[op][k] += v
    out = {}
    for op, b in totals.items():
        n = b["candidates"]
        out[op] = dict(b,
                       yield_rate=round(b["refuted"] / n, 4) if n else None,
                       malformed_rate=round(b["malformed"] / n, 4) if n else None)
    return out


def write_jsonl(pairs, dest: Path):
    dest.write_text("\n".join(json.dumps(p.__dict__) for p in pairs), encoding="utf-8")
    return dest


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Semantic-mutation Dafny pair generator")
    ap.add_argument("paths", nargs="*", help=".dfy files or directories")
    ap.add_argument("--rlimit", type=int, default=dv.DEFAULT_RLIMIT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--per-line-cap", type=int, default=4)
    ap.add_argument("--max-candidates", type=int, default=None)
    ap.add_argument("--limit-files", type=int, default=None)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    files = []
    for p in a.paths:
        pp = Path(p)
        if pp.is_dir():
            files.extend(sorted(pp.rglob("*.dfy")))
        else:
            files.append(pp)
    if a.limit_files:
        files = files[:a.limit_files]

    if not files:
        print("no input files", file=sys.stderr)
        raise SystemExit(1)

    pairs, stats = generate(files, rlimit=a.rlimit, workers=a.workers,
                            per_line_cap=a.per_line_cap, max_candidates=a.max_candidates)

    base_tally: dict[str, int] = {}
    for s in stats:
        base_tally[s["base"]] = base_tally.get(s["base"], 0) + 1

    report = {
        "files_seen": len(files),
        "base_outcome_tally": base_tally,
        "verified_files": base_tally.get(dv.Outcome.VERIFIED, 0),
        "total_pairs": len(pairs),
        "operators": aggregate_operator_stats(stats),
    }
    print(json.dumps(report, indent=2))
    if a.out:
        write_jsonl(pairs, Path(a.out))
        print(f"wrote {len(pairs)} pairs -> {a.out}", file=sys.stderr)
