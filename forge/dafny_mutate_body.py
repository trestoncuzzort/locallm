#!/usr/bin/env python3
"""dafny_mutate_body.py — the "body-mutation" axis: hold the SPEC fixed, corrupt the CODE.

dafny_pairs.py ablates proof HINTS (invariant/assert/decreases) and asks "can Z3 still
find the proof without this line". That is a different failure mode from the one most
code-generation errors actually are: a wrong loop bound, a flipped comparison, a
dropped statement. This module targets THAT axis instead.

THE CONTRACT (same oracle, opposite side of the file)
-------------------------------------------------------
  seed     = a file that is dv.Outcome.VERIFIED as a whole (never VACUOUS: rule #3).
  mutant   = seed with ONE small edit made STRICTLY INSIDE a method body.
  pair     = usable only when mutant verifies to dv.Outcome.REFUTED (rule #2). A mutant
             that still verifies is preference noise (the spec didn't care); a mutant
             that is MALFORMED teaches syntax, not "does this meet its spec", and is
             discarded the same way dafny_pairs.py discards a malformed hint-ablation.

WHY THIS AXIS COVERS FILES THE HINT AXIS CANNOT
------------------------------------------------
34 of 60 sampled DafnyBench files hold ZERO extractable hints (measured, upstream).
Every one of those files still has a method BODY, and a body is always mutable. This
is deliberately the largest-reach axis: it needs a verified file and a statement,
nothing else.

NEVER TOUCH THE SPEC — HOW THIS IS ENFORCED, NOT JUST ASSERTED
------------------------------------------------------------------
"Only mutate inside method bodies, never inside requires/ensures/invariant/decreases"
is enforced structurally, not by hoping the regex misses:
  1. Method BODIES are located by skipping the signature's own requires/ensures/
     modifies clauses first (each one is brace/paren-depth scanned to its own
     terminating ';' — so a `ensures S == {1,2,3};` set-literal does not fool the
     scanner into stopping early), so mutation never even sees that text.
  2. INSIDE a body, a second pass masks every `invariant`/`decreases`/`modifies`/
     `reads` clause of every loop (these live inside the body's braces), the same
     depth-scanned way. A masked byte is never inside a mutation span.
  3. String literals and comments are masked too — a mutation that lands inside a
     `"..."` or `//...` produces a fake finding (looks like a code change, changes
     nothing checkable) or corrupts unrelated text.
This means every mutation candidate is verified, before use, to sit entirely outside
all three: (a) the file region before the body brace, (b) any spec-clause span found
inside the body, (c) any string/comment span. See `_build_mask`.

OPERATORS (measured separately — an operator whose mutants mostly still verify is
reported as weak, not hidden):
  off_by_one          integer literal N -> N+1 and N-1 (bounds/indices)
  comparison_swap     < <= > >= == != -> a different one of the six
  boolean_swap        && <-> ||
  negate_condition    if/while condition C -> !(C)
  swap_branches       if C {A} else {B}  ->  if C {B} else {A}
  return_constant     `return E;` -> `return <plausible-typed constant>;`
  drop_statement      delete one whole statement line

KNOWN GAPS — stated so silence is not mistaken for coverage (rule #4):
  * `function`/`function method` bodies are NOT mutated (they are expressions, not
    statement lists; every operator here is statement- or condition-shaped). A file
    whose only body is a function is simply not a seed for this module.
  * The generic-vs-comparison ambiguity (`array<int>` vs `i<n`) is resolved by a
    heuristic (see `_mask_generics`): a `<...>` span is treated as a type argument
    list, and excluded from comparison_swap, ONLY if everything between the angle
    brackets is identifier/`,`/`.`/`?`/whitespace/nested-`<>` — i.e. contains no
    operator, digit-as-standalone-token, or punctuation an expression would need.
    This can misclassify a genuine chained comparison like `a<b>c` (rare, and not
    seen in this corpus during spot checks) as a generic. It cannot misclassify a
    real generic as a comparison in the other direction without an adversarial name.
  * `swap_branches` only fires on `if COND { A } else { B }` — a plain, brace-bodied
    else. `else if` chains and paren-less single-statement arms are skipped (refuse
    rather than guess, same discipline as dafny_pairs' line-anchored hints).
  * `return_constant` guesses the return type from surface syntax (does the original
    expression look boolean?) to pick a same-shape constant. When the guess is wrong
    the mutant is MALFORMED (type error) and is counted, not silently retried.
  * A method with no `ensures` (a test harness, a `Main`) can rarely be "refuted" by
    body mutation — there is nothing for the mutant to violate. Every result carries
    `method_has_ensures` so this dilution is visible in the breakdown, not hidden in
    an aggregate.
"""
from __future__ import annotations

