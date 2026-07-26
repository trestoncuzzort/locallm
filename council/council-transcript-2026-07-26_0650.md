# srlm-forge Council — Full Transcript, Activation #7

2026-07-26 ~06:50. Triggered by the DIRECTIVE-block watcher (task `bkk3n3jtj`) firing on a real content change after two false triggers (a stand-down edit, then a self-corrected re-open — both logged by the executor in §16-17 of `instructions.txt`).

---

## 1. The DIRECTIVE (verbatim, from `instructions.txt`)

> Read scope: THIS FILE (§17 = executor log) + CODE AT COMMIT ccbee91:
> localllm/studio.py, localllm/model.py, localllm/train.py, localllm/data.py.
> Read that commit, not my summary of it.
>
> ASK — THE PROGRAM HAS TWO TRACKS AND ONLY ONE PROPRIETOR. RANK THEM.
> Track A (§14, ruled, unstarted): llama3:8b QLoRA DPO+NLL, N=918, prereg, frozen ruler. Every blocking pre-step from §14 is still open. Zero gradient steps have ever been taken on this track.
> Track B (new, commit ccbee91): from-scratch char-GPT, random init, now with a GUI to build and train it.
>
> Q1. Does Track A still execute as ruled, or is it PARKED?
> Q2. FOR THE PHD: what single, citation-backed modification to a ~0.4M-param char-GPT would most improve loss-per-FLOP (or loss-per-wall-second) on one RTX 4080, falsifiable in under an hour, with a success bar preregistered before the run?
> Q3. TRACK B HAS NO RULER... What is the minimum honest instrument before any Track-B result counts?
>
> NON-CLAIMS: not claiming the smoke run's loss means quality; not claiming param_count() is correct for bias=False (untested); not claiming the GUI is robust; not claiming Track B is novel; not claiming Track A is broken.
>
> CLOSED-CLASS CLAIM + RED WITNESS: studio.param_count() equals instantiated GPT.num_params() exactly — 5/5 hand-picked configs, bias=True only, RED (corrupted formula) = 5/5 mismatch, GREEN = 5/5 exact.

---

## 2. Orchestrator's pre-round verification (before spawning any seat)

Read the actual code at commit `ccbee91` (diff-confirmed identical to `HEAD`) for all four named files. Then, rather than trust the executor's "untested for bias=False" non-claim, ran the closed-class claim's untested branch directly:

```
bias=True   {vocab:65,block:128,n_layer:4,n_head:4,n_embd:256} real=3,176,192 est=3,176,192 -> MATCH
bias=False  {vocab:65,block:128,n_layer:4,n_head:4,n_embd:256} real=3,166,976 est=3,166,976 -> MATCH
bias=True   {vocab:100,block:256,n_layer:6,n_head:8,n_embd:256} real=4,764,672 est=4,764,672 -> MATCH
bias=False  {vocab:100,block:256,n_layer:6,n_head:8,n_embd:256} real=4,750,848 est=4,750,848 -> MATCH
bias=True   {vocab:256,block:64,n_layer:2,n_head:2,n_embd:128} real=429,568 est=429,568 -> MATCH
bias=False  {vocab:256,block:64,n_layer:2,n_head:2,n_embd:128} real=427,264 est=427,264 -> MATCH
```

Then, because the DIRECTIVE's Q1 is fundamentally a code-shaped claim, read `train_native.py` (outside the named scope, but required by the channel's own SCOPE clause — "the DIRECTIVE must name the file(s) AND the commit hash... the council reads THAT version" — here the claim needed a file the DIRECTIVE never named). Found: the merge bug at line 113 still present; the N=918 cap not enforced (script loads all 1,234 lines of `dpo_pairs.jsonl` directly); and — not previously known to the round — **zero of the §14 "THE RECIPE" hyperparameters appear to be wired in** (no `rpo_alpha`, wrong `lr` default, wrong LoRA alpha/dropout, wrong `max_length`, no cosine schedule). This became the seed of the round's biggest Q1 finding and was handed to every subsequent seat.

