"""baselines.py — what a DUMB model scores on the same text, so "it learned" is a
claim you can check rather than a number you have to trust.

WHY THIS EXISTS. The studio's headline said the model had come "99% of the way
from guessing to certainty". Both ends of that sentence were real; the *start*
was not a fair opponent. "Guessing" meant a uniform draw over the alphabet — 83
equally-likely characters — and essentially anything beats it. Measured on the
20MB stories corpus, on the exact split the trainer used:

    uniform over the alphabet          6.375 bits/char    83.00 choices
    letter frequency alone             4.446 bits/char    21.80 choices
    bigram   (previous 1 character)    3.317 bits/char     9.97 choices
    trigram  (previous 2 characters)   2.436 bits/char     5.41 choices
    the trained 3.18M model            1.111 bits/char     2.16 choices

A trigram is a lookup table. It has no parameters to train, no gradient, no GPU,
and it already covers most of the distance from 83 to 1. Against uniform the
model looks 99% of the way there; against the trigram it is about 74% of the
remaining distance. Both numbers are true and only the second one is useful.

The failure this prevents is not a small one. On a corpus with heavy repetition
or a skewed alphabet, a model can post an excellent loss having learned almost
nothing a lookup table did not already know — and with uniform as the only
reference, the report would congratulate it. The gap between the model and the
n-gram is the part that required learning; that gap is what this file measures.

WHAT THIS IS NOT. These are deliberately weak models, and a stronger baseline
would only make the comparison harsher. Add-1 smoothing is the simplest thing
that works, not the best (Kneser-Ney would score better and so would a longer
context). That direction is safe: understating the baseline is the failure mode
to avoid, because it flatters the model. If someone replaces these with better
n-grams and the model's advantage shrinks, the new number is the honest one.

AND THE ELIGIBILITY RULE RIDES ALONG. A baseline is only meaningful on the same
held-out text the model was scored on. If that split cannot support a validation
claim — data.split_verdict() returns anything but None, or the leakage scan is
not CLEAN — then the comparison is as meaningless as the model's own val loss,
and callers must not present it as evidence. compare() therefore takes the
already-split text rather than re-splitting, so it cannot silently score a
different split than the one that trained (the F-02 trap, in miniature).
"""
from __future__ import annotations

import math
from collections import Counter

LN2 = math.log(2)

# Add-1 (Laplace). Chosen for inspectability: one number, no tuning, and a reader
# can verify the arithmetic by hand. See the module docstring on why a weak
# smoother is the safe direction.
ALPHA = 1.0

# The n-gram order reported alongside the frequency model. 3 is the strongest of
# the cheap references measured above (bigram 3.317 bits, trigram 2.436) while
# still fitting in a table of ~11k cells on a 20MB corpus. Reporting the hardest
# cheap opponent to beat is the point; reporting an easy one would repeat the
# mistake this file exists to fix.
NGRAM_ORDER = 3


def _mean_nats(logprobs_sum: float, n: int) -> float:
    """Cross-entropy in nats per character. Same unit train.py reports, so the
    numbers can be compared without converting anything."""
    return -logprobs_sum / max(n, 1)


def uniform_nats(vocab_size: int) -> float:
    """Every character equally likely — the reference the studio used to call
    'pure guessing'. Included so the old headline number stays visible next to
    the ones that mean something."""
    return math.log(max(vocab_size, 1))


def frequency_nats(train: str, val: str, vocab_size: int) -> float:
    """The DoR's 'trivial character-frequency model': how well you predict the
    next character knowing only how common each character is, and nothing else."""
    counts = Counter(train)
    total = sum(counts.values())
    denom = total + ALPHA * vocab_size
    s = sum(math.log((counts.get(c, 0) + ALPHA) / denom) for c in val)
    return _mean_nats(s, len(val))


