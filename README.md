# srlm-forge private review copy

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
becomes preference-training data. **The model never grades itself** a program
that runs decides.

**The trainer** (`localllm/`) builds a small GPT from random numbers on your own
text. It is finished enough to use, it has a one-click installer, and it is not
the priority. It is here because the two grew up together.

The interesting claim about the forge is not the loop, which is not new. It is
that the domain-specific part is essentially **one function** the thing that
decides whether a candidate is correct. Sample K candidates, score them
objectively, prefer the winner, emit a pair, route the unsolvable to a
curriculum: none of that shape is specific to code. Any domain where a machine
can decide correctness could use it.

---

## What is actually true right now

Stated plainly, because the difference between these matters more than any of
them individually.

**There is still no efficacy result.** Nothing here shows the loop makes a model
better. That has not changed, and the work below does not bear on it.

**What has changed is that the weight-space finding is now demonstrated rather
than inferred.** Under the production 8-bit optimizer, 176 coordinates of one
adapter tensor moved past Adam's own worst-case per-coordinate displacement
bound. That was previously localized and its mechanism guessed at. It is now
measured end to end, and the guess was right in outline and wrong in one detail.

**The optimizer ablation (F2) is confirmed on all four arms.** One flag apart,
fixed seed, `--max-steps 20`:

| arm | optimizer state | over-bound coordinates |
|---|---|---|
| `adamw_bnb_8bit` | 8-bit | 178 |
| `adamw_torch` | 32-bit | **0** |
| `paged_adamw_8bit` | 8-bit, paged | 178 |
| `adamw_bnb_8bit`, `min_8bit_size` raised | 32-bit fallback | **0** |

Bit width, not paging: the two 8-bit arms produce bit-identical `train_loss`
(0.3544428050518036). Gradient clipping is excluded as a cause `grad_norm`
averaged 26.7–26.8 across all four arms.

**The mechanism, each link measured on this machine:**

1. **Source.** Layer 1's `down_proj` input channel 2427 reads **386.0 at the BOS
   token**, at exactly one token position, in all eight probe prompts spanning
   code, prose, digits, punctuation and non-Latin script, 2 to 49 tokens. It is
   input-agnostic to three significant figures.
2. **Gradient.** That channel's squared gradient exceeds its 255 block-mates'
   median by a median **9.0 × 10⁷**, ranking 1 of 256 at every live step.
3. **Optimizer state.** Read directly off the live optimizer: channel 2427 sets
   its 256-element block's absmax in **288 of 320** (step, row) cells, and a
   median **98.7%** of its block-mates' second moments are quantized to
   **exactly zero** relative error −1.0000, not merely small. With `v̂ = 0`
   Adam's denominator collapses to `eps`.
4. **Displacement.** The block-mates inflate 14.9× against the 32-bit arm, while
   the absmax holder exactly representable by construction is the **least**
   displaced column in its own block, rank 256 of 256.

**A massive activation is necessary but not sufficient, and the model contains
its own negative control.** A whole-model sweep finds exactly two channels
meeting the published criterion, both at BOS:

| layer | channel | magnitude | within-block ratio | over-bound | inflation |
|---|---|---|---|---|---|
| 1 | 2427 | 386.0 | 219,021× | 178 | 14.86× |
| 31 | 12111 | 104.0 | 2,380× | **0** | **1.02×** |

Layer 31 qualifies as a massive activation and corrupts nothing. Adam's second
moment squares the gradient, so the ratios square against the 8-bit map's
representable span (minimum positive value 3.25 × 10⁻⁷ of block absmax): layer
1 lands about 10⁴ past the floor, layer 31 barely past it. The claim is
therefore narrower than "massive activations corrupt their block" the
within-block dynamic range has to be large enough, and one of the two cases here
is not.

**Two preregistered entries contradict each other, and neither noticed until one
was run.** F2 specifies a *one-step* gradient witness. F9 states, correctly, that
`∂L/∂A = 0` while `B = 0`. Since `B` initialises to zero and a `--max-steps 1`
run on this pipeline takes its single step at learning rate **exactly zero**
(transformers computes warmup as `ceil(steps × warmup_ratio) = ceil(0.1) = 1`),
`∂L/∂A` is identically zero and the witness measures nothing. Confirmed
empirically: steps 0 and 1 record exactly that. F9's step-1 liveness gate
"every `lora_B` is nonzero" cannot pass on this pipeline for the same reason.

