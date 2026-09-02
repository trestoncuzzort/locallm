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

ALL THREE DECIDE THE VERDICT, each against its own bar, and the verdict is the
worst call any of them makes. This file used to print all three and decide on
content alone, which is not merely untidy: content overlap cannot see a copied
run shorter than 50 characters at all, so a holdout made entirely of verbatim
copies of short training documents scored 0.0% and read CLEAN. See Report.

TWO OF THE THREE CAN BE n/a, and an arm that is n/a says so rather than voting
CLEAN: documents on a split that cut mid-document, lines on a holdout with too
few of them for a fraction to be a measurement. A CLEAN verdict is only ever as
strong as the arms that could actually be read, and the report names them.

Content overlap is the finest-grained of the three, WITHIN a scope worth stating
up front: this is an exact-substring scanner, not a near-duplicate scanner.
Measured recall on this project's own documents, by clone type:

    verbatim copy                          100%
    reformatted (whitespace re-rendered)    90%
    every identifier renamed                 0%
    renamed + 10% of statements edited       0%

Renaming identifiers costs almost nothing; replacing the string literals is what
destroys detection. On this codebase roughly 7% of the text is prose inside the
code, and that 7% carries nearly all the surviving signal. So a CLEAN verdict
means no one copied and pasted. It does not mean validation is independent.

Nothing here is a model. It is string matching, and it runs in under a second.
"""
from __future__ import annotations

import argparse
import sys
import hashlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import runlog
from data import documents, group_split, split_health, split_verdict

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

# The other two signals get their own bars, because they are not the same kind
# of evidence. Justified against measurement in Report._calls().
DOC_CONTAMINATED = 0.10
DOC_SUSPECT = 0.01
LINE_CONTAMINATED = 0.90
LINE_SUSPECT = 0.50

# The line arm needs a denominator before its fraction means anything. At n
# validation lines, ONE honestly recurring line -- a licence header, a repeated
# heading -- is worth 1/n, so at n = 2 a single shared line reads 50.0% and
# trips the SUSPECT bar on its own. Measured on 110 genuinely clean grouped
# splits of this project's own text (its Python sources, and its markdown; 5
# seeds x 11 requested val fractions), three of them read SUSPECT on the line
# arm with nothing copied anywhere: two 2-line holdouts at 50.0% and one
# 12-line holdout at 50.0%. Above 20 lines, none of the 56 splits measured
# reached the bar and the worst clean reading was 39.1%.
#
# 20 is that measured floor and it is also where the arithmetic stops being a
# coin flip: one recurring line is worth 5 points, so reaching 0.50 takes ten
# shared lines rather than one. Below it the arm reads n/a and says so, the
# same way the document arm is gated by doc_aligned -- an unreadable signal is
# not a clean one, and the report must not let it look like either.
LINE_MIN_VAL_LINES = 20

_RANK = {"CLEAN": 0, "SUSPECT": 1, "CONTAMINATED": 2}


def _call(frac: float, contaminated: float, suspect: float) -> str:
    """One signal's own verdict against its own two bars."""
    if frac >= contaminated:
        return "CONTAMINATED"
    return "SUSPECT" if frac >= suspect else "CLEAN"


