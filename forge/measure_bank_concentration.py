#!/usr/bin/env python3
"""measure_bank_concentration.py — how repetitive is the run-1 training bank?

THE QUESTION, and it is not the one build_training_set.py already answered.
That file measures TASK concentration: effective task count (exp of the Shannon
entropy over tid) is 9.93 after the cap, over 918 pairs. It says plainly that
the cap is "a mild diversity improvement, not the fix for template skew".

Template skew was never measured. This measures it.

WHY IT MATTERS RIGHT NOW. The plan is to score a DPO adapter trained on these
918 pairs against the frozen ruler. If the bank is structurally repetitive, a
null result cannot be read: it cannot separate "DPO did not work" from "the
curriculum was one program renamed nine hundred times". The forge already
demonstrated that failure mode once -- the block labelled `# file:
localllm/train.py` in the old corpus was 86.3% of it and was actually this
generator's candidate stream (ruled on in 73b37f8).

The layer exact de-duplication misses is RENAMING. `def f(a, b)` and
`def g(x, y)` with identical bodies are different bytes, identical behaviour.
So each `chosen` program is parsed and its identifiers canonicalised before
hashing: same shape, same cluster, regardless of names, comments or spacing.

A FLASHLIGHT, NOT A FENCE. This is a one-off measurement, not a permanent
check. Structural identity is one representation among several -- it will not
see two different-shaped programs that behave identically, and it will split
one algorithm written with a loop and with a comprehension. Behavioural probes
would answer that and are not built here. Read the numbers as a lower bound on
repetition, never as its full extent.

    python measure_bank_concentration.py
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import math
from pathlib import Path

import dataset_gate
import forge

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def effective_count(counts: list[int]) -> float:
    """exp(Shannon entropy) over a distribution.

    The SAME estimator build_training_set.py uses for effective task count, so
    the structural number can be read against the 9.93 it reports rather than
    against a second definition of the same word.
    """
    total = sum(counts)
    if not total:
        return 0.0
    h = -sum((c / total) * math.log(c / total) for c in counts if c)
    return math.exp(h)


class _Canon(ast.NodeTransformer):
    """Rename every identifier to a positional token, drop docstrings.

    Names are assigned in first-seen order, so two programs that differ only by
    what things are called collapse to the same tree.
    """

    def __init__(self) -> None:
        self.names: dict[str, str] = {}

    def _tok(self, name: str) -> str:
        if name not in self.names:
            self.names[name] = f"v{len(self.names)}"
        return self.names[name]

    def visit_Name(self, node: ast.Name):
        node.id = self._tok(node.id)
        return self.generic_visit(node)

    def visit_arg(self, node: ast.arg):
        node.arg = self._tok(node.arg)
        node.annotation = None
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.name = self._tok(node.name)
        node.returns = None
        # Drop a leading docstring: prose is not structure.
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:] or [ast.Pass()]
        return self.generic_visit(node)


def structural_key(source: str) -> str | None:
    """Canonical shape of a program, or None if it will not parse."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    tree = _Canon().visit(tree)
    ast.fix_missing_locations(tree)
    return hashlib.sha256(ast.dump(tree).encode()).hexdigest()


def report(label: str, counts: collections.Counter, total: int) -> dict:
    sizes = sorted(counts.values(), reverse=True)
    largest = sizes[0] if sizes else 0
    top3 = sum(sizes[:3])
    out = {
        "clusters": len(counts),
        "effective": round(effective_count(sizes), 2),
        "largest_share_pct": round(100 * largest / total, 1) if total else 0.0,
        "top3_share_pct": round(100 * top3 / total, 1) if total else 0.0,
    }
    print(f"\n{label}")
    print(f"  distinct clusters      : {out['clusters']}")
    print(f"  effective (exp entropy): {out['effective']}")
    print(f"  largest cluster share  : {out['largest_share_pct']}%")
    print(f"  top-3 cluster share    : {out['top3_share_pct']}%")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="dpo_pairs_capped.jsonl",
                    help="which bank to measure (default: run-1's input)")
    args = ap.parse_args()

    # Through the gate, never around it: this reads verified bytes or it does
    # not read at all, and test_gate_coverage.py stays true.
    paths = dataset_gate.load_verified([str(DATA / args.file)], DATA)

    rows = []
    with open(paths[0], encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    total = len(rows)
    print(f"measuring {total} pairs in {args.file}")

    tids = collections.Counter()
    exact = collections.Counter()
    struct = collections.Counter()
    unparsed = 0

    for r in rows:
        tids[r.get("meta", {}).get("tid")] += 1
        chosen = forge.extract_code(r["chosen"]) or r["chosen"]
        exact[hashlib.sha256(chosen.strip().encode()).hexdigest()] += 1
        key = structural_key(chosen)
        if key is None:
            unparsed += 1
        else:
            struct[key] += 1

    res = {"file": args.file, "pairs": total, "unparsed_chosen": unparsed}
    res["task"] = report("BY TASK (tid) - comparable to build_training_set's 9.93",
                         tids, total)
    res["exact"] = report("BY EXACT TEXT of chosen", exact, total)
    parsed = total - unparsed
    res["structural"] = report(
        f"BY STRUCTURE of chosen (identifiers canonicalised, {parsed} parsed)",
        struct, parsed)

    if unparsed:
        print(f"\n  {unparsed} chosen completions did not parse and are "
              f"excluded from the structural row only.")

    print("\nWHAT THIS DOES NOT SEE: behavioural duplicates with different "
          "shapes,\nand it splits the same algorithm written two ways. Lower "
          "bound on repetition.")

    out = DATA / "bank_concentration.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