def ngram_nats(train: str, val: str, vocab_size: int,
               order: int = NGRAM_ORDER) -> float:
    """The DoR's 'smoothed character n-gram': predict the next character from the
    previous `order - 1`.

    Counted with zip-slices over the string rather than a dict-of-Counters: it is
    one pass, and on the 20MB corpus it builds in 1.8s into ~11k cells. That cost
    is why this can run on every claim-bearing run instead of being opt-in.

    The context table is FOLDED OUT OF the n-gram table rather than counted from
    the string a second time, and that is a correctness point before it is a
    speed one. Counting (k-1)-grams over the string walks one position further
    than counting k-grams does, so the FINAL (k-1)-gram gets counted as a
    context that never had a following character. Any context equal to that one
    then divides by a denominator one too large and its conditional
    distribution sums to less than 1: measured on an 8,708-character corpus,
    0.99953 at order 2, 0.99762 at order 3 and 0.99160 at order 4. Summing the
    k-gram counts instead makes sum_c (n + 1) / (d + V) equal (d + V) / (d + V)
    by construction, at every order, for every context.

    An unseen context falls back to add-1 over the whole alphabet, which is the
    same floor `uniform_nats` reports — a context the model has never seen is a
    context this baseline cannot help with, and pretending otherwise would
    understate the baseline.
    """
    k = max(order, 1)
    if len(train) <= k or not val:
        return uniform_nats(vocab_size)

    # counts[ctx][nxt] via two flat Counters: the full n-gram, and its context.
    # The context table is the n-gram table with the last character dropped, so
    # the two can never disagree about how many positions were counted. See the
    # docstring: counting it from the string instead walked one position further
    # and left the last context with a successor it never had.
    full = Counter(zip(*(train[i:] for i in range(k))))
    ctx = None
    if k > 1:
        ctx = Counter()
        for gram, n in full.items():
            ctx[gram[:-1]] += n

    hist = tuple(train[-(k - 1):]) if k > 1 else ()
    s = 0.0
    for c in val:
        if k == 1:
            n, d = full.get((c,), 0), sum(full.values())
        else:
            n = full.get(hist + (c,), 0)
            d = ctx.get(hist, 0)
        s += math.log((n + ALPHA) / (d + ALPHA * vocab_size))
        if k > 1:
            hist = (hist + (c,))[-(k - 1):]
    return _mean_nats(s, len(val))


def holdout_eligibility(text: str, train_text: str | None, val_text: str | None,
                        val_frac: float = 0.1, seed: int = 1337) -> str | None:
    """Why this holdout cannot carry a baseline comparison, or None if it can.

    THE RULE IN THIS MODULE'S DOCSTRING, MADE CALLABLE. It was prose here and
    an inline check in studio.py, and the two experiments had neither: they
    published closed_fraction on any corpus at all. Measured, before this
    existed, with training stubbed so only the analysis ran:

      one document holding 99% of the corpus   split_verdict "corpus",
                                               closed_fraction 0.0221 published
      near-duplicate documents on both sides   leakage CONTAMINATED,
                                               closed_fraction -0.3258 published
      one character, no holdout at all         ZeroDivisionError

    Every one of those numbers is the model and the baseline being wrong in the
    same direction on the same unusable holdout, printed as a percentage with a
    "vs table" column heading over it.

    The split arm and the leakage arm are both required, and they catch
    different things: a corpus can split perfectly and still have the same
    passages on both sides, and a corpus with no overlap at all can still fail
    to yield a holdout worth the name.

    Imports are local so that importing baselines stays free for callers that
    only want the arithmetic, and so this module never has to be ordered
    against leakage.py at import time.
    """
    from data import split_health, split_verdict
    from leakage import scan

    if train_text is None or not val_text:
        return ("no held-out text was produced, so there is nothing to score a "
                "baseline on")
    v = split_verdict(split_health(text, val_frac, seed))
    if v is not None:
        return {
            "empty": "nothing was held back at all, so there is no holdout",
            "corpus": ("this corpus cannot support the requested split: no "
                       "whole-document split of it gets near the request"),
            "splitter": ("this split fell short of the requested holdout, "
                         "though the corpus could support it -- another seed "
                         "probably would"),
        }[v]
    rep = scan(train_text, val_text)
    if not rep.trustworthy:
        return f"the leakage scan reads {rep.verdict}: {rep.reason}"
    return None


