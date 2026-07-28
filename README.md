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

**The left half of that diagram has run; the right half has not.** Generation and
verification have produced 1,234 gate-verified pairs over 284 logged generation
rounds (`data/round_stats.jsonl`).
No training step has ever executed, so no adapter and no `llama3-forged` model
exist — the loop has not yet been closed end to end. Details in the status
paragraph below and in `OPEN-ITEMS.md`.

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

**Status: implemented and data-verified; parked before any gradient step.** No
training run has been executed — there is no adapter directory and no
`run_meta.json` in this repository, and `export_adapter.py`, referenced by
`train_native.py`, does not exist yet. Every training hyperparameter below is
configured, not exercised.

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
