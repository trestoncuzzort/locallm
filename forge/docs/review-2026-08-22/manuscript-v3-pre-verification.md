# A Preregistered Null Result That Did Not Reproduce in a Second Training Environment: Measurement-Integrity Failures and Uncontrolled Initialization in a Local Execution-Verified Pipeline

Treston Malachi Cuzzort

Independent Researcher

---

**Author Note**

The original experiments were conducted on a single consumer workstation (NVIDIA RTX 4080, 16 GB VRAM). The independent replication, the retraining runs, and the same-session controls reported in the Results were conducted on separate hardware (NVIDIA RTX 4090) by a second investigator, from this project's code, data, and configuration. A fourth environment (NVIDIA RTX 5080, Blackwell architecture) contributed the preregistered positive-control run added in this revision. Code, data, preregistrations, and the complete working record are retained in a private repository. Correspondence concerning this article should be addressed to the author.

*Disclosure:* Analysis code, instrumentation, and drafting were produced with AI assistance under the author's direction.
---

## Abstract

Execution-verified preference pipelines replace human judges with unit tests, providing an objective reward. We report a preregistered evaluation of direct preference optimization (DPO) applied via low-rank adaptation to an 8-billion-parameter model, tested on a frozen 31-task benchmark. The trained adapter did not outperform its null baseline (+0.55 percentage points, *p* = .514), equivalence testing rejected an aggregate difference of ±2 pp or larger (*p* = .043), and the null replicated on independent hardware (−0.03 pp). Retraining from the same code, data, and configuration in a second environment produced three adapters that beat their same-session nulls by +8.8 to +10.9 pp. This revision decomposes that gain and finds that 48–58% of it is an instrument artifact: the pinned verifier fails any completion that annotates a signature without importing `typing`, and the retrained adapters learned to emit the import — a statement that appears in none of the 918 training pairs — so the construct-valid gain is +3.7 to +5.7 pp, still significant in every retrain. The three retrains are orthogonal in weight space (mean cosine 0.004) yet have per-task behavioral profiles that agree at the instrument's reliability ceiling (disattenuated *r* ≈ 1.0 on both metrics). We trace the orthogonality to a library call order that initializes the adapter before the seed is set, show that the initialized factor barely trains, and derive the observed cosine (*r*/*d*ᵢₙ) from those two facts: at this learning rate the data determine the function and the initialization only chooses its coordinates. The original null adapter's profile is unrelated to the retrains', and a deliberately over-trained positive control (40× learning rate, three epochs; 9 of 40 preregistered replicates banked when the machine failed) reaches the same raw gain through a different, seed-specific solution whose construct-valid gain is +2.0 pp. We further report a block-localized 8-bit optimizer-state artifact caused by the base model's massive-activation channel, six measurement-integrity failures in which components kept emitting well-formed numbers after they stopped measuring, and a seventh candidate in which the recorded configuration did not govern the run. We conclude that execution-grounded reward requires treating the verdict channel as adversarial, that a benchmark gain must be decomposed against the verifier's own idiosyncrasies before it is attributed to the task, and that the earlier attribution of the original null to a silent driver timeout must be stated as a hypothesis rather than a conclusion.

*Keywords:* direct preference optimization, execution-grounded reward, preregistration, null result, replication, reward hacking, measurement validity, training-seed variance, large language models, security smells

---

## A Preregistered Null Result That Did Not Reproduce in a Second Training Environment: Measurement-Integrity Failures and Uncontrolled Initialization in a Local Execution-Verified Pipeline

Preference-based fine-tuning of language models conventionally requires human annotators to rank model outputs. Direct preference optimization (DPO; Rafailov et al., 2023) removes the separately trained reward model from this loop but not the preference labels. Self-rewarding approaches (Shao et al., 2024; Yuan et al., 2024) go further, using the model itself as the judge, which introduces a well-documented hazard: a model that scores its own output can improve its score without improving its behavior (Amodei et al., 2016; Gao et al., 2023; Skalse et al., 2022).

Code generation admits a stronger alternative. A candidate program can be executed against hidden unit tests, and the verdict is supplied by the interpreter rather than by any model's opinion. This is the premise of the pipeline studied here: sample *K* candidates for a task, execute each against tests the model never sees, take a passing candidate as `chosen` and a demonstrably failing one as `rejected`, and train on the resulting preference pairs. The reward is objective by construction.

This article reports what happened when that pipeline was measured properly, and it makes five claims, two more than the first drafts. The first is empirical and negative: on the benchmark used, the trained adapter did not beat its null baseline, and the interval excludes effects of the size the study was designed to detect. The second is that this negative result does not generalize to the procedure, but that the procedure's positive result is smaller than it looks: retraining from the same inputs produced a large, consistent, and highly significant effect three times out of three, and roughly half of it is the adapters learning to satisfy an idiosyncrasy of the verifier that scores them. The remainder is real, concentrated on two benchmark tasks, and identical across the three retrains. The third, new to this revision, is theoretical: the three retrains occupy mutually orthogonal subspaces of weight space and implement the same function, and we can say why — the adapter's input factor is initialized before the seed is set and then barely trains, so each run is a random projection of the same update. The fourth is methodological and, we argue, the most transferable: producing the first result required finding and closing failures in the measurement apparatus, several of which would have produced a plausible-looking number that meant nothing, and two of which (an unbuilt container and an untraced seed) survived into earlier drafts as claims. The fifth is that this project's failures are not *sui generis*: they recur, in different clothing, in adjacent software-security research on tool adequacy and detectable-but-unexploited defects, and one strand of that research (formally verified code generation) points at a stronger fix than the one this article implements. The objectivity of an execution-based reward is a property of the *verdict*, not of the *pipeline that reports it*, and the difference turned out to be where the problems lived.

### The Distinction Between an Objective Reward and a Trustworthy One

An execution-grounded reward is objective in the sense that its ground truth does not depend on anyone's judgment. It is not thereby trustworthy. Between the interpreter's verdict and the training file lie several mechanisms — a harness that runs the candidate, a channel that reports the outcome, a dataset builder, a gate that certifies the data, and a benchmark that scores the result — and each is capable of failing in a way that produces a number rather than an error.

The failures reported in the Results section share a shape. In each case a component continued to emit well-formed output after it had stopped measuring what it claimed to measure: a verdict that could be forged by the candidate, a verifier whose answer depended on which script invoked it, a benchmark returning its ceiling regardless of input, a gate certifying a dataset it could no longer parse, an analysis script pooling a reference arm across two instruments, and — as of this revision — a claimed fix that was never actually implemented. None raised an exception. Two of them survived into a previous draft of this article. This is the failure mode that preregistration, red-witness testing, and measured noise floors exist to catch, and it is why we report them alongside the null result rather than in a separate engineering note.

---

## Method

### Design

A two-arm between-model comparison with 40 independent evaluation replicates per arm, fixed in advance.

The two arms differ by exactly one directive in the served model definition. The *trained* arm is the base model with the LoRA adapter attached at serve time as a GGUF adapter (`FROM llama3:8b-instruct-q4_K_M` + `ADAPTER adapter.gguf`); the *null* arm is the same base model with no adapter (`FROM llama3:8b-instruct-q4_K_M`). Neither arm's base weights were merged, dequantized, or re-quantized. A line-by-line comparison of the two served model definitions, as emitted by `ollama show --modelfile`, returns 103 lines against 102 with three differing lines: one inserted `ADAPTER` directive, and one comment line replaced by another naming the model that was queried. The base weight blob (`sha256-8d2bf4416eb1…cb13d`), the chat template, the four serving parameters (`num_keep 24` and three `stop` tokens), and the license block are identical between the arms. Only the adapter itself was converted, from PEFT safetensors to GGUF, tensor-for-tensor (448 in, 448 out).

This is a stronger design than earlier drafts of this article described. Those drafts characterized the arms as "both produced through the identical export and quantization path," so that export-path cost would cancel in the difference. That description was wrong in a way that understated the design: there is no export path in the null arm to cancel. The comparison is a pure A/B on one serving directive.

The unmodified base model was scored separately as a reference point. That reference is *not* sampler- or verifier-matched to the two arms, and the consequences of treating it as if it were are reported in Failure 5.

### Materials

**Base Model.** `unsloth/llama-3-8b-Instruct-bnb-4bit`, a 4-bit quantized 8-billion-parameter instruction-tuned model, served for inference through Ollama as `llama3:8b-instruct-q4_K_M`.

**Training Data.** 918 preference pairs (`dpo_pairs_capped.jsonl`, SHA-256 `85fc0bdc…`), stratified with a 120-pair-per-task cap from a larger bank of 1,244. Every pair was verified bidirectionally before training: the `chosen` completion was required to pass its hidden tests and the `rejected` completion was required to fail them. The full verified corpus comprised 1,279 unique pairs across 2,200 rows in three files.

None of the 918 pairs retains the verbatim text the policy emitted. The training loader reports `918 pairs …; 0 carry verbatim completions, 918 fall back to re-fenced source`: the optimization target is reconstructed by re-wrapping fence-stripped executable source, because the corpus builder discarded the raw emission. The reconstruction is applied identically to both halves of every pair, so it cannot carry the preference gradient; it does, however, define what the `rpo_alpha` likelihood term is trained toward. This is a property of the corpus both the original adapter and every retrain were trained on, and it is stated here rather than in Limitations because it changes what "the model was optimized toward" means.

