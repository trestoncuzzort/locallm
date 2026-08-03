# srlm-forge — private review copy

**This repository is shared for review, not for release.** It holds the working
record as well as the code: the full commit history, the run logs, and the
project channel. A separate public repository will be created when the work is
ready to be seen, so nothing here is a publication and nothing here is final.

If you read only one section, read **"What is actually true right now."**

---

## What is in here, and which part matters

Two projects share this repository. They share almost no code.

**The forge** (repository root) is the one that matters. A language model writes
code; the code is executed against hidden unit tests; whichever candidate
actually passes becomes `chosen`, a worse one becomes `rejected`, and the pair
becomes preference-training data. **The model never grades itself** — a program
that runs decides.

**The trainer** (`localllm/`) builds a small GPT from random numbers on your own
text. It is finished enough to use, it has a one-click installer, and it is not
the priority. It is here because the two grew up together.

The interesting claim about the forge is not the loop, which is not new. It is
that the domain-specific part is essentially **one function** — the thing that
decides whether a candidate is correct. Sample K candidates, score them
objectively, prefer the winner, emit a pair, route the unsolvable to a
curriculum: none of that shape is specific to code. Any domain where a machine
can decide correctness could use it.

---

## What is actually true right now

Stated plainly, because the difference between these matters more than any of
them individually.

**There is no efficacy result.** Nothing here shows the loop makes a model
better.

**A real training run already happened, and its measurement was worthless.** A
DPO adapter was trained on the real 8B base over 918 verified pairs and exported
with a null baseline. It was then scored against a benchmark that had gone
saturated: `pass@3` came back `0.9` on all ten runs across **both** arms, and the
trained arm landed fractionally *below* null. An instrument at its ceiling
returns the same number whatever you do to the model, so that run measured
nothing. The notes in `OPEN-ITEMS.md` said "nothing has run on the real base",
which was wrong in fact and right in spirit.

**A re-score is in flight, against a replacement benchmark.** 31 tasks screened
to sit inside a `[0.2, 0.8]` band where a change can register, frozen with a
recorded hash, and with a **measured** noise floor: run-level `pass@1` standard
deviation `0.0283`. The design was preregistered before the first replicate
(`data/prereg_track_a_run1.json`): 40 replicates per arm, fixed N, no peeking,
no stopping early because the effect looks good.

**Even when it lands, it cannot settle the question.** One checkpoint has zero
training-seed variance by construction, so the estimate has no slot for the thing
that varies most between training runs. It is a look, not a verdict. The real
arm is two or three seeds, which costs rearranged budget rather than extra
generations.

---

## The scaffolding, which is the part worth reviewing

A self-rewarding loop is unusually good at fooling the person running it. Most of
this repository exists to make that failure loud instead of quiet. **Every
mechanism below was built because the matching failure actually happened here.**

- **The freeze is enforced.** `build_ruler.verify_frozen()` re-hashes every
  benchmark task before any measurement. An earlier version wrote the hash and
  nothing ever read it — a freeze nobody checks is a comment.
- **The data is gated on execution.** `verify_dataset.py` re-runs every pair in
  both directions before training: `chosen` must still pass, `rejected` must
  still fail. Passing writes a receipt of file hashes, and training refuses to
  start without one that matches.
- **The receipt pins the verifier, not just the data.** Weaken an assert and
  every data hash still matches while "verified" quietly means less.
- **The interpreter is pinned.** Ground truth used to be inherited from whichever
  script called the verifier. Red witness: 310 identical completions scored
  **172/310** under one Python and **154/310** under another, all 18
  disagreements running the same way.
- **Claims ship with the evidence that they failed first.** Before a fix, a probe
  is written that fails *because of* the bug, and the failing output is kept. A
  test that passes before and after proves nothing.
- **`verify_claims.py` re-derives the published README's factual claims** and
  exits non-zero when one has drifted. It caught a live one this week.

---

## Where to look, if you want to check something specific

| Question | File |
|---|---|
| What does the loop actually do? | `forge.py` |
| How is the reward decided? | `forge.py` → `verify()` |
| Why should the data be believed? | `verify_dataset.py`, `dataset_gate.py` |
| What is the benchmark, and is it honest? | `build_ruler.py`, `data/ruler_frozen.json` |
| How noisy is the measurement? | `ruler_noise.py`, `screen_tasks.py` |
| What was promised before the run? | `data/prereg_track_a_run1.json` |
| Is the training bank repetitive? | `measure_bank_concentration.py` |
| What is still open and known-broken? | `OPEN-ITEMS.md` |
| The full working record | `instructions.txt` (long; numbered sections) |

`instructions.txt` is the project channel and the single source of truth. It is
append-only and numbered; the most recent sections are the current state.

---

## What is NOT claimed

- Not that this makes models better. That is unmeasured.
- Not that the loop generalises beyond code. The seam exists in principle; only
  one additional domain has been built, and it is not evidence.
- Not that the benchmark is unsaturated for the arms now being scored. 27 of 31
  channels are clearly live and 4 are weak — measured on the base model, not on
  these two.
- Not that the training bank is broad. It is **13 tasks**, effective count
  `9.93`. The preference *contrast* is diverse (767 distinct shapes over 918
  pairs, largest 1.4%), so it is not collapsed — but it is narrow, and nothing
  here transfers beyond that.
- Not that the verifier is a sandbox. It is a subprocess with a filter. Do not
  run it on code from someone you do not trust.
- Not that any coverage list here is exhaustive unless a machine enforces it
  every run.

---

## Open questions where a second opinion would help

1. **Is a single-checkpoint re-score worth reporting at all**, or should the
   budget go straight to a two-or-three-seed arm that can carry a claim?
2. **Task breadth.** 13 tasks is the binding limit. Pool-derived tasks yield
   2.46x more pairs per generation, which is the obvious lever — is widening the
   bank the right next spend, ahead of any further measurement?
3. **Whether the data-diversity question is the more publishable one.** Verified
   correctness and data diversity are separate variables, and that is testable
   here without a training run.

---

## Running it

Requires a local Ollama with the base model, and `.venv-train` (Python 3.11 with
torch) for anything that trains or verifies. Setup notes for the trainer side
live in `localllm/README.md`.

```
python forge.py                     # generate + verify preference pairs
python verify_dataset.py            # the gate: re-verify every pair, write the receipt
python build_ruler.py verify        # check the frozen benchmark still hashes
python ruler_noise.py measure --runs 40 --model <tag>   # score against the ruler
python train_native.py              # refuses to start without a matching receipt
```

`data/` holds the pairs, the frozen ruler, the receipt and the preregistration.
`council/` holds run logs and analysis output — it is this project's own output
directory, not a review body.
