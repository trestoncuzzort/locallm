"""leakage.py — find training text hiding in your validation set.

This is the check almost no training tool performs, and it is the most common
way a good-looking number turns out to be fake. If validation text also appears
in training, the model has already seen the answers, val loss drops, and you
conclude your change helped when it did nothing.

    python leakage.py --data corpus.txt

It measures three things, cheapest first:

  document overlap  whole documents that appear on both sides of the split
  line overlap      validation lines that appear verbatim in training
  content overlap   winnowing fingerprints of validation text found in training

Content overlap is the one to trust. Line overlap over-reports on code, where
`    return None` legitimately appears everywhere. Fingerprints cover 50
characters, so matching by coincidence is unlikely, and they are selected by
CONTENT rather than by position: see shingles() for why that distinction is the
difference between catching a verbatim copy every time and catching it one time
in ten.

Nothing here is a model. It is string matching, and it runs in under a second.
"""
from __future__ import annotations

import argparse
import sys
import zlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from data import documents, group_split, split_health

SHINGLE = 50          # characters per k-gram
WINDOW = 25           # winnowing window, in k-grams. Guarantees that any shared
                      # run of >= WINDOW + SHINGLE - 1 = 74 characters is caught,
                      # regardless of where it starts. See shingles().
DOC_MARKER = "\n\n# file: "

# Above this fraction of validation shingles found in training, a val number is
# not worth reporting. Below the lower bound, incidental overlap is expected in
# any corpus with shared vocabulary and is not a finding.
CONTAMINATED = 0.20
SUSPECT = 0.05


def shingles(text: str, k: int = SHINGLE, window: int = WINDOW) -> set[int]:
    """Winnowing fingerprints (Schleimer, Wilkerson & Aiken 2003).

    The obvious approach, keeping every k-th window at a fixed stride, is
    PHASE-DEPENDENT and quietly broken: two identical passages are only compared
    when both happen to start on the same stride phase. Measured on this
    project's own corpus, a document copied verbatim into training was detected
    at 1 of 10 byte offsets. A detector that misses nine tenths of the exact
    case it exists to catch is worse than none, because it reads CLEAN.

    Winnowing instead selects windows by CONTENT: hash every k-gram, then in
    each sliding window of `window` hashes keep the smallest. Which hashes get
    kept therefore depends on the text, not on where the text starts, so the
    same passage yields the same fingerprints wherever it appears. It also
    guarantees that any shared run of at least (window + k - 1) characters is
    detected, which fixed-stride sampling cannot promise at all.
    """
    if len(text) < k:
        return {zlib.crc32(text.encode("utf-8", "ignore"))} if text.strip() else set()

    b = text.encode("utf-8", "ignore")
    hashes = [zlib.crc32(b[i:i + k]) for i in range(len(b) - k + 1)]
    if len(hashes) < window:
        return set(hashes)

    # Sliding-window minimum. Popping on >= keeps the RIGHTMOST minimal hash,
    # which is the tie-break the paper specifies: consecutive windows then tend
    # to re-select the same fingerprint instead of two adjacent ones.
    selected: set[int] = set()
    dq: deque[int] = deque()
    prev = -1
    for i, h in enumerate(hashes):
        while dq and hashes[dq[-1]] >= h:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - window:
            dq.popleft()
        if i >= window - 1:
            j = dq[0]
            if j != prev:
                selected.add(hashes[j])
                prev = j
    return selected