---

## 3. The brief sent verbatim to all five style advisors

*(Full text below is what each of the five agents received identically, per the kit's "same packet, byte-for-byte" rule; the closing instructions differed only in which advisor-specific question each was asked to foreground — Q1/Q3 for four of them, Q2 explicitly reserved for The PhD.)*

> COUNCIL BRIEF — srlm-forge — activation #7 (2026-07-26)
> Prose is a pointer map, not evidence — the orchestrator has verified the code claims below directly by reading the actual files at commit ccbee91 and running probes, not by trusting the executor's summary.
>
> [Track A status, Track B description, full code summaries of model.py/train.py/data.py/studio.py, the DIRECTIVE's Q1/Q3, the executor's NON-CLAIMS with the orchestrator's bias=False update, the CLOSED-CLASS CLAIM extended to 6/6 match, HARD CONSTRAINTS, and the "what's at stake" framing — see §2 above and the code excerpts in the report for the substance; reproduced in full in each advisor's own spawn prompt in this session's tool log.]

---

## 4. The five style advisors — raw responses (banked before review)

### Contrarian

> TRACK A IS PARKED. The blocking pre-steps don't exist in code... That N=918 enforcement is not a nice-to-have — it is a council-approved constraint the executor accepted. Without it in code, you cannot run the experiment as ruled. This deferral must be written to disk with a blocker list, not left in conversation.
>
> TRACK B HAS A FATAL METHODOLOGICAL ERROR MASQUERADING AS A TEACHING RIG. The 90/10 split is fixed and not random... val is always the same tail of the corpus (structural bias if the corpus has temporal drift); some train tokens are never sampled, others oversample; two evals on the identical checkpoint report different numbers... This isn't imperfect instrumentation — you cannot tell signal from noise right now.
>
> The proprietor's framing is also backwards: he says "attack why does training take so long," but a 0.41M-param model training in 2 seconds means he is NOT hitting the hard problems — he's learning the skeleton, pedagogically fine, but not the question he asked.
>
> **Q1:** TRACK A IS PARKED. Write the deferral with the blocker list.
> **Q3:** Fixed random seed for val evals, noise-floor measurement (identical checkpoint, 10 evals, report stderr), and a random/shuffled train/val split instead of the fixed 90/10 tail. The fixed split alone disqualifies every result until fixed.

### First Principles

> The ranked-choice frame — "Track A or Track B" — is the wrong question entirely. What's at stake is not resource allocation, it's execution fidelity. Track A's blocking pre-steps... are not blockers because they're hard — they're rituals that catch yourself lying. Track B is the proprietor saying plainly he's entering AI-engineering coursework... that's not a competing goal, it's the prerequisite for executing Track A well.
>
> The sequencing is inverted in the question: someone who runs Track A cold after 11 hours of parking will execute the protocol as theater... Track B is exactly the regime where he learns [to measure noise].
>
> Reframe: not "rank A vs B" but "run B first to build instrumentation maturity, then execute A with the rigor it deserves." Q1 asks the wrong layer entirely.

### Expansionist

> The biggest miss is treating Track B as a distraction when it's a prerequisite science instrument for Track A's success. A 2-second training cycle means ~1,800 experiments per GPU-hour: (1) validate the pipeline before the expensive run; (2) measure the signal-to-noise floor by running 100 seeds; (3) architecture-search — train 50 variants in under a minute; (4) rehearse the reward signal — train a tiny model on a subset of the project's own preference data.
>
> Biggest opportunity: Track B becomes the control-plane for Track A.

*(The Asshole's audit found the throughput figure overstated ~9.3x, the 50-variant claim overstated ~15x, and proposals 2 and 4 mechanically impossible given zero shared code between the two stacks — see §5 below.)*

### Outsider

> The inversion of stated priority: Track A is the "real" work... but blocked; Track B is "pedagogical," ungated, zero rigor, yet consuming the GPU with working smoke runs while Track A sits at zero gradient steps for 11 hours. This is not mysterious — it's psychologically predictable: friction is a blocker... preregistration is SUPPOSED to create friction, and it's working as designed.
>
> The thing that would alarm a stranger most: this brief contains tools to prevent self-deception... and then describes why they're not being used, wrapped in prioritization language but structured as avoidance.

*(The Asshole found the "consuming the GPU" mechanism factually wrong — no resource contention exists — but independently confirmed the deeper claim via the total absence of Track A artifacts.)*

### Pragmatist

> Track A is not parked — it's blocked on enumerated pre-steps... Q1: Track A executes as ruled; pre-steps are documented.
>
> Q3, concrete: (1) fixed eval seed added to estimate_loss(); (2) noise-floor benchmark — 10 identical-config runs; (3) gate: improvement is real if it beats baseline + 3-sigma. This is a 2-hour checklist.
>
> Monday morning: fix the NF4 label at train_native.py:113 (one line), commit, tag Track A pre-step #1 complete. Then pivot to Track B: add fixed eval seed to estimate_loss(), launch the 10-run noise-floor benchmark.

*(The Asshole ran the proposed eval-seed fix and found it an active bug — see §5.)*

---

## 5. The Asshole — audit pass (full)

*(Reproduced in full; this was the longest and most consequential pass of the round.)*

### A. Corrections to the orchestrator
1. HEAD is `bf02c03`, not `ccbee91` — provenance nit, content claim survives (diff empty).
2. Every parameter claim in the brief re-derived independently and confirmed: `dpo_pairs.jsonl` = 1234 lines; `train_native.py:113` merge call unfixed; zero `rpo_alpha`/`918`/`lr_scheduler` hits in the codebase; `optim="paged_adamw_8bit"` at :98; `lr` default `8e-6` at :36; LoRA `alpha=16, dropout=0.0` at :69; `max_length=M.max_seq` (2048) at :101-102; `_ATTN_MLP` = the 7 correct proj targets in `config.py`.
3. **Category error in the orchestrator's framing:** `paged_adamw_8bit` vs non-paged is a numerical no-op when paging never fires (bitsandbytes docs) — demoted from "recipe deviation" to cosmetic. Real substantive deviation count: 6, not 7, and only one (`rpo_alpha`) is method-level.
4. **"Two tracks fighting for GPU time" is false** and poisoned three advisors' answers — measured: one full Track B run (2000 steps, 0.81M-param config as then understood) = 18.5s wall. No contention exists.
5. Reconciled 1272 (gate-verified total, dpo+repair) vs 1234 (dpo-only, what `train_native.py` actually trains on) — consistent, not a bug, but the two numbers have been used interchangeably by the project and shouldn't be.

### B. Corrections to the Expansionist
6. "~1,800 experiments/GPU-hour" overstated 9.3x — measured 194/hour (18.5s/run); the "2 seconds" cited was the *step*-count smoke run, not a full experiment, and the executor's own non-claim said so explicitly.
7. "50 variants in under a minute" is actually 15.4 minutes.
8. "100 seeds tells you Track A reproducibility" — three stacked errors: wrong cost (31 min not seconds), wrong transfer (zero shared code between tracks, verified by import inspection), and a repeat of a measurement the council already demoted at `instructions.txt:599` ("test-retest repeatability... not between-model variance").
9. "Validate the pipeline / find silent tokenization bugs" — impossible; Track B is char-level `set(text)`, Track A is Llama-3 BPE with a chat template; zero shared surface.
10. "Rehearse the reward signal on Track A's own preference data" — category error; `dpo_pairs.jsonl` needs a DPO objective and a reference model, `localllm/` has neither, only next-char cross-entropy.

### C. Corrections to the Pragmatist
11. **The proposed "one-line" eval-seed fix is an active bug, confirmed by execution.** `Corpus.get_batch` draws from the global torch RNG with no dedicated generator. Measured: eval-free step-3 training indices `[365223, 88542, 339122, 25812, 474970, 458695]`; with an eval inserted at step 3, indices diverge from index 3 onward. Adding `torch.manual_seed(k)` inside `estimate_loss` makes training indices become `[292117, 25069, 491601, 292117, 25069, 491601, ...]` — **training replays 3 batches forever.** Correct fix: a dedicated `torch.Generator` threaded through `get_batch`.
12. "Fix the NF4 label, one line" — not a label, not one line. Read installed PEFT 0.14.0 source (`peft/tuners/lora/bnb.py:355-388`): merge dequantizes, adds the delta, **re-quantizes back to 4-bit NF4** — a second quantization error on top of the first, and the real fix needs a second bf16 model load (~16GB).
13. **The merge's stated purpose is broken outright, independent of quality**: `train_native.py:116` labels its output "merged fp16 -> ... for convert_hf_to_gguf.py," but the artifact is still 4-bit bitsandbytes; `convert_hf_to_gguf.py` requires fp16/bf16 safetensors. The export step cannot succeed at all, not just "with degraded quality."
14. His gate ("beat baseline + 3-sigma") has the right shape but the wrong sigma — his protocol would have measured test-retest sigma, not between-config sigma (see #18).

### D. Corrections to the Contrarian
15. Credit: he is the only one of five who correctly identified the eval-nondeterminism mechanism. Confirmed by direct measurement on a provably identical checkpoint, 10 evals: mean 1.5060, **sd 0.0078**.
16. "Fixed split disqualifies every result... *if* the corpus has temporal drift" — right conclusion, hedged reasoning; it's not drift, it's outright duplication (see the omission finding below), and it's certain, not conditional.
17. "Some train tokens never sampled, others oversample" — numerically dead at GUI defaults (coverage ~33x per token at 2000 steps/batch 32); asserted without checking magnitude.
18. **Decomposed the two noise floors he and the Pragmatist conflated**: eval/test-retest sd=0.0078; run-to-run (6 seeds) sd=0.0093; true seed effect after removing eval noise in quadrature, sd≈0.0051. **~70% of apparent run-to-run spread is measurement noise, not real variability** — the cheap fix (deterministic eval) removes most of the observed spread for free.
19. **Confirmed and quantified**: at 0.81M params (the config then measured), ~8.5% MFU, "kernel-launch- and memory-bound... Track B cannot teach 'why training takes so long' because it is not compute-bound." *(Superseded by The PhD's correction in §6 — the true GUI default is a different, larger config with materially higher MFU; the qualitative point about a launch-bound floor at small scale stands.)*

### E. Corrections to First Principles
20. Refusing Q1 outright is a dodge, not a reframe — the DIRECTIVE asked a binary with an operational consequence.
21. Inflated Track A's blocker list from §14's actual 2 items (merge fix, N=918 cap) to 5 ("merge bug, cap, smoke sheet, null baseline, prereg") — miscounting in the direction that supports his own conclusion.
22. "He'll execute it as theater" is unfalsifiable psychology presented as a technical finding.

### F. Corrections to the Outsider
23. His central image ("Track B consuming the GPU") is factually wrong — no resource contention (see correction 4).
24. But independently confirmed the deeper claim from the filesystem: `ls -d dpo_adapter*` → no output; no `run_meta.json`; `smoke_train.log` empty. Track A has everything it needs (base model fully downloaded) and has produced zero artifacts.

### Contradictions resolved
**Contrarian ("PARKED") vs Pragmatist ("not parked, blocked on pre-steps") → Contrarian wins, for a stronger reason than he gave.** `train_native.py` was written essentially concurrently with the §14 ruling it was supposed to implement (one commit, `9aeef51`, ~18:49) and never touched again — it isn't a partial implementation of the approved run, it's a different, already-rejected experiment (vanilla DPO on same-task low-edit-distance pairs, the exact case §14 cited Pal 2024 to rule out). But the Pragmatist is right that the fix is cheap: 6 of 8 real deviations are keyword arguments (~20 min); the honest total estimate is a half-day, and the recipe is verified expressible in the installed TRL 0.12.2 (`rpo_alpha` confirmed present in the installed `DPOConfig`).

### Prior art / adopt-don't-build
1. TRL 0.12.2 already implements DPO+NLL — `rpo_alpha=1.0`, one keyword, no hand-rolling needed.
2. **Better than §14's own mandate**: don't merge at all. `llama.cpp`'s `convert_lora_to_gguf.py` + Ollama's `ADAPTER` Modelfile directive apply the LoRA at runtime against an untouched base GGUF — no dequant/requant round-trip, and the null baseline becomes trivially the same code path with no adapter loaded.
3. §14's own citation (PEFT #2321) is an unanswered user question, not authoritative — stronger citations exist: transformers#31293, PEFT#2105, Kaitchup's "Don't Merge Your LoRA Adapter Into a 4-bit LLM."
4. §14's *reason* for non-paged optimizer was backwards (claimed paging never fires so it's untested; real reason is Windows/WDDM doesn't support the CUDA unified-memory paging relies on, so if it DID fire, failure mode is undefined rather than a clean OOM) — conclusion unchanged, rationale corrected.
5. Track B's split fix is a named technique, not a bespoke instrument: Lee et al. 2021 (dedup), group-aware splitting (`GroupShuffleSplit`/`GroupKFold`) keyed on the `tid` field already in `dpo_pairs.jsonl`.
6. Deterministic eval needs a `torch.Generator`, not `torch.manual_seed` — see correction 11.

### ★ What all five missed — finding of the round
No advisor opened `localllm/make_corpus.py`. It builds `corpus.txt` by concatenating the project's `.py` sources **plus the `chosen` field of all 1,234 rows of `data/dpo_pairs.jsonl`** — Track A's own training data, spanning 13 tasks. Measured on the fixed 90/10 tail split this produces:

```
corpus 549,023 chars | train 494,120 | val 54,903
project .py source portion : ~79,706 chars (14.5%)
dpo 'chosen' solutions     : 466,849 chars from 1234 solutions (85.5%)
'# file:' source headers —  train: 13   val: 0   <- val is 0% source, 100% solutions
val solutions EXACT duplicates of a train solution: 95/139 (68.3%)
val LINES appearing verbatim in train split:      1933/1968 (98.2%)
64-char shingles of val also present in train:                56.4%
```

Two defects, both invisible to every advisor: distribution shift by construction (train has source+solutions, val has solutions only) and outright contamination (68.3% exact duplication). Measured val loss (~0.30) is substantially memorization read-back. This reorders the whole Q3 answer — the round spent most of its effort on a σ=0.0078 eval-noise defect while the metric itself is invalid at the 68% level.

### Other omissions
- Second occurrence of "no ruler" (§5 for Track A, now Track B) — per the project's own stop-the-tar-pit rule, build one shared utility, not a bespoke instrument per track. Noise-floor magnitudes are nearly identical (0.009 vs 0.0093) — same failure mode.
- `param_count()` independently re-verified: 6/6 exact match, credit given.
- `config.py`'s `load_in_4bit` is dead code on the native path — `train_native.py` relies entirely on the base repo's embedded quantization config; pointing `SRLM_HF_BASE` at a non-prequantized repo would silently load full bf16 (~16GB), breaking the model-agnostic promise silently.
- `train_native.py` hardcodes `"beta": 0.1` in its own `run_meta.json` output rather than reading it back from config — a prereg trail that hardcodes what it claims to record.

---

## 6. The PhD — closing pass (full)

*(Reproduced in full.)*

### Corrections to the Asshole's own numbers, first
- **805,760 params is not the GUI default** — `studio.py:282-285` sets embd=256, not 128; the real default is **3,184,384 params** (matches the repo's own "trained 3.18M GPT" commit message).
- **MFU at the real default is ~24.6%, not 8.5%.** Full measured table (params / ms-step / TFLOP/s / MFU): 409,216→4.5%; 805,760→6.3%; **3,184,384→24.6%**; 10,684,800→56.2%; 25,269,760→76.4%; 85,130,496→90.6%. The launch-bound floor is real at the very bottom of the range but far less severe than first reported at the actual default. Batch 32→128 buys 67.1% MFU for near-free.

### Q2 answer: the learning rate is set for a model ~100x wider than the one being trained
`train.py:57` hardcodes `lr=3e-4`, a GPT-2-lineage constant. Under standard parameterization the optimal LR moves down roughly an order of magnitude as width increases 256→8192 (**Yang et al. 2022, "Tensor Programs V"/muP, arXiv:2203.03466** — verified at the byte, §3/Fig.3). Reproduced directly on this project's RTX 4080:

| width | best LR | val loss at best |
|---|---|---|
| 64 | 2e-2 | 0.2479 |
| 128 | 2e-2 | 0.1687 |
| 256 | 6e-3/1e-2 (tie) | 0.1182/0.1182 |
| 512 | 1e-3 | 0.0999 |

Monotone downward drift confirmed, divergence cliff walks down with it (~1.3 orders of magnitude, width 64→512).

At width 128 (0.41M model), lr=3e-4 (current default) reaches val 0.4716 in 2000 steps; lr=2e-2 (tuned) reaches val 0.1687 — the default needs **~16,000 steps (8x)** to match what the tuned LR reaches in 2000. Expressed as compute: **~5x compute-equivalent penalty from one mis-set constant** — larger than any architecture change (RoPE/RMSNorm/SwiGLU/ALiBi typically single-digit-% to ~1.3x).

**Why this is the one experiment safe to run today:** its primary endpoint is TRAIN loss, not val loss — immune to the contamination bug found by The Asshole.

**Preregistered protocol:** 2L/4H/128D and 4L/4H/256D configs, 2000 steps, batch 32, block 128; control lr=3e-4 vs treatment lr=2e-2 (width 128) / 3e-3 (width 256); 5 seeds each; primary endpoint mean final train loss; measured SE of the difference of two 5-seed means = 0.0060. **Success bar: treatment beats control by ≥0.020 mean train loss (>3x the SE), zero overlap between 5-seed ranges.** Predicted gap: 0.42 (0.41M model), 0.15 (3.18M model) — clearing the bar 7-20x. Runtime: ~90 seconds total at 0.41M.

**Durable fix**: adopt muP's width-scaling (LR ∝ 1/width) rather than a new hardcoded constant, which will be wrong again at the next width the GUI's slider reaches.

**Dead end, checked**: `torch.compile` — the canonical fix for a launch-bound regime — fails on this rig; Triton has no working Windows install in `.venv-train` (`RuntimeError: Cannot find a working triton installation`).

### Q1 notes
Pal et al. 2024 (DPOP, arXiv:2402.13228) is real and says what §14 claimed (verified). But measured `difflib` similarity between `chosen`/`rejected` across all 1,234 pairs: **median 0.378**, only 13.2% exceed 0.8 similarity, 6.7% exceed 0.9. The DPOP low-edit-distance failure mode applies to a ~13% tail, not the corpus generally — §14's framing overstated the scope; `rpo_alpha=1.0` is still cheap and worth keeping for that tail.

### Q3 notes
- **Melis, Dyer & Blunsom 2017 (arXiv:1707.05589)**, verified: under equal tuning budget, properly regularized LSTMs beat architectures claimed to supersede them — reported gains were tuning artifacts. Directly relevant: at the untuned lr=3e-4, the 3.18M model (val 0.1635) barely beats the 7.8x-smaller 0.41M model at its own tuned LR (val 0.1687) — an architecture ablation run today would "discover" that width doesn't matter, a tuning artifact. **No architecture comparison is admissible unless each arm's LR is independently tuned.**
- **Bouthillier et al. 2021 (arXiv:2103.03098)**, verified: randomize multiple variance sources together rather than controlling all-but-one; 51x compute savings vs an "ideal" estimator. Practical translation: vary the training seed while holding the eval stream fixed — the dedicated-Generator design, opposite of the Pragmatist's global `manual_seed`.

### Citation table (as submitted; see §7 for spot-check corrections)

| Paper | Year | Claim | Verification (PhD's own note) |
|---|---|---|---|
| Yang et al., Tensor Programs V / muP (arXiv:2203.03466) | 2022 | Optimal LR shifts ~1 order of magnitude, width 256→8192 | VERIFIED — Fig. 1 caption |
| Pal et al., Smaug/DPOP (arXiv:2402.13228) | 2024 | DPO can reduce chosen likelihood on low-edit-distance pairs | VERIFIED |
| Melis, Dyer & Blunsom (arXiv:1707.05589) | 2017 | Tuned LSTMs beat "superseding" architectures | VERIFIED |
| Bouthillier et al. (arXiv:2103.03098) | 2021 | Randomize multiple variance sources, 51x compute savings | VERIFIED |
| McCandlish et al. (arXiv:1812.06162) | 2018 | Gradient noise scale predicts critical batch size | VERIFIED |
| Kaplan et al. (arXiv:2001.08361) Appendix D.6 LR(N) formula | 2020 | LR(N) ≈ 0.003239 − 0.0001395·ln(N) | **UNVERIFIED — NOT USED** (fetch failed, PhD excluded it) |
| Karpathy nanoGPT `train_shakespeare_char.py` | — | lr=1e-3 for a 10.65M char model, "baby networks can afford higher" | VERIFIED |

---

## 7. Citation spot-check (The Asshole, second pass, narrow scope)

**6 of 7 clean, 1 note wrong (favorably — the excluded citation is real).**

1. **Yang et al. (muP)** — claim correct, but sourced from **Fig. 3, not Fig. 1** as the PhD's note said (Fig. 1 is a different experiment — Transformers/Adam vs Fig. 3's MLP/SGD/CIFAR-10). Direction confirmed by inference from the paper's divergence clause.
2. **Pal et al. (DPOP)** — PASS, clean, both claim-halves verbatim in the abstract.
3. **Melis, Dyer & Blunsom** — PASS, clean, verbatim in abstract.
4. **Bouthillier et al.** — PASS, clean, verbatim ("51× reduction in compute cost").
5. **McCandlish et al.** — PASS, clean; his scoped use of it (critical batch size, not a blanket "bigger batch is free" claim) is correctly modest.
6. **Kaplan et al. Appendix D.6 — THE PHD'S "UNVERIFIED" NOTE WAS WRONG. The formula is real.** Appendix D.6 ("Learning Rate Schedules and Error Analysis") exists and contains it verbatim as Equation D.1: *"LR(N) ≈ 0.003239 + (−0.0001395) log(N)... We found that larger models require a smaller learning rate."* The PhD's own `ln` interpretation is also right (confirmed by where the formula crosses zero relative to the paper's stated N>10¹⁰ breakdown point). He should not have excluded this — it's direct textual corroboration of the same direction-of-effect he had to infer sideways from citation 1's divergence clause. "The fetch failed twice" was not sufficient grounds to mark a citation unconfirmable.
7. **Karpathy nanoGPT config** — PASS, clean, exact line and config confirmed on GitHub master; the ~10.65M param arithmetic checks out.

**Bottom line: no fabricated citations, no paper saying something other than claimed.** Both defects are in verification notes, not arguments — recommend citation 6 be reinstated into the round's reasoning (it strengthens the LR finding, doesn't change it).

---

## 8. Chairman synthesis

See `COUNCIL RESPONSE §18` in `instructions.txt` (2026-07-26 ~06:50) for the full ranked critique, evidence-read list, EXECUTED/READ-ONLY labels, leftover risks, "the questions themselves," and the one recommended next prompt. Summary reproduced in `council-report-2026-07-26_0650.md`.

---

*Watcher re-armed on the DIRECTIVE block (task `bkk3n3jtj`) — fires automatically on the next real content change.*
