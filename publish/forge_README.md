# srlm-forge

**A self-improvement loop for language models where the reward is a program that runs, not a model's opinion.**

The model writes code. The code is executed against hidden unit tests. Whichever
candidate actually passes becomes `chosen`, a worse one becomes `rejected`, and
the pair becomes preference-training data. The model never grades itself.

That idea is not new. What this repository is actually about is the **scaffolding
underneath it** — the machinery that stops a self-rewarding loop from quietly
grading its own homework and reporting a number that means nothing.

---

## Why the scaffolding is the point

A self-rewarding loop is unusually good at fooling the person running it.

Every part of it is a place where a number can look real and be worthless. The
verifier can pass code for the wrong reason. The benchmark can sit at its
ceiling and report movement that is noise. The training data can be one program
renamed nine hundred times. The evaluation can inherit a different Python than
the one that generated the data, and score the same bytes differently. Each of
those produces a plausible number and a false conclusion.

Most of this repository exists to make those failures **loud instead of quiet**.
Every mechanism below was built because the corresponding failure actually
happened here and was caught.

### The ruler is frozen, and the freeze is enforced

The benchmark is a fixed set of tasks with a recorded `sha256` over their
contents. `build_ruler.verify_frozen()` re-hashes every task from its stored
payload before any measurement runs, so a benchmark that has drifted refuses to
be used rather than silently reporting on a different set.

This exists because an earlier version wrote the hash and nothing ever read it.
A freeze nobody checks is a comment.

The first benchmark here **died of saturation** and had to be replaced. It sat at
`pass@20 == pass@3 == 0.9000` with 7 of 10 tasks pinned at ceiling — an
instrument that returns the same number whatever you do to the model. Its
replacement was screened for tasks that land inside a `[0.2, 0.8]` band, where a
change can actually register, and its noise floor was **measured** rather than
assumed: run-level `pass@1` standard deviation `0.0283` over null replicates.

**A benchmark without a measured noise floor cannot support a claim.** If you do
not know how much your number moves when nothing changes, you cannot know
whether it moved because of your training.

### The data is gated on execution, not on trust

`verify_dataset.py` re-runs **every** preference pair through the verifier in
both directions before any training: `chosen` must still pass, `rejected` must
still fail. A `rejected` that passes is preference noise pointing the wrong way.

Passing writes a **receipt** recording the `sha256` of every file verified, and
`train_native.py` refuses to start without one that matches its inputs. Rebuild
a dataset and its hash changes, the receipt stops covering it, and training
stops. That is what makes "verified before training" a mechanism rather than a
habit.

The receipt also pins the **verifier itself** — not just the data. Weaken an
assert, loosen a filter, shorten a timeout, and every data hash still matches
while the meaning of "verified" silently changes. Whole files are hashed,
deliberately: choosing which parts of a verifier are semantic is exactly the
mistake this is guarding against.

Numbers a reader can check against the code and the shipped artifacts:

Latest gate run: **1,279 unique pairs, 0 violations**, covering 2,200 rows across
`dpo_pairs.jsonl` (1,244), `dpo_pairs_capped.jsonl` (918 — the training file) and
`repair_pairs.jsonl` (38). Candidates run in a `python -I` subprocess under an **8-second timeout** with a
coarse banned-operation filter.

The training objective is DPO **plus** an NLL term, which is easy to claim and
easy to get silently wrong, so it is settled by whether `nll_loss` appears in the
metrics at all:

| `rpo_alpha` | `loss` | `nll_loss` |
|---|---|---|
| `1.0` | 1.0959 | **0.4036** |
| unset | 0.6914 | *absent* |

`0.6914 + 0.4036 = 1.0950` against an observed `1.0959` — the NLL term is added
exactly as documented. Recorded in `data/smoke_rpo_alpha_result.json`.

### The interpreter is pinned, because ground truth was inherited

