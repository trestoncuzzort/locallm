"""test_detectors.py — tests for the leakage detector.

    python test_detectors.py

No framework, no dependencies, no config. Run it and read the output.

Why this file exists, stated plainly because it is the point: the detector in
leakage.py shipped twice with a correctness bug that no test would have caught,
because there were no tests. Both bugs were found by a reviewer reading the
code, which is luck, not a system. This is the system.

Two rules the bugs themselves taught, and both are load-bearing here:

  ASSERT ON THE DECISION, NOT A SUB-METRIC. The first bug lived in one metric
  while a neighbouring metric still looked fine, and the report printed both. A
  human read the healthy number. So these tests assert on the VERDICT the tool
  actually returns, which is what a user acts on.

  DO NOT PICK TEST INPUTS BY HAND. The first bug was a fixed stride of 10, and
  every "obvious" test offset a person reaches for (0, 100, 500, 1000) is a
  multiple of 10, so a hand-written suite passes on the broken code. When an
  implementation parameter could align with a test input, the input must be
  adversarial or random. Every offset test below mixes round numbers with
  random.Random-drawn ones, and the random ones are what actually bite.

The old, broken fixed-stride sampler is KEPT here on purpose as a regression
oracle, and every test runs against both implementations so you can see which
tests actually discriminate.

BE PRECISE ABOUT WHAT THIS SUITE GUARANTEES, because the first version of this
docstring overstated it: only ONE of the five tests (phase invariance) fails
against the known-broken sampler. Three of the others pass on both, because they
guard properties the old sampler also had. That is not a defect in them, but it
does mean they could not have caught the bug that made this file necessary.

THE FIFTH TEST HAS A DIFFERENT ORACLE, and it is named here so nobody reads the
"passes on both samplers" column and calls it toothless. `short copies are
caught` guards the VERDICT, not the fingerprinter: it fails against leakage.py
as of commit 4b0b4f7, whose verdict read content overlap alone. Its fixture is
the one that change was measured on, and it lives in this file rather than in a
commit message because a fixture quoted in prose is not run by anything.

NOT COVERED, measured rather than assumed: renamed or rewritten copies. The
detector scores 0% recall on identifier-renamed Python. No test here checks for
that, because the detector is not built to find it and a test would only assert
a known failure.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import leakage
from leakage import Report, shingles as current_shingles


def broken_fixed_stride_shingles(text: str, k: int = 50, stride: int = 10) -> set:
    """The original sampler, preserved as a permanent regression oracle.

    DO NOT USE THIS. It is here so the tests can prove they are capable of
    failing. It samples every `stride`-th window starting from position 0, so
    two copies of a passage are only ever compared when both happen to start on
    the same phase.
    """
    if len(text) < k:
        return {text} if text.strip() else set()
    return {text[i:i + k] for i in range(0, len(text) - k + 1, stride)}


def _verdict(train: str, val: str, shingle_fn) -> str:
    """Build a Report the way scan() does, but with a swappable fingerprinter,
    then ask for the VERDICT. Tests assert on this, never on a raw fraction."""
    train_sh, val_sh = shingle_fn(train), shingle_fn(val)
    rep = Report(
        train_chars=len(train), val_chars=len(val),
        val_docs=0, val_docs_in_train=0, doc_aligned=False,
        val_lines=len([l for l in val.splitlines() if l.strip()]),
        val_lines_in_train=0,
        val_shingles=len(val_sh),
        val_shingles_in_train=len(val_sh & train_sh))
    return rep.verdict


def _scan_like(train: str, val: str, shingle_fn, doc_aligned: bool) -> Report:
    """scan(), with a swappable fingerprinter and all three signals real.

    _verdict above zeroes the document and line counts on purpose: its tests are
    about the fingerprinter, and a stray line collision in generated filler
    would move a verdict those tests read as the fingerprinter's answer. This
    one keeps all three, because the fixture below is about what the verdict
    does with the two signals content overlap cannot see.
    """
    train_docs = set(leakage.documents(train))
    val_docs = leakage.documents(val)
    train_lines = set(train.splitlines())
    val_lines = [l for l in val.splitlines() if l.strip()]
    train_sh, val_sh = shingle_fn(train), shingle_fn(val)
    return Report(
        train_chars=len(train), val_chars=len(val),
        val_docs=len(val_docs),
        val_docs_in_train=sum(1 for d in val_docs if d in train_docs),
        doc_aligned=doc_aligned,
        val_lines=len(val_lines),
        val_lines_in_train=sum(1 for l in val_lines if l in train_lines),
        val_shingles=len(val_sh),
        val_shingles_in_train=len(val_sh & train_sh))


def short_document_fixture(seed: int = 4242, n_copied: int = 40) -> tuple[str, str]:
    """A holdout made ENTIRELY of verbatim copies of SHORT training documents.

    Every copied document is 30-35 characters, which is below SHINGLE = 50, so
    the content arm cannot fingerprint the duplication at any offset: it is not
    a matter of the copies being hard to find, they are shorter than the unit
    the arm measures in. The copies are re-ordered on the holdout side and the
    training side interleaves unrelated multi-line filler, so no 50-character
    window is shared across the two either — the content arm reads 0.0% because
    there is nothing there for it to see, while 100% of the holdout is
    byte-identical to training.
    """
    rng = random.Random(seed)
    words = ["alpha", "beta", "gamma", "delta", "value", "index", "buffer",
             "result", "window", "offset", "table", "kernel", "row", "seed"]

    def line(lo: int, hi: int) -> str:
        s = ""
        while len(s) < lo:
            s += (" " if s else "") + rng.choice(words)
        return s[:hi]

    copied = [line(30, 35) for _ in range(n_copied)]
    filler = ["\n".join(line(60, 90) for _ in range(4)) for _ in range(n_copied)]
    train_docs = []
    for c, f in zip(copied, filler):
        train_docs += [f, c]
    rng.shuffle(train_docs)
    val_docs = list(copied)
    rng.shuffle(val_docs)
    return "\n\n".join(train_docs), "\n\n".join(val_docs)


def _filler(n: int, seed: int) -> str:
    rng = random.Random(seed)
    words = ["alpha", "beta", "gamma", "delta", "value", "return", "index",
             "buffer", "result", "compute", "window", "offset"]
    out = []
    while sum(len(w) + 1 for w in out) < n:
        out.append(rng.choice(words))
        if rng.random() < 0.12:
            out.append("\n")
    return " ".join(out)[:n]


# ---------------------------------------------------------------- the tests

def test_phase_invariance(shingle_fn) -> tuple[bool, str]:
    """A verbatim copy must be found no matter what byte offset it sits at.

    Offsets deliberately mix round numbers with random ones. Round numbers
    alone pass on the broken sampler, which is exactly the trap this guards.
    """
    rng = random.Random(0)
    offsets = [0, 100, 500, 1000] + [rng.randrange(1, 997) for _ in range(12)]
    victim = _filler(3000, seed=7)
    missed = []
    for off in offsets:
        train = _filler(4000, seed=8) + ("x" * off) + victim + _filler(4000, seed=9)
        if _verdict(train, victim, shingle_fn) != "CONTAMINATED":
            missed.append(off)
    ok = not missed
    round_only = [o for o in missed if o % 10 == 0]
    detail = (f"{len(offsets) - len(missed)}/{len(offsets)} offsets detected"
              + ("" if ok else f"; missed {sorted(missed)[:8]}"
                               f" (of which {len(round_only)} were round numbers)"))
    return ok, detail


def test_no_false_positive_at_scale(shingle_fn) -> tuple[bool, str]:
    """Two independently generated corpora share no text, so any overlap is the
    fingerprinter colliding with itself. Must stay clean as size grows."""
    worst, worst_size = -1.0, 0
    for size in (200_000, 800_000):
        rng_a, rng_b = random.Random(101), random.Random(202)
        a = "".join(rng_a.choice("abcdefghijklmnopqrstuvwxyz \n") for _ in range(size))
        b = "".join(rng_b.choice("abcdefghijklmnopqrstuvwxyz \n") for _ in range(size))
        sa, sb = shingle_fn(a), shingle_fn(b)
        frac = len(sa & sb) / max(len(sb), 1)
        if frac > worst:
            worst, worst_size = frac, size
    ok = worst < 0.001
    return ok, f"worst false overlap {worst:.4%} at {worst_size // 1000}KB"


def test_clean_split_reads_clean(shingle_fn) -> tuple[bool, str]:
    """The complement of the phase test: unrelated text must NOT read as
    contaminated. A detector that always says CONTAMINATED would pass the
    phase test alone."""
    train, val = _filler(20000, seed=11), _filler(4000, seed=12)
    v = _verdict(train, val, shingle_fn)
    return v == "CLEAN", f"unrelated text reads {v}"


def test_guarantee_length(shingle_fn) -> tuple[bool, str]:
    """The documented guarantee is that a shared run of >= WINDOW + SHINGLE - 1
    characters is caught. Assert the documented number, not a hopeful one."""
    need = leakage.WINDOW + leakage.SHINGLE - 1
    rng = random.Random(3)
    hits = 0
    trials = 20
    for _ in range(trials):
        run = _filler(need, seed=rng.randrange(10**6))
        train = _filler(6000, seed=rng.randrange(10**6)) + run + _filler(6000, seed=rng.randrange(10**6))
        if shingle_fn(run) & shingle_fn(train):
            hits += 1
    ok = hits == trials
    return ok, f"{hits}/{trials} runs of the documented {need} chars were found"


def test_short_copies_are_caught(shingle_fn) -> tuple[bool, str]:
    """A holdout of verbatim copies too SHORT to fingerprint must not read CLEAN.

    The regression oracle here is not the old sampler, it is the old VERDICT:
    against leakage.py at 4b0b4f7, which decided on content overlap alone while
    printing all three signals, this fixture returns CLEAN with trustworthy
    True. Measured on that commit: documents 40/40, lines 40/40, content 0/95.

    The assertion deliberately includes `content is below its own SUSPECT bar`.
    Without it the test would pass on a detector that reached CONTAMINATED
    through the content arm, which is the one arm that structurally cannot see
    this fixture; with it, the test can only pass because the document and line
    arms are read too.
    """
    train, val = short_document_fixture()
    rep = _scan_like(train, val, shingle_fn, doc_aligned=True)
    ok = (rep.verdict == "CONTAMINATED" and not rep.trustworthy
          and rep.doc_frac == 1.0 and rep.line_frac == 1.0
          and rep.shingle_frac < leakage.SUSPECT)
    return ok, (f"documents {rep.val_docs_in_train}/{rep.val_docs} "
                f"({rep.doc_frac:.1%}), lines {rep.val_lines_in_train}/"
                f"{rep.val_lines} ({rep.line_frac:.1%}), content "
                f"{rep.shingle_frac:.1%} -> {rep.verdict}")


TESTS = [
    ("phase invariance", test_phase_invariance),
    ("no false positive at scale", test_no_false_positive_at_scale),
    ("clean split reads CLEAN", test_clean_split_reads_clean),
    ("documented length guarantee", test_guarantee_length),
    ("short copies are caught", test_short_copies_are_caught),
]


def main() -> None:
    print("Running each test against the CURRENT detector (must pass) and against")
    print("the OLD fixed-stride sampler (must FAIL, or the test proves nothing).\n")

    failures = 0
    toothless = 0
    for name, fn in TESTS:
        cur_ok, cur_detail = fn(current_shingles)
        old_ok, old_detail = fn(broken_fixed_stride_shingles)

        status = "PASS" if cur_ok else "FAIL"
        print(f"  [{status}] {name}")
        print(f"         current: {cur_detail}")
        print(f"         old     : {old_detail}")
        if not cur_ok:
            failures += 1
        # A test the old broken sampler also passes cannot have caught the bug.
        # That is worth reporting, but only the phase test is expected to
        # discriminate; the others guard different properties.
        if name == "phase invariance" and old_ok:
            print("         !! this test PASSES on the known-broken sampler and is "
                  "therefore worthless")
            toothless += 1
        print()

    print("=" * 64)
    if failures:
        print(f"{failures} of {len(TESTS)} tests FAILED against the current detector")
    elif toothless:
        print("all tests passed, but a regression test did not fail on known-bad code")
    else:
        print(f"all {len(TESTS)} tests pass, and the phase test still fails on the "
              f"old sampler")
    print("=" * 64)
    sys.exit(1 if (failures or toothless) else 0)


if __name__ == "__main__":
    main()