That same fact has a useful corollary: **an `--max-steps 1` run is a pure
initialisation**, `A = A₀` and `B = 0` exactly. Recovering any adapter's `A₀` is
therefore a 30-second run rather than a reconstruction.

**The seeding patch (F1) is validated with both witnesses.** Two runs at one
seed: 224 of 224 `lora_A` tensors bitwise identical. Two runs with no `--seed`
at all: **0 of 224**, mean cosine −0.000121, mean relative difference 1.414295
two independent draws. The green witness alone proved nothing; the red one is
what closes it. Note that F1's own text also requires the F9 step-1 gates to
pass, which they cannot, so by the letter of its preregistration F1 is not
fully validated.

**F6 is in flight.** A norm-matched random adapter is built on the healthy
adapter's own `A₀` (per-layer `‖B‖_F` matched to 1.6 × 10⁻⁶ relative error) and
is being scored interleaved against null and healthy arms at N = 40 per arm on
the frozen 31-task benchmark. Before any behaviour was measured, the two arms
were checked for spectral separability and are **indistinguishable**: zero
intruder dimensions each at every threshold from 0.3 to 0.9, median `max|cos|`
to the pretrained basis 0.999702 and 0.999663. Amplified controls confirm the
metric is live rather than merely quiet `lora_B × 1000` yields 167 of 280.

**F7 is blocked, and not on compute.** It requires the remaining rows be scored
under committed `forge.py` `f22eede7…` "so that the amendment's fingerprint and
the scoring fingerprint agree." That is unachievable for two independent
reasons: `f22eede7` is the **CRLF** digest of `forge.py` at `f755dea`, so the
same bytes hash differently on this machine; and commit `c4290b4` added a line
to `verifier_interpreter()`, so today's file is that plus one line. It needs an
amendment decision, not a longer run.

---

## The scaffolding, which is the part worth reviewing

A self-rewarding loop is unusually good at fooling the person running it. Most of
this repository exists to make that failure loud instead of quiet. **Every
mechanism below was built because the matching failure actually happened here.**

- **The freeze is enforced.** `build_ruler.verify_frozen()` re-hashes every
  benchmark task before any measurement. An earlier version wrote the hash and
  nothing ever read it a freeze nobody checks is a comment.
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
  test that passes before and after proves nothing. The seeding patch above is
  the current example, and the intruder-dimension count is the other: a metric
  that returns zero is indistinguishable from a broken one, so amplified
  controls are run alongside and reported.
- **Exports prove the adapter is applied.** `export_adapter.py --verify` builds a
  third model with `lora_B` scaled 50,000× and requires its output to differ from
  the null baseline. If a 50,000× amplification changes nothing, the adapter was
  never being applied and every other check would still have passed.
- **One README here is machine-checked, and it is not this one.**
  `localllm/verify_claims.py` re-derives the *trainer's* README claims and exits
  non-zero when one drifts. The forge's README this file has no such
  mechanism, so every number above was checked by hand against the artifact it
  describes. An earlier revision of this file asserted the checker covered this
  README; it never has. That is the exact failure this project catalogues, found
  in its own front page while rewriting it.

---

## Where to look, if you want to check something specific

| Question | File |
|---|---|
| What does the loop actually do? | `forge.py` |
| How is the reward decided? | `forge.py` → `verify()` |
| Why should the data be believed? | `verify_dataset.py`, `dataset_gate.py` |
| What is the benchmark, and is it honest? | `build_ruler.py`, `data/ruler_frozen.json` |
| How noisy is the measurement? | `ruler_noise.py`, `screen_tasks.py` |
| Did the seed reach the adapter? | `poscontrol/init_vs_training.py`, `docs/port-2026-08-24/` |
| Which coordinates broke Adam's bound? | `poscontrol/adam_bound_scan.py` |
| Where does the gradient blow up? | `poscontrol/grad_witness_hook.py` |
| What is the optimizer actually storing? | `poscontrol/optstate_trace.py` |
| Is it really second-moment underflow? | `poscontrol/quantized_adam_emulator.py` |
| Where are the massive activations? | `poscontrol/activation_probe.py --scan-all-layers` |
| Are two adapters spectrally separable? | `poscontrol/intruder_dimensions.py` |
| How is the random null built? | `poscontrol/make_random_adapter.py` |
| What was promised before the run? | `data/prereg_track_a_run1.json`, Appendix F of the manuscript |
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
  channels are clearly live and 4 are weak measured on the base model, not on
  these two.