def _h(chunk: bytes) -> int:
    """64-bit hash of one k-gram.

    Width matters here in a way it would not for an ordinary hash table, because
    winnowing keeps the MINIMUM hash in each window. Minima are drawn from the
    bottom of the range, so the effective space is far smaller than the nominal
    one and collisions inflate accordingly. Measured with 32-bit crc32: selected
    fingerprints averaged 0.056 of the range against 0.502 for all hashes, a 9x
    concentration, and two independently generated, genuinely CLEAN corpora
    showed false overlap rising with size (0.0065% at 200KB to 0.0293% at 2MB).
    Extrapolated, a large clean corpus would eventually trip the contamination
    threshold on collisions alone. 64 bits removes the effect entirely at every
    size measured, for the same fingerprint count and no measurable cost.
    """
    return int.from_bytes(hashlib.blake2b(chunk, digest_size=8).digest(), "big")


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
    same passage yields the same fingerprints wherever it appears.

    IT IS A TRADE, NOT A FREE WIN, and the trade is measured rather than
    asserted. Detection against the length of the shared run, 20 trials each,
    winnowing versus the old sampler:

        100 chars   100%  vs   90%
         74 chars   100%  vs  100%     <- the documented guarantee, window+k-1
         73 chars   100%  vs   90%
         60 chars    40%  vs   80%     <- old sampler is BETTER here
         50 chars    10%  vs   80%     <- and much better here
         40 chars     0%  vs    0%

    So winnowing buys phase-invariance above the guarantee length and gives up
    short-run sensitivity below it. For finding duplicated documents, passages
    and functions, that is the right trade. For finding copied fragments shorter
    than ~60 characters it is the wrong one, and this returns fewer of them than
    the code it replaced.

    The 74-character guarantee is checked by test_detectors.py, which asserts
    the documented number rather than a hopeful one. Per this file's own rule:
    a docstring that says "guarantee" names the test that checks it.
    """
    if len(text) < k:
        return {_h(text.encode("utf-8", "ignore"))} if text.strip() else set()

    b = text.encode("utf-8", "ignore")
    hashes = [_h(b[i:i + k]) for i in range(len(b) - k + 1)]
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
    def lines_readable(self) -> bool:
        """Whether the holdout has enough lines for line_frac to be a
        measurement. See LINE_MIN_VAL_LINES."""
        return self.val_lines >= LINE_MIN_VAL_LINES

    def _calls(self) -> list[tuple[str, str]]:
        """Each signal's own call, with the sentence that justifies it.

        THREE MEASUREMENTS, THREE BARS, AND THE VERDICT IS THE WORST OF THEM.
        This used to read shingle_frac alone while printing all three, which is
        precisely the failure test_detectors.py's docstring names — a human
        reads the healthy number — except that here the blind spot is
        structural rather than incidental. Winnowing cannot fingerprint a
        shared run shorter than SHINGLE = 50 characters, so a holdout built
        ENTIRELY of byte-identical copies of short training documents scores no
        content overlap whatsoever. Measured: 40 copied documents of 30-35
        characters, 100% of the holdout duplicated, content overlap 0.0%, old
        verdict CLEAN and trustworthy True.

        The three bars differ because the three signals do:

          content   0.20 / 0.05, unchanged. A shared 74-character run can be
                    coincidence in a corpus with shared vocabulary and
                    boilerplate, so it needs room before it means anything.

          documents 0.10 / 0.01, TIGHTER, because a byte-identical document has
                    no innocent explanation: two independently written
                    documents are not byte-identical. Measured 0.000% across
                    six clean grouped splits (this project's own sources and
                    its markdown, seeds 1337/7/99). Read only when the split is
                    document-aligned; on a positional cut the counts describe
                    fragments and the report already prints n/a for them.
                    Expect 0 on the grouped path — group_split de-duplicates
                    before it splits — so this arm exists for the callers that
                    bring their own split, which is what scan() invites.

          lines     0.90 / 0.50, MUCH LOOSER, because short lines legitimately
                    recur: `}`, `    return`, a repeated heading. Measured on
                    this project's own sources as a corpus, grouped split, with
                    nothing copied anywhere: 11.1%, 18.4% and 26.7% of
                    validation lines at seeds 99, 7 and 1337. A 0.20 bar here
                    would cry wolf on every code corpus in existence. At 0.90
                    the holdout is a re-arrangement of training lines and there
                    is nothing unseen left in it. Read only above
                    LINE_MIN_VAL_LINES, because a bar is only half of a signal:
                    below 20 lines one recurring line is worth 5 points or more
                    and the fraction is noise with a percent sign on it.
        """
        calls = [(_call(self.shingle_frac, CONTAMINATED, SUSPECT),
                  f"{self.shingle_frac:.1%} of validation content fingerprints "
                  f"are found in training")]
        if self.doc_aligned:
            calls.append((_call(self.doc_frac, DOC_CONTAMINATED, DOC_SUSPECT),
                          f"{self.doc_frac:.1%} of validation documents are "
                          f"byte-identical to a training one"))
        if self.lines_readable:
            calls.append((_call(self.line_frac, LINE_CONTAMINATED, LINE_SUSPECT),
                          f"{self.line_frac:.1%} of validation lines appear "
                          f"verbatim in training"))
        return calls

    @property
    def verdict(self) -> str:
        return max((c for c, _ in self._calls()), key=_RANK.__getitem__)

    @property
    def reason(self) -> str:
        """Which signal produced the verdict, in words. A verdict whose own
        summary quotes a different number than the one that caused it sends the
        reader looking in the wrong place."""
        v = self.verdict
        if v == "CLEAN":
            docs = (f", documents {self.doc_frac:.1%}" if self.doc_aligned else "")
            lines = (f"{self.line_frac:.1%}" if self.lines_readable
                     else f"n/a on {self.val_lines} line(s)")
            return (f"nothing above a bar (content {self.shingle_frac:.1%}, "
                    f"lines {lines}{docs})")
        return "; ".join(r for c, r in self._calls() if c == v)

    @property
    def trustworthy(self) -> bool:
        return self.verdict == "CLEAN"

    def summary(self) -> str:
        return f"{self.verdict}: {self.reason}"

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
            (f"  lines      {self.val_lines_in_train:>6,} / {self.val_lines:<6,} "
             f"of validation lines appear verbatim in training "
             f"({self.line_frac:.1%})"
             if self.lines_readable else
             f"  lines         n/a  the holdout is {self.val_lines} line(s), under "
             f"the {LINE_MIN_VAL_LINES}-line floor: below it one recurring line is "
             f"worth {1 / LINE_MIN_VAL_LINES:.0%} of the fraction or more"),
            f"  content    {self.val_shingles_in_train:>6,} / {self.val_shingles:<6,} "
            f"of validation fingerprints are found in training "
            f"({self.shingle_frac:.1%})   <- the finest-grained",
            "",
            f"  verdict {self.verdict}: {self.reason}",
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
            lines += [
                "  No signal above its bar. Note what that does and does not mean:",
                "  this is an EXACT-SUBSTRING scanner. It finds shared runs of >=74",
                "  characters at any offset, measured 100% recall. It does NOT find",
                "  renamed or rewritten copies: measured 0% recall on identifier-",
                "  renamed Python, where re-rendering whitespace and replacing string",
                "  literals removes essentially all of the signal it relies on.",
                "  CLEAN here means 'no copy-paste found', not 'val is independent'.",
            ]
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
    # lines_readable rides with line_frac because the row is read by someone who
    # was not here. Without it a row can say verdict CLEAN and line_frac 0.5 on
    # the same line and look like a contradiction, when the truth is that the
    # holdout had two lines and the arm was never read. The raw fraction is kept
    # rather than nulled: it is a real count, it just is not a verdict.
    runlog.record("leakage", corpus=runlog.corpus_fingerprint(text),
                  split=args.split,
                  leakage={"verdict": rep.verdict, "content_frac": rep.shingle_frac,
                           "line_frac": rep.line_frac,
                           "lines_readable": rep.lines_readable,
                           "val_lines": rep.val_lines})

    if args.split == "grouped":
        h = split_health(text, args.val_frac, args.seed)
        # Two ratios, two different failures, two different remedies - which the
        # single boolean this replaced could not tell apart. The comparison
        # itself lives in data.split_verdict so this file, the GUI and the
        # double-click launcher cannot answer the same question differently.
        verdict = split_verdict(h)
        if verdict:
            print(f"\n  WARNING: asked for a {h['requested_val_frac']:.0%} validation "
                  f"split, got {h['achieved_val_frac']:.1%}; the best any whole-document "
                  f"split could reach is {h['achievable_val_frac']:.1%}.")
            print(f"  {h['unique_documents']} unique document(s) after de-duplication, "
                  f"largest is {h['largest_unique_doc_frac']:.0%} of them.")
            if verdict == "empty":
                print("  Nothing was held back at all: there is no validation number.")
            elif verdict == "corpus":
                print("  The CORPUS cannot support the request: it needs more, smaller "
                      "documents.")
            elif verdict == "splitter":
                print("  The corpus could support it but this SPLIT fell short: try "
                      "another seed.")
            print("  Prefer train loss until then.")
            sys.exit(1)
    sys.exit(0 if rep.trustworthy else 1)


if __name__ == "__main__":
    main()
