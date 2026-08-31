#!/usr/bin/env python3
"""dafny_triage.py — classify the corpus BEFORE seeding pairs from it.

WHY THIS EXISTS
----------------
A prior sample measured 56.7% of files verifying. That number mixes two very
different populations: real proof corpus (DafnyBench, dafny-synthesis,
libraries, aws-cmpl, aws-esdk, evm-dafny, reportgen, and most of dafny-main
itself) and dafny-main's OWN COMPILER TEST SUITE, which deliberately contains
broken programs — files whose entire purpose is to exercise the parser's or
resolver's error reporting, or the language server's diagnostics. Averaging
those two populations into one "yield" number understates how seedable the
real corpus is and overstates how broken it is. This module separates them
BEFORE verifying, then verifies everything anyway so the separation is
checked against measurement, not asserted from directory names alone.

THE FIXTURE-DIRECTORY HEURISTIC, AND HOW IT WAS VALIDATED (not assumed)
------------------------------------------------------------------------
dafny-main is a git checkout of a .NET solution. Its own test projects follow
a distinct, capitalized .NET naming convention that is NOT used by any of the
other seven corpora for their OWN application-level Dafny tests:
  - `LitTests` / `LitTest`   — the lit-based CLI/compiler test harness
  - `IntegrationTests`       — same harness, parent dir
  - `TestFiles`              — payload dirs nested under the above
  - `<Name>.Test`            — C# test-project convention (DafnyLanguageServer.Test,
                               AutoExtern.Test, DafnyPipeline.Test)
MEASURED on this exact checkout (2026-08-27): the regex below matches 1979 of
dafny-main's 2201 .dfy files, and ZERO files anywhere else in the 4584-file
corpus. aws-cmpl, aws-esdk, evm-dafny, dafny-synthesis all ship their OWN
lowercase `test/` directories full of real, meant-to-verify Dafny code (e.g.
aws-cmpl/AwsCryptographyPrimitives/test) — this pattern is deliberately
case- and name-sensitive so it does NOT catch those. See `_verify_fixture_regex_specificity()`.

A second, corpus-wide filename marker (`bad`, `invalid`, `illegal`, `negative`,
`xfail`, `malformed` as a path segment) catches likely negative fixtures
outside dafny-main too, on the same "directory says what the file is for"
principle, applied narrowly.

WHAT THIS HEURISTIC DOES NOT PROVE
------------------------------------
Directory convention is a PRIOR, not a verdict. A file under LitTests can
still genuinely verify (many do — trivial CLI-flag smoke tests), and a file
outside it can still be broken junk. That is why every file, fixture or not,
is ACTUALLY RUN through dv.verify_source and the real outcome is recorded.
`category` (corpus vs compiler_fixture) is a denominator choice for reporting
yield; `outcome` (verified/refuted/malformed/vacuous/timeout/tool_error) is
the measured fact. `is_seed` requires BOTH: outcome == VERIFIED (never
vacuous — dv already enforces that distinction) AND category == "corpus".
A verified LitTest fixture is recorded and counted, just not seeded from,
because "attr-help.dfy" (one RUN line, zero methods) is not useful proof
material even when it verifies.

HINT DENSITY
------------
dp.find_hints() is reused unedited (imported, not reimplemented) to count
whole-line invariant/assert/decreases/ensures/requires/modifies/reads
candidates per file. Ranking seeds by this count is what the project's own
subset-ablation measurement said was missing: 34 of 60 sampled files had ZERO
hints, so survivors were one-per-file with only 48 combinations to try. A
density-ranked list lets the next stage draw its subset-ablation sample from
the files that actually have combinatorics to explore.

OUTPUT
------
Two JSONL files under ~/dafny-corpus/ (never under srlm-forge —
this is corpus metadata, other stages read it from the corpus dir):
  triage.jsonl     — one record per file actually attempted, full classification.
  seed_rank.jsonl  — the is_seed subset of triage.jsonl, sorted by hint_count
                     desc, ready for a subset-ablation stage to consume directly.

Both are written incrementally so a deadline cutoff still leaves a valid,
loadable partial result — never a half-written line.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from pathlib import Path

import dafny_verify as dv
import dafny_pairs as dp

SCHEMA = 1

CORPUS_ROOT = Path(os.environ.get("DAFNY_CORPUS", str(Path.home() / "dafny-corpus")))

# Directory convention specific to dafny-main's own .NET test projects and lit
# harness. See module docstring for the measured specificity check.
_FIXTURE_DIR_RE = re.compile(r'(^|/)([A-Za-z][\w]*\.Test|LitTests?|IntegrationTests|TestFiles)(/|$)')

# Corpus-wide filename/dir marker for likely negative fixtures outside dafny-main.
_FILENAME_MARKER_RE = re.compile(r'(?:^|[_\-/])(bad|invalid|illegal|negative|xfail|malformed)(?:[_\-./]|$)',
                                 re.IGNORECASE)

# dafny-main's lit RUN directive names the CLI verb under test. Only present
# on lit-harness files; None everywhere else.
_RUN_RE = re.compile(r'^//\s*RUN:\s*%(?:bare)?dafny\s+/?(\S+)', re.MULTILINE)

# A local `include "..."` is resolved relative to the FILE'S OWN location on
# disk, not to a copy elsewhere. MEASURED (2026-08-27): verifying via
# dv.verify_source() (which copies the text into a fresh temp dir) turns every
# such file into a spurious tool_error ("file X not found") because the sibling
# file it includes isn't in that temp dir. dv.verify_path() runs dafny against
# the file IN PLACE, so relative includes resolve normally -- confirmed by
# re-running dafny-main/Source/DafnyCore/AST/Formatting.dfy both ways: temp-copy
# -> tool_error "System.dfy not found"; in-place -> refuted (a real verdict).
# This module therefore verifies in place via verify_path, never verify_source.
_INCLUDE_RE = re.compile(r'^\s*include\s+"', re.MULTILINE)

DEFAULT_WALL_TIMEOUT = 20   # triage-scale backstop; shorter than dv's own 120s default
                            # so one hung file cannot eat the sweep's time budget.


def classify_path(rel_path: str) -> dict:
    """Directory/filename convention only — no file I/O, no verification.
    Kept separate from triage_one() so it is independently testable/auditable."""
    reasons = []
    if _FIXTURE_DIR_RE.search(rel_path):
        reasons.append("dotnet_test_project_dir")
    fname = Path(rel_path).name
    m = _FILENAME_MARKER_RE.search(fname)
    if m:
        reasons.append(f"filename_marker:{m.group(1).lower()}")
    corpus = rel_path.split("/", 1)[0]
    category = "compiler_fixture" if reasons else "corpus"
    return {"corpus": corpus, "category": category, "fixture_reasons": reasons}


def sidecar_signal(path: Path) -> dict:
    """Cheap, best-effort read of lit-harness metadata: the RUN verb (what CLI
    command this file was actually written to test — 'verify' or something
    else entirely) and whether a sibling .expect file's text mentions an
    error (a strong sign the file is expected to NOT cleanly verify).
    Returns None fields when the convention isn't present — most of the
    corpus has neither, and that absence is itself information."""
    sig = {"run_verb": None, "expect_mentions_error": None}
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:2000]
    except Exception:
        return sig
    m = _RUN_RE.search(head)
    if m:
        sig["run_verb"] = m.group(1).rstrip(":")
    expect = Path(str(path) + ".expect")
    if expect.exists():
        try:
            etxt = expect.read_text(encoding="utf-8", errors="replace")
            sig["expect_mentions_error"] = bool(re.search(r'error', etxt, re.IGNORECASE))
        except Exception:
            pass
    return sig


@dataclass
class TriageRecord:
    path: str                       # relative to CORPUS_ROOT
    corpus: str                     # top-level dir (DafnyBench, dafny-main, ...)
    category: str                   # "corpus" | "compiler_fixture"
    fixture_reasons: list
    run_verb: str | None
    expect_mentions_error: bool | None
    loc: int
    hint_count: int
    hint_density: float             # hint_count / loc
    has_include: bool               # local `include "..."` present (see module docstring)
    outcome: str
    ok: bool
    exit_code: int
    wall_ms: int
    timed_out: bool
    is_seed: bool                   # outcome==VERIFIED AND category=="corpus"
    error: str

    def to_json(self) -> dict:
        return asdict(self)


def triage_one(path: Path, corpus_root: Path = CORPUS_ROOT,
               rlimit: int = dv.DEFAULT_RLIMIT,
               wall_timeout: int = DEFAULT_WALL_TIMEOUT) -> TriageRecord:
    rel = str(path.relative_to(corpus_root))
    cls = classify_path(rel)
    sig = sidecar_signal(path)
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return TriageRecord(rel, cls["corpus"], cls["category"], cls["fixture_reasons"],
                            sig["run_verb"], sig["expect_mentions_error"],
                            0, 0, 0.0, False, "tool_error", False, -1, 0, False, False,
                            f"unreadable: {e}")

    lines = [l for l in src.splitlines() if l.strip()]
    loc = len(lines)
    hint_count = len(dp.find_hints(src))
    density = (hint_count / loc) if loc else 0.0
    has_include = bool(_INCLUDE_RE.search(src))

    # verify_path, NOT verify_source: run dafny against the file IN PLACE so a
    # relative `include "../foo.dfy"` resolves against the real checkout instead
    # of an empty temp dir. See _INCLUDE_RE comment above for the measured proof.
    res = dv.verify_path(path, rlimit=rlimit, wall_timeout=wall_timeout)
    is_seed = (res.outcome == dv.Outcome.VERIFIED and cls["category"] == "corpus")

    return TriageRecord(rel, cls["corpus"], cls["category"], cls["fixture_reasons"],
                        sig["run_verb"], sig["expect_mentions_error"],
                        loc, hint_count, density, has_include,
                        res.outcome, res.ok, res.exit_code, res.wall_ms, res.timed_out,
                        is_seed, res.error)


def discover(root: Path = CORPUS_ROOT, corpora: list | None = None) -> list:
    """All .dfy files under root, optionally restricted to named top-level corpora.
    Sorted for determinism; NOT shuffled, so a deadline cutoff always drops the
    same tail rather than a different random subset on every run."""
    files = []
    for p in sorted(root.rglob("*.dfy")):
        rel = p.relative_to(root)
        if not rel.parts:
            continue
        if corpora and rel.parts[0] not in corpora:
            continue
        files.append(p)
    return files


def run_sweep(paths: list, out_path: Path, workers: int = 8,
              deadline_s: float | None = None, rlimit: int = dv.DEFAULT_RLIMIT,
              wall_timeout: int = DEFAULT_WALL_TIMEOUT,
              corpus_root: Path = CORPUS_ROOT) -> dict:
    """Verify+classify every path, writing one JSON line per COMPLETED file as it
    finishes (never buffered to the end — a killed/deadlined run still leaves a
    valid partial file). Honors an overall wall-clock deadline: futures not yet
    started when the deadline passes are cancelled, not silently included as
    'covered'. Returns exact coverage counts — no projection."""
    t0 = time.monotonic()
    n_done = 0
    n_cancelled = 0
    tally: dict = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as out_f:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            future_to_path = {ex.submit(triage_one, p, corpus_root, rlimit, wall_timeout): p
                              for p in paths}
            hit_deadline = False
            for fut in as_completed(future_to_path):
                try:
                    rec = fut.result()
                except Exception as e:
                    p = future_to_path[fut]
                    rel = str(p.relative_to(corpus_root))
                    cls = classify_path(rel)
                    rec = TriageRecord(rel, cls["corpus"], cls["category"], cls["fixture_reasons"],
                                       None, None, 0, 0, 0.0, False, "tool_error", False, -1, 0,
                                       False, False, f"harness_exception: {e}")
                out_f.write(json.dumps(rec.to_json()) + "\n")
                out_f.flush()
                n_done += 1
                key = (rec.corpus, rec.category, rec.outcome)
                tally[key] = tally.get(key, 0) + 1

                if deadline_s is not None and not hit_deadline and (time.monotonic() - t0) > deadline_s:
                    hit_deadline = True
                    for f2 in future_to_path:
                        if not f2.done() and f2.cancel():
                            n_cancelled += 1
                    break

    elapsed = time.monotonic() - t0
    return {
        "attempted_total": len(paths),
        "completed": n_done,
        "cancelled_before_start": n_cancelled,
        "not_covered": len(paths) - n_done,
        "elapsed_s": round(elapsed, 1),
        "hit_deadline": deadline_s is not None and (elapsed > deadline_s or n_cancelled > 0),
        "tally": {"|".join(k): v for k, v in sorted(tally.items())},
    }


def write_seed_rank(triage_jsonl: Path, out_path: Path) -> dict:
    """Read triage.jsonl back, filter to is_seed, sort by hint_count desc
    (ties broken by hint_density desc). This is the file a subset-ablation
    stage should consume directly instead of re-verifying the corpus."""
    seeds = []
    with open(triage_jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("is_seed"):
                seeds.append(rec)
    seeds.sort(key=lambda r: (r["hint_count"], r["hint_density"]), reverse=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in seeds:
            f.write(json.dumps(r) + "\n")
    zero_hint = sum(1 for r in seeds if r["hint_count"] == 0)
    total_hints = sum(r["hint_count"] for r in seeds)
    top10_hints = sum(r["hint_count"] for r in seeds[:10])
    return {
        "seed_count": len(seeds),
        "zero_hint_seeds": zero_hint,
        "total_hints_across_seeds": total_hints,
        "top10_hint_share": (top10_hints / total_hints) if total_hints else 0.0,
    }


def _verify_fixture_regex_specificity(root: Path = CORPUS_ROOT) -> dict:
    """Self-check cited in the module docstring: confirm _FIXTURE_DIR_RE matches
    dafny-main's known test dirs and NOTHING outside dafny-main. Run on demand
    (`python3 dafny_triage.py --selfcheck`), not on every import."""
    hits_outside = 0
    hits_inside = 0
    for p in root.rglob("*.dfy"):
        rel = str(p.relative_to(root))
        if _FIXTURE_DIR_RE.search(rel):
            if rel.split("/", 1)[0] == "dafny-main":
                hits_inside += 1
            else:
                hits_outside += 1
    return {"hits_inside_dafny_main": hits_inside, "hits_outside_dafny_main": hits_outside}


def main():
    ap = argparse.ArgumentParser(description="Triage the Dafny corpus: classify + verify + rank by hint density.")
    ap.add_argument("--corpora", nargs="*", default=None,
                    help="restrict to these top-level corpus dirs (default: all)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--deadline-seconds", type=float, default=None)
    ap.add_argument("--rlimit", type=int, default=dv.DEFAULT_RLIMIT)
    ap.add_argument("--wall-timeout", type=int, default=DEFAULT_WALL_TIMEOUT)
    ap.add_argument("--out", default=str(CORPUS_ROOT / "triage.jsonl"))
    ap.add_argument("--seed-rank-out", default=str(CORPUS_ROOT / "seed_rank.jsonl"))
    ap.add_argument("--limit", type=int, default=None, help="cap number of files discovered (debug)")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        print(json.dumps(_verify_fixture_regex_specificity(), indent=2))
        return

    paths = discover(CORPUS_ROOT, a.corpora)
    if a.limit:
        paths = paths[:a.limit]
    print(f"discovered {len(paths)} .dfy files"
         + (f" (restricted to {a.corpora})" if a.corpora else "") + f", workers={a.workers}"
         + (f", deadline={a.deadline_seconds}s" if a.deadline_seconds else ", no deadline"))

    summary = run_sweep(paths, Path(a.out), workers=a.workers, deadline_s=a.deadline_seconds,
                        rlimit=a.rlimit, wall_timeout=a.wall_timeout)
    print(json.dumps(summary, indent=2))

    rank_summary = write_seed_rank(Path(a.out), Path(a.seed_rank_out))
    print(json.dumps(rank_summary, indent=2))


if __name__ == "__main__":
    main()
