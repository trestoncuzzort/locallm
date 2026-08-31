"""Tests for baselines.py. `python test_baselines.py`, no framework.

THE CLAIM UNDER TEST is not "the arithmetic runs". It is that these numbers can
tell a model that learned something from one that did not — which is the whole
reason the file exists. So the tests below are ordered by how much they would
hurt if they were wrong:

  1. the baselines rank in the only order they can (uniform worst, longer
     context better) — if this breaks, every comparison built on it is noise;
  2. on text with STRUCTURE the n-gram beats letter frequency by a wide margin,
     and on text with NONE they converge — this is the red witness: a broken
     n-gram that ignored its context would pass test 1 and fail here;
  3. `closed_fraction` goes NEGATIVE when the "model" is worse than the lookup
     table, because a comparison that cannot deliver bad news is decoration.
"""
import math
import random
import sys

import baselines

FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if detail:
        print(f"         {detail}")
    if not ok:
        FAILS.append(name)


def structured_text(n: int = 60_000) -> str:
    """Repetitive, strongly-ordered text: a trigram should do very well here."""
    words = ["the cat sat on the mat. ", "the dog ran to the park. ",
             "a boy saw the cat. ", "the girl ran home. "]
    rng = random.Random(1337)
    return "".join(rng.choice(words) for _ in range(n // 20))


def unstructured_text(n: int = 60_000) -> str:
    """Same characters, no order at all: context cannot help, so the n-gram
    should collapse toward the frequency model."""
    rng = random.Random(1337)
    src = structured_text(n)
    chars = list(src)
    rng.shuffle(chars)
    return "".join(chars)


def split(text: str) -> tuple[str, str, int]:
    cut = int(len(text) * 0.9)
    return text[:cut], text[cut:], len(set(text))


print("Scoring dumb models against each other, so 'your model learned something'")
print("is a comparison rather than an assertion.\n")

# ---------------------------------------------------------------- 1. ordering
tr, va, V = split(structured_text())
uni = baselines.uniform_nats(V)
freq = baselines.frequency_nats(tr, va, V)
bi = baselines.ngram_nats(tr, va, V, order=2)
tri = baselines.ngram_nats(tr, va, V, order=3)

check("uniform is the worst possible reference", uni > freq,
      f"uniform {uni:.4f} > frequency {freq:.4f} nats")
check("knowing the previous character beats knowing none", freq > bi,
      f"frequency {freq:.4f} > bigram {bi:.4f} nats")
check("knowing two characters beats knowing one", bi > tri,
      f"bigram {bi:.4f} > trigram {tri:.4f} nats")
check("uniform equals log(vocab) exactly", abs(uni - math.log(V)) < 1e-12,
      f"log({V}) = {math.log(V):.6f}")

# --------------------------------------------------- 2. RED WITNESS: context
# A trigram that ignored its context would still rank below frequency on
# test 1 (more smoothing mass), so test 1 alone does not prove it reads the
# context. This does: the SAME characters, shuffled, must destroy its edge.
s_tr, s_va, s_V = split(structured_text())
u_tr, u_va, u_V = split(unstructured_text())
edge_structured = baselines.frequency_nats(s_tr, s_va, s_V) - \
    baselines.ngram_nats(s_tr, s_va, s_V)
edge_shuffled = baselines.frequency_nats(u_tr, u_va, u_V) - \
    baselines.ngram_nats(u_tr, u_va, u_V)
check("the n-gram's advantage comes from CONTEXT, not from smoothing",
      edge_structured > 0.5 and edge_structured > edge_shuffled * 3,
      f"advantage over frequency: structured {edge_structured:.4f} nats, "
      f"same characters shuffled {edge_shuffled:.4f} nats")

# ------------------------------------------- 3. it must be able to say 'worse'
good = baselines.compare(s_tr, s_va, s_V, model_val_nats=tri * 0.5)
bad = baselines.compare(s_tr, s_va, s_V, model_val_nats=tri * 2.0)
check("a model better than the lookup table closes a positive fraction",
      good["closed_fraction"] > 0,
      f"closed_fraction = {good['closed_fraction']:+.3f}")
check("a model WORSE than the lookup table reports negative, not zero",
      bad["closed_fraction"] < 0,
      f"closed_fraction = {bad['closed_fraction']:+.3f}")
check("the bad-news path says so in words",
      any("WORSE" in ln for ln in baselines.summary_lines(bad)),
      [ln.strip() for ln in baselines.summary_lines(bad) if "WORSE" in ln][:1])

# ----------------------------------------------------------- 4. unit sanity
row = good["model"]
check("bits/char is nats/char divided by ln 2",
      abs(row["bits_per_char"] - row["nats_per_char"] / math.log(2)) < 1e-12)
check("'choices' is exp of the loss, matching the studio's plot",
      abs(row["choices"] - math.exp(row["nats_per_char"])) < 1e-9)

# ------------------------------------------------------------- 5. edge cases
check("an empty holdout does not divide by zero",
      isinstance(baselines.ngram_nats("abcabc", "", 3), float))
check("a corpus shorter than the context falls back to uniform",
      abs(baselines.ngram_nats("ab", "ab", 3) - baselines.uniform_nats(3)) < 1e-12)

print()
if FAILS:
    print(f"{len(FAILS)} failed: {', '.join(FAILS)}")
else:
    print("=" * 64)
    print("all tests pass — and the n-gram's edge survives only on ordered text")
    print("=" * 64)
sys.exit(1 if FAILS else 0)
