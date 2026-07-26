"""leakage.py — find training text hiding in your validation set.

This is the check almost no training tool performs, and it is the most common
way a good-looking number turns out to be fake. If validation text also appears
in training, the model has already seen the answers, val loss drops, and you
conclude your change helped when it did nothing.

    python leakage.py --data corpus.txt

It measures three things, cheapest first:

  document overlap  whole documents that appear on both sides of the split
  line overlap      validation lines that appear verbatim in training
  shingle overlap   50-character windows of validation text found in training

Shingle overlap is the one to trust. Line overlap over-reports on code, where
`    return None` legitimately appears everywhere; shingles are long enough that
matching by coincidence is unlikely.

Nothing here is a model. It is string matching, and it runs in about a second.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from data import documents, group_split, split_health

SHINGLE = 50          # characters per window
STRIDE = 10           # step between windows; 1 is exact but needlessly slow
DOC_MARKER = "\n\n# file: "

# Above this fraction of validation shingles found in training, a val number is
# not worth reporting. Below the lower bound, incidental overlap is expected in
# any corpus with shared vocabulary and is not a finding.
CONTAMINATED = 0.20
SUSPECT = 0.05


def shingles(text: str, k: int = SHINGLE, stride: int = STRIDE) -> set[str]:
    if len(text) < k:
        return {text} if text.strip() else set()
    return {text[i:i + k] for i in range(0, len(text) - k + 1, stride)}


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
            f"  shingles   {self.val_shingles_in_train:>6,} / {self.val_shingles:<6,} "
            f"of {SHINGLE}-char validation windows are in training "
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
