#!/usr/bin/env python3
"""test_gate_coverage.py — nothing loads training data except through the gate.

`dataset_gate.load_verified()` makes the check the way you OBTAIN the file list,
rather than a line you must remember to write first. That narrows the hole; it
does not close it, because a future module can still build a path itself and open
it. This test is what bounds that: it fails if any module outside the gate itself
reads data/*.jsonl directly.

Run standalone, or let sync_public.py run it before publishing:

    python test_gate_coverage.py

WHAT THIS DOES NOT COVER, stated so the pass is not read as more than it is:
it greps for the call shapes listed in READERS on .py files in the repo root. It
would miss a read built by string concatenation, one performed inside a library,
one in a subdirectory, or a path assembled at runtime from config. A clean result
means "no direct read in the shapes this searches", never "impossible".
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Modules that are ALLOWED to read the data directly: the gate itself, the
# verifier that produces the receipt, and the tools whose whole job is rewriting
# the dataset before any receipt exists.
ALLOWED = {
    "dataset_gate.py",      # hashes the files; must open them
    "verify_dataset.py",    # produces the receipt
    "clean_dataset.py",     # rewrites the dataset pre-receipt
    "build_training_set.py",  # builds the capped file pre-receipt
    "test_gate_coverage.py",  # this file
}

# Call shapes that constitute "reading the training data".
READERS = re.compile(
    r"""(load_dataset\s*\(|open\s*\(|\.read_text\s*\(|\.open\s*\(|json\.load\s*\()""",
    re.VERBOSE)
# A line only counts if it also names a training-data file or a dataset load.
DATA_REF = re.compile(r"""(dpo_pairs\w*\.jsonl|repair_pairs\.jsonl|data_files\s*=)""")
# ...but a module that routes its paths through the gate is fine, however it then
# loads them. The property being tested is "reads training data WITHOUT passing the
# gate", not "reads training data" -- the first version of this test flagged both
# legitimate trainers, which is the same invented-scope error it exists to catch.
GATED = re.compile(r"""load_verified\s*\(""")


def main() -> int:
    offenders: list[tuple[str, int, str]] = []
    gated: list[str] = []
    scanned = 0
    for path in sorted(HERE.glob("*.py")):
        if path.name in ALLOWED:
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        if GATED.search(text):
            gated.append(path.name)
            continue
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if READERS.search(line) and DATA_REF.search(line):
                offenders.append((path.name, i, stripped[:100]))

    print(f"gate coverage: scanned {scanned} module(s); "
          f"{len(ALLOWED)} exempt, {len(gated)} routed through the gate "
          f"({', '.join(sorted(gated)) or 'none'})")
    if offenders:
        print("\nFAIL: training data read outside dataset_gate.load_verified():\n")
        for name, i, text in offenders:
            print(f"  {name}:{i}  {text}")
        print("\nRoute it through dataset_gate.load_verified(), or add the module to\n"
              "ALLOWED here with a reason if it legitimately predates the receipt.")
        return 1
    print("PASS: every training-data read goes through the gate")
    print("      (scope: direct call shapes in repo-root .py files - see docstring)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