import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import dafny_verify as dv

# ---------------------------------------------------------------------------
# Masking: string/comment literals, and spec-clause spans (requires/ensures at the
# signature, invariant/decreases/modifies/reads on loops inside the body).
# ---------------------------------------------------------------------------

SPEC_KW_RE = re.compile(r"\b(requires|ensures|invariant|decreases|modifies|reads)\b")

# Dafny's method/loop specification clauses take an OPTIONAL trailing ';' — this
# corpus has both styles, and the semicolon-optional style is common (measured: the
# very first sample file inspected during development used it, and a naive
# ";"-only terminator silently failed to find that file's only specced method,
# finding just its unspecced Main()/Test() harnesses instead — exactly the wrong
# methods to seed mutation from). So a clause ends at whichever comes FIRST:
#   - a ';' at paren/bracket depth 0
#   - the start of the NEXT clause keyword at depth 0 (the no-semicolon style)
#   - a bare '{' at depth 0 (the loop/method body opening — depth here tracks
#     only '(' ')' '[' ']', not braces, so a `{` always reads as "stop": in the
#     overwhelming common case that IS the body, and in the rare case a clause
#     ends with a raw set/map-display literal, this undermasks that one literal
#     — a documented, accepted gap, never a case of finding the WRONG body).
def _scan_clause_end(text: str, start: int) -> int:
    n = len(text)
    depth = 0
    i = start
    first = True
    while i < n:
        if not first and depth == 0 and SPEC_KW_RE.match(text, i):
            return i
        c = text[i]
        if c in "([":
            depth += 1
        elif c in ")]":
            if depth == 0:
                return i
            depth -= 1
        elif c == ";" and depth == 0:
            return i + 1
        elif c == "{" and depth == 0:
            return i
        i += 1
        first = False
    return n


def _mask_strings_comments(text: str, mask: list) -> None:
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" and j + 1 < n else 1
            j = min(j + 1, n)
            for k in range(i, j):
                mask[k] = False
            i = j
        elif text[i:i + 2] == "//":
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                mask[k] = False
            i = j
        elif text[i:i + 2] == "/*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                mask[k] = False
            i = j
        else:
            i += 1


def _mask_spec_clauses(text: str, mask: list) -> None:
    for m in SPEC_KW_RE.finditer(text):
        s = m.start()
        if not mask[s]:
            continue
        e = _scan_clause_end(text, s)
        for k in range(s, min(e, len(text))):
            mask[k] = False


_GENERIC_INNER_OK = re.compile(r"^[\w\s,\.\?]*$")


def _mask_generics(text: str, mask: list) -> None:
    """Best-effort: mask `IDENT<...>` spans that read as a type-argument list, so
    comparison_swap never treats `array<int>`'s brackets as `<`/`>` operators."""
    n = len(text)
    i = 1
    while i < n:
        if text[i] == "<" and (text[i - 1].isalnum() or text[i - 1] == "_"):
            depth = 1
            j = i + 1
            ok = True
            while j < n and depth > 0:
                ch = text[j]
                if ch == "<":
                    depth += 1
                elif ch == ">":
                    depth -= 1
                elif not _GENERIC_INNER_OK.match(ch):
                    ok = False
                    break
                j += 1
            if ok and depth == 0:
                for k in range(i, j):
                    mask[k] = False
                i = j
                continue
        i += 1


def _build_mask(body: str) -> list:
    """True = mutation allowed at this byte. False = spec clause, string, comment,
    or a generic type-argument list."""
    mask = [True] * len(body)
    _mask_strings_comments(body, mask)
    _mask_spec_clauses(body, mask)
    _mask_generics(body, mask)
    return mask


def _span_clear(mask: list, a: int, b: int) -> bool:
    return all(mask[a:b]) if a < b else False


