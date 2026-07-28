# srlm-forge

A failure-driven self-rewarding loop that trains a local model to fix its own
mistakes. The model proposes; **unit tests decide**; preferences are learned
from the verdict. No ungrounded self-judging, so it improves instead of drifting.

## Benchmark findings (Track B — `localllm`, the from-scratch trainer)

These are results from the from-scratch model in `localllm/`. They say nothing
about the DPO pipeline below, which has never been trained.

- **Splitting the corpus by document, not by position, removes most contamination.**
  The old positional split put 82.6% of validation content inside training; the
  document-aware split drops that to 1.5%. Separately, the detector that measures
  this is an exact-substring scanner with measured recall of 100% on verbatim
  copies, 90% on reformatted text, and **0% once identifiers are renamed**
  (`localllm/leakage.py`). A CLEAN verdict means nobody copy-pasted — it does not
  mean validation is independent.
- **The learning-rate sweep passed its preregistered check** (RTX 4080, CUDA). The
  width-appropriate LR improved mean *train* loss from 0.1495 to 0.1056 over 2000
  steps — a gap of 0.0439 across 5 seeds with no overlap in the seed ranges.
- **A faster 800-step profile also passed**, reaching lower train loss sooner:
  mean 0.1884 versus 0.2937 for the baseline. Its own verdict string records that
  this is a *speed* claim, not the canonical effect size.
- **GPU vs CPU on the default 3.18M model: ~13.6s versus ~324.2s for 2000 steps.**
  Both are extrapolations from a short timing window — 200 measured steps on CUDA,
  25 on CPU — not wall-clock times of full 2000-step runs.

The LR and device numbers come from `localllm/exp_lr_width_result.json`,
`exp_lr_width_result_fast.json` and `bench_device_result.json`, all committed here.
The 82.6% / 1.5% contamination figures are recorded in `localllm/README.md`; there
is no separate result file for them.

## The loop

```
forge.py                          train_dpo.py
--------                          ------------
actor  -> K candidates
verify -> unit tests = reward -->  DPO on (prompt, chosen, rejected)
pair   -> chosen vs rejected  -->  QLoRA adapter -> GGUF
fails  -> failures.jsonl                |
   ^                                    v
   +------ better actor <-- ollama create llama3-forged
```

`failures.jsonl` is the point: the tasks no candidate could solve are the
curriculum for the next round and the seed for training from scratch on
current failures.

**The left half of that diagram has run; the right half has been smoke-tested
only.** Generation and verification have produced 1,234 gate-verified pairs over
284 logged generation rounds (`data/round_stats.jsonl`).
Training has been executed once, on a small stand-in model, purely to prove the
path runs — no run on the real base, no `llama3-forged` model, and no
re-injection back into the actor. **The loop has never been closed end to end.**
Details in the status paragraph below and in `OPEN-ITEMS.md`.

## The DPO pipeline & objective verification (Track A)

While the from-scratch model (Track B) is the focus of the GUI, this repository
also contains an automated Direct Preference Optimization (DPO) pipeline built to
keep the reward signal out of a language model's hands entirely.

Instead of asking a larger model to grade candidate outputs, the pipeline grounds
its reward in execution:

* **Isolated subprocess verification.** `forge.py` samples K candidates from a
  local instruction-tuned model via Ollama and runs each against unit tests the
  model never sees, in a `python -I` subprocess under an 8-second timeout with a
  coarse banned-operation filter (`forge.py:74-78`, `:392-394`). This is
  defense-in-depth, **not a sandbox** — see the safety notes below.
* **Correctness-gap preference pairs.** A `(prompt, chosen, rejected)` pair is
  emitted only when `chosen` passes every assert and `rejected` demonstrably
  fails (`forge.py:481-485`). The weaker "conciseness" pair type — preferring the
  shorter of two passing solutions — is a length-bias reward hack and is gated off
  (`EMIT_CONCISENESS = False`, `forge.py:62`); the one legacy pair of that kind was
  removed by `clean_dataset.py`, with the pre-clean file preserved as
  `data/dpo_pairs.raw.jsonl`. What makes the signal hard to game is that the tests
  are fixed and held out of the prompt — not any inherent property of unit tests.
* **A bidirectional gate that training cannot skip.** `verify_dataset.py`
  re-executes both sides of every pair: `chosen` must still pass, `rejected` must
  still fail. It then writes a receipt recording the sha256 of each file it
  verified, and both trainers refuse to start unless a receipt matches the exact
  bytes they are about to load (`dataset_gate.py`). Edit a dataset and the hash
  stops matching, so training halts until it is re-verified. There is no bypass
  flag.

Latest gate run: **1,269 unique pairs, 0 violations**, covering 2,190 rows across
`dpo_pairs.jsonl` (1,234), `dpo_pairs_capped.jsonl` (918, the run-1 training file,
sha256 `85fc0bdc…`) and `repair_pairs.jsonl` (38). Unique is below the 1,272 row
total because 3 pairs appear in both `dpo_pairs.jsonl` and `repair_pairs.jsonl` —
they are verified once and would be seen twice per epoch only under
`--include-repair`, not in the default run-1 configuration.