The verifier used to launch `[sys.executable, ...]` — so ground truth depended on
whichever script happened to call it.

Red witness: 310 identical completions, replayed under both interpreters, scored
**172/310 on one and 154/310 on the other**. All 18 disagreements ran the same
direction. The cause was deferred annotation evaluation — code omitting
`from typing import List` fails on one version and passes on the next:

```python
def f(x: List[int]) -> int: ...   # Python <=3.13 -> NameError
                                  # Python 3.14   -> exits 0
```

The interpreter is now pinned in one place and recorded in the receipt. It
refuses to fall back to the launching interpreter, because returning
`sys.executable` silently would restore the defect while every artifact went on
claiming a pin was in force — quietly wrong is worse than failing.

### Claims ship with the evidence that they failed first

The rule this project runs on: **before a fix, write a probe that fails because
of the bug, and keep the failing output.** A test that passes before and after
proves nothing. Claims shaped like "this whole class is handled" ship with the
failing-then-passing pair, or they are labelled `pending`.

`verify_claims.py` re-derives factual claims about this pipeline from the
repository and exits non-zero if any has drifted. A claim-checker only the
author can run is a promise; the point is that a reader can settle it without
trusting anyone.

It earns its keep. The day this repository was split out, a fix to the data gate
moved the receipt from 1,269 verified pairs to 1,279 — and the checker
immediately failed the published page for still quoting the old number. Nobody
had noticed. **Its claim list covers the pipeline's own figures, not yet every
sentence on this page**; extending it to cover the rest is open work, and until
it does, treat the unchecked prose here as prose.

### Preregistration, because the analysis is decided before the number exists

`data/prereg_track_a_run1.json` fixes the arms, the metric, the replicate count,
the statistical test and the stopping rule — and is committed **before** the
first scoring run. It also records, in the same file, what the experiment
**cannot** show.

Fixed N, no peeking, no stopping early because the effect looks good.

---

## Honest status

**There is no efficacy result.** Nothing here demonstrates that this loop makes a
model better.

A DPO adapter has been trained on the real 8B base over 918 verified pairs, and
exported alongside a null baseline and an adapter-is-live positive control. Its
first evaluation was scored on the saturated benchmark described above and is
therefore uninterpretable — both arms sat at the ceiling, and the trained arm
came in fractionally *below* null. A re-score against the replacement benchmark
is what the preregistration covers.

Even when that lands, it will not support a claim about DPO in general: one
checkpoint has **zero training-seed variance by construction**, so the variance
of the estimate has no slot for the thing that varies most between training
runs. A single-checkpoint result is a look, not a verdict.

Known limits, stated rather than implied:

- The training bank is **13 tasks**, effective task count `9.93`. Structural
  diversity of the preference *contrast* is high (767 distinct shapes over 918
  pairs, largest 1.4%), so the bank is not collapsed — but it is **narrow**, and
  nothing here transfers beyond that task distribution on this evidence.
- The verifier is a subprocess with a filter, **not a sandbox**. Do not run it on
  code from someone you do not trust.
- The receipt is unsigned. It defends against drift and accident, not against
  someone editing the receipt.
- Everything is measured on one machine, one base model, one language.

---

## What this is for

The domain-specific part of this loop is essentially **one function**: the thing
that decides whether a candidate is correct. Sampling K candidates, scoring them
objectively, preferring the winner, emitting a preference pair and routing
unsolvable tasks to a curriculum — none of that shape is specific to code.

The interesting direction is any domain where a machine can decide correctness,
and the scaffolding above is what would have to travel with it. An objective
reward is worth little without the machinery that keeps it honest.

---

## License

**All rights reserved.** See [LICENSE](LICENSE).

This source is published so it can be read, reviewed and cited. That is not a
grant of any right to use, copy, modify or redistribute it; for anything beyond
reading, ask. Task data derived from AceCode-89K remains under its own MIT terms
and is attributed in the licence file.