# ---------------------------------------------------------------------------
# Method-body location. Signature -> skip its own requires/ensures/modifies/reads
# clauses (depth-scanned, see above) -> the next '{' is the body -> brace-match it.
# ---------------------------------------------------------------------------

METHOD_SIG_RE = re.compile(
    r"\b(?:static\s+|ghost\s+)*(?P<kw>method|constructor)\b\s*"
    r"(?P<name>\w+)?\s*(?:<[^>]*>)?\s*\((?P<params>[^)]*)\)\s*"
    r"(?:returns\s*\((?P<outs>[^)]*)\))?"
)


@dataclass
class MethodSpan:
    name: str
    sig_start: int
    body_start: int   # index of the opening '{'
    body_end: int      # index of the matching closing '}'
    has_ensures: bool


def _skip_ws_and_specs(text: str, i: int) -> int:
    n = len(text)
    while True:
        while i < n and text[i] in " \t\r\n":
            i += 1
        m = SPEC_KW_RE.match(text, i)
        if not m:
            return i
        i = _scan_clause_end(text, i)


def find_methods(src: str) -> list:
    """Every `method`/`constructor` body in SRC, in source order. Refuses (skips)
    anything whose signature or body brace-matching does not close cleanly —
    conservative by construction, same discipline as dafny_pairs.find_hints."""
    out = []
    for m in METHOD_SIG_RE.finditer(src):
        i = _skip_ws_and_specs(src, m.end())
        if i >= len(src) or src[i] != "{":
            continue
        depth, j = 0, i
        n = len(src)
        while j < n:
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            continue
        sig_text = src[m.start():i]
        out.append(MethodSpan(
            name=m.group("name") or "<anon>",
            sig_start=m.start(),
            body_start=i,
            body_end=j,
            has_ensures="ensures" in sig_text,
        ))
    return out


# ---------------------------------------------------------------------------
# Mutation candidates. Each is (local_start, local_end, replacement, label) in
# BODY-local coordinates (body = src[body_start:body_end+1], braces included).
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    operator: str
    label: str            # short human description, e.g. "12 -> 13"
    start: int             # local to body
    end: int
    replacement: str
    line_in_body: int      # 0-based line within body text


def _line_of(body: str, idx: int) -> int:
    return body.count("\n", 0, idx)


INT_LIT_RE = re.compile(r"(?<![\w.])(\d+)(?![\w.])")


def op_off_by_one(body: str, mask: list) -> list:
    out = []
    for m in INT_LIT_RE.finditer(body):
        s, e = m.span()
        if not _span_clear(mask, s, e):
            continue
        val = int(m.group(1))
        for delta, tag in ((1, "+1"), (-1, "-1")):
            nv = val + delta
            rep = f"({nv})" if nv < 0 else str(nv)
            out.append(Candidate("off_by_one", f"{val}->{nv} ({tag})", s, e, rep, _line_of(body, s)))
    return out


CMP_RE = re.compile(r"<=|>=|==|!=|<|>")
CMP_SWAP_TO = {
    "<": [">=", ">", "<=", "==", "!="],
    ">": ["<=", "<", ">=", "==", "!="],
    "<=": [">", ">=", "<", "==", "!="],
    ">=": ["<", "<=", ">", "==", "!="],
    "==": ["!="],
    "!=": ["=="],
}


def op_comparison_swap(body: str, mask: list) -> list:
    out = []
    for m in CMP_RE.finditer(body):
        s, e = m.span()
        if not _span_clear(mask, s, e):
            continue
        op = m.group(0)
        # Exclude `==>`/`<==`/`<==>` (implication/iff) and `:=`/`=>` neighbours.
        before = body[s - 1] if s > 0 else ""
        after = body[e] if e < len(body) else ""
        if op in ("<", ">") and after == "=" or before in ("=", ":"):
            # already handled by <=/>=/==/!= alternation; this guards stray
            # adjacency like `<==` (iff) where `<` sits right before `==`.
            if body[s:e + 2] in ("<==",) or body[max(0, s - 1):e] in ("<==",):
                continue
        if op == "<" and body[s:s + 3] == "<==":
            continue
        if op == ">" and s > 0 and body[s - 2:s + 1] == "==>":
            continue
        repls = CMP_SWAP_TO.get(op, [])
        # Cap fan-out: try one flip (first alternative) plus the pure negation
        # (last in the list, which CMP_SWAP_TO always orders as the logical `not`).
        chosen = repls[:1] + (repls[-1:] if len(repls) > 1 else [])
        for rep in dict.fromkeys(chosen):
            out.append(Candidate("comparison_swap", f"{op}->{rep}", s, e, rep, _line_of(body, s)))
    return out


