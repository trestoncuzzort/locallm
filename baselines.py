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

    An unseen context falls back to add-1 over the whole alphabet, which is the
    same floor `uniform_nats` reports — a context the model has never seen is a
    context this baseline cannot help with, and pretending otherwise would
    understate the baseline.
    """
    k = max(order, 1)
    if len(train) <= k or not val:
        return uniform_nats(vocab_size)

    # counts[ctx][nxt] via two flat Counters: the full n-gram, and its context.
    full = Counter(zip(*(train[i:] for i in range(k))))
    ctx = Counter(zip(*(train[i:] for i in range(k - 1)))) if k > 1 else None

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