def closed_fraction(ngram_choices: float, model_choices: float,
                    ineligible: str | None = None) -> tuple[float | None, str | None]:
    """Of the distance the lookup table left on the table, how much the model
    closed -- or None, and the sentence that says why there is no number.

    Two ways there is no number. The holdout may be ineligible, in which case
    the caller already knows why and passes it through. Or the lookup table may
    already be at 1.0 choices, which leaves the fraction without a denominator:
    both experiments divided by (ngram_choices - 1.0) unguarded and died with
    ZeroDivisionError on a single-character corpus, where the n-gram falls back
    to uniform_nats(1) == 0 and exp(0) is exactly 1.0.

    NOT USED BY compare() BELOW, deliberately and not happily: compare()
    answers the same question with 0.0 in the no-denominator case, which reads
    as "the model closed none of the distance" when the truth is "there was no
    distance". Changing it moves what train.py and studio.py print, so it wants
    its own change and its own witness rather than a ride on this one.
    """
    if ineligible:
        return None, ineligible
    if ngram_choices <= 1.0:
        return None, (f"the lookup table already scores {ngram_choices:.4f} "
                      f"choices, so there is no distance left to close and the "
                      f"fraction has no denominator")
    return (ngram_choices - model_choices) / (ngram_choices - 1.0), None


def compare(train: str, val: str, vocab_size: int,
            model_val_nats: float | None = None) -> dict:
    """Score every baseline on this split, plus the model if you have its loss.

    Returns nats/char, bits/char and 'choices' (exp of the loss — the same
    quantity the studio plots) for each, so a caller can present whichever unit
    suits its reader. `closed_fraction` answers the question the old headline was
    reaching for, but against the n-gram instead of against uniform: of the
    distance the n-gram left on the table, how much did the model close?
    """
    out: dict[str, dict] = {}

    def row(name: str, nats: float) -> None:
        out[name] = {"nats_per_char": nats,
                     "bits_per_char": nats / LN2,
                     "choices": math.exp(nats)}

    row("uniform", uniform_nats(vocab_size))
    row("frequency", frequency_nats(train, val, vocab_size))
    row(f"ngram_{NGRAM_ORDER}", ngram_nats(train, val, vocab_size))

    if model_val_nats is not None:
        row("model", model_val_nats)
        ng = out[f"ngram_{NGRAM_ORDER}"]["choices"]
        md = out["model"]["choices"]
        # How much of the n-gram's remaining distance to perfect the model closed.
        # Negative means the model is WORSE than the lookup table, which is the
        # single most useful thing this file can tell you.
        out["closed_fraction"] = (ng - md) / (ng - 1.0) if ng > 1.0 else 0.0
    return out


def summary_lines(cmp: dict) -> list[str]:
    """Plain-language rendering. Deliberately states what beating uniform is
    worth, because that is the sentence the old headline left out."""
    order_key = f"ngram_{NGRAM_ORDER}"
    label = {"uniform": "pure guessing (every character equally likely)",
             "frequency": "knowing only which letters are common",
             order_key: f"a lookup table on the previous {NGRAM_ORDER - 1} characters",
             "model": "YOUR MODEL"}
    lines = []
    for key in ("uniform", "frequency", order_key, "model"):
        if key not in cmp:
            continue
        r = cmp[key]
        lines.append(f"  {label[key]:<52} {r['bits_per_char']:5.3f} bits/char"
                     f"   {r['choices']:6.2f} choices")
    if "closed_fraction" in cmp:
        pct = cmp["closed_fraction"] * 100
        if pct < 0:
            lines.append(f"  Your model is WORSE than the lookup table "
                         f"({-pct:.0f}% behind it). More training, more text, or a "
                         f"bigger model — but right now it has not earned its cost.")
        else:
            lines.append(f"  Beating pure guessing is easy — the lookup table above "
                         f"does most of it for free.")
            lines.append(f"  Of what the lookup table could NOT do, your model did "
                         f"{pct:.0f}%. That part needed learning.")
    return lines