BOOL_RE = re.compile(r"&&|\|\|")


def op_boolean_swap(body: str, mask: list) -> list:
    out = []
    for m in BOOL_RE.finditer(body):
        s, e = m.span()
        if not _span_clear(mask, s, e):
            continue
        op = m.group(0)
        rep = "||" if op == "&&" else "&&"
        out.append(Candidate("boolean_swap", f"{op}->{rep}", s, e, rep, _line_of(body, s)))
    return out


COND_HEAD_RE = re.compile(r"\b(if|while)\b")


def _find_condition(body: str, kw_end: int) -> tuple:
    """Condition span right after `if`/`while`. Handles both `if (C) {` and the
    paren-less `if C {` / `while C invariant ... {` Dafny styles.

    Returns (expr_start, expr_end, resume_pos): `body[expr_start:expr_end]` is the
    boolean condition itself; `resume_pos` is where to keep scanning to reach the
    body's opening '{' — NOT the same position as `expr_end` for the parenthesized
    form (which stops ON the closing ')', so the caller must skip past it), and
    NOT always immediately '{' for the paren-less form either (a `while` may still
    have `invariant`/`decreases` clauses between the condition and the body)."""
    n = len(body)
    i = kw_end
    while i < n and body[i] in " \t\r\n":
        i += 1
    if i < n and body[i] == "(":
        depth, j = 0, i
        while j < n:
            if body[j] == "(":
                depth += 1
            elif body[j] == ")":
                depth -= 1
                if depth == 0:
                    return i + 1, j, j + 1
            j += 1
        return None
    start = i
    depth = 0
    while i < n:
        c = body[i]
        # NOTE: only '(' '[' count as depth here — '{' must stay a depth-0 SIGNAL
        # (the then-block / loop-body opener), never a bracket to increment past.
        if c in "([":
            depth += 1
        elif c in ")]":
            if depth == 0:
                return None
            depth -= 1
        elif depth == 0 and c == "{":
            return start, i, i
        elif depth == 0 and SPEC_KW_RE.match(body, i) and i > start:
            return start, i, i
        i += 1
    return None


def _body_brace_after_condition(body: str, resume_pos: int) -> int | None:
    """From just past a condition (see `_find_condition`), skip any loop
    invariant/decreases/modifies clauses and return the index of the body's
    opening '{', or None if the source doesn't resolve cleanly."""
    i = _skip_ws_and_specs(body, resume_pos)
    return i if i < len(body) and body[i] == "{" else None


def op_negate_condition(body: str, mask: list) -> list:
    out = []
    for m in COND_HEAD_RE.finditer(body):
        if not mask[m.start()]:
            continue
        span = _find_condition(body, m.end())
        if not span:
            continue
        s, e, _resume = span
        cond = body[s:e].strip()
        if not cond or not _span_clear(mask, s, e):
            continue
        rep = f"!({body[s:e]})"
        out.append(Candidate("negate_condition", f"{m.group(1)} cond negated", s, e, rep, _line_of(body, s)))
    return out


IF_ELSE_RE = re.compile(r"\bif\b")


def _match_brace_block(body: str, i: int) -> tuple:
    """body[i] must be '{'. Returns (start_after_brace, end_before_close)."""
    n = len(body)
    depth, j = 0, i
    while j < n:
        if body[j] == "{":
            depth += 1
        elif body[j] == "}":
            depth -= 1
            if depth == 0:
                return i + 1, j
        j += 1
    return None