@dataclass
class Report:
    train_chars: int
    val_chars: int
    val_docs: int
    val_docs_in_train: int
    doc_aligned: bool          # False when the split cut through a document
    val_lines: int
    val_lines_in_train: int
    val_shingles: int
    val_shingles_in_train: int

    @property
    def doc_frac(self) -> float:
        return self.val_docs_in_train / max(self.val_docs, 1)

    @property
    def line_frac(self) -> float:
        return self.val_lines_in_train / max(self.val_lines, 1)

    @property
    def shingle_frac(self) -> float:
        return self.val_shingles_in_train / max(self.val_shingles, 1)

    @property
    def verdict(self) -> str:
        if self.shingle_frac >= CONTAMINATED:
            return "CONTAMINATED"
        return "SUSPECT" if self.shingle_frac >= SUSPECT else "CLEAN"

    @property
    def trustworthy(self) -> bool:
        return self.verdict == "CLEAN"

    def summary(self) -> str:
        return (f"{self.verdict}: {self.shingle_frac:.1%} of validation text "
                f"also appears in training")

    def report(self) -> str:
        bar = "=" * 64
        lines = [
            bar,
            f"LEAKAGE SCAN                                  verdict: {self.verdict}",
            bar,
            f"  train {self.train_chars:>10,} chars     val {self.val_chars:>10,} chars",
            "",
            (f"  documents  {self.val_docs_in_train:>6,} / {self.val_docs:<6,} "
             f"of validation documents are byte-identical to a training one "
             f"({self.doc_frac:.1%})"
             if self.doc_aligned else
             "  documents     n/a  the split cut through a document, so document "
             "counts are not meaningful"),
            f"  lines      {self.val_lines_in_train:>6,} / {self.val_lines:<6,} "
            f"of validation lines appear verbatim in training ({self.line_frac:.1%})",
            f"  content    {self.val_shingles_in_train:>6,} / {self.val_shingles:<6,} "
            f"of validation fingerprints are found in training "
            f"({self.shingle_frac:.1%})   <- the one that matters",
            "",
        ]
        if self.verdict == "CONTAMINATED":
            lines += [
                "  Validation loss from this split is NOT a measure of generalisation.",
                "  The model is being tested on text it trained on. Do not compare",
                "  configurations with it, and do not report it as a result.",
                "",
                "  Fix: split by document (Corpus(..., grouped=True)) so duplicated",
                "  material cannot land on both sides, and de-duplicate the corpus.",
            ]
        elif self.verdict == "SUSPECT":
            lines += [
                "  Some overlap. Small amounts are normal when documents share",
                "  vocabulary and boilerplate, but treat small val differences with",
                "  suspicion, and prefer train loss for close comparisons.",
            ]
        else:
            lines += ["  Validation looks independent of training. Val loss is usable."]
        lines.append(bar)
        return "\n".join(lines)


def scan(train_text: str, val_text: str, doc_aligned: bool = True) -> Report:
    train_docs = set(documents(train_text))
    val_docs = documents(val_text)
    train_lines = set(train_text.splitlines())
    val_lines = [l for l in val_text.splitlines() if l.strip()]
    train_sh = shingles(train_text)
    val_sh = shingles(val_text)

    return Report(
        train_chars=len(train_text),
        val_chars=len(val_text),
        val_docs=len(val_docs),
        val_docs_in_train=sum(1 for d in val_docs if d in train_docs),
        val_lines=len(val_lines),
        val_lines_in_train=sum(1 for l in val_lines if l in train_lines),
        val_shingles=len(val_sh),
        val_shingles_in_train=len(val_sh & train_sh),
        doc_aligned=doc_aligned,
    )


def positional_split(text: str, val_frac: float = 0.1) -> tuple[str, str]:
    """The naive split: cut the corpus at 90% of its length. Kept so the scan
    can show you what it costs."""
    n = int(len(text) * (1 - val_frac))
    return text[:n], text[n:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="corpus.txt")
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--split", choices=["positional", "grouped"], default="positional",
                    help="which split to scan (default: positional, what data.py did)")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    text = Path(args.data).read_text(encoding="utf-8", errors="ignore")
    if args.split == "positional":
        tr, va = positional_split(text, args.val_frac)
    else:
        tr, va = group_split(text, args.val_frac, args.seed)

    print(f"corpus: {Path(args.data).name}  {len(text):,} chars, "
          f"{len(documents(text)):,} documents, split={args.split}\n")
    rep = scan(tr, va, doc_aligned=(args.split == "grouped"))
    print(rep.report())

    if args.split == "grouped":
        h = split_health(text, args.val_frac, args.seed)
        if not h["ok"]:
            print(f"\n  WARNING: asked for a {h['requested_val_frac']:.0%} validation "
                  f"split, got {h['achieved_val_frac']:.1%}.")
            print(f"  This corpus has only {h['documents']} document(s) and the largest "
                  f"is {h['largest_doc_frac']:.0%} of the text,")
            print("  so whole-document splitting cannot hit the target. A clean split")
            print("  needs more, smaller documents. Prefer train loss until then.")
            sys.exit(1)
    sys.exit(0 if rep.trustworthy else 1)


if __name__ == "__main__":
    main()
