# START HERE

**For:** the srlm-forge author, and whatever AI assistant is helping.
**From:** the replication run, 2026-08-04 → 2026-08-05, on separate hardware (RTX 4090).
**What this is:** your experiment, independently reproduced. Data, scripts, and findings.

---

## THE ONE-PARAGRAPH VERSION

Your null result is **real and correctly measured**. Your adapter produces no
improvement — confirmed four separate times, twice against a control run in the same
session. But retraining from **your code, your data, your hyperparameters** produces a
**+10 percentage point** improvement, three times out of three. So the null is a null
about *that adapter*, not about the method. Your paper already said exactly this
(*"cannot support a claim about DPO as a method — it characterizes this adapter"*), and
that sentence turns out to be the most important one in the draft.

---

## THE NUMBERS

Pooled null baseline: **n=70, mean 0.5066**, measured across three separate sessions
(0.5021 / 0.5071 / 0.5183 — the instrument is stable to ~1.6 pp).

| Adapter | Effect vs null | t |
|---|---|---|
| **Yours** (Aug 4) | −0.48 pp | −0.60 |
| **Yours** (Aug 5, same-session control) | +0.00 pp | 0.00 |
| Retrain 1 | **+9.66 pp** | 11.94 |
| Retrain 2 | **+10.95 pp** | 13.64 |
| Retrain 3 | **+9.94 pp** | 9.63 |

The three retrains are **statistically indistinguishable from each other** (pairwise
−1.29, −0.28, +1.01 pp; all non-significant) — *even though they are orthogonal in
weight space* (mean cosine 0.004, i.e. sharing no direction at all). Random luck would
scatter them. It doesn't. Something **systematic** differs between your training run and
this one.

---

## FOUR THINGS THE PAPER NEEDS

**1. Withdraw the export-path finding.** It's in the abstract, its own Results section,
and the conclusion. It's an artifact, two ways over: (a) your null arm **is** the base
model — same weights blob, same template, same parameters, no ADAPTER line — so it
traverses no export path and can't have cost anything; (b) the base reference was scored
with the **old greedy-anchored sampler** (greedy draws score +12.76 pp higher) and pools
rows from two different verifier states (p=1.9e-8). Matched on sampler and verifier, the
3.3–3.8 pp gap becomes +0.71 pp (p=.48) and +0.16 pp (p=.86). It disappears.
Root cause is in code: `analyze_run1.py` groups by model name alone, pooling exactly what
`ruler_noise.py` refuses to pool for the arms.

**2. "Zero training-seed variance by construction" understates it.** `train_native.py`
has **no seeding call at all** — `grep -nE "set_seed|manual_seed|seed"` returns nothing.
The `seed: 42` in your `training_args.bin` is HuggingFace's *default*, and it does not
reach LoRA initialization: across two runs of the identical command, `lora_A` is **0/224
bitwise identical**. The runs don't drift apart during training — they never start from
the same place.

**3. The null replicates — say so.** Different hardware, different session, arms
interleaved: your +0.55 pp (p=.51) vs our **+0.07 pp (p=.94)**, each estimate inside the
other's confidence interval.

**4. Limitation 4 is dischargeable.** All **31 of 31** benchmark tasks are responsive *at
the arms' operating point* — no task at 0.00 or 1.00 for any arm. You could only verify
that against the base model before.

---

## THINGS YOU CAN NOW FILL IN (recovered from your own artifacts)

Your assistant reported the training config unrecoverable because the console log is
gone. It isn't — it's in `dpo_adapter_native/training_args.bin`:

- batch 2 × grad-accum 8 = **effective batch 16**
- 1 epoch, lr 5e-6, cosine schedule
- **warmup_ratio 0.1 WITH warmup_steps 0** — state both; the derived-params file lists
  only `warmup_steps = 0`, which reads as "no warmup" and is misleading
- beta 0.1, rpo_alpha 1.0, max_length 1024, max_prompt_length 512, bf16, adamw_bnb_8bit
- **seed 42** (HuggingFace default, not set by anyone)
- **Total optimizer steps = 57** — 918 pairs ÷ 16, confirmed by the live trainer

Also settled: the adapter is **not** zero (224/224 LoRA B matrices non-zero, mean
‖dW‖_F ≈ 0.020), and the two arms are provably different models (the served adapter blob
name equals the SHA-256 of `adapter.gguf`; a per-task permutation test separates them at
p < 5e-5).

---