def op_swap_branches(body: str, mask: list) -> list:
    out = []
    for m in IF_ELSE_RE.finditer(body):
        if not mask[m.start()]:
            continue
        cond = _find_condition(body, m.end())
        if not cond:
            continue
        _, _, resume = cond
        n = len(body)
        j = _body_brace_after_condition(body, resume)
        if j is None:
            continue
        then_blk = _match_brace_block(body, j)
        if not then_blk:
            continue
        ts, te = then_blk
        k = te + 1
        while k < n and body[k] in " \t\r\n":
            k += 1
        if body[k:k + 4] != "else":
            continue
        k += 4
        while k < n and body[k] in " \t\r\n":
            k += 1
        if k >= n or body[k] != "{" :
            continue  # skip `else if` and paren-less else arms — refuse, don't guess
        else_blk = _match_brace_block(body, k)
        if not else_blk:
            continue
        es, ee = else_blk
        if not (_span_clear(mask, ts, te) and _span_clear(mask, es, ee)):
            continue
        then_body, else_body = body[ts:te], body[es:ee]
        if then_body.strip() == else_body.strip():
            continue  # swapping identical branches is not a mutation
        # Replace the whole `{then}...else...{else}` span at once.
        # `ee` is the INDEX of the else-block's own closing '}' (see
        # _match_brace_block's docstring: it returns the interior span, i.e. the
        # closing brace is AT ee, not past it). The overall replacement must
        # consume through and including that brace, or it survives untouched and
        # collides with the '}' `rep` supplies for the relocated then-block —
        # producing a literal doubled '}' (measured: 22/22 attempts on the first
        # cut of this operator came back MALFORMED with "rbrace expected" /
        # "this symbol not expected", 100% a bug, not a real operator-weakness
        # finding — fixed here, then re-measured).
        whole_start, whole_end = j, ee + 1
        rep = "{" + else_body + "}" + body[te + 1:k] + "{" + then_body + "}"
        out.append(Candidate("swap_branches", "then<->else", whole_start, whole_end, rep, _line_of(body, j)))
    return out


RETURN_RE = re.compile(r"\breturn\s+([^;]+);")


def op_return_constant(body: str, mask: list) -> list:
    out = []
    for m in RETURN_RE.finditer(body):
        s, e = m.span(1)
        if not _span_clear(mask, m.start(), m.end()):
            continue
        expr = m.group(1).strip()
        looks_bool = bool(re.search(r"\btrue\b|\bfalse\b|&&|\|\||<=|>=|==|!=|<|>|\bnot\b", expr))
        if looks_bool:
            cands = ["true", "false"]
        else:
            cands = ["0", "1"]
        for rep in cands:
            if rep == expr:
                continue
            out.append(Candidate("return_constant", f"'{expr}' -> {rep}", s, e, rep, _line_of(body, s)))
    return out


def op_drop_statement(body: str, mask: list) -> list:
    out = []
    lines = body.split("\n")
    pos = 0
    offsets = []
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1
    for idx, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped or not stripped.endswith(";"):
            continue
        if stripped in ("{", "}"):
            continue
        s = offsets[idx]
        e = s + len(ln)
        if not _span_clear(mask, s, e):
            continue
        # Don't drop the sole statement of a single-line `{ stmt; }` body — that
        # would leave `{ }`, a different (usually MALFORMED-free, trivially-weak)
        # edit than "drop one of several statements". Still allowed if it's a
        # multi-statement line's own line; this check only guards the braces-only
        # degenerate case already excluded above.
        newline_start = s if idx == 0 else offsets[idx - 1] + len(lines[idx - 1]) + 1
        rep_start, rep_end = newline_start, e + 1 if e < len(body) and body[e] == "\n" else e
        out.append(Candidate("drop_statement", stripped[:40], rep_start, min(rep_end, len(body)), "", idx))
    return out


OPERATORS = {
    "off_by_one": op_off_by_one,
    "comparison_swap": op_comparison_swap,
    "boolean_swap": op_boolean_swap,
    "negate_condition": op_negate_condition,
    "swap_branches": op_swap_branches,
    "return_constant": op_return_constant,
    "drop_statement": op_drop_statement,
}


def all_candidates(body: str) -> dict:
    mask = _build_mask(body)
    return {name: fn(body, mask) for name, fn in OPERATORS.items()}