**Status: the pipeline runs end to end; no result has been produced.** The
training path has been exercised on a small stand-in model
(`Qwen/Qwen2.5-0.5B-Instruct`, 10 optimizer steps on 64 gate-verified pairs),
which wrote a real adapter and `run_meta.json`. That is a *smoke test*: it shows
the machinery executes. **No run on the real base model has happened, no
held-out evaluation has been scored, and no claim is made that DPO improves
anything.**

The export path now exists and is verified: `export_adapter.py` converts the LoRA
to GGUF with llama.cpp and applies it through Ollama's `ADAPTER` directive against
the **untouched** base — nothing is ever merged. Its `--verify` mode ran clean on
the smoke adapter: conversion exit 0 with tensor count 336 = 336, both the adapted
model and the null baseline created, a coherent spot check, and — the check that
matters — an adapter-is-live control. Scaling the LoRA `B` matrices by 50,000×
collapses output into gibberish (similarity 0.0238 against the null baseline),
which is what proves Ollama is genuinely applying the adapter rather than parsing
the directive and ignoring it. Full record in `data/export_acceptance_result.json`.

That smoke test did settle one thing that source-reading could not. TRL adds the
NLL term only when `rpo_alpha` is set, so the question "is this actually DPO+NLL
or silently vanilla DPO?" is answered by whether `nll_loss` appears in the
training metrics. Run with `rpo_alpha=1.0` it does; run with it unset, the key is
absent entirely — and the losses differ by exactly that term
(`0.6914 + 0.4036 = 1.0950` against an observed `1.0959`). Both runs are recorded
in `data/smoke_rpo_alpha_result.json`.

**What would be needed for an efficacy claim**, none of which has been done: a run
on the real base under a prereg signed *beforehand*; `eval.py`'s frozen held-out
set scored before and after; a null baseline (the same Modelfile with the
`ADAPTER` line removed, so "the adapter did something" is not confounded with
"the export path did something"); and k≥5 seeds with test-retest sigma reported
separately from between-config sigma. The ruler's measured cross-run std is
**0.0199** over 57 logged runs, putting the honest 95% bar at **±0.055** — and it is
saturated besides: 6 of its 10 tasks scored 1.000 in every one of those runs. `eval.py`'s docstring
also concedes its task shapes may overlap the base model's pretraining, making it
a *relative* instrument — iteration-N against iteration-0 on a frozen set. It
cannot support a statement like "the model is N% better at coding."

**A configuration defect found by reading the library source.** TRL's `rpo_alpha`
defaults to `None`, and in that state the NLL branch of `DPOTrainer` never runs
(`trl/trainer/dpo_config.py:178`; `dpo_trainer.py:1291-1299`, `:1337-1338`). Our
trainer had never set it, so a configuration labelled "DPO+NLL" would in fact have
run vanilla DPO — the NLL term is what counters chosen-likelihood collapse on the
low-edit-distance pairs this pipeline produces (Pal 2024, arXiv:2402.13228; Pang
2024, arXiv:2404.19733). Comparing our `DPOConfig` against the installed TRL 0.12.2
source caught it; the fix is `rpo_alpha=1.0` at `train_native.py:115`. **This was a
defect in our configuration, not in TRL** — the library behaves as documented, and
nothing in TRL, PEFT (0.14.0) or transformers (4.46.3) is patched: both TRL files
carrying that path hash byte-identical to the published wheel per its own
`RECORD`.

## What you need to make it run

1. **Ollama up with a model** (not currently reachable on this box):
   ```
   ollama serve            # if not already running
   ollama pull llama3:8b-instruct-q4_K_M
   ```
2. **Generate data** (works on the system Python 3.14; only needs `requests`):
   ```
   python forge.py
   ```
   → `data/dpo_pairs.jsonl` and `data/failures.jsonl`
3. **Verify the data** (required — training refuses without a current receipt):
   ```
   python verify_dataset.py
   ```
   → re-runs every pair in both directions and writes
   `data/dataset_verification.json`. Re-run it whenever a dataset changes.
4. **Train** — in a *separate* Python 3.10–3.12 env with CUDA torch (the
   system 3.14 can't run Unsloth/torch). See the header of `train_dpo.py`.

## VRAM budget (16 GB card)

- Generation: only the 4-bit actor is resident (~5–6 GB for an 8B). `keep_alive`
  keeps it warm between tasks and releases it on exit.
- Training: 8B QLoRA fits in ~10–12 GB. Lower `MAX_SEQ` or batch if you OOM.

## Safety notes (read before scaling)

- `forge.py` executes model-generated code in an isolated subprocess (`python -I`,
  timeout) with a coarse banned-op filter. That is **defense-in-depth, not a real
  sandbox.** For untrusted or large runs, execute inside a container or a
  throwaway VM.
- Tasks are pure-function coding problems on purpose: the reward is objective and
  the blast radius is small. Keep new tasks in that shape and the loop stays sound.