- Not that the training bank is broad. It is **13 tasks**, effective count
  `9.93`. That is the *training* bank; the benchmark is a separate frozen
  31-task set, and the two are not the same instrument.
- Not that the 8-bit artifact matters functionally. It is a real defect in weight
  space and a nearly inert one in function space, in a run that succeeded. What
  is claimed is that the class exists and is deterministic, not that it caused
  anything here.
- Not that the numpy emulator models the magnitude. It reproduces the mechanism
  second moment alone yields over-bound coordinates, first moment alone yields
  none, removing the outlier channel yields none on synthetic Gaussian
  gradients, giving 6 coordinates against the real run's 178. It discriminates
  the cause; it does not predict the count.
- Not that the mechanism is established beyond this model and this optimizer
  version. It is measured on bitsandbytes 0.50.1, block size 256, Llama-3-8B,
  rank-16 LoRA, on one card.
- Not that the verifier is a sandbox. It is a subprocess with a filter. Do not
  run it on code from someone you do not trust.
- Not that any coverage list here is exhaustive unless a machine enforces it
  every run.

---

## Open questions where a second opinion would help

1. **Task breadth.** 13 training tasks is the binding limit. Pool-derived tasks
   yield 2.46x more pairs per generation, which is the obvious lever is
   widening the bank the right next spend, ahead of any further measurement?
2. **Whether the data-diversity question is the more publishable one.** Verified
   correctness and data diversity are separate variables, and that is testable
   here without a training run.
3. **F7's fingerprint.** Amend to name the current `forge.py` and disclose both
   deviations, take the N = 15 option the amendment already permits, or leave
   the run paused at n = 9 and report it as interim.
4. **Whether the layer-31 negative control belongs in the Results or the
   Discussion.** It narrows the mechanism claim, which is the honest direction,
   but it also means the headline finding rests on one tensor in one layer.

---

## Running it

Requires a local Ollama with the base model, and `.venv-train` (Python 3.12 with
torch 2.6.0+cu124) for anything that trains or verifies. Setup notes for the
trainer side live in `localllm/README.md`.

**Two environment variables are not optional.** `SRLM_VERIFY_PY` must point at
the venv interpreter or `dataset_gate` exits at import; `CUDA_VISIBLE_DEVICES=0`
selects the allotted card on a shared machine.

```
export SRLM_VERIFY_PY=$PWD/.venv-train/bin/python
export CUDA_VISIBLE_DEVICES=0

python forge.py                     # generate + verify preference pairs
python verify_dataset.py            # the gate: re-verify every pair, write the receipt
python build_ruler.py verify        # check the frozen benchmark still hashes
python ruler_noise.py measure --runs 40 --model <tag>   # score against the ruler
python train_native.py              # refuses to start without a matching receipt

# the weight-space instruments, all with argparse guards
python poscontrol/adam_bound_scan.py --arm <adapter> --a0 <init-adapter>
python poscontrol/activation_probe.py --scan-all-layers
python poscontrol/intruder_dimensions.py --adapter <a> --adapter <b>
python poscontrol/quantized_adam_emulator.py        # CPU only, no GPU needed
```

Several scripts in this repository execute their whole pipeline **on import**
and write data files `measure.py`, `eval*.py`, `analyze_run1.py`, `repair.py`,
`clean_dataset.py`, `verify_dataset.py`, `traces.py`. Do not import them to
inspect them. Everything under `poscontrol/` added since 2026-08-25 has a proper
argparse guard.

`data/` holds the pairs, the frozen ruler, the receipt and the preregistration.
`council/` holds run logs and analysis output it is this project's own output
directory, not a review body.