## REPRODUCIBILITY PROBLEMS TO DISCLOSE

- **`train_native.py` will not run on a fresh install.** `rpo_alpha` was removed from
  `DPOConfig` in later TRL. You need `trl==0.12.2`, which pins `transformers==4.46.3`.
  The paper names no TRL version anywhere — it should.
- **Appendix B's `python build_ruler.py verify` does not exist.** The CLI only accepts
  `nominate | confirm | freeze`. Anyone following your reproduction section fails at
  step one.
- **Raw completions were never retained**, so exact-output agreement between arms is not
  computable — for your run or ours.
- **`run_meta.json` records every hyperparameter but zero library versions.** That's why
  the PEFT version had to be inferred from field counts.

---

## THE FILES

Read in this order:

| File | What it is |
|---|---|
| **`START-HERE.md`** | this file |
| **`PAPER-CORRECTIONS-2026-08-05.md`** | section-by-section against your draft with proposed replacement text ⚠ written before the last two results — this file supersedes it where they disagree |
| `FINDING-unseeded-lora-init-2026-08-05.md` | the unseeded-init finding, with the instrument controls |
| `ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md` | the export-path artifact, the 31/31 task table, arms-are-different |
| `RESIDUALS-2026-08-04.md` | six reproducibility defects, each with a reproduction and a discharge condition |
| `FINAL-SUMMARY-2026-08-05.txt` | the numbers table above |
| `REPLICATION-RESULT-2026-08-05.txt` | your run vs the replication |
| `CONTROL-VERDICT-2026-08-05.txt` | the same-session control that ruled out instrument drift |
| `data/ruler_noise.jsonl` | **the data** — your rows plus 215 new replicate rows |
| `*.py` | every analysis, runnable |

---

## FOR THE AI ASSISTANT — HOW TO USE THIS

**Everything here is reproducible from the data. Run the scripts; don't take the numbers
on trust.** From the repo root, with the training venv:

```
.venv-train\Scripts\python.exe poscontrol\final_summary.py        # the headline table
.venv-train\Scripts\python.exe poscontrol\compare_replication.py  # original vs replication
.venv-train\Scripts\python.exe poscontrol\control_verdict.py      # the same-session control
.venv-train\Scripts\python.exe poscontrol\fingerprint_audit.py    # verifier provenance per arm
```

`compare_replication.py` reads the original arms from a transfer package path that exists
only on the replication machine — set `SRLM_ORIG_ROWS` to your own
`data/ruler_noise.jsonl` if you want to run it locally.

**Four rules that made this work, and that the numbers depend on:**

1. **Never compare arms measured in different sessions without a same-session control.**
   That single mistake is what produced the false export-path finding in the paper. When
   the retrains came in 10 pp high, the first move was a fresh null in the *same* session
   — because a 10 pp jump across sessions is exactly what an instrument shift looks like.
2. **Verify a measurement tool on a known answer before trusting it on an unknown one.**
   The adapter-comparison script initially returned cosine 1.0049 — mathematically
   impossible — caught only because it was run against an adapter compared with itself
   (must return exactly 1.0) and against a 50,000× amplified control (must return
   50,000). Fixed by computing in float64.
3. **Check that every arm carries the same verifier fingerprint before comparing them.**
   `fingerprint_audit.py` does this. The paper's export-path error was invisible for
   months precisely because the original rows record only the interpreter, not the
   verifier.
4. **Interleave arms; don't run them as sequential blocks.** The original run scored one
   arm for three hours and then the other, which makes session drift mathematically
   inseparable from the arm effect. `run_interleaved.py` alternates.

**What NOT to claim from this bundle:**

- It replicates the **measurement**, not the training. The replication arms serve *your*
  adapter, so training-seed variance is still zero there.
- **Which stack variable is worth 10 pp is NOT isolated.** Leading suspect is the library
  stack (your `adapter_config.json` predates the `peft_version` field; ours records
  0.20.0), but establishing it needs a version matrix, not another retrain. Do not write
  that PEFT caused it.
- Whether three orthogonal adapters would still agree on a *different* benchmark is
  untested.

**Adapter binaries are not included** — they're hundreds of megabytes and reproducible
from the code plus the gated corpus, which is the convention `.gitignore` already sets.

---

## THE POINT

Nothing here says your measurement was wrong. It says the thing you measured was one
artifact — and your paper said that already. The correction isn't "you were wrong," it's
"you were more right than you knew, and here is the evidence."
