# FINDING — LoRA initialisation is unseeded; two identical runs land in orthogonal subspaces

**Date:** 2026-08-05 · **Machine:** RTX 4090, `.venv-train` Python 3.11.9, torch 2.6.0+cu124,
trl 0.12.2, transformers 4.46.3, peft 0.20.0 · **Branch:** `replication/2026-08-04`

---

## The claim

Running `python train_native.py` **twice on the same machine, with the same data, the same code, and
the same recorded seed** produces two adapters that are **orthogonal in weight space and equal in
magnitude**. The divergence is present in the *initialisation*, not only in the optimisation: the
`lora_A` factors — which are supposed to be seeded — share no direction between runs.

This is not a claim that training is chaotic. It is narrower and more fixable: **the seed never
reaches LoRA initialisation, so every run starts from a different random subspace.**

## The measurements

Two adapters, `poscontrol/adapter_replication` and `poscontrol/adapter_replication2`, produced by the
identical command minutes apart on the same box.

**Effective update `dW = (B@A)·(alpha/r)`, 224 layers, float64** (`poscontrol/compare_adapters.py`):

| | value |
|---|---|
| mean cosine | **0.004177** (sd 0.004431, min −0.008700) |
| mean magnitude ratio | **1.001948** |
| mean relative difference | **1.412689** |

√2 = 1.414214. Two equal-magnitude orthogonal vectors must give exactly that. The three metrics are
mutually consistent: √(1 + 1.001948² − 2·1.001948·0.004177) = 1.4127.

**Factor-level split** (`poscontrol/init_vs_training.py`):

| family | bitwise identical | mean cosine | mean rel diff |
|---|---|---|---|
| `lora_A` (seeded init, then trained) | **0 / 224** | −0.000474 | 1.414451 |
| `lora_B` (init exactly zero, then trained) | 0 / 224 | −0.001459 | 1.415996 |

`lora_A` differing is the decisive line. B starts at zero in every run, so B *must* differ if training
differs — that alone would be consistent with mere kernel non-determinism. A is drawn from a seeded
RNG before a single step is taken. **A being orthogonal across runs means the runs did not start from
the same place.**

**Both runs converged equally well.** Run 1: `train_loss 0.5821`, runtime 753.7 s. Run 2:
`train_loss 0.5831`, runtime 757.7 s. Reward accuracies 0.925–0.975 in both. Two orthogonal solutions
of equal magnitude and equal quality.

## The instrument was verified before these numbers were trusted

- **Self-comparison control:** the same tool on the same adapter twice returns
  `mean cos=1.000000 (sd 0.000000, min 1.000000), ratio=1.000000, rel=0.000000` — exact, zero variance.
- **Known-transform control:** against the author's 50,000× amplified adapter it recovers
  `ratio ≈ 50000` with cosine 1.0 and confirms all 224 `lora_B` scaled exactly 50000.0 and all 224
  `lora_A` scaled 1.0.
- **A defect this control caught:** in float32 the cosine returned **1.0049** — impossible, cosine
  cannot exceed 1. Fixed by computing in float64. Every number above is post-fix. Had the control not
  been run on a known answer, an out-of-range metric would have been reported as a result.

## The cause, at the byte

`train_native.py` **contains no seeding call of any kind** — verified:
`grep -nE "set_seed|manual_seed|seed" train_native.py` returns nothing. The `seed: 42` recovered from
the author's `training_args.bin` is HuggingFace's `TrainingArguments` **default**, not an authorial
choice, and empirically it does not govern the LoRA factors: `peft_cfg = LoraConfig(...)` is built at
`train_native.py:145` and handed to `DPOTrainer` at `:197`, and the A matrices it produces differ
completely between runs.

**NOT CLAIMED:** the exact call-order inside TRL/PEFT that leaves the init unseeded is not traced
here. What is demonstrated is the *effect* — A orthogonal across runs of the same command — and the
absence of any seeding call in the script. The precise interaction is worth naming before proposing a
fix as correct.

## Why it matters to the paper

The draft states: *"A single training run has zero training-seed variance by construction."* That is
true only in the sense that one run has no variance to measure. What this shows is stronger and
worse: **the run has no fixed seed at all in the way that matters**, so the adapter under test is one
draw from an uncontrolled distribution of orthogonal, equally-performing solutions. The single
checkpoint is not merely unreplicated — it is not even the checkpoint the same command would produce
again.

This does not overturn the null result. The measurement replicated cleanly against a *different*
adapter served identically (see `REPLICATION-RESULT-2026-08-05.txt`). It sharpens what the null is
about: the draft's own Discussion already says *"The correct design spends the same generation budget
across two or three independently seeded training runs."* This supplies the evidence for how much
that matters, and shows the seeds would need to be set first.

## What would close this

1. Add an explicit `set_seed(...)` before the model is wrapped, re-run twice, and confirm `lora_A`
   goes bitwise-identical. That converts the claim from "unseeded" to "seeded, and here is the
   residual non-determinism," which is the honest end state.
2. With initialisation pinned, re-measure `dW` agreement to isolate kernel-level non-determinism
   (bf16 accumulation order, the 8-bit optimiser, non-deterministic CUDA kernels — none of which
   `torch.use_deterministic_algorithms(True)` is currently requested for).
3. Train N≥3 adapters and evaluate each. Orthogonal weights with equal loss say nothing about whether
   benchmark scores agree; that is a separate measurement and it is the one the null actually needs.

**NOT MEASURED HERE:** whether the two orthogonal adapters score the same on the benchmark. Only
`adapter_replication` was evaluated (40 replicates, +0.065 pp vs null). `adapter_replication2` has not
been served or scored.
