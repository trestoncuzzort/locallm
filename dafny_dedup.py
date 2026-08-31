#!/usr/bin/env python3
"""dafny_dedup.py — is a 14,000-pair dataset actually 14,000 problems?

This repo already learned that a training set can be "one program renamed nine hundred
times" (measure_bank_concentration.py exists because that happened). Every Dafny
generation axis makes that failure MORE likely, not less, because they all work by
perturbing a seed file: single-hint ablation, subset ablation, body mutation and
semantic mutation each emit many pairs whose `chosen` side is BYTE-IDENTICAL.

So the headline count is the wrong number to look at, and the naive dedup is wrong too.

⛔ DO NOT DEDUPLICATE ON `chosen`. Every pair from one seed shares it, so hashing
   `chosen` would collapse a file's entire legitimate yield to one row and destroy
   real data. The variety lives entirely on the rejected side.

⛔ AND DO NOT DEDUPLICATE ON `rejected` ALONE either. Two different seeds can produce
   textually similar broken programs; what makes a pair distinct is the RELATIONSHIP —
   which specific perturbation was applied to which specific proof.

THE UNIT OF NOVELTY IS THE EDIT. A pair is characterised by the diff between chosen and
rejected: the lines removed or changed, normalised for whitespace. Two pairs are the same
problem when they are the same edit against the same proof. That is what `pair_key`
hashes, and it is the only identity claim this module makes.

WHAT IT REPORTS, AND WHY EACH NUMBER EXISTS
  exact_duplicates   — same (chosen, rejected) bytes. Pure waste.
  same_edit          — same normalised edit against the same seed. Near-waste: two axes
                       independently finding the same perturbation (deletion and
                       "replace conjunct with true" can coincide).
  distinct_seeds     — THE HONEST DENOMINATOR. 14,000 pairs over 400 seeds is 400
                       problems seen 35 ways, and should be reported that way.
  top_k_share        — concentration. If 10% of seeds carry 80% of pairs, the dataset is
                       dominated by a handful of hint-dense files, and a model can score
                       well by overfitting them.
  edit_kind_mix      — which operators dominate. One operator at 90% is a monoculture
                       however many rows it produced.

This module makes NO claim about semantic novelty. Two different edits to the same proof
may still teach the identical lesson; detecting that needs the model, not a hash. Stated
so the count is not mistaken for a diversity guarantee.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path


def _norm(line: str) -> str:
    """Whitespace-insensitive line identity. Indentation changes when a clause is excised,
    so raw comparison would report edits that are not edits."""
    return re.sub(r"\s+", " ", line.strip())


def edit_signature(chosen: str, rejected: str) -> tuple:
    """The normalised multiset difference between the two sides, as (removed, added).

    Deliberately order-insensitive and line-based: an excision that shifts following lines
    must not read as a hundred-line rewrite."""
    c = collections.Counter(_norm(l) for l in chosen.splitlines() if l.strip())
    r = collections.Counter(_norm(l) for l in rejected.splitlines() if l.strip())
    removed = tuple(sorted((c - r).elements()))
    added = tuple(sorted((r - c).elements()))
    return removed, added


def pair_key(pair: dict) -> str:
    """Identity of a pair = (which proof, which edit). See the module docstring for why
    this is neither `chosen` nor `rejected` alone."""
    removed, added = edit_signature(pair["chosen"], pair["rejected"])
    seed = hashlib.sha256(pair["chosen"].encode("utf-8")).hexdigest()[:16]
    body = json.dumps({"seed": seed, "removed": removed, "added": added}, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def exact_key(pair: dict) -> str:
    return hashlib.sha256((pair["chosen"] + "\x00" + pair["rejected"]).encode("utf-8")).hexdigest()


def analyse(pairs: list, top_k: int = 10) -> dict:
    """Concentration + duplication report over a list of pair dicts."""
    n = len(pairs)
    if n == 0:
        return {"pairs": 0}

    exact = collections.Counter(exact_key(p) for p in pairs)
    edits = collections.Counter(pair_key(p) for p in pairs)
    seeds = collections.Counter(
        hashlib.sha256(p["chosen"].encode("utf-8")).hexdigest()[:16] for p in pairs)
    per_source = collections.Counter(p.get("source_path", "?") for p in pairs)
    kinds = collections.Counter(p.get("hint_kind", p.get("operator", "?")) for p in pairs)

    counts = sorted(seeds.values(), reverse=True)
    top = sum(counts[:top_k])

    return {
        "pairs": n,
        "exact_duplicates": n - len(exact),
        "same_edit_duplicates": n - len(edits),
        "unique_after_dedup": len(edits),
        "distinct_seeds": len(seeds),
        "pairs_per_seed": round(n / len(seeds), 2),
        "distinct_source_files": len(per_source),
        f"top{top_k}_seed_share": round(top / n, 3),
        "max_pairs_from_one_seed": counts[0],
        "edit_kind_mix": dict(kinds.most_common(12)),
    }


def dedup(pairs: list) -> list:
    """Keep the first pair for each distinct (seed, edit). Order-stable."""
    seen, out = set(), []
    for p in pairs:
        k = pair_key(p)
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


def load_jsonl(path) -> list:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Concentration/duplication report for Dafny pairs")
    ap.add_argument("jsonl", nargs="+", help="pair files (chosen/rejected per row)")
    ap.add_argument("--write-deduped", help="write the deduplicated union here")
    a = ap.parse_args()

    allp = []
    for f in a.jsonl:
        rows = load_jsonl(f)
        print(f"{f}: {len(rows)} rows")
        allp.extend(rows)

    print("\n--- per-corpus union ---")
    print(json.dumps(analyse(allp), indent=2))

    if a.write_deduped:
        kept = dedup(allp)
        Path(a.write_deduped).write_text("\n".join(json.dumps(p) for p in kept), encoding="utf-8")
        print(f"\nwrote {len(kept)} deduplicated pairs -> {a.write_deduped}")