def apply_candidate(src: str, method: MethodSpan, cand: Candidate) -> str:
    body = src[method.body_start:method.body_end + 1]
    mutant_body = body[:cand.start] + cand.replacement + body[cand.end:]
    return src[:method.body_start] + mutant_body + src[method.body_end + 1:]


# ---------------------------------------------------------------------------
# Pair record + per-file / per-corpus driving.
# ---------------------------------------------------------------------------

@dataclass
class MutPair:
    source_path: str
    operator: str
    method_name: str
    method_has_ensures: bool
    line_in_body: int
    label: str
    chosen: str
    rejected: str
    outcome: str            # dv.Outcome of the mutant
    diagnostic: str = ""


def mutate_file(path: Path, rlimit: int = dv.DEFAULT_RLIMIT, per_op_cap: int = 3,
                seed_result=None) -> tuple:
    """One verified file -> up to per_op_cap mutants PER OPERATOR PER METHOD.
    Returns (pairs, discards, stats). discards holds every non-usable mutant
    result too (rule #2: counted, never silently dropped)."""
    stats = {"file": str(path), "base": "", "methods": 0, "attempted": 0,
             "operator_attempted": {}, "operator_flipped": {}}
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        stats["base"] = "unreadable"
        return [], [], stats

    base = seed_result if seed_result is not None else dv.verify_source(src, rlimit=rlimit)
    stats["base"] = base.outcome
    if base.outcome != dv.Outcome.VERIFIED:
        return [], [], stats

    methods = find_methods(src)
    stats["methods"] = len(methods)
    pairs, discards = [], []

    for meth in methods:
        body = src[meth.body_start:meth.body_end + 1]
        cands_by_op = all_candidates(body)
        for op, cands in cands_by_op.items():
            random.Random(hash((str(path), meth.name, op)) & 0xffffffff).shuffle(cands)
            for cand in cands[:per_op_cap]:
                mutant_src = apply_candidate(src, meth, cand)
                r = dv.verify_source(mutant_src, rlimit=rlimit)
                stats["attempted"] += 1
                stats["operator_attempted"][op] = stats["operator_attempted"].get(op, 0) + 1
                rec = MutPair(str(path), op, meth.name, meth.has_ensures, cand.line_in_body,
                              cand.label, src, mutant_src, r.outcome,
                              "; ".join(d["message"] for d in r.diagnostics[:3]))
                if r.outcome == dv.Outcome.REFUTED:
                    stats["operator_flipped"][op] = stats["operator_flipped"].get(op, 0) + 1
                    pairs.append(rec)
                else:
                    discards.append(rec)
    stats["pairs"] = len(pairs)
    return pairs, discards, stats


def mutate_corpus(paths, rlimit: int = dv.DEFAULT_RLIMIT, workers: int = 8,
                  per_op_cap: int = 3, seed_results: dict | None = None):
    def one(p):
        sr = seed_results.get(str(p)) if seed_results else None
        return mutate_file(Path(p), rlimit=rlimit, per_op_cap=per_op_cap, seed_result=sr)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, paths))
    pairs = [p for ps, _, _ in results for p in ps]
    discards = [d for _, ds, _ in results for d in ds]
    stats = [s for _, _, s in results]
    return pairs, discards, stats


def write_jsonl(records, dest: Path):
    dest.write_text("\n".join(json.dumps(r.__dict__) for r in records), encoding="utf-8")
    return dest


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="body-mutation pair generator")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--rlimit", type=int, default=dv.DEFAULT_RLIMIT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--per-op-cap", type=int, default=3)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not a.paths:
        raise SystemExit("usage: dafny_mutate_body.py FILE.dfy [FILE2.dfy ...]")
    pairs, discards, stats = mutate_corpus(a.paths, rlimit=a.rlimit, workers=a.workers,
                                           per_op_cap=a.per_op_cap)
    tally = {}
    for s in stats:
        for op, n in s.get("operator_attempted", {}).items():
            tally.setdefault(op, {"attempted": 0, "flipped": 0})
            tally[op]["attempted"] += n
        for op, n in s.get("operator_flipped", {}).items():
            tally[op]["flipped"] += n
    print(json.dumps({"files": len(stats), "pairs": len(pairs), "discards": len(discards),
                      "per_operator": tally}, indent=2))
    if a.out:
        write_jsonl(pairs, Path(a.out))