**Training Procedure.** Low-rank adaptation (LoRA; Hu et al., 2021) over a quantized base (Dettmers et al., 2023), rank 16, α = 32, dropout 0.05, applied to seven projection modules (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`). One epoch over 918 pairs at effective batch size 16 (per-device 2 × gradient accumulation 8), giving **57 optimizer steps**; learning rate 5 × 10⁻⁶ with a cosine schedule and `warmup_ratio` 0.1 (`warmup_steps` is 0, which is not the same as "no warmup" and has been misread as such); β = 0.1, `rpo_alpha` = 1.0, `max_length` 1,024, `max_prompt_length` 512, `max_grad_norm` 1.0, bf16, `adamw_bnb_8bit` optimizer. The resulting adapter (SHA-256 `f416f3f9…`, 167 MB) is the object under test in the primary comparison.

The step count is stated as observed rather than derived. No `trainer_state.json` survived the original run, and the arithmetic admits 57 or 58 depending on an unrecorded `drop_last`; a retrain from the same corpus and configuration reported 57 *(replication)*.

**Software Versions.** The adapter's own model card records **PEFT 0.14.0**. No other library version was recorded by the original run: `run_meta.json` stores every hyperparameter and no library versions, and `adapter_config.json` predates PEFT's `peft_version` field. The training script passes `rpo_alpha` to `DPOConfig`, which current TRL rejects — `TypeError: DPOConfig.__init__() got an unexpected keyword argument 'rpo_alpha'`, raised at config construction before any training begins — so reproduction requires `trl==0.12.2`, which in turn pins `transformers==4.46.3` and `tokenizers==0.20.3`. The script names 0.12.2 in a source comment; nothing enforces it, and the version actually installed for the original run is not recorded anywhere. The replication ran under `trl` 0.12.2, `transformers` 4.46.3, `peft` 0.20.0, and `torch` 2.6.0+cu124 *(replication)*. The positive-control run added in this revision ran under the same `trl`/`transformers`/`tokenizers` pins, `peft` 0.20.0, and `torch` 2.11.0+cu128 on a Blackwell-architecture GPU, which requires the cu128 build; this environment is recorded in full in `data/prereg_positive_control.json` rather than summarized here, on the same principle as the rest of this section.

**Initialization Was Not Controlled, and This Revision Traces Why.** `train_native.py` contains no seeding call of any kind; a search for `set_seed`, `manual_seed`, or `seed` in the file returns nothing. The `seed = 42` recoverable from the run's `training_args.bin` is HuggingFace's `TrainingArguments` default rather than an authorial choice. Earlier drafts stated that this default "does not reach LoRA initialization" without saying why. The mechanism is a call order in the installed libraries, read at the byte: `train_native.py` hands `peft_config` to `DPOTrainer`; TRL 0.12.2's `DPOTrainer.__init__` wraps the model with `get_peft_model` at `dpo_trainer.py:376` and only reaches `super().__init__` — the `transformers` `Trainer` constructor, whose first action of consequence is `set_seed(self.args.seed)` at `trainer.py:424` — at line 640. PEFT 0.20.0's `reset_lora_parameters` (`lora/layer.py:334`) draws *A* with `kaiming_uniform_` from the default torch generator, passing no generator of its own, and zeroes *B*. Every draw *after* line 424 — the data order (`SeedableRandomSampler`, seeded from `torch.initial_seed()` = 42) and dropout — is seeded; the 224 draws of `lora_A` are the only unseeded randomness in the training graph, and `run_meta.json` records no seed at all. The same order is present in TRL's current `DPOTrainer`, `SFTTrainer`, and `GRPOTrainer`, so any TRL-based LoRA run that passes `peft_config` and does not seed manually shares the property; we have not audited how many published results do. The consequences are measured in the Results.

**Benchmark.** A frozen 31-task set (SHA-256 over task contents `74560a4c…`) screened from the AceCode-89K corpus (TIGER-Lab) to select tasks whose base-model pass rate fell inside a [0.2, 0.8] band, i.e., tasks on which a change can register. The task set is disjoint from the 43-task pool from which training pairs were drawn. Each replicate sampled 5 completions per task at temperature 0.8 with no greedy anchor, yielding 155 generations per replicate and 12,400 generations across the two primary-comparison arms.

### Measures

The primary outcome was greedy-free run-level pass@1. An earlier version of the metric blended one greedy draw with four sampled draws in a fixed 20/80 ratio. This was abandoned before the present study on grounds of estimator validity: the unbiased pass@*k* estimator of Chen et al. (2021) assumes *n* independent, identically distributed draws, and a fixed-ratio policy blend violates that assumption. The blend was therefore a change of estimand rather than a variance reduction, and the greedy anchor was removed. The magnitude of that change is not hypothetical and is quantified in Failure 5: within the same rows, greedy draws score 12.76 pp higher than sampled draws.

The benchmark's noise floor was measured rather than assumed. Repeated evaluation of an unchanged model yielded a run-level pass@1 standard deviation of 0.0283 across 10 null replicates under the pinned verifier. A subsequent greedy-free characterization gave a standard deviation of 0.0476, which was the value used for study sizing and, per its own preregistration, for the positive-control run added in this revision.

**A Declared Counterfactual Metric.** Every replicate row also records, per task and per draw, whether a failure's only error was a `NameError` on an un-imported `typing` name (`List`, `Optional`, `Tuple`, and the like), and the harness reports an upper-bound counterfactual pass rate in which such failures are counted as passes (`aggregate_if_typing_imported`). The field exists because the interpreter pin of Failure 2 made un-imported annotations fail, and because the benchmark's prompts carry annotated signatures while the training corpus does not. It is an upper bound — a completion that fails only on the import is not re-executed with the import supplied — and it is reported as a decomposition of the primary metric, not as a replacement for it. Earlier drafts used it once, as a robustness check on the null result; this revision applies it to every arm, and the consequences for the retrain result are reported under *The Typing-Import Decomposition* below.

### Preregistration

The analysis plan was written to a versioned file (`prereg_track_a_run1.json`) and committed to version control before the first replicate was scored. It fixed the arms, the metric, the replicate count (40 per arm), the statistical test (Welch's *t*-test on run-level pass@1, two-sided, α = .05, each arm retaining its own variance), and the stopping rule (fixed *N*; no interim analysis; no early stopping on the observed effect). Every hash recorded in it — the benchmark set, the adapter, the dataset files, the verifier fingerprint — was derived programmatically from the live artifacts rather than transcribed. The file's `written_at` timestamp precedes the first trained replicate by 26.15 minutes and the first null replicate by 179.28 minutes.

The preregistration additionally recorded, in the same file and before any result existed, what the study *could not* show. This practice follows the preregistration literature's rationale (Nosek et al., 2018; Simmons et al., 2011): the constraints on interpretation are least self-serving when fixed before the number is known. One of those entries — that benchmark responsiveness had been established on the base model rather than on the two arms — is discharged in the Results.

**Sizing.** With an assumed standard deviation of 0.0476 and *n* = 40 per arm, the standard error of the difference is 1.064 pp, giving a minimum detectable effect of 2.98 pp at 80% power. Observed variability came in *below* the assumption (0.0415 and 0.0327), yielding an observed standard error of 0.836 pp and an achieved sensitivity of 2.34 pp. The study was therefore somewhat better powered than planned, which bears on the interpretation of the null.

A second preregistration, `prereg_positive_control.json`, follows the identical sizing (same instrument, same *n*, same test), fixing an additional decision rule in advance: success iff *p* < .05 **and** the observed effect is at least +5.00 pp, a threshold set comfortably above the 2.98 pp MDE so that the design is powered for the effect size the rule actually requires rather than merely for detecting some nonzero effect.

### Verifier Integrity

Candidates execute in an isolated subprocess (`python -I`) under an 8-second timeout with a coarse banned-operation filter. This is defense in depth and explicitly not a sandbox. Return values are type-checked against a fixed set of plain builtins by exact type rather than by `isinstance`, so that a subclass with an overridden `__eq__` cannot satisfy a test it should fail.

Two further properties were established in the course of this work and are reported in the Results, because in both cases the property did not hold when first examined: the interpreter executing candidates is pinned rather than inherited from the calling script, and the verdict is reported through a channel the candidate cannot trivially write. A third property, examined for the first time in this revision rather than assumed from an earlier draft's description, is reported as Failure 6: the channel a *sufficiently deliberate* candidate could still write to.

A methodological note belongs here rather than in an appendix. While the interleaved replicate driver for the positive-control run (below) was already in progress, an edit landed in `forge.py` mid-run — the statement-level check this revision reports as Failure 6. `ruler_noise.py`'s own drift guard, built for exactly this situation and previously exercised only in the abstract, caught the fingerprint mismatch on the affected round, refused to bank the row, and printed the reason rather than silently mixing pre- and post-fix replicates. The affected round was recovered automatically by the driver's own resumable design on the following round. The consequence for the preregistration — every banked row carries the post-edit fingerprint while the preregistration names the pre-edit one — is recorded in a dated amendment file (`data/prereg_positive_control_amendment_2026-08-22.json`) rather than by editing the preregistration, and is discussed under *The Positive Control* below. This is reported not as an incident but as the guard working: the discipline Failure 5 traces the absence of is, elsewhere in this same codebase, present and load-bearing.

---

## Results

### Primary Comparison

The trained adapter did not outperform its null baseline (Table 1).

**Table 1**

*Run-Level Pass@1 on the Frozen 31-Task Benchmark*

| Arm | *n* | *M* | *SD* |
|---|---|---|---|
| Trained (adapter) | 40 | .4976 | .0415 |
| Null (baseline) | 40 | .4921 | .0327 |

*Note.* The two arms are the preregistered comparison. The base reference rows have been moved to Failure 5.

The difference between trained and null arms was +0.55 pp, 95% CI [−1.12, +2.21], *t*(74.0) = 0.66, *p* = .514. The effect did not reach the preregistered minimum detectable effect of 2.98 pp, nor the achieved sensitivity of 2.34 pp, and was not significant at α = .05.

A secondary paired analysis, in which the two arms were compared task by task across the 31 benchmark tasks, gave the same point estimate with a wider interval: +0.55 pp, 95% CI [−2.36, +3.46], *t*(30) = 0.39, *p* = .703. The paired analysis is reported second because the preregistration designated the run-level test as primary; selecting whichever test yielded the more favorable result after seeing both is the specific practice preregistration is intended to prevent.

Three checks not required by the preregistration are added because they bound the null rather than restate it. A permutation test over 200,000 relabelings gives *p* = .518 and a tie-corrected Mann–Whitney test gives *p* = .432, so the Welch *p* is not an artifact of the normality assumption. Two one-sided equivalence tests (TOST; Lakens, 2017) at the preregistered margin give *p* = .0024, and at ±2.00 pp gives *p* = .0433: **a true aggregate effect of ±2 pp or larger is rejected at α = .05**, while anything below ±1 pp (*p* = .295) is simply not resolved at this *n*. The 90% TOST interval is [−0.84, +1.94] pp. Finally, the arms do not differ in spread either, *F*(39, 39) = 1.61, *p* = .141, with a median-centered Brown–Forsythe check at *p* = .128.

The result is therefore informative rather than merely inconclusive. Effects of the magnitude this study was designed to detect are excluded; small effects are not.

### The Null Replicated; The Training Did Not

The comparison was repeated on different hardware, in a different session, with the arms interleaved replicate by replicate rather than run as sequential blocks, and with a four-file verifier fingerprint recorded on every row *(replication)*. The trained arm scored *M* = .5018 (*SD* = .0401, *n* = 41) and the null *M* = .5021 (*SD* = .0396, *n* = 40): −0.03 pp, *t*(79.0) = −0.03, *p* = .975, 95% CI [−1.79, +1.73]. Each point estimate falls inside the other run's interval and both are null.

Both runs serve the **same** adapter GGUF — the file's SHA-256 was computed independently on both machines and matches — so this replicates the *measurement*, not the training. Training-seed variance remains zero in both.

The training is a different story. Three adapters were retrained from this project's code, the same gated 918-pair corpus, and the same recorded configuration, and each was served through the same path and scored against the same frozen benchmark *(replication)*. All three beat the null decisively (Table 2).

**Table 2**

*Retrained Adapters Against Their Same-Session Null Baselines, on the Primary Metric and on the Typing-Forgiven Counterfactual*

| Arm | *n* | *M* | *SD* | Δ raw | *t* | *p* | Δ typing-forgiven | *p* | Typing failures per replicate |
|---|---|---|---|---|---|---|---|---|---|
| Original adapter, session A | 41 | .5018 | .0401 | −0.03 pp | −0.03 | .975 | −0.01 pp | .986 | 11.1 |
| Original adapter, session B | 15 | .5067 | .0325 | −0.04 pp | −0.03 | .976 | +0.52 pp | .714 | 11.1 |
| Retrain 1 | 40 | .6032 | .0405 | **+9.61 pp** | 7.19 | 2.7 × 10⁻⁷ | **+4.40 pp** | .0023 | 2.1 |
| Retrain 2 | 40 | .6161 | .0400 | **+10.90 pp** | 8.18 | 3.4 × 10⁻⁸ | **+5.65 pp** | 1.9 × 10⁻⁴ | 2.1 |
| Retrain 3 | 15 | .6060 | .0351 | **+8.77 pp** | 6.16 | 1.4 × 10⁻⁶ | **+3.66 pp** | .010 | 2.6 |

*Note.* Δ and statistics are computed against each arm's same-session null (*n* = 40 for session A; *n* = 15 for session B, which also serves retrains 1 and 2; *n* = 15 for retrain 3's own session), avoiding instrument drift. The nulls record 10.2–11.1 typing failures per 155-generation replicate. All arms carry an identical four-file verifier fingerprint. Welch's test throughout, each arm retaining its own variance. The typing-forgiven column is the upper-bound counterfactual declared in the Method; against session A's *n* = 40 overnight null instead of session B's, retrains 1 and 2 give +10.11/+11.40 pp raw and +4.32/+5.56 pp forgiven, so the decomposition does not depend on which null is used. The three raw effects span +8.77 to +10.90 pp with *p*-values from 3.4 × 10⁻⁸ to 1.4 × 10⁻⁶ — the exact figures are given here because an earlier draft of this article's own positive-control preregistration paraphrased this row as "+9.6 to +10.9pp… p<1e-6," which understates the range and overstates the third *p*-value; the error was caught before the run it justified was interpreted and is corrected in the artifact itself.

Two controls make this interpretable rather than merely striking. First, **instrument drift is excluded by a same-session control**: on the same day the retrains were scored, the original adapter and the null were re-run interleaved, and the difference between them was −0.04 pp, *t*(25.3) = −0.03, *p* = .976. A 10 pp jump measured across sessions is exactly what an instrument shift looks like, so a fresh null was scored in the same session before the retrain result was believed. Against *that* null, retrains 1 and 2 sit +9.61 pp and +10.90 pp. Second, **the three retrains are statistically indistinguishable from one another** (pairwise −1.29, −0.28, +1.01 pp; all non-significant), which is not what independent lucky draws would produce.

The retrains therefore separate cleanly from the original adapter, and the original adapter does not separate from no adapter at all. What the retrains separate *on* is the subject of the next section.

### The Typing-Import Decomposition: Half the Gain Is the Instrument

Failure 2 pinned the verifier to Python 3.11, under which a function whose signature references `List` or `Optional` without importing it raises `NameError` at definition time. The benchmark's AceCode prompts carry annotated signatures; the training corpus's 13 seed tasks do not. The harness counts these failures separately (Method, *A Declared Counterfactual Metric*), and applying that count to every arm gives a decomposition the earlier drafts did not make.

The null arms fail on an un-imported annotation 10.2–11.1 times per 155-generation replicate, and the original adapter fails 11.1 times — identical to null, in both sessions. The three retrains fail 2.1, 2.1, and 2.6 times (each against its null: *t* = −8.7, −8.8, −13.8; all *p* < 2 × 10⁻⁷). Counting those failures as passes, the retrains' gains fall from +9.61/+10.90/+8.77 pp to **+4.40/+5.65/+3.66 pp** — still significant in every case (Table 2) — so **54%, 48%, and 58% of the raw gain is the adapter learning to clear a verifier check that the benchmark's tasks, not the training tasks, impose**. Per task, the gain on `ace_oss_11023`, `ace_oss_23069`, `ace_oss_4327`, and `ace_oss_23132` (null typing-failure rates 53%, 54%, 40%, and 22% of draws) is entirely typing: +56/+50/+43, +29/+35/+27, +39/+40/+39, and +23/+20/+15 pp raw against 0, 0, −3/−1/−1, and −1/−4/0 pp forgiven (Appendix E). The construct-valid gain is concentrated on two tasks with no typing failures at all — `ace_oss_17851` (+44/+44/+39 pp) and `ace_oss_24748` (+45/+44/+33 pp) — and is accompanied by a consistent loss on `ace_oss_3243` (−25/−22/−31 pp).

Where the behavior came from is the more interesting question, because it is not in the data. Across the 918 pairs, 866 rejected halves fail on a wrong answer, 17 on a `NameError` (none involving a `typing` name), and the rest on type, index, syntax, or timeout errors; **no chosen or rejected half in the corpus contains an import statement of any kind, and none has an annotated signature**. The adapters could not have learned `from typing import List` from a contrast that never presented it. Serving the one adapter retained on the present machine (the positive control, below) against its null on three annotated benchmark tasks, five draws each, the null arm imported `typing` in 7 of 15 completions and omitted it in 7 (one dropped the annotation), while the adapted arm imported it in 12 of 15 and dropped the annotation in 2. The adapter did not suppress annotations; it completed them with the import the base model already supplies about half the time. Since nothing in the corpus contrasts on imports, the most economical reading is that preference optimization sharpened a pre-existing mode of the base model (cf. Yue et al., 2025, on verifiable-reward training as sharpening) whose selection was incidental to the training signal — a reading from 15 draws under a chat template that is not the harness's, offered as a mechanism to test rather than a result.

Two things follow. The retrain result stands, at about half its stated size: +3.7 to +5.7 pp against a preregistered minimum detectable effect of 2.98 pp, with all three *p*-values below .01. And a measured gain on an execution-verified benchmark is a statement about the model *and the verifier jointly* until it has been decomposed against the verifier's known idiosyncrasies — the point the reward-hackability literature makes for tests that accept wrong programs (Rajan, 2026; Ray, 2026), which applies equally, in the opposite direction, to a verifier that rejects right ones for an environmental reason.

### The Adapter Under Test Was One Draw From an Uncontrolled Distribution

The obvious reading of Table 2 — that the original training run simply landed badly — is supported by a measurement of the training procedure itself.

Running the training command twice on the same machine, with the same data, the same code, and the same recorded seed, produces two adapters that are **orthogonal in weight space and equal in magnitude** *(replication)*. Over the effective update Δ*W* = (*BA*)·α/*r* across all 224 adapted layers, computed in float64: mean cosine similarity **0.0042** (*SD* 0.0044, minimum −0.0087), mean magnitude ratio 1.0019, mean relative difference 1.4127. Two equal-magnitude orthogonal vectors must give exactly √2 = 1.41421, and the three metrics are mutually consistent to four decimals.

The decisive detail is *which* factors differ. LoRA initializes *A* from a generator and *B* to exactly zero. *B* must therefore differ between any two runs whose optimization differed at all, so *B* alone would be consistent with mere kernel non-determinism. But of 224 `lora_A` tensors, **0 are bitwise identical across the two runs**, with mean cosine −0.0005. The runs did not drift apart during training; they never started from the same place. This is the signature the Method now explains: the adapter is initialized before the seed is set.

Both runs converged equally well — train loss 0.5821 and 0.5831, runtimes 753.7 s and 757.7 s, reward accuracies 0.925–0.975 in both. Two orthogonal solutions, of equal magnitude and equal training quality.

The measurement instrument for this claim was itself verified on known answers before its output was believed: compared against itself, the tool returns cosine exactly 1.000000 with zero variance; compared against a 50,000× amplified control, it recovers a ratio of 50000 with cosine 1.0. In float32 it had returned a cosine of 1.0049 — an impossible value — which was caught only by the self-comparison control and fixed by computing in float64 *(replication)*. The same self-comparison and amplified-control pattern was reused, and re-verified rather than assumed, for the export path exercised by the positive-control adapter below: `export_adapter.py`'s own spot check confirms the amplified-control comparison returns cosine 0.0000 against the null and 0.9668 for the adapted-vs-null comparison, on the adapter reported in the next section.

**Orthogonality Is Predicted, Not Anomalous.** Earlier drafts presented the orthogonality as surprising. It is a consequence of two facts, one from the Method and one measured here. First, *A* is drawn at random and differs between runs. Second, *A* barely trains. In the only adapter retained on the present machine — the positive control, trained at 40× the original learning rate for three epochs — 95.5% of `lora_A` entries still lie inside the kaiming-uniform initialization box |*a*| ≤ 1/√fan_in, the entries' standard deviation is 1.02× that of the initial uniform distribution, and their kurtosis is 2.05 against 1.80 for a uniform and 3.00 for a Gaussian. At the original recipe the movement is bounded rather than measured: 57 steps at a peak rate of 5 × 10⁻⁶ with six warm-up steps and a cosine schedule sum to Σ*lr* = 1.47 × 10⁻⁴, and an Adam step moves a coordinate by at most about *lr* in the typical case and 3.16·*lr* in the worst case (Kingma & Ba, 2015), so no element of *A*, whose scale is 1/√(3·4096) ≈ 0.009, could have moved more than 1.6% (typical) or 5.2% (worst case) of its own magnitude. The learned update is therefore Δ*W* ≈ *B*·*A*₀: a readout *B*, trained on the data, applied to a random, effectively frozen 16-dimensional projection *A*₀ of the layer's input (Zhu et al., 2024; Hayou et al., 2024). Two runs share the update that *B* learns and differ in the projection, and the expected cosine between the same matrix projected onto two independent random *r*-dimensional row subspaces of a *d*ᵢₙ-dimensional space is *r*/*d*ᵢₙ: 16/4096 = 0.0039 for the attention and gate/up projections, 16/14336 = 0.0011 for `down_proj`, and 0.0035 averaged over the seven adapted modules. A simulation of the model (random uniform *A*₁, *A*₂; Δ*W*ᵢ ∝ *G A*ᵢᵀ*A*ᵢ for a common *G*) returns 0.0039 ± 0.0005 and 0.0011 ± 0.0002. The measured 0.0042 ± 0.0044 is that number. Orthogonality in weight space is the wrong place to look for what the runs share; the next section looks in behavior.

### Three Orthogonal Adapters, One Function

If Δ*W* is a random projection of a common update, the three retrains should not merely agree in their mean gain; they should agree task by task. The retained rows record every draw's outcome per task, so the per-task *delta profile* of each arm — its 31-vector of pass-rate changes against its same-session null — can be compared across arms without new generations. Table 2b reports the result, with each profile's split-half reliability (odd versus even replicates, Spearman–Brown corrected) as the ceiling any correlation between two profiles can reach.

**Table 2b**

*Agreement of Per-Task Delta Profiles Across Arms (31 Tasks)*

| Comparison | *r*, primary metric | *r*, typing-forgiven | Disattenuated *r* (primary / forgiven) | Permutation *p* (primary / forgiven) |
|---|---|---|---|---|
| Retrain 1 vs. retrain 2 | **.974** | **.965** | 1.06 / 1.11 | < 5 × 10⁻⁵ / < 5 × 10⁻⁵ |
| Retrain 1 vs. retrain 3 | **.801** | **.703** | 0.99 / 0.96 | < 5 × 10⁻⁵ / 1 × 10⁻⁴ |
| Retrain 2 vs. retrain 3 | **.793** | **.683** | 1.02 / 0.99 | < 5 × 10⁻⁵ / 1 × 10⁻⁴ |
| Original adapter (session B) vs. retrain 1 | .171 | .391 | 0.24 / 0.57 | .18 / .016 |
| Original adapter (session A) vs. retrain 1 | −.074 | .081 | — | .66 / .32 |
| Original adapter, session A vs. session B | .467 | .453 | — | .004 / .005 |
| Positive control (*n* = 9) vs. retrains 1, 2, 3 | .382, .381, .561 | .268, .267, .494 | 0.41, 0.42, 0.70 / 0.29, 0.31, 0.67 | .017, .018, .0006 / .076, .079, .003 |

*Note.* Split-half reliabilities of the delta profiles: retrains .945, .888, .688 (primary) and .915, .821, .586 (forgiven); original adapter .209 (session A) and .519 (session B); positive control .927 / .922. Disattenuated *r* = *r*/√(rel₁·rel₂); a value near 1 means the two profiles are indistinguishable at the instrument's own reliability. Permutation *p* from 20,000 shuffles of task labels. Replicate-resampling bootstrap intervals are in Appendix E; they are biased toward zero by resampling noise and are reported as conservative bounds.

The three retrains' profiles agree at the reliability ceiling: disattenuated *r* = 1.06, 0.99, and 1.02 on the primary metric and 1.11, 0.96, and 0.99 on the typing-forgiven metric. Fifteen tasks move up and three move down under all three adapters (twelve and three on the forgiven metric), the same two tasks carry the construct-valid gain, and the same task carries the loss. Three adapters that share no direction in weight space — cosine 0.004 — implement, to within what a 40-replicate instrument can resolve, the same function on this benchmark. This is the opposite of the expectation the seed-variance literature supplies: models with identical aggregate scores routinely differ at the item level (McCoy et al., 2020; D'Amour et al., 2022; Marx et al., 2020), and any source of non-determinism is expected to produce full run-to-run diversity (Summers & Dinneen, 2021; Zhuang et al., 2022). Here the per-task profile is invariant to the one unseeded draw in the training graph. The weight-space degrees of freedom the initialization consumes are, on this evidence, coordinates rather than content: at this learning rate the data determine the function, and the initialization chooses the basis in which it is written.

### The Null Adapter Is Not a Weak Retrain

The original adapter's profile is weakly reliable (split-half .21 in session A, .52 in session B) but real — its two sessions' profiles correlate at .47 (*p* = .004), so the redistribution Failure 5 reports is a property of the adapter, not of a session. It is not, however, a scaled-down version of the retrains' profile. Against retrain 1 it correlates at −.07 (session A) and .17 (session B) on the primary metric, neither distinguishable from zero, and at .08 and .39 on the forgiven metric, the latter significant (*p* = .016) but far below the .97 the retrains reach with each other. Whatever the original run produced, it moved behavior in a direction mostly unrelated to the direction every healthy run finds. This bears on the Discussion's attribution of the original null: a corrupted update would be expected to point somewhere arbitrary, and this one does; but so would a number of other failure modes, and the profile cannot tell them apart.

### The High-Learning-Rate Regime Leaves the Seed-Invariant Solution

The positive control — the same corpus at 40× the learning rate for three epochs, reported in full below — reaches the retrains' raw mean gain (+11.40 pp at *n* = 9) but not their profile. Its profile is highly reliable (split-half .93) and correlates with the retrains' at only .38, .38, and .56 (primary) and .27, .27, and .49 (forgiven); its per-task deltas have a standard deviation of 33 pp against 15–18 pp for the retrains, with swings of +73, +64, and +62 pp on three tasks and −60, −38, and −31 pp on three others (Appendix E); and its typing-forgiven gain is +2.0 pp (*p* = .23). Its update is about 26× the retrains' in Frobenius norm per layer (0.53 versus 0.02). The same data, pushed harder, leave the solution that every low-rate run finds and arrive at a different one, with the same aggregate and a different shape — the signature of a regime boundary between an effectively linear adaptation, in which the learned function is determined by the data, and a non-linear one, in which it is not. Where the boundary lies, and whether two high-rate runs would agree with each other as the low-rate runs do, is not measured here; it is the first experiment in *Planned Experiments*.

**What Is Not Isolated.** Which variable separates the original run from the retrains remains open, and this revision narrows it by one: the initialization draw is now known not to matter at this recipe, because three different draws produced one function. The original and the replication still differ in the GPU, the CUDA/torch stack, and the PEFT version (0.14.0 recorded on the original adapter's model card; 0.20.0 on the replication and on the positive-control run below), and the versions of TRL and transformers used for the original run were never recorded, so they cannot be excluded either. Establishing the cause requires a version matrix, not another retrain, and no claim about a specific library is made here.

### The Positive Control (Preregistered, In Flight)

Earlier drafts of this article listed as outstanding "an adapter trained at a deliberately high learning rate for multiple epochs, served through the same path, with a decision rule fixed in advance." That run's marginal evidentiary value is lower than when the limitation was first written — Table 2's three retrains, at the *original* recipe, already demonstrate the pipeline transmits adaptation at a large, repeatable magnitude — but the paper had still listed it as open, and it is reported here as far as it has run.

**Design**, preregistered in `data/prereg_positive_control.json` before training began: learning rate 2 × 10⁻⁴ — approximately 40× the original 5 × 10⁻⁶, itself sourced from a QLoRA recipe rather than chosen as a LoRA-specific default — combined with 3 epochs rather than 1, so that the run is an unambiguous positive control rather than a fourth ordinary retrain. Same 918-pair corpus, same LoRA configuration (r=16, α=32, dropout 0.05, same seven target modules), same frozen benchmark. 40 replicates per arm, same-session, interleaved rather than sequential, Welch's *t*-test at α=.05. Decision rule fixed before training: success iff *p* < .05 **and** the observed effect is at least +5.00 pp.

**Training**, executed on a fourth machine (RTX 5080, Blackwell architecture) not used in any prior part of this record: reward accuracy at 1.00 for the tail of training, train loss converging to 0.121, three full epochs over 918 pairs (171 optimizer steps). `run_meta.json`, written by the training script itself rather than transcribed, matches the preregistration in every field.

**A driver-level safety gate specific to this environment.** The machine used for this run had no administrator access and could not have its Windows TDR (Timeout Detection and Recovery) delay raised from the operating system default — the same class of silent driver timeout this article's Discussion identifies as the likely cause of the *original* null result. Absent the ability to prevent it, the Windows System event log was checked for TDR, WHEA hardware-error, unclean-reboot, and NVIDIA-provider events across the exact training window, before the adapter was trusted: zero such events, checked twice, several minutes apart, to allow for delayed log flushing. This does not establish the training was free of the failure mode this article otherwise attributes causal weight to; it establishes that the one channel available to detect it, without the ability to prevent it, found nothing.

**Export**, verified before being trusted: tensor-for-tensor GGUF conversion matched 448 of 448 tensors; the amplified-adapter control (50,000× LoRA-B) diverges from the null baseline at cosine 0.0000 while the true adapted output sits at cosine 0.9668 against the null, confirming the served adapter is neither identical to the base model nor a broken export.

**Status as of this draft.** Eighteen of the preregistered 80 rows are banked — 9 per arm, interleaved — and the run is paused, not complete. Three deviations are recorded in a dated amendment file, `data/prereg_positive_control_amendment_2026-08-22.json`, written before any further row was scored. First, every banked row carries the post-Failure-6 verifier fingerprint (`forge.py` f22eede7…) while the preregistration names the pre-edit one (13d52d9c…); both arms were scored under the same verifier on every row, so the contrast is internally valid, and the remaining rows will be scored under the committed fingerprint rather than the preregistered one. Second, the lab machine rebooted without a clean shutdown at 13:32 on 2026-08-20 (Kernel-Power 41), two minutes after the eighteenth row was banked and during round 10 of 40; the training and evaluation windows contain no TDR, WHEA, or driver event, so the adapter is not implicated by the preregistration's own distrust rule, but rows banked after the restart are a second session and will be reported per session as well as pooled. Third — and disclosed because the preregistration's rule is *no peeking* — the arm's *n* = 9 aggregate was seen on 2026-08-22 while the per-task profiles of Table 2b were being computed for every arm in the data file: .6179 versus .5039 (+11.40 pp, *t*(15.9) = 6.76) on the primary metric and .6186 versus .5986 (+2.01 pp, *p* = .23) on the typing-forgiven counterfactual, with 0.1 typing failures per replicate against 14.7 for its null. These are interim, non-decisional figures. *N* remains 40 per arm, no early stop is taken, and the decision rule is applied only at *N* = 40; what the look changes is that the typing-forgiven comparison is now declared in the amendment as a secondary analysis rather than chosen afterwards. On the evidence so far, the positive control is a positive control for the *instrument*: it drives the verifier's typing check to the floor and redistributes the rest. This section will be completed in a subsequent revision; it is included here, incomplete, because the same preregistration discipline this article argues for applies to its own unfinished work, not only to the parts already scored.

---

### Measurement-Integrity Failure 1: A Forgeable Verdict

The verifier reported its verdict by printing a sentinel string to standard output, and the parent process accepted a candidate when the subprocess exited zero and the sentinel appeared in `stdout`. The candidate's code is placed first in the generated harness and therefore executes at module level before the tests are defined. A candidate consisting solely of

```python
print("__PASS__ 0.0")
raise SystemExit(0)
```

satisfied both conditions and was scored as passing, despite never defining the requested function. Both halves of the verdict were writable by the artifact under judgment.

This falsifies, as implemented, the pipeline's central claim — that the model does not score itself. It is a reward-hacking channel in the sense of Skalse et al. (2022), differing from the usual case in that no optimization pressure was required to exploit it; a single literal string sufficed.

The defect was repaired by requiring the parent process to supply a 128-bit nonce per run, captured by a prelude executing before the candidate and removed from the environment so that candidate code cannot read it, with the sentinel emitted only after the test function returns. Verification before and after (Table 3):

**Table 3**

*Verifier Response to Honest and Forged Candidates, Before and After the Nonce*

| Candidate | Before | After |
|---|---|---|
| Correct solution | pass | pass |
| Incorrect solution | fail | fail |
| Forged sentinel | **pass** | fail |
| Forged sentinel + guessed nonce | — | fail |
| Forged sentinel + nonce read from environment | — | fail |

Whether the channel had ever been exploited was measured rather than assumed: the sentinel string appeared in 0 of 2,200 banked rows, and appears in no prompt the model receives. The hole was live but unexercised. All 1,279 pairs were re-verified under the repaired verifier and passed, so the training corpus and the present result stand.

**CORRECTION (this revision).** Every earlier draft of this article continued the preceding paragraph with a claim that the verifier "was re-architected into a locked-down Alpine Linux container," that the execution environment "now drops all privileges, enforces strict memory (256 MB) and CPU limits, mounts the candidate code as strictly read-only, and completely disables network access," and that "this OS-level containment definitively closes the forgeable verdict channel." **That claim is withdrawn.** No Dockerfile, container build configuration, or reference to Alpine Linux exists anywhere in this repository or its history; `forge.verify()` executes every candidate via a bare `subprocess.run` against a plain Python interpreter, exactly as it did before the paragraph was written, guarded only by the nonce above and a regex-based banned-operation filter explicitly commented "NOT a real sandbox." A sibling verifier in the same codebase (`domains/sql/runtime.py`) states, independently and candidly, that "the honest end state is the one SWE-bench arrived at — a container per instance — and every regex or authorizer is a deferral of that," which is not a statement anyone would write if a container already existed one file over. The claim was never checked against the bytes it described before publication, which is the exact failure this article's own Failure 5 already named this project's habit of correcting rather than concealing. What has actually closed, and what remains open, is reported honestly as Failure 6, below, rather than folded silently back into this one.

### Measurement-Integrity Failure 2: Ground Truth Dependent on the Interpreter

The verifier launched candidates using the interpreter of whichever script invoked it. Some pipeline components re-executed under a pinned Python 3.11 environment while others ran under the system Python 3.14, meaning the process that admitted benchmark tasks and the process that scored them could disagree about ground truth.

The magnitude was established by replaying 310 banked completions through both interpreters with identical inputs: 172/310 passed under 3.14 and 154/310 under 3.11, with all 18 disagreements running the same direction, concentrated on 6 of 31 tasks. The cause was deferred evaluation of annotations, under which a function signature referencing an unimported typing generic raises at definition time on one version and is harmless on the other. The permissive reading converted five benchmark tasks into dead channels at a pass rate of 1.000.

The interpreter is now resolved in one place, recorded in the dataset receipt, and refuses to fall back to the launching interpreter — a silent fallback would restore the defect while every artifact continued to assert that a pin was in force.

The trained and null arms carry an identical verifier record in all four fields, so **the primary comparison is not exposed to this confound at all.** The base reference arm is, and that is part of Failure 5.

### Measurement-Integrity Failure 3: A Saturated Benchmark

The same adapter evaluated in this study had been evaluated once before, on an earlier 10-task benchmark. That evaluation returned pass@3 = 0.9 on all ten runs across both arms without exception, and pass@1 means of .880 (trained) versus .888 (null). The instrument had reached its ceiling — a prior characterization found pass@20 equal to pass@3 equal to 0.9000, with 7 of 10 tasks pinned at ceiling and 1 at floor — and was returning a constant.

An instrument at its ceiling does not announce that it has stopped measuring; it returns a plausible number. The earlier evaluation was consequently uninterpretable, and the project record had described the state as "nothing has run on the real base," which was false in fact (a real run had occurred) and correct in implication (no interpretable result existed). The distinction matters operationally: one description implies training is the next step, the other implies re-measurement is.

The replacement benchmark was screened for tasks inside a [0.2, 0.8] band, frozen with an enforced content hash, and given a measured noise floor.

**Responsiveness at the Arms' Own Operating Point.** Earlier drafts listed as an open limitation that the benchmark's liveness had been established against the base model rather than against the two arms compared here. From the retained 200 draws per task per arm, that is now closed: **no task returns 0.00 or 1.00 for any arm; all 31 are strictly interior in both arms; none is within one draw (1/200) of a boundary.** The most extreme interiors are `ace_oss_24748` (trained .1900, Wilson lower bound .1417) and `ace_oss_16070` (trained .8400, Wilson upper bound .8843). Twenty-eight of 31 tasks sit inside the ruler's own [0.20, 0.80] admission band in *both* arms; the three exceptions — `ace_oss_16070`, `ace_oss_24748`, `ace_oss_27102` — fall outside by 4 pp or less, i.e., by 1 to 8 draws out of 200. The full table is Appendix C (Table C1).

The instrument was live where the comparison was made. The null is not a saturation artifact.

### Measurement-Integrity Failure 4: A Gate That Had Stopped Verifying

The dataset gate re-executes every preference pair before training and writes a receipt of file hashes that the trainer requires. It was found to be failing on its own corpus: 1,269 of 1,279 pairs verified, with 10 returning `no_matching_task`.

The cause was a scope error. The gate resolved tasks only from a hard-coded seed list, while ten pairs appended in a prior measurement had been drawn from a separately screened task pool. Those pairs were unverifiable in principle rather than merely stale, and re-running the gate — which the failure message advised — reproduced the same failure indefinitely.

The gate was extended to resolve tasks from the screened source through the same constructor used at screening time, restoring 1,279/1,279. The receipt was simultaneously extended to fingerprint the task source, on the reasoning that "0 violations" is a statement about a verifier *and a set of tasks*: while the task set was a literal inside the verifier file, the existing hash covered it incidentally; once tasks came from a data file, it no longer did. Tamper tests confirmed that corrupting either new fingerprint entry causes the gate to refuse. The positive-control run's own dataset gate re-verification, performed under a third interpreter (Python 3.12.10, on the environment described above), reproduced 1,279/1,279 with zero violations, giving a third independent confirmation of this corpus's integrity under three different interpreters.

A defect in the same machinery was surfaced by the replication: the fingerprint hashes working-tree bytes, and with `core.autocrlf=true` and no line-ending normalization in `.gitattributes`, the same source file hashes differently depending on how git materialized it. In a live reproduction, a file authored with LF endings hashed to `b28a47cb…`; checked out into a tree where git wrote CRLF, the same 1,485 bytes of source hashed to `15770d4d…` and the gate refused with a `VERIFIER-CHANGED` error, which reads exactly like tampering *(replication)*. Any clone with different line-ending settings, and any Linux or CI runner, hits this. This defect has now been fully resolved by introducing a `.gitattributes` file enforcing `eol=lf` across the repository, ensuring the dataset gate remains robust regardless of the host operating system.

### Measurement-Integrity Failure 5: A Reference Arm Measured on a Superseded Instrument

This one reached print. A previous draft of this article carried, in its abstract, a dedicated Results section, and its conclusion, the claim that the export and quantization path cost 3.3–3.8 pp of benchmark accuracy — more than the effect the study was designed to detect. **That claim is withdrawn.** It is an artifact, and it fails on two independent grounds, either of which is sufficient.

*There Was No Export Path in the Null Arm to Cost Anything.* As established in the Design, the null arm is the base model served with no adapter, from the same weight blob and the same template as the trained arm. Nothing was merged, dequantized, or re-quantized for either arm. The premise of the finding — that both arms traverse a lossy path whose cost is visible against the unmodified base — has no referent.

*The Measured Gap Was an Instrument Mismatch.* The base reference was scored 3.9 days before the arms, under the earlier metric, and its 50 replicates are not one population. Within the same base rows, greedy draws score .6323 and sampled draws .5047 — **+12.76 pp on the same model, the same tasks, and the same run.** The base arm also spans two verifier states: 10 rows banked before the interpreter pin (*M* = .5910) and 40 after it (*M* = .5150), with Welch between the two sub-populations at +7.60 pp, *t*(24.1) = 8.22, *p* = 1.9 × 10⁻⁸. They are not poolable.

Peeling both confounds gives a sampler- and verifier-matched base reference of *M* = .4905 (*SD* = .0476, *n* = 40). Against it, **trained is +0.71 pp** (*t*(76.6) = 0.71, *p* = .482) and **null is +0.16 pp** (*t*(69.1) = 0.17, *p* = .864). There is no deficit left to explain. The greedy anchor accounts for −2.55 pp of the apparent gap and pooling the pre-pin rows for a further −1.42 pp. Incidentally, the matched reference's *SD* of .0476 is exactly the figure the preregistration assumed as its sizing floor, and exactly the figure the positive-control preregistration inherited from it.

The mechanism is in code, and naming it is the point of reporting this as a failure rather than an erratum. `analyze_run1.load()` groups replicates by model name alone (`out.setdefault(r.get("model"), []).append(r)`), so all 50 base rows average together across two samplers and two verifier states. The measurement script refuses exactly this pooling for the arms and prints `ignoring N replicate(s) banked under a different verifier`. The guard exists; the analysis path did not inherit it. This does not touch the primary comparison, which never uses the base rows.

Two explanations previously left open are now closed rather than left standing. A chat-template or EOS defect between the arms is excluded by the byte comparison of the two served model definitions, which share a template and stop parameters, and by the shape of the difference profile: the common-mode component of trained − null is +0.55 pp and accounts for 0.49% of the total squared difference, with a 90% interval of [−0.84, +1.94] pp, whereas a template defect would be broad and one-sided. Session drift is excluded by measurement: serving the identical adapter file on different hardware two days later moved the trained arm by +0.42 pp (*p* = .642) and the null arm by +1.00 pp (*p* = .222), so session-to-session variance is on the order of 1 pp — far too small to be a 3.8 pp gap *(replication)*.

One loose thread is retained rather than resolved: the base arm shows a significant downward drift across its own run order (*r* = −.498, *t*(48) = −3.98, *p* = .0002; first half .5489 vs. second half .5115, Welch *p* = .0037), which is unexplained. The two served arms show no such drift. That is a reason not to treat the base arm as a clean reference even after matching, and it is why the base row appears in Table 1 as a reference rather than as a comparator.

### Measurement-Integrity Failure 6: A Statement-Level Residual in the Verdict Channel, Demonstrated and Closed

Failure 1's nonce fix shipped with its own honest residual, stated at the time and repeated in every draft's Limitations without ever being tested: "the nonce lives in a module global while the candidate runs in that same namespace, so code written deliberately against THIS harness could still read it back out." No earlier draft demonstrated this. This one does.

```python
print('__PASS__' + _NONCE)
raise SystemExit(0)
```

— a two-line candidate that never defines the requested function and never executes a single test — was accepted as a full pass (`res.ok = True`, `res.passed = res.total`) by the current, unmodified verifier on the `two_sum` seed task. The dynamic nonce cannot close this by construction, independent of how it is implemented: the candidate and any check written into the same namespace share that namespace on identical terms, so no string, however long, closes a channel the candidate can read directly.

What closes it is refusing to execute code that exhibits the pattern, before execution — the same move a statement-level taxonomy of malicious code makes for supply-chain security (Rahman et al., 2025a): classify specific syntactic patterns into named, independently checkable categories, rather than trust one broad heuristic. `harness_smells.py` implements three categories scoped to this harness's specific residual:

- **HARNESS_INTROSPECTION** — any reference to the harness's own internal names (`_NONCE` among them), or a call to `globals()`, `vars()`, or `locals()` with no arguments, which is exactly how a candidate would discover the nonce without hardcoding its name.
- **SENTINEL_FORGERY** — the literal string `__PASS__` appearing anywhere in candidate code. No task's intended solution ever needs to reference the harness's own protocol string.
- **PREMATURE_TERMINATION** — a call to `exit()`, `quit()`, `os._exit()`, or a `raise SystemExit`, anywhere in candidate code. No intended solution terminates the interpreter; this is exactly what both the original and the nonce-reading exploit use to skip real test execution.

Every candidate is walked as an abstract syntax tree and rejected, before the harness file is even assembled, if any category fires.

**Table 3b**

*Verifier Response to the Demonstrated Residual, Before and After the Static Check*

| Candidate | Before | After |
|---|---|---|
| Legitimate `two_sum` solution | pass | pass |
| Original Failure-1 sentinel guess | fail (nonce) | fail (nonce + 2 static categories) |
| Nonce-reading exploit (`_NONCE` referenced directly) | **pass** | fail (3 static categories) |
| Nonce-reading exploit via `globals()`, name not hardcoded | **pass** | fail (HARNESS_INTROSPECTION) |

Two controls were run before this was trusted. Exact-name matching was checked against a legitimate-looking candidate using an unrelated identifier that merely *contains* a watched substring (`_nonce_count`); it does not fire, confirming the detector matches whole names rather than performing text search. And `scan()` was checked against code that does not parse at all, returning an empty finding list rather than raising, so a candidate that fails to parse remains the execution path's problem to report, not this static check's.

**HONEST RESIDUAL, same shape as before.** This is defense in depth, not a sandbox, exactly like the check it sits beside: a sufficiently indirect construction — building the sentinel string one character at a time via arithmetic on character codes, for instance — is not claimed to be caught, and no data-flow analysis is performed. What this closes is the demonstrated exploit and its direct variants, the same scope the nonce itself claimed for the class it closed in Failure 1. Genuine isolation — a separate process for the candidate, or a runner it cannot introspect at all — remains the only way to close the class rather than the instance, and remains undone. Section "Relation to Security-Smell and Verified-Generation Research," below, names a stronger alternative this article does not implement.

### Measurement-Integrity Failure 7: A Recorded Configuration That Did Not Govern the Run

The six failures above concern the verdict channel and the analysis path. The seventh, found while tracing the initialization for this revision, concerns the training record itself, and it has the same shape: four fields that a reader would take as descriptions of what ran, three of which are not.

`training_args.bin` records `seed = 42`. The seed did not reach the adapter's initialization (Method), so the field is true of the data order and false of the thing a reader checking reproducibility would care about. It records `gradient_checkpointing = False`; checkpointing is nonetheless active, because `train_native.py` calls `prepare_model_for_kbit_training`, whose default enables it, and every training log carries the resulting `use_reentrant` warning. It records `warmup_steps = 0` beside `warmup_ratio = 0.1`, which reads as "no warm-up" and is not — the run has six warm-up steps at 57 total, or eighteen at 171. And it records `optim = "adamw_bnb_8bit"`, whose update is not Adam everywhere, for the reason given next. `run_meta.json`, written by the training script itself, records every hyperparameter and no library versions and no seed at all.

None of these is a bug in the sense of raising an error, and none changes a reported number. They are recorded here because the article's thesis is about components that emit well-formed values after they stop describing what happened, and a training-configuration dump is such a component. The repair is to write the *effective* configuration — `torch.initial_seed()` after the model is wrapped, the checkpointing flag as resolved, the realized warm-up step count, and the installed versions of torch, TRL, transformers, PEFT and bitsandbytes — rather than the requested one.

### An 8-Bit Optimizer Artifact Localized by a Massive-Activation Channel

The `adamw_bnb_8bit` entry above is not merely mis-descriptive. Scanning all 224 `lora_A` tensors of the positive-control adapter for elements that moved further than an exact Adam optimizer could have moved them — the bound is the initialization box plus 3.16·Σ*lr* = 0.0547 for that run's schedule — returns exactly one tensor: `layers.1.mlp.down_proj.lora_A`, with 169 such elements. All 169 lie in the columns [2304, 2558], spread over 93 distinct columns and all 16 rank rows; the largest reaches |*a*| = 0.175, twenty-one times the initialization bound of 1/√14336 = 0.0084 and three times the worst-case Adam displacement. Mean per-column max |*a*| is 0.058 inside that window and 0.009 outside it. No other tensor in the adapter has a single such element, and the layer's *B* factor stays well inside its own bound.

Two facts locate the cause. The window is the ninth 256-element block of the row-major tensor, and 256 is the block size bitsandbytes 0.50.1 uses to quantize optimizer state (`functional.py:940`, `optimizer.py:524`; Dettmers et al., 2022). And a single forward pass of the base model on a code prompt shows that the intermediate channel feeding `down_proj` column 2427 — inside that window — carries an activation of magnitude 386, against 46 for the next largest channel and a median of 0.013 across the layer's 14,336 channels: a massive activation of the kind Sun et al. (2024) describe, in the early-layer `mlp.down_proj` where the super-weight literature reports them (Yu et al., 2024, whose index does not include Llama-3-8B; the coordinate here is measured, not cited). Because ∂*L*/∂*A*[:, *j*] scales with the *j*-th input activation, that channel's second-moment state dominates the absmax of its 256-element quantization block, and its neighbours' states underflow the 8-bit dynamic format, inflating their effective step size. The mechanism is inferred from the exact block alignment and the activation measurement; it has not been demonstrated by ablation, and the one-flag test — retrain at a fixed seed with `optim="adamw_torch"` — is listed in *Planned Experiments*.

The artifact's functional weight is small: the window holds 70.4% of that layer's ‖Δ*W*‖²_F (1.8% would be uniform) but 0.94% of the whole adapter's, and in an activation-weighted forward pass the layer's entire adapter contribution is channel 2427's, because the 255 inflated neighbours multiply activations near zero. The adapter's delta at that layer is 0.58% of the base layer's output. So this is a real defect in weight space and a nearly inert one in function space — which is precisely why it matters for the analyses in this article and in the LoRA-geometry literature: cosines, Frobenius norms, and intruder-dimension counts computed over QLoRA adapters trained with 8-bit optimizer state on a model with a massive-activation channel are measuring, in part, a quantization artifact. A side consequence is worth stating: because the super activation is prompt-invariant, the LoRA on that layer acts largely as a learned constant offset injected into the residual stream.

### The Arms Were Different Models, and the Difference Was Redistribution

A null between two arms is uninterpretable if the arms might be the same model. Three independent lines establish that they were not.

*Artifact Chain.* The `ADAPTER` line in the live trained model names blob `sha256-4107cf60…436a`, which is character-for-character the SHA-256 computed over the exported `adapter.gguf` (83,917,120 bytes). That file was converted tensor-for-tensor (448 = 448) from the safetensors checkpoint whose digest `f416f3f9…` the preregistration recorded 26 minutes before the first replicate. Ollama names blobs by content digest.

*Behavioral, Whole Profile.* Permuting whole replicate rows between arms (20,000 relabelings), the summed per-task χ²(1) statistic is **observed 84.92** against a permutation null of mean 32.21, *SD* 7.99, 95th percentile 46.25, and **maximum 76.58** — *p* < 5 × 10⁻⁵, the observed value exceeding every one of 20,000 permutations. Two tasks survive Bonferroni correction at .05/31: `ace_oss_32606` (.335 vs. .505, *p* = .00057) and `ace_oss_23132` (.615 vs. .765, *p* = .00118).

*Behavioral, Independent Counter.* The arms differ in how often they emit code that raises `NameError` on an unimported typing annotation: trained 463/6,200 draws (7.47%) versus null 515/6,200 (8.31%); on the 40 per-run counts, *t*(77.9) = −2.74, *p* = .0077 (permutation *p* = .0092; Mann–Whitney *p* = .0137).

The shape of the difference matters for what the null means. The common-mode component of trained − null is +0.55 pp and explains **0.49%** of the total squared difference; the signs split 15 up, 14 down, 2 flat (sign test *p* = 1.0); and the *SD* of the per-task delta expected from sampling noise alone, if the arms were the same model, is 4.69 pp against an observed 7.93 pp — implying a **true per-task effect *SD* of 6.39 pp**. Run-level dispersion is close to the independent-Bernoulli prediction in both arms (ratios 1.11 and 0.87), so no large over-dispersion is inflating this.

The adaptation moved behavior around, task by task, without moving the mean. "No aggregate effect" and "no effect" are different claims, and only the first is supported.

A further robustness check sharpens rather than merely survives. Re-running the primary comparison on the harness's own upper-bound metric, which forgives unimported-typing failures, gives trained .5723 (*SD* .0403) versus null .5752 (*SD* .0302): −0.29 pp, *t*(72.3) = −0.36, *p* = .717. The sign flips. The entire +0.55 pp raw difference is carried by the trained arm making fewer unimported-typing errors, and none of it by solving more tasks — the null result is *more* null on the confound-free metric.

### Training-Data Concentration

Because a repetitive training corpus would render a null result ambiguous — indistinguishable from a corpus consisting of one program repeated — structural concentration was measured before the comparison was interpreted. Programs were parsed and their identifiers canonicalized before hashing, so that renaming does not create apparent diversity.

**Table C1**

*Concentration of the 918-Pair Training Bank*

| Level | Clusters | Effective count | Largest share |
|---|---|---|---|
| Task identifier | 13 | 9.93 | 13.1% |
| Chosen, exact text | 407 | 165.64 | 8.5% |
| Chosen, canonical structure | 273 | 90.41 | 9.8% |
| Rejected, canonical structure | 632 | 441.59 | 4.2% |
| (Chosen, rejected) contrast | 767 | 666.41 | 1.4% |

The task-level row reproduces an independently published figure from the corpus builder (effective task count 9.93) to the reported precision, serving as a control on the estimator before its novel rows are trusted.

Preference optimization trains on the *contrast* between chosen and rejected, and at that level the corpus is diverse: 767 distinct contrast structures across 918 pairs, largest cluster 1.4%. The apparent concentration on the chosen side reflects 13 tasks with converging correct solutions, which is what correctness entails. The corpus is therefore narrow but not collapsed, and the null result is not attributable to structural repetition. Task breadth — 13 tasks, effective count 9.93 — remains the binding constraint on what any result here can generalize to, and it binds the retrain result in Table 2, and the positive-control result above, exactly as much as it binds the null.

### Information Discarded by Pair-Primary Pipelines

A subsidiary finding concerns pipeline economics rather than the comparison. The pipeline sampled *K* candidates per task and emitted at most one preference pair, discarding the remainder. On tasks where every candidate passed, it emitted nothing and recorded the attempt as producing no signal. Instrumentation established that 66% of task attempts produced no training row and that only 16.9% of paid-for generations reached one.

This is a property of the preference-pair format, not of the data. A pair requires both a success and a failure; supervised fine-tuning requires only a success; and prospect-theoretic alignment (KTO; Ethayarajh et al., 2024) requires only a label, making a task on which everything failed a source of genuine negative signal rather than waste. A task with four passing candidates yields zero preference pairs and four supervised examples from generations already purchased and already verified.

The pipeline was accordingly restructured so that an immutable per-candidate trace is primary and each training format is a pure derivation over it. A view can always be rebuilt from the trace; a trace cannot be rebuilt from a view, so emitting pairs first destroys exactly what any alternative objective would require. Unit tests fix the property: four passing candidates yield 0 pairs and 4 supervised rows; four failing candidates yield 4 labeled negatives; and a timed-out candidate never becomes a `rejected` half, a timeout being an absence of information rather than a wrong answer.

The same argument applies to the raw emissions the old builder discarded, and that omission is now visible in the training data itself: because no pair retains what the policy actually emitted, every optimization target in this study's corpus is a reconstruction (see Method, Training data).

---

## Discussion

The trained adapter did not beat its null baseline, the interval excludes effects of the size the study was powered to detect, and the comparison replicated on independent hardware. Three readings were available when only that much was known, and they implied different next actions. Two of them can now be settled.

**The First Reading — That DPO Does Not Help Here — Is Contradicted.** Three adapters retrained from the same code, corpus, and configuration beat the null by +9.7 to +11.0 pp, each at *p* < 10⁻⁹, with instrument drift excluded by a same-session control. Whatever this pipeline's limits are, "the method produces no benchmark movement" is not one of them. Earlier drafts declined this reading on the grounds that a single checkpoint carries zero training-seed variance by construction; that caution was correct, and the retrains are what it was cautioning about.

**The Second Reading — That the Training Signal Was Too Narrow to Transfer — Is Weakened but Not Eliminated.** The corpus still spans 13 tasks with an effective count of 9.93, and the benchmark, though disjoint, is drawn from the same source distribution. But a corpus too narrow to transfer should be too narrow for every adapter trained on it, and three of four adapters trained on it transferred. Narrowness now bounds *generalization beyond this distribution*; it no longer explains the original null.

**The Third Reading — That the Effect Was Real but Smaller Than 2.34 pp — Is Superseded by the Equivalence Result and Then by Table 2.** TOST rejects a true aggregate effect of ±2 pp or larger for the original adapter. That adapter's effect is small. Other adapters from the same recipe have effects an order of magnitude larger.

What is left is a fourth reading: **something in the original training run, and not the initialization draw, produced an adapter unlike the ones the same command produces now.** The seed is now positively exonerated rather than merely acquitted. Three unseeded runs, beginning in mutually orthogonal random subspaces, agree with each other to within 1.3 pp in aggregate and — the stronger statement this revision adds — agree task by task at the reliability ceiling of the instrument (Table 2b). A bad initialization draw cannot explain an outcome that three independent draws do not produce; and because we can now say *why* the draws do not matter at this recipe (Δ*W* = *B*·*A*₀ with *A*₀ frozen and random), the exoneration is mechanistic rather than statistical.

The candidate cause earlier drafts named is a silent Windows GPU timeout (`TdrDelay`) aborting CUDA kernels during the original run. The supporting datum is a local replication on the *original* software stack (PEFT 0.14) that beat its null by +10.3 pp (pass@1 .6194 vs .5161) after the timeout was mitigated. **This revision demotes that from a conclusion to a hypothesis**, for three reasons that we would rather state than have a reader find. It rests on a single reported comparison, without the replicate-level treatment Table 2 receives, and it is the one result in this article that is reported only in prose. The vendor documentation for the mechanism does not describe it as silent: Microsoft's WDDM documentation and NVIDIA's own note state that after a timeout the engine or adapter is reset and the CUDA context begins reporting errors, so "a TDR that raised no exception" requires a specific path — plausibly the Windows 8-and-later per-engine reset with packet resubmission — that nobody has characterized for a PyTorch training loop. And the artifact evidence is equivocal in a way the profile analysis now makes visible: the null adapter's per-task profile is weakly reliable and unrelated to the retrains' (Table 2b), which is consistent with a corrupted update but equally consistent with several other failure modes, and no published work distinguishes a hardware-corrupted fine-tune from a merely different one on the basis of its behavior or its weights.

We therefore conclude only that the original run differed from the retrains in something other than its seed, that a silent driver-level abort is the leading named candidate, and that the general lesson stands independently of which candidate is right: an execution-grounded pipeline is only as objective as the hardware executing it, and when prevention is unavailable the honest fallback is detection — the posture the positive-control run adopts, and the one the silent-data-corruption literature (Ma et al., 2025; Altenbernd et al., 2026) arrives at for datacenter training, where nobody has yet looked at a consumer GPU under a display driver.

**A second general lesson, new to this revision, concerns what the gain was made of.** Roughly half of the retrains' benchmark movement was the model learning to satisfy a property of the verifier — an import required by the pinned interpreter, on prompts whose annotated signatures invite its omission — rather than a property of the task. The behavior is not in the training corpus, which contains no import statement in any of its 1,836 halves, so the pipeline did not teach it; the preference signal selected among modes the base model already had, which is what verifiable-reward training is increasingly understood to do (Yue et al., 2025). The construct-valid effect survives at +3.7 to +5.7 pp, and the practice we would recommend from this is narrow and cheap: before attributing a benchmark delta to a training intervention, decompose it against the failure modes the verifier itself imposes, using counters the harness can record for free. The reward-hackability literature audits verifiers that accept wrong programs (Rajan, 2026; Ray, 2026); the mirror-image error — a verifier that rejects right ones for an environmental reason, and a model that learns to clear it — is the same class of failure and, on this evidence, the more likely one when a pipeline's training and evaluation prompts come from different distributions.

### On the Value of the Null

The result's usefulness rests on the apparatus, not on the number. Seven components of that apparatus were found to be reporting confidently while not measuring: a verdict channel the candidate could write, a residual in that same channel that survived the first fix and was only demonstrated as exploitable in a later revision, a verifier whose ground truth depended on its caller, a benchmark at its ceiling, a gate certifying data it could no longer parse, an analysis path that pooled a reference arm across two instruments, and — added here — a training-configuration record whose seed, checkpointing flag, warm-up count, and optimizer name did not describe the run they were written for. Each produced well-formed output. None raised an exception. Any of the first four would have yielded a publishable-looking number with no content; the fifth did, in a previous draft of this article, for several weeks; the sixth's *fix* did, in the form of an unverified claim that a container already existed, for every draft before this revision's predecessor; and the seventh's `seed = 42` is why two drafts of this article said the initialization was uncontrolled without being able to say why.

An eighth belongs here in substance if not in form, because it is the one that changed a headline number. The retrain gain of +8.8 to +10.9 pp was not a measurement failure in the sense of the others — the instrument reported exactly what it was built to report — but it was a *construct* failure: about half the movement was the model clearing an environmental check rather than solving more tasks, and the article stated the whole of it as evidence that the pipeline transmits adaptation. The harness had recorded the counter that decomposes it since before the retrains were run. Nobody had applied it to those arms. The lesson we take is that a free diagnostic left uncomputed is indistinguishable, in its effect on a published claim, from a diagnostic that does not exist.

That last point is not a confession appended for candor. It is the strongest available evidence for the article's thesis. The Failure 5 defect was found by a reader who recomputed a published figure from the raw rows rather than reading the number, which is the only procedure that would have caught it. The Failure 1 container claim was found the same way, applied to prose instead of arithmetic: by reading the file the claim described rather than the sentence describing it. Every earlier draft's arithmetic was correct; every published statistic reproduced from the raw rows to four decimal places. Neither defect was in the calculation. Both were in what had been silently asserted — pooled data in one case, an unbuilt container in the other — before the calculation, or the claim, began.

We take the general lesson to be that in execution-grounded training the objectivity of the reward is the easy part. A test suite genuinely does decide correctness without appeal to opinion, though execution verified code can still be flawed or insecure (Liu et al., 2023). What is not thereby guaranteed is that the verdict which reaches the training file is the verdict the interpreter produced, and every failure documented here lived in that gap. The literature on reward hacking concerns itself largely with optimization pressure discovering unintended maxima of a specified objective (Amodei et al., 2016; Gao et al., 2023; Skalse et al., 2022). The failures reported here required no optimization pressure at all — they were latent in the plumbing, and one of them, demonstrated for the first time in this revision, was exploitable by a two-line literal that needed only to read a variable already sitting in its own namespace.

This suggests two practices. For any automated reward, the channel carrying the verdict should be treated as adversarial with respect to the artifact being judged, independently of whether that artifact is believed to be adversarial; the candidate need not intend to cheat for a writable verdict channel to corrupt a dataset. And no two measurements should be compared until something mechanical has confirmed they were produced by the same instrument — the guard that would have caught Failure 5 already existed in this codebase and simply was not on the path the published figure took, and the same class of guard, elsewhere in this codebase, is what caught this revision's own mid-run edit to the verifier before it could corrupt a row.

### Relation to Security-Smell and Verified-Generation Research

The failures reported here have direct counterparts in adjacent software-security research, and naming them situates this project's methodology rather than merely decorating it.

Rahman et al.'s work on security smells in configuration scripts and shared code (2019, 2021) treats a detectable-but-unexploited pattern — a hard-coded secret, a disabled certificate check — as a defect in its own right, independent of whether anyone has yet exploited it. That is exactly the posture Failure 6 takes toward the nonce residual: the pattern was named as a smell at the time of the nonce fix, and this revision's contribution is to show the smell was load-bearing rather than cosmetic, the same escalation their replication study made for IaC scripts (2021) — a re-run, under different conditions, surfacing what the original methodology had named but not demonstrated. Their finding that automated secret-detection tooling is "not enough… it's not just about false positives" (Rahman et al., 2022) is the same argument this article makes about execution-grounded reward in different words: a tool that reports confidently against its own stated metric can still fail at the thing it exists to guarantee, for reasons the metric never surfaces. And their case that security metrics are worthless before the measuring instrument is itself validated — "if you cannot measure it, you cannot secure it" (Rahman et al., 2025c) — is this article's noise-floor and benchmark-ceiling methodology, restated for a different kind of instrument and a different kind of measurement.

A separate strand of that group's current work points at a stronger remedy than the one this article implements. Rahman et al.'s work on AI-assisted, Dafny-based formally verified code generation (2026) pairs generation with a machine-checked proof of correctness against a specification, rather than sampling behavior against a finite, hidden test suite. Every failure in this article's verifier — a forgeable channel, an interpreter-dependent harness, a namespace a candidate can read from — is a failure specific to *execution-based* verification, where a candidate and its judge necessarily share a runtime. A specification the candidate cannot satisfy by exploiting the harness's own execution environment closes the entire class Failure 6 has only narrowed to its currently demonstrated instances. Adopting that approach here would require a formal specification per benchmark task in place of a hidden assert-based test, which this project's 31-task ruler does not have and this revision does not attempt to build; it is named as the more principled fix this project's own defense-in-depth posture has, so far, deliberately deferred rather than solved, in the same spirit `domains/sql/runtime.py`'s own comment already names for a different verifier in this codebase.

Two of the group's evaluation-methodology papers bear on this article's own instrument discipline without being adopted outright. Their comparison of coarse- versus fine-grained LLM-based malicious-package detection (2026b) is the same distinction Failure 5 turns on — an aggregate number (base-model pass rate, pooled across two verifier states) hid a fine-grained confound (the interpreter pin) that only a per-row audit surfaced — restated as an evaluation-methodology finding in a different domain rather than adopted as a technique here. Their self-reflection loop for turning threat intelligence into deployable detection rules (2025b) is structurally close to this pipeline's own actor-verify-pair loop, aimed at a different artifact; noting the structural similarity does not constitute using their method, and none of their specific techniques were implemented in this pipeline beyond the statement-level classification approach credited above.

### Relation to Data-Quality Concerns

An adjacent hazard is that verified correctness and data diversity are separable properties. Execution filtering guarantees that retained programs pass their tests; it does not prevent the retained set from being behaviorally repetitive, and exact deduplication does not detect renaming. This concern is sharpened by evidence that training on recursively generated data degrades models when diversity collapses (Shumailov et al., 2024). In the present corpus the concern was tested and not substantiated at the contrast level, though the corpus is narrow at the task level. We note it as a variable requiring independent measurement rather than an assumption inherited from the presence of a verifier.

---

## Limitations

The following constrain interpretation and are stated as bounds on the claim rather than as caveats.

1. **One checkpoint per arm in the primary comparison, and it was unseeded.** The primary result cannot support a claim about DPO as a method; it characterizes one adapter, drawn from a distribution the code does not control. This is now measured rather than assumed, and its mechanism traced to a library call order (see Method and Results).
2. **The replication replicates the measurement, not the training.** Both the original run and the replication of it serve the same adapter GGUF, verified by hash on both machines. Training-seed variance is zero in both.
3. **Which stack variable is worth 10 pp is not isolated**, though the search space is now smaller. The retrains differ from the original run in GPU, CUDA/torch stack, at least one library version, and initialization; initialization is excluded by Table 2b, since three orthogonal draws produce one function. No version matrix has been run, and no claim is made that any particular library caused the difference.
3a. **The typing decomposition is an upper bound, not a re-execution.** `aggregate_if_typing_imported` counts a failure as a pass when its only error is a `NameError` on a `typing` name; it does not re-run the completion with the import supplied, so a completion that would fail for a second reason after the import is credited anyway. The construct-valid gains of +3.7 to +5.7 pp are therefore lower bounds on the artifact's share and upper bounds on the residual effect. A re-execution arm would settle it and has not been run.
3b. **Where the import behavior came from is not established.** It is absent from all 1,836 halves of the training corpus, and a 15-draw probe of the one locally retained adapter against its null suggests the adapter completes an import the base model already emits about half the time rather than suppressing annotations. That probe used a chat template that is not the harness's, and it is offered as a mechanism to test, not a finding.
3c. **The 8-bit optimizer artifact is localized, not explained.** The block alignment and the massive-activation channel are measured on this machine; the quantization mechanism connecting them is inferred. The ablation that would demonstrate it (`adamw_torch` versus `adamw_bnb_8bit` at a fixed seed) has not been run, and the Llama-3-8B super-weight coordinate is measured here rather than taken from a published index, which does not list that model.
4. **Narrow task distribution.** 13 training tasks, effective count 9.93; 31 benchmark tasks from one source corpus, one programming language. This bounds the retrain result, and the positive-control result, exactly as much as it bounds the null.
5. **Benchmark responsiveness is verified at these two arms' operating points**, not at arbitrary ones. Within that scope it is fully discharged: 31 of 31 tasks strictly interior, none within one draw of a boundary.
6. **The verifier is closed against the demonstrated exploit and its direct variants, not against the class.** Failure 6's static check refuses the residual named at the time of the nonce fix and shown, in this revision, to be live. It is defense in depth, not a sandbox: a sufficiently indirect construction of the sentinel string is not claimed to be caught, and no data-flow analysis is performed. Genuine isolation — a separate process or an unintrospectable runner for the candidate — remains undone, and a formally verified alternative to execution-based checking entirely is named in the Discussion rather than implemented.
7. **The dataset receipt is unsigned**, and its fingerprint is line-ending dependent (Failure 4). It defends against drift and accident, not against modification of the receipt itself, and it produces false refusals across clones with differing line-ending configuration.
8. **No replicate row attests which model served it.** The rows carry no model digest, adapter hash, Ollama version, generation seed, prompt, or completion. The chain from row to served model is artifact-level plus statistical, not per-row. Enumerating every field present across all rows and probing for thirteen such keys returns none.
9. **Raw completions were never retained**, so exact-output agreement between arms is not computable for either run and cannot be computed retroactively. The longest string anywhere in the retained rows is 61 characters (a filesystem path).
10. **Replicate-identifier bookkeeping in the replication arms is imperfect.** The interleaved driver's resume logic produced duplicate replicate identifiers in both replication arms (trained: 41 rows across 35 distinct identifiers; null: 40 rows across 35). Each row remains an independent 155-generation measurement and the arm-level statistics are unaffected, but the identifiers cannot be used for pairing. Relatedly, one arm-summary file distributed with the replication quotes *n* = 40 and +0.07 pp; the shipped data contains 41 trained rows and gives −0.03 pp. Both are null and the discrepancy is a timing artifact — the summary was generated before the final replicate landed — but the figures reported here are recomputed from the data rather than copied from the summary.
11. **Coverage claims are bounded by their mechanisms.** Where this article reports that a class of defect was closed, the claim extends to what the corresponding automated check enforces on every run, and no further.
12. **Findings 1, 4, and 6 were repaired by the authors of the code under test.** Findings 5 and the unseeded-initialization result were identified by an independent party working from the retained artifacts; their repairs are not yet implemented. The container claim withdrawn from Failure 1 in this revision was identified by the authors themselves, on a re-read of the code prompted by preparing this revision, not by an outside party — a fact stated here because it bears on Limitation 11's honesty rather than on any technical claim.
13. **The positive-control run is paused at 9 of 40 replicates per arm, with three recorded deviations.** Training, export, and both event-log safety-gate passes are done; the interleaved evaluation stopped when the machine rebooted uncleanly mid-round. The verifier fingerprint on every banked row differs from the preregistered one, the resumed rows will constitute a second session, and the arm's interim aggregate was seen during the profile analysis. All three are recorded in `data/prereg_positive_control_amendment_2026-08-22.json`, written before further scoring, and reported in the Results rather than resolved by editing the preregistration.
14. **Two claims in this article rest on a single unreplicated observation each.** The TDR-mitigated +10.3 pp local replication is reported in prose without replicate-level statistics, and the 15-draw import probe of Limitation 3b is a mechanism sketch. Both are labelled as such where they appear; neither carries a conclusion on its own.
15. **The behavioral-equivalence claim is bounded by the instrument.** Table 2b establishes that three orthogonal adapters are indistinguishable *on this 31-task benchmark at 40 replicates*, with disattenuated correlations at or slightly above 1.0 — a value greater than 1 is a reminder that the reliability correction is itself estimated, not evidence of super-perfect agreement. It does not establish equivalence out of distribution, on other tasks, or at other ranks and learning rates; the positive control already shows the agreement fails at 40× the learning rate.

---

## Conclusion

Execution-verified preference training on 918 pairs produced no detectable improvement over its own null baseline on a 31-task frozen benchmark: +0.55 pp, 95% CI [−1.12, +2.21], against an achieved sensitivity of 2.34 pp, with equivalence testing rejecting any true aggregate effect of ±2 pp or larger. The comparison replicated on independent hardware with the arms interleaved: −0.03 pp, *p* = .975.

That null belongs to one adapter. Retraining from the same code, data, and configuration produced a +8.8 to +10.9 pp improvement three times out of three — of which 48% to 58% is the adapters learning to emit an import that the pinned verifier requires and the benchmark's annotated prompts invite omitting, a statement that appears in none of the corpus's 1,836 halves. Decomposed against that counter, the effect is +3.7 to +5.7 pp, still above the preregistered minimum detectable effect of 2.98 pp and significant in all three runs, and concentrated on two of thirty-one tasks. Half of a headline number was a property of the instrument, and the counter that shows it had been recorded on every row since before those runs were scored.

The training script that produced all four adapters sets no seed, and this revision says why: TRL wraps the model with PEFT before the `Trainer` constructor sets the seed, so the adapter's input factor is the one unseeded draw in an otherwise seeded graph, in a call order shared by TRL's DPO, SFT, and GRPO trainers as currently shipped. That factor then barely moves during training — 95.5% of its entries remain inside their initialization box even at forty times the studied learning rate — so each run's update is the same learned readout applied to a different random projection, and the measured cross-run cosine of 0.004 is *r*/*d*ᵢₙ, the value that geometry predicts. The three orthogonal adapters are nonetheless the same function: their per-task profiles agree at the reliability ceiling of a 40-replicate instrument, the same fifteen tasks rise and the same three fall, and the same two tasks carry the construct-valid gain. At this recipe the data determine what is learned and the initialization determines only the coordinates it is written in — which exonerates the seed as an explanation of the original null more firmly than the aggregate agreement alone could, and which fails at forty times the learning rate, where the same corpus produces the same mean through a demonstrably different solution.

Three claims from earlier drafts are withdrawn or demoted. An apparent 3.3–3.8 pp cost of the export and quantization path is withdrawn: the null arm traverses no such path, and the gap was a reference arm scored under a superseded sampler and pooled across two verifier states. A claim that the verdict-channel residual had been closed by containerization is withdrawn: the container did not exist, the residual was live, and a statement-level static check closes it instead. And the attribution of the original null to a silent GPU driver timeout is demoted from conclusion to leading hypothesis: it rests on one unreplicated comparison, the vendor documentation describes the mechanism as raising errors rather than staying silent, and the null adapter's per-task profile — weakly reliable, and unrelated to the direction every healthy run finds — is consistent with a corrupted update but does not distinguish it from other failures.

The methodological findings are the more transferable contribution. An objective reward is not a trustworthy reward; the interval between the interpreter's verdict and the training corpus contained seven independent mechanisms capable of reporting confidently while measuring nothing, one of which permitted a candidate program to certify its own correctness by reading a variable out of its own execution namespace, one of which recorded a seed that governed nothing, and two of which produced well-formed spurious claims — one arithmetic, one architectural — that survived into earlier drafts of this paper. Even the weights are not exempt: a single 256-element block of one adapter tensor moved further than its optimizer could have moved it, because an 8-bit quantization block happened to contain the model's massive-activation channel. Adjacent software-security research names the same shape of failure in different domains, under the language of security smells and tool-adequacy claims, and one strand of it — formally verified code generation — names a fix stronger than any implemented here. We recommend that execution-grounded pipelines treat the verdict channel as adversarial by default, measure benchmark noise floors and ceilings before reporting differences, decompose any measured gain against the failure modes the verifier itself imposes before attributing it to the task, refuse to compare any two measurements until a machine has confirmed they came from the same instrument, compare adapters in function space rather than weight space when the initialization is random, record the configuration that ran rather than the one requested, retain an immutable per-candidate trace so that the choice of training objective does not have to be made before the data are generated, verify every claim of a completed fix against the bytes it describes before publishing it — and set the seed *before the model is wrapped*, then prove it took.

---

## References

Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., & Mané, D. (2016). *Concrete problems in AI safety*. arXiv. https://arxiv.org/abs/1606.06565

Bouthillier, X., Delaunay, P., Bronzi, M., Trofimov, A., Nichyporuk, B., Szeto, J., Sepah, N., Raff, E., Madan, K., Voleti, V., Kahou, S. E., Michalski, V., Serdyuk, D., Arbel, T., Pal, C., Varoquaux, G., & Vincent, P. (2021). Accounting for variance in machine learning benchmarks. *Proceedings of Machine Learning and Systems, 3*, 747–769.

Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H. P. de O., Kaplan, J., Edwards, H., Burda, Y., Joseph, N., Brockman, G., Ray, A., Puri, R., Krueger, G., Petrov, M., Khlaaf, H., Sastry, G., Mishkin, P., Chan, B., Gray, S., … Zaremba, W. (2021). *Evaluating large language models trained on code*. arXiv. https://arxiv.org/abs/2107.03374

Dettmers, T., Lewis, M., Shleifer, S., & Zettlemoyer, L. (2022). 8-bit optimizers via block-wise quantization. *Proceedings of the 10th International Conference on Learning Representations*. https://arxiv.org/abs/2110.02861

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized LLMs. *Advances in Neural Information Processing Systems, 36*.

D'Amour, A., Heller, K., Moldovan, D., Adlam, B., Alipanahi, B., Beutel, A., Chen, C., Deaton, J., Eisenstein, J., Hoffman, M. D., Hormozdiari, F., Houlsby, N., Hou, S., Jerfel, G., Karthikesalingam, A., Lucic, M., Ma, Y., McLean, C., Mincu, D., … Sculley, D. (2022). Underspecification presents challenges for credibility in modern machine learning. *Journal of Machine Learning Research, 23*(226), 1–61. https://arxiv.org/abs/2011.03395

Dodge, J., Ilharco, G., Schwartz, R., Farhadi, A., Hajishirzi, H., & Smith, N. A. (2020). *Fine-tuning pretrained language models: Weight initializations, data orders, and early stopping*. arXiv. https://arxiv.org/abs/2002.06305

Ethayarajh, K., Xu, W., Muennighoff, N., Jurafsky, D., & Kiela, D. (2024). KTO: Model alignment as prospect theoretic optimization. *Proceedings of the 41st International Conference on Machine Learning*.

Gao, L., Schulman, J., & Hilton, J. (2023). Scaling laws for reward model overoptimization. *Proceedings of the 40th International Conference on Machine Learning*, 10835–10866.

Hayou, S., Ghosh, A., & Yu, B. (2024). *The impact of initialization on LoRA finetuning*. arXiv. https://arxiv.org/abs/2406.08447

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. *Proceedings of the 10th International Conference on Learning Representations*.

Kingma, D. P., & Ba, J. (2015). Adam: A method for stochastic optimization. *Proceedings of the 3rd International Conference on Learning Representations*. https://arxiv.org/abs/1412.6980

Lakens, D. (2017). Equivalence tests: A practical primer for *t* tests, correlations, and meta-analyses. *Social Psychological and Personality Science, 8*(4), 355–362.

Liu, J., Xia, C. S., Wang, Y., & Zhang, L. (2023). Is your code generated by ChatGPT really correct? Rigorous evaluation of large language models for code generation. *Advances in Neural Information Processing Systems, 36*.

Ma, J., Pei, H., Lausen, L., & Karypis, G. (2025). *Understanding silent data corruption in LLM training*. arXiv. https://arxiv.org/abs/2502.12340

McCoy, R. T., Min, J., & Linzen, T. (2020). BERTs of a feather do not generalize together: Large variability in generalization across models with similar test set performance. *Proceedings of the Third BlackboxNLP Workshop on Analyzing and Interpreting Neural Networks for NLP*, 217–227. https://arxiv.org/abs/1911.02969

Marx, C., du Pin Calmon, F., & Ustun, B. (2020). Predictive multiplicity in classification. *Proceedings of the 37th International Conference on Machine Learning*, 6765–6774. https://arxiv.org/abs/1909.06677

Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences, 115*(11), 2600–2606.

Picard, D. (2021). *Torch.manual_seed(3407) is all you need: On the influence of random seeds in deep learning architectures for computer vision*. arXiv. https://arxiv.org/abs/2109.08203

Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct preference optimization: Your language model is secretly a reward model. *Advances in Neural Information Processing Systems, 36*.

Rahman, M. R., et al. (2019). Share, but be aware: Security smells in Python gists. *Proceedings of the IEEE International Conference on Software Maintenance and Evolution (ICSME)*.

Rahman, M. R., et al. (2021). Security smells in Ansible and Chef scripts: A replication study. *ACM Transactions on Software Engineering and Methodology (TOSEM)*.

Rahman, M. R., et al. (2022). Why secret detection tools are not enough: It's not just about false positives — an industrial case study. *Empirical Software Engineering*.

Rahman, M. R., et al. (2025a). Unveiling malicious logic: Towards a statement-level taxonomy and dataset for securing Python packages. arXiv preprint.

Rahman, M. R., et al. (2025b). FALCON: Transforming cyber threat intelligence into deployable IDS rules with self-reflection. arXiv preprint.

Rahman, M. R., et al. (2025c). If you cannot measure it, you cannot secure it: A case study on metrics for informed choice of security controls. *Journal of Information Security and Applications*.

Rahman, M. R., et al. (2026a). From natural language to verified code: Toward AI-assisted problem-to-code generation with Dafny-based formal verification. arXiv preprint.

Rahman, M. R., et al. (2026b). Mind the gap: Evaluating LLMs for high-level malicious package detection vs. fine-grained indicator identification. arXiv preprint.

Rajan, S. (2026). *Auditing reward hackability in code RL training environments*. arXiv. https://arxiv.org/abs/2606.16062

Ray, J. (2026). *Before the model learns the bug: Fuzzing RLVR verifiers*. arXiv. https://arxiv.org/abs/2606.01066

Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Bi, X., Zhang, H., Zhang, M., Li, Y. K., Wu, Y., & Guo, D. (2024). *DeepSeekMath: Pushing the limits of mathematical reasoning in open language models*. arXiv. https://arxiv.org/abs/2402.03300

Shumailov, I., Shumaylov, Z., Zhao, Y., Papernot, N., Anderson, R., & Gal, Y. (2024). AI models collapse when trained on recursively generated data. *Nature, 631*, 755–759.

Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology: Undisclosed flexibility in data collection and analysis allows presenting anything as significant. *Psychological Science, 22*(11), 1359–1366.

Skalse, J., Howe, N. H. R., Krasheninnikov, D., & Krueger, D. (2022). Defining and characterizing reward hacking. *Advances in Neural Information Processing Systems, 35*, 9460–9471.

Summers, C., & Dinneen, M. J. (2021). Nondeterminism and instability in neural network optimization. *Proceedings of the 38th International Conference on Machine Learning*, 9913–9922. https://arxiv.org/abs/2103.04514

Sun, M., Chen, X., Kolter, J. Z., & Liu, Z. (2024). *Massive activations in large language models*. arXiv. https://arxiv.org/abs/2402.17762

Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika, 34*(1–2), 28–35.

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association, 22*(158), 209–212.

Yu, M., Wang, D., Shan, Q., Reed, C., & Wan, A. (2024). *The super weight in large language models*. arXiv. https://arxiv.org/abs/2411.07191

Yuan, W., Pang, R. Y., Cho, K., Li, X., Sukhbaatar, S., Xu, J., & Weston, J. (2024). Self-rewarding language models. *Proceedings of the 41st International Conference on Machine Learning*.

Yue, Y., Chen, Z., Lu, R., Zhao, A., Wang, Z., Yue, Y., Song, S., & Huang, G. (2025). Does reinforcement learning really incentivize reasoning capacity in LLMs beyond the base model? *Advances in Neural Information Processing Systems, 38*. https://arxiv.org/abs/2504.13837

Zhu, J., Greenewald, K., Nadjahi, K., Sáez de Ocáriz Borde, H., Bamler, R., Solomon, J., & Mitra, A. (2024). Asymmetry in low-rank adapters of foundation models. *Proceedings of the 41st International Conference on Machine Learning*. https://arxiv.org/abs/2402.16842

Zhuang, D., Zhang, X., Song, S. L., & Hooker, S. (2022). Randomness in neural network training: Characterizing the impact of tooling. *Proceedings of Machine Learning and Systems, 4*, 316–336. https://arxiv.org/abs/2106.11872

*Note on the Rahman citations above: these are working citations assembled from a Google Scholar author page during drafting, to the precision that page's listing provides (title and venue; several entries lack full author lists, volume, or page numbers as scraped). They should be checked against the primary source and formatted to the target venue's style before submission, exactly as any other citation would be — they are marked here rather than silently presented as complete, on this article's own stated principle that a claim ships with what it can currently support.*

---

## Appendix A

### Statistical Detail

Welch's *t*-test (Welch, 1947) was used rather than the pooled-variance alternative because the arms are not assumed to share a variance: a training intervention that changes the spread of outcomes has changed the model, and pooling would absorb that change into the denominator.

Given trained (*M* = .4976, *SD* = .0415, *n* = 40) and null (*M* = .4921, *SD* = .0327, *n* = 40):

- Difference: +0.55 pp
- Standard error of the difference: √(.041526²/40 + .032727²/40) = .00836039 (0.836 pp)
- Welch–Satterthwaite degrees of freedom: 74.0
- *t* = 0.0054825 / 0.00836039 = 0.655816
- Two-sided *p* = .514
- 95% CI: [−1.117496, +2.213996] pp

All figures in this appendix are computed from the unrounded per-replicate rates and then rounded for display. Recomputing them from the rounded means in Table 1 yields [−1.11, +2.22] and *p* ≈ .512; those are artifacts of display rounding and not the reported values. Every published figure in Table 1 and in the primary comparison is the correctly rounded form of the value recomputed from the raw rows, the largest deviation across an eighteen-figure comparison being 0.041 on the degrees of freedom.

Sizing at the preregistered *SD* of .0476 gives a standard error of 1.064 pp and a minimum detectable effect of approximately 2.8 × 1.064 = 2.98 pp at 80% power. The observed standard error of 0.836 pp corresponds to an achieved sensitivity of 2.34 pp. The positive-control preregistration inherits this sizing unchanged (same instrument, same *n*, same test), giving the same 2.98 pp MDE against its own +5.00 pp decision threshold.

**Supplementary tests on the primary contrast.**

| Test | Statistic | *p* |
|---|---|---|
| Welch's *t* (primary) | *t*(74.0) = 0.656 | .514 |
| Permutation, 200,000 relabelings | Δ = +0.548 pp | .518 |
| Mann–Whitney *U*, tie-corrected | *U* = 881.5, *z* = 0.786 | .432 |
| TOST at ±2.98 pp (preregistered margin) | — | .0024 (equivalent) |
| TOST at ±2.00 pp | — | .0433 (equivalent) |
| TOST at ±1.00 pp | — | .295 (not resolved) |
| Variance ratio | *F*(39, 39) = 1.610 | .141 |
| Brown–Forsythe on \|*x* − median\| | *t*(74.6) = 1.538 | .128 |
| Robustness: typing failures forgiven | *t*(72.3) = −0.364 | .717 |

The 90% (TOST) interval is [−0.844, +1.941] pp.

The *t* distribution was implemented directly (regularized incomplete beta by Lentz continued fraction; critical values by bisection on the resulting CDF). The implementation self-checks against known critical values — *t*₍.₉₇₅₎(10) = 2.2281 against a tabulated 2.228, *t*₍.₉₇₅₎(30) = 2.0423 against 2.042, *t*₍.₉₇₅₎(78) = 1.9908 against 1.991 — and aborts before reporting if any check fails. Every *p*-value reported in this article was additionally cross-checked against direct Simpson integration of the *t* density, agreeing to better than 5 × 10⁻¹⁴. The same implementation, independently re-derived rather than imported, underlies the decision-rule script for the positive-control run and self-checks against the same critical values before reporting anything.

## Appendix B

### Reproduction

All figures derive from retained artifacts. The comparison is reproduced by:

```
python verify_dataset.py                        # re-verify all pairs; write the receipt
python ruler_noise.py measure --runs 40 --model <arm>
python analyze_run1.py                          # the preregistered comparison
```

Reproducing the *training* additionally requires pinning the stack, because `train_native.py` passes `rpo_alpha` to `DPOConfig` and later TRL removed it:

```
pip install trl==0.12.2 transformers==4.46.3 tokenizers==0.20.3
python train_native.py
```

The positive-control run is reproduced the same way with two flags:

```
python train_native.py --lr 2e-4 --epochs 3 --out dpo_adapter_poscontrol
python export_adapter.py --adapter dpo_adapter_poscontrol --base-tag <base ollama tag> --name <arm name> --verify
python poscontrol\run_interleaved.py --rounds 40 --arms <positive-control tag> <null tag>
python poscontrol\poscontrol_verdict.py
```

on a CUDA 12.8-capable stack if the GPU is Blackwell-architecture or newer, which the original reproduction commands above do not require.

Two corrections to earlier drafts of this appendix. First, `python build_ruler.py verify` was listed as the first reproduction step; that subcommand does not exist. `build_ruler.py` accepts only `nominate`, `confirm`, and `freeze`, so a reader following the previous appendix failed at step one. Second, no library versions were stated anywhere in earlier drafts; the pins above are now mandatory rather than advisory.

Artifacts retained: the preregistrations (`data/prereg_track_a_run1.json`, `data/prereg_positive_control.json`); the frozen benchmark with its content hash (`data/ruler_frozen.json`); per-replicate raw outcomes (`data/ruler_noise.jsonl`); the verified corpus and its receipt (`data/dpo_pairs_capped.jsonl`, `data/dataset_verification.json`); the concentration measurement (`data/bank_concentration.json`); the adapter under test with its training metadata (`dpo_adapter_native/`); the positive-control adapter and its training metadata (`dpo_adapter_poscontrol/`); and the statement-level detector with its test suite (`harness_smells.py`, `tests/test_harness_smells.py`, `poscontrol/red_witness_nonce_exploit.py`).

Each replicate comprised 155 generations (31 tasks × 5 samples) and required approximately 151 s. The two primary-comparison arms together consumed 12,400 generations.

Two artifact-level gaps are named so that a replicator does not assume they were checked: the served Ollama blob was matched to the exported adapter by content-addressed *name* rather than by hashing the blob file itself, and the base reference model's own served definition was never captured, so "the base was served with the same template and stop parameters as the arms" is highly likely but unverified. Each closes with a single command on the machine holding the model store.

## Appendix C

### Per-Task Pass Rates at the Arms' Operating Point

Pooled over all replicates. Trained and null are 200 draws per task (40 replicates × 5 samples). "Base matched" is the sampler- and verifier-matched reference of Failure 5: the 40 base replicates carrying a verifier fingerprint, recomputed greedy-free, at 160 draws per task. Generated from `data/ruler_noise.jsonl` rather than transcribed.

| Task | Trained *k*/*n* | Trained | Null *k*/*n* | Null | T − N (pp) | Base matched *k*/*n* | Base matched |
|---|---|---|---|---|---|---|---|
| `ace_oss_11023` | 97/200 | .4850 | 76/200 | .3800 | +10.5 | 64/160 | .4000 |
| `ace_oss_11739` | 97/200 | .4850 | 104/200 | .5200 | −3.5 | 79/160 | .4938 |
| `ace_oss_14121` | 104/200 | .5200 | 121/200 | .6050 | −8.5 | 92/160 | .5750 |
| `ace_oss_15186` | 147/200 | .7350 | 129/200 | .6450 | +9.0 | 105/160 | .6562 |
| `ace_oss_15273` | 108/200 | .5400 | 107/200 | .5350 | +0.5 | 73/160 | .4562 |
| `ace_oss_16070` | 168/200 | .8400 | 162/200 | .8100 | +3.0 | 136/160 | .8500 |
| `ace_oss_17851` | 112/200 | .5600 | 92/200 | .4600 | +10.0 | 65/160 | .4062 |
| `ace_oss_17880` | 141/200 | .7050 | 114/200 | .5700 | +13.5 | 99/160 | .6188 |
| `ace_oss_19459` | 148/200 | .7400 | 158/200 | .7900 | −5.0 | 131/160 | .8188 |
| `ace_oss_19944` | 55/200 | .2750 | 63/200 | .3150 | −4.0 | 50/160 | .3125 |
| `ace_oss_21695` | 75/200 | .3750 | 60/200 | .3000 | +7.5 | 61/160 | .3812 |
| `ace_oss_23069` | 78/200 | .3900 | 55/200 | .2750 | +11.5 | 53/160 | .3312 |
| `ace_oss_23132` | 123/200 | .6150 | 153/200 | .7650 | −15.0 | 108/160 | .6750 |
| `ace_oss_23388` | 57/200 | .2850 | 74/200 | .3700 | −8.5 | 49/160 | .3062 |
| `ace_oss_2454` | 49/200 | .2450 | 49/200 | .2450 | +0.0 | 36/160 | .2250 |
| `ace_oss_24748` | 38/200 | .1900 | 56/200 | .2800 | −9.0 | 29/160 | .1812 |
| `ace_oss_27102` | 49/200 | .2450 | 38/200 | .1900 | +5.5 | 44/160 | .2750 |
| `ace_oss_28031` | 149/200 | .7450 | 121/200 | .6050 | +14.0 | 93/160 | .5812 |
| `ace_oss_28113` | 58/200 | .2900 | 53/200 | .2650 | +2.5 | 53/160 | .3312 |
| `ace_oss_31420` | 139/200 | .6950 | 139/200 | .6950 | +0.0 | 98/160 | .6125 |
| `ace_oss_31439` | 137/200 | .6850 | 140/200 | .7000 | −1.5 | 113/160 | .7062 |
| `ace_oss_3243` | 62/200 | .3100 | 72/200 | .3600 | −5.0 | 61/160 | .3812 |
| `ace_oss_32606` | 67/200 | .3350 | 101/200 | .5050 | −17.0 | 65/160 | .4062 |
| `ace_oss_33450` | 64/200 | .3200 | 61/200 | .3050 | +1.5 | 48/160 | .3000 |
| `ace_oss_34760` | 72/200 | .3600 | 83/200 | .4150 | −5.5 | 73/160 | .4562 |
| `ace_oss_35622` | 150/200 | .7500 | 133/200 | .6650 | +8.5 | 120/160 | .7500 |
| `ace_oss_36489` | 118/200 | .5900 | 113/200 | .5650 | +2.5 | 81/160 | .5062 |
| `ace_oss_4327` | 103/200 | .5150 | 109/200 | .5450 | −3.0 | 99/160 | .6188 |
| `ace_oss_4862` | 131/200 | .6550 | 118/200 | .5900 | +6.5 | 100/160 | .6250 |
| `ace_oss_633` | 111/200 | .5550 | 116/200 | .5800 | −2.5 | 94/160 | .5875 |
| `ace_oss_869` | 78/200 | .3900 | 81/200 | .4050 | −1.5 | 61/160 | .3812 |
| **Pooled** | 3085/6200 | **.4976** | 3051/6200 | **.4921** | **+0.55** | 2433/4960 | **.4905** |

*Note.* Lowest rate over both arms .1900, highest .8400. Tasks at exactly 0.00 or 1.00 in any arm: 0. Both arms inside the [0.20, 0.80] admission band: 28 of 31; the exceptions are `ace_oss_16070`, `ace_oss_24748`, and `ace_oss_27102`.

## Appendix D

### The Statement-Level Detector (Failure 6)

**Table D1**

*harness_smells.py's Three Categories*

| Category | Trigger | Legitimate-solution false-positive risk |
|---|---|---|
| HARNESS_INTROSPECTION | reference to `_NONCE` or any harness-internal name; `globals()`/`vars()`/`locals()` called with no arguments | none observed; exact-name match, not substring (Table D2, control 1) |
| SENTINEL_FORGERY | the literal string `__PASS__` anywhere in candidate code | none expected; no task prompt or intended solution has reason to reference the harness's own protocol string |
| PREMATURE_TERMINATION | `exit()`, `quit()`, `os._exit()`, `raise SystemExit` | none expected; no seed task requires terminating the interpreter |

**Table D2**

*Controls Run Before Trusting the Detector*

| Control | Design | Result |
|---|---|---|
| 1. Substring vs. exact-name matching | Candidate defines a legitimate-looking local variable `_nonce_count` that contains but does not equal a watched name | 0 findings — confirms AST name matching, not text search |
| 2. Malformed input | `scan()` called on code that raises `SyntaxError` on parse | Returns `[]` rather than raising — a candidate that fails to parse remains `forge.py`'s execution path's problem to report |
| 3. Legitimate solution, unaffected | A correct `two_sum` implementation | `res.ok = True`, `res.passed = res.total` — no regression |

Scope statement, restated from the Results: this closes the demonstrated exploit (direct `_NONCE` reference, and dynamic discovery via `globals()`) and direct textual variants of the sentinel and termination patterns. It is not claimed to close indirect constructions of the sentinel string (e.g., built from character codes) or any exploit that does not require referencing a watched name, calling a watched function, or containing a watched literal. The formally verified alternative named in the Discussion is the path to closing the class rather than the instance.

---

## Appendix E

### Per-Task Delta Profiles and the Typing Decomposition

Per-task pass-rate change against each arm's same-session null, pooled over that arm's replicates. "Typing" is the share of null-arm draws on that task whose only failure was a `NameError` on an un-imported `typing` name, pooled over the three null arms (12,090 draws). Raw and forgiven columns are the primary metric and the upper-bound counterfactual of the Method. Generated from `data/ruler_noise.jsonl`, not transcribed.

**Table E1**

*Per-Task Delta (Percentage Points) by Arm and Metric*

| Task | Typing | R1 raw | R2 raw | R3 raw | R1 fgv | R2 fgv | R3 fgv | Orig fgv | PosCtl raw | PosCtl fgv |
|---|---|---|---|---|---|---|---|---|---|---|
| `ace_oss_11023` | 52.9% | +56.0 | +50.5 | +42.7 | +0.0 | +0.0 | +0.0 | +0.0 | +53.3 | +0.0 |
| `ace_oss_11739` | 0.0% | -0.5 | +2.0 | +6.7 | -0.5 | +2.0 | +6.7 | +2.7 | +64.4 | +33.3 |
| `ace_oss_14121` | 0.0% | -0.2 | +3.3 | -1.3 | -0.2 | +3.3 | -1.3 | +1.3 | -6.7 | -6.7 |
| `ace_oss_15186` | 2.9% | +7.8 | +10.3 | +10.7 | +6.5 | +9.0 | +5.3 | -1.3 | +17.8 | +15.6 |
| `ace_oss_15273` | 0.0% | -9.3 | -6.8 | +1.3 | -9.3 | -6.8 | +1.3 | +1.3 | -4.4 | -4.4 |
| `ace_oss_16070` | 0.0% | +13.3 | +13.3 | +14.7 | +13.3 | +13.3 | +14.7 | -13.3 | +26.7 | +26.7 |
| `ace_oss_17851` | 1.7% | +45.3 | +45.3 | +40.0 | +44.0 | +44.0 | +38.7 | +8.0 | +13.3 | +13.3 |
| `ace_oss_17880` | 2.9% | -0.2 | +6.8 | +2.7 | -0.2 | +6.8 | -4.0 | -2.7 | -60.0 | -60.0 |
| `ace_oss_19459` | 0.0% | +9.8 | +11.3 | +4.0 | +9.8 | +11.3 | +4.0 | +8.0 | +22.2 | +22.2 |
| `ace_oss_19944` | 0.0% | +8.0 | +4.0 | +6.7 | +8.0 | +4.0 | +6.7 | -20.0 | +26.7 | +26.7 |
| `ace_oss_21695` | 0.0% | +13.3 | +12.3 | +16.0 | +13.3 | +12.3 | +16.0 | -2.7 | -22.2 | -22.2 |
| `ace_oss_23069` | 54.0% | +28.5 | +34.5 | +26.7 | +0.0 | +0.0 | +0.0 | +0.0 | +68.9 | +0.0 |
| `ace_oss_23132` | 22.0% | +22.7 | +19.7 | +14.7 | -1.3 | -4.3 | +0.0 | -1.3 | +20.0 | +0.0 |
| `ace_oss_23388` | 0.0% | +4.3 | +0.3 | +2.7 | +4.3 | +0.3 | +2.7 | +0.0 | -8.9 | -8.9 |
| `ace_oss_2454` | 0.0% | +3.5 | +5.0 | +8.0 | +3.5 | +5.0 | +8.0 | +6.7 | +2.2 | +2.2 |
| `ace_oss_24748` | 0.0% | +45.0 | +44.0 | +33.3 | +45.0 | +44.0 | +33.3 | -1.3 | +64.4 | +64.4 |
| `ace_oss_27102` | 0.0% | +0.2 | +0.2 | -9.3 | +0.2 | +0.2 | -9.3 | +10.7 | -11.1 | -11.1 |
| `ace_oss_28031` | 20.3% | -0.5 | +10.0 | +6.7 | +4.8 | +13.3 | +5.3 | -2.7 | +11.1 | +0.0 |
| `ace_oss_28113` | 0.0% | -14.5 | -12.5 | -2.7 | -14.5 | -12.5 | -2.7 | -2.7 | +2.2 | +2.2 |
| `ace_oss_31420` | 0.0% | +4.3 | +11.3 | +0.0 | +4.3 | +11.3 | +0.0 | +2.7 | +11.1 | +11.1 |
| `ace_oss_31439` | 3.4% | +4.3 | -2.2 | +14.7 | +0.3 | -6.2 | +9.3 | +1.3 | +62.2 | +8.9 |
| `ace_oss_3243` | 11.1% | -14.2 | -11.7 | -17.3 | -24.8 | -22.3 | -30.7 | -20.0 | -20.0 | -31.1 |
| `ace_oss_32606` | 0.0% | +9.3 | +7.8 | +12.0 | +9.3 | +7.8 | +12.0 | +13.3 | -37.8 | -37.8 |
| `ace_oss_33450` | 2.6% | +20.3 | +13.8 | +8.0 | +19.0 | +12.5 | +2.7 | +16.0 | -2.2 | -2.2 |
| `ace_oss_34760` | 1.7% | -6.3 | -2.3 | -4.0 | -4.7 | +0.3 | +0.0 | -5.3 | -31.1 | -31.1 |
| `ace_oss_35622` | 0.0% | -5.2 | -1.7 | +13.3 | -5.2 | -1.7 | +13.3 | -4.0 | -2.2 | -2.2 |
| `ace_oss_36489` | 0.0% | +17.0 | +19.0 | -5.3 | +17.0 | +19.0 | -5.3 | +21.3 | -13.3 | -13.3 |
| `ace_oss_4327` | 40.3% | +38.7 | +40.2 | +38.7 | -2.7 | -1.2 | -1.3 | -2.7 | +42.2 | +2.2 |
| `ace_oss_4862` | 0.0% | +6.7 | +9.7 | -12.0 | +6.7 | +9.7 | -12.0 | +12.0 | +0.0 | +0.0 |
| `ace_oss_633` | 0.0% | -14.7 | -7.7 | +12.0 | -14.7 | -7.7 | +12.0 | -8.0 | +73.3 | +73.3 |
| `ace_oss_869` | 0.0% | +5.0 | +8.0 | -12.0 | +5.0 | +8.0 | -12.0 | -1.3 | -8.9 | -8.9 |
| **Mean / SD** | | +9.61 / 17.76 | +10.90 / 16.46 | +8.77 / 15.12 | +4.40 / 14.12 | +5.65 / 13.40 | +3.66 / 12.69 | +0.52 / 9.05 | +11.40 / 33.36 | +2.01 / 26.50 |

*Note.* R = retrain, fgv = typing-forgiven, Orig = original adapter (session B), PosCtl = positive control at *n* = 9 per arm (interim, non-decisional). Four tasks carry the typing artifact: `ace_oss_11023` (52.9% of null draws), `ace_oss_23069` (54.0%), `ace_oss_4327` (40.3%), `ace_oss_23132` (22.0%); on all four the raw retrain gain is large and the forgiven gain is approximately zero. The construct-valid gain is carried by `ace_oss_17851` and `ace_oss_24748`, neither of which has a material typing rate, and is offset by a consistent loss on `ace_oss_3243`.


---

## Appendix F

### Planned Experiments

Each entry states the question, the design, the prediction that would confirm it, the outcome that would refute it, and the measured cost on the machine now available (an RTX 5080, 16 GB, on a shared workstation with no persistent storage: 25 min per 1-epoch training run at 24.3 s/step, 69 min for 3 epochs, 4 min to export and verify, 2.15 min per null evaluation replicate and 2.76 min per adapter replicate, so 74 min for a 15-replicate interleaved pair and 3.3 h for a 40-replicate pair). They are listed because this article's own preregistration discipline applies to what it intends to run, not only to what it has run.

**F1. Where the seed-invariant regime ends.** Train two adapters at each of several learning rates spanning the two recipes already measured (5 × 10⁻⁶ and 2 × 10⁻⁴), with initialization seeds fixed and differing within each pair, and compare per-task profiles within and across rates. *Prediction:* profile agreement between independent runs stays at the reliability ceiling at low rates and falls off above some rate, with the fall-off tracking the point at which `lora_A` leaves its initialization box. *Refuted if:* two runs at the original recipe disagree, or two runs at 2 × 10⁻⁴ agree as closely as the retrains do. *Cost:* four 1-epoch trainings and four 15-replicate arms, about two sessions.

**F2. Seeding the initialization, and what remains.** Add `--seed` to `train_native.py`, set it before the model is wrapped rather than relying on the `Trainer`, record `torch.initial_seed()` after wrapping in `run_meta.json`, and train twice at one seed. *Prediction:* all 224 `lora_A` tensors become bitwise identical, and the residual Δ*W* disagreement isolates kernel and 8-bit-optimizer non-determinism. *Refuted if:* `lora_A` still differs, which would mean the call order is not the whole story. *Cost:* two 1-epoch trainings, under an hour, no evaluation needed for the weight-space claim.

**F3. Is the 8-bit optimizer the cause of the block artifact?** Retrain at a fixed seed under `optim="adamw_torch"` and under `adamw_bnb_8bit`, holding everything else constant, and rescan every `lora_A` tensor against the Adam displacement bound. *Prediction:* the [2304, 2558] excess vanishes with 32-bit optimizer state. *Refuted if:* it persists, which would point at the gradient rather than the optimizer state. *Cost:* two runs at `--max-steps 20`, about 20 minutes, plus a CPU scan.

**F4. A re-execution arm for the typing decomposition.** Re-run the failing completions of a scored replicate with `from typing import *` prepended, rather than crediting them by counter. *Prediction:* the re-executed gain falls between the raw and forgiven figures, closer to the latter. *Refuted if:* it matches the raw figure, meaning the counter is not identifying what it claims. *Cost:* requires retaining raw completions (Residual R-3), so it is gated on a retention flag not yet built.

**F5. Function-space comparison of orthogonal adapters.** With two adapters on one machine, forward the benchmark prompts through base and both adapters and compare logit deltas directly, rather than inferring agreement from pass rates. *Prediction:* high cosine in logit-delta space alongside the 0.004 weight-space cosine. *Refuted if:* logit deltas are as orthogonal as the weights, which would make the per-task agreement of Table 2b a coincidence of the metric's coarseness. *Cost:* one training run plus a few minutes of forward passes.

**F6. A norm-matched random adapter as a null arm.** Serve an adapter whose *B* is random with per-layer Frobenius norms matched to a trained adapter's, and score it interleaved against the base. *Prediction:* no aggregate gain and a per-task profile unrelated to the retrains'. *Refuted if:* it gains, which would place this pipeline in the regime where uninformative interventions help. *Cost:* no training; export plus one 15-replicate pair, about 75 minutes.

**F7. Finish the positive control.** Thirty-one further interleaved rounds to reach *N* = 40 per arm under the amendment's terms, reporting per session and pooled. *Cost:* about 2.5 hours.

---
