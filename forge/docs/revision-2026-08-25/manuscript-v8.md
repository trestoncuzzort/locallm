# A Preregistered Null Result That Did Not Reproduce in a Second Training Environment: Measurement-Integrity Failures and Uncontrolled Initialization in a Local Execution-Verified Pipeline

Treston Malachi Cuzzort

Independent Researcher

---

**Author Note**

The original experiments were conducted on a single consumer workstation (NVIDIA RTX 4080, 16 GB VRAM). The independent replication, the retraining runs, and the same-session controls reported in the Results were conducted on separate hardware (NVIDIA RTX 4090) by a second investigator, from this project's code, data, and configuration. A third environment (NVIDIA RTX 5080, Blackwell architecture) contributed the preregistered positive-control run added in this revision. Code, data, preregistrations, and the complete working record are retained in a private repository. Correspondence concerning this article should be addressed to the author.

*Disclosure:* Analysis code, instrumentation, and drafting were produced with AI assistance under the author's direction.

*Revision note (v5):* This revision corrects, and does not extend, the record. Four assertions
were found to overstate what the retained artifacts support and have been narrowed. (1) The
seed-order audit's coverage is restated from "39 releases … 108 trainer constructors" to 30
releases and 83 constructors: the earlier figures counted audit records and table rows, one
release having been audited twice in eight cases, and are an instance of the same overcount this
article documents elsewhere. The verdict is unchanged — every constructor examined wraps before
it seeds, and none seeds first. (2) An analysis script named in Appendix F was described as
committed to the repository; it is specified by that entry and has not been written, and the
sentence now says so. (3) Three passages stated that the primary comparison's null column could
not be regenerated from any retained artifact. Its per-replicate rows are indeed lost, but the
column itself reproduces on all 31 tasks against a committed record now cited by name. (4) A
median activation magnitude reported to two significant figures is restated at the precision the
record supports, the exact prompt behind it not having been retained. No claim is added and no
conclusion changes.

*Revision note (v6):* This revision adds what the previous one deliberately withheld, each item
carrying a witness captured before any repair. (1) An eighth measurement-integrity failure is
reported: the gate's interpreter identity check writes the literal `python unknown` whenever the
pinned interpreter cannot be launched or exits non-zero, so two hosts running different
interpreters record the same value and compare equal — a fail-open guard inside the apparatus
built to catch fail-open guards. It was surfaced by moving the repository to a second operating
system, where the pinned interpreter is present and unexecutable. (2) Two further properties of
the same receipt are recorded: it is stale on every platform, naming a revision of the verifier
nineteen days older than the commit that wrote it; and every digest in it is the hash of the
file's CRLF form, so the fingerprint is a function of the file and of the platform that checked
it out. This states as a measurement the residual carried since Failure 4. (3) The seed-order
audit is extended from 30 releases to 34, v0.7.11 through v1.10.0, and from 83 trainer
constructors to 95, the twelve added constructors traced from source at their published tags.
Every constructor examined still wraps before it seeds; none seeds first. The failure count is
propagated to eight throughout, and the unnumbered construct failure of the Discussion is
renumbered accordingly.

*Revision note (v7):* A consistency pass over the whole article, prompted by the additions in v6.
One contradiction introduced by those additions is resolved: Failure 2's resolution had claimed
that the interpreter pin could not silently assert itself while not being in force, and Failure 8
is exactly that condition arriving by another route; the earlier paragraph now says which half of
its claim survived and defers the rest. One reported inconsistency was checked and rejected rather
than applied — Table 2's session-A adapter arm carries *n* = 41 against its same-session null's
*n* = 40, which Limitation 10 already states as 41 rows across 35 identifiers against the null's
40 across 35, so the figures are correct as printed and the apparent conflict was a
misreading. The block-artifact passage records that a scanner written from its own stated
quantities reproduces every figure in it. No claim is added and no conclusion changes.

*Revision note (v8):* Appendix G is added. It restates the seed-order defect already reported in
the Method as a self-contained upstream defect report — affected versions, constructor positions
at ten named tags, a minimal bitwise reproduction, the suggested repair, and an explicit statement
of what the absence of a prior report does and does not establish — so that a library maintainer
can act on it without reading the rest of this article. Nothing in the appendix is new evidence;
it is the existing finding put in the form its audience needs.

---

## Abstract

Execution-verified preference pipelines replace human judges with unit tests, providing an objective reward. We report a preregistered evaluation of direct preference optimization (DPO) applied via low-rank adaptation to an 8-billion-parameter model, tested on a frozen 31-task benchmark. The trained adapter did not outperform its null baseline (+0.55 percentage points, *p* = .514), equivalence testing rejected an aggregate difference of ±2 pp or larger (*p* = .043), and the null replicated on independent hardware (−0.03 pp). Retraining from the same code, data, and configuration in a second environment produced three adapters that beat their same-session nulls by +8.8 to +10.9 pp. This revision decomposes that gain against a counter the harness records on every row and attributes 48–58% of it (each retrain against its same-session null) to an instrument artifact: the verifier — pinned to Python 3.11.9 on the machines that scored the primary comparison and every Table 2 arm, and to 3.12.10 on the machine that scored the positive control — fails any completion that annotates a signature without importing `typing`, and the retrained adapters learned to emit the import, a statement that appears in none of the 918 training pairs, so the construct-valid gain is +3.7 to +5.6 pp, still significant in every retrain. The counter credits a typing-only failure as a pass without re-executing it, and the re-execution arm that would fix the share has not been run; the 48–58% is a counter's bound on the artifact, not a measurement of it. The three retrains are orthogonal in weight space: mean cross-run cosine 0.0042 ± 0.0044, against an analytic floor of *r*/*d*ᵢₙ = 0.0039 for two independent random rank-16 projections of a 4,096-wide input — the number any published cross-run LoRA cosine should be read against. The orthogonality itself is not new: Nikolich et al. (2026, §3.4) already report cross-seed cosines of 0.07–0.36 for same-objective LoRA updates in a study whose six objectives include DPO, attribute them to the random initialization of *A*, and find no loss barrier between seeds. What this article adds is the floor as a number, traced to a library call order that initializes the adapter before the seed is set and to an input factor that barely trains, and a claim that paper does not test: the three adapters' per-task behavioral profiles agree at the instrument's reliability ceiling (disattenuated *r* ≈ 1.0 on both metrics) on an execution-verified generative benchmark — item-level agreement across seeds that the seed-variance literature expects not to find (Summers & Dinneen, 2021; Bui et al., 2025). At this learning rate the data determine the function and the initialization only chooses its coordinates. The original null adapter's profile is unrelated to the retrains', and a deliberately over-trained positive control (40× learning rate, three epochs; 9 of 40 preregistered replicates banked when the machine failed) reaches the same raw gain through a different solution whose construct-valid gain is +2.0 pp. The finding we regard as hardest to dispute is in the weights: under the production 8-bit blockwise Adam optimizer (`adamw_bnb_8bit`), 176 coordinates of one tensor, `layers.1.mlp.down_proj.lora_A`, moved past Adam's own worst-case per-coordinate displacement bound by up to three times, all inside the single 256-element quantization block that contains the base model's massive-activation channel. The mechanism is inferred and its one-flag ablation is listed as planned; the bound is Kingma and Ba's (2015), not ours, and because a low-rate LoRA run stays far inside it, it doubles as a free post-hoc check on any finished adapter. We also report six measurement-integrity failures in which components kept emitting well-formed numbers after they stopped measuring, a seventh in which the recorded configuration did not govern the run, and an eighth in which the verifier's own identity check recorded the same constant whether or not it had obtained one. We conclude that execution-grounded reward requires treating the verdict channel as adversarial, that a benchmark gain must be decomposed against the verifier's own idiosyncrasies before it is attributed to the task, and that the earlier attribution of the original null to a silent driver timeout must be stated as a hypothesis rather than a conclusion.

*Keywords:* direct preference optimization, execution-grounded reward, preregistration, null result, replication, reward hacking, measurement validity, training-seed variance, large language models, security smells

---

## A Preregistered Null Result That Did Not Reproduce in a Second Training Environment: Measurement-Integrity Failures and Uncontrolled Initialization in a Local Execution-Verified Pipeline

Preference-based fine-tuning of language models conventionally requires human annotators to rank model outputs. Direct preference optimization (DPO; Rafailov et al., 2023) removes the separately trained reward model from this loop but not the preference labels. Self-rewarding approaches (Shao et al., 2024; Yuan et al., 2024) go further, using the model itself as the judge, which introduces a well-documented hazard: a model that scores its own output can improve its score without improving its behavior (Amodei et al., 2016; Gao et al., 2023; Skalse et al., 2022).

Code generation admits a stronger alternative. A candidate program can be executed against hidden unit tests, and the verdict is supplied by the interpreter rather than by any model's opinion. This is the premise of the pipeline studied here: sample *K* candidates for a task, execute each against tests the model never sees, take a passing candidate as `chosen` and a demonstrably failing one as `rejected`, and train on the resulting preference pairs. The reward is objective by construction.

This article reports what happened when that pipeline was measured properly, and it makes five claims, two more than the first drafts. The first is empirical and negative: on the benchmark used, the trained adapter did not beat its null baseline, and the interval excludes effects of the size the study was designed to detect. The second is that this negative result does not generalize to the procedure, but that the procedure's positive result is smaller than it looks: retraining from the same inputs produced a large, consistent, and highly significant effect three times out of three, and roughly half of it is the adapters learning to satisfy an idiosyncrasy of the verifier that scores them. The remainder is real, concentrated on two benchmark tasks, and identical across the three retrains. The third, new to this revision, is theoretical: the three retrains occupy mutually orthogonal subspaces of weight space and implement the same function, and we can say why — the adapter's input factor is initialized before the seed is set and then barely trains, so each run is a random projection of the same update. The fourth is methodological and, we argue, the most transferable: producing the first result required finding and closing failures in the measurement apparatus, several of which would have produced a plausible-looking number that meant nothing, and two of which (an unbuilt container and an untraced seed) survived into earlier drafts as claims. The fifth is that this project's failures are not *sui generis*: they recur, in different clothing, in adjacent software-security research on tool adequacy and detectable-but-unexploited defects, and one strand of that research (formally verified code generation) points at a stronger fix than the one this article implements. The objectivity of an execution-based reward is a property of the *verdict*, not of the *pipeline that reports it*, and the difference turned out to be where the problems lived.

### The Distinction Between an Objective Reward and a Trustworthy One

An execution-grounded reward is objective in the sense that its ground truth does not depend on anyone's judgment. It is not thereby trustworthy. Between the interpreter's verdict and the training file lie several mechanisms — a harness that runs the candidate, a channel that reports the outcome, a dataset builder, a gate that certifies the data, and a benchmark that scores the result — and each is capable of failing in a way that produces a number rather than an error.

The failures reported in the Results section share a shape. In each case a component continued to emit well-formed output after it had stopped measuring what it claimed to measure: a verdict that could be forged by the candidate, a residual in that same channel that survived the first fix, a verifier whose answer depended on which script invoked it, a benchmark returning its ceiling regardless of input, a gate certifying a dataset it could no longer parse, an analysis script pooling a reference arm across two instruments, and a training-configuration record whose seed, checkpointing flag, warm-up count, and optimizer name did not describe the run, and an identity check that answered the same way whether or not it had an answer — eight in all — together with, as of this revision, a claimed fix to the first of them (a container) that was never actually implemented. None raised an exception. Two of them survived into a previous draft of this article. This is the failure mode that preregistration, red-witness testing, and measured noise floors exist to catch, and it is why we report them alongside the null result rather than in a separate engineering note.

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

**Training Procedure.** Low-rank adaptation (LoRA; Hu et al., 2022) over a quantized base (Dettmers et al., 2023), rank 16, α = 32, dropout 0.05, applied to seven projection modules (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`). One epoch over 918 pairs at effective batch size 16 (per-device 2 × gradient accumulation 8), giving **57 optimizer steps**; learning rate 5 × 10⁻⁶ with a cosine schedule and `warmup_ratio` 0.1 (`warmup_steps` is 0, which is not the same as "no warmup" and has been misread as such); β = 0.1, `rpo_alpha` = 1.0, `max_length` 1,024, `max_prompt_length` 512, `max_grad_norm` 1.0, bf16, `adamw_bnb_8bit` optimizer. The resulting adapter (SHA-256 `f416f3f9…`, 167 MB) is the object under test in the primary comparison.

The step count is stated as observed rather than derived. No `trainer_state.json` survived the original run, and the arithmetic admits 57 or 58 depending on an unrecorded `drop_last`; a retrain from the same corpus and configuration reported 57 *(replication)*.

**Software Versions.** The adapter's own model card records **PEFT 0.14.0**. No other library version was recorded by the original run: `run_meta.json` stores every hyperparameter and no library versions, and `adapter_config.json` predates PEFT's `peft_version` field. The training script passes `rpo_alpha` to `DPOConfig`, which current TRL rejects — `TypeError: DPOConfig.__init__() got an unexpected keyword argument 'rpo_alpha'`, raised at config construction before any training begins — so reproduction requires `trl==0.12.2`, which in turn pins `transformers==4.46.3` and `tokenizers==0.20.3`. The script names 0.12.2 in a source comment; nothing enforces it, and the version actually installed for the original run is not recorded anywhere. The replication ran under `trl` 0.12.2, `transformers` 4.46.3, `peft` 0.20.0, and `torch` 2.6.0+cu124 *(replication)*. The positive-control run added in this revision ran under the same `trl`/`transformers`/`tokenizers` pins, `peft` 0.20.0, and `torch` 2.11.0+cu128 on a Blackwell-architecture GPU, which requires the cu128 build; this environment is recorded in full in `data/prereg_positive_control.json` rather than summarized here, on the same principle as the rest of this section.

**Initialization Was Not Controlled, and This Revision Traces Why.** `train_native.py` contains no seeding call of any kind; a search for `set_seed`, `manual_seed`, or `seed` in the file returns nothing. The `seed = 42` recoverable from the run's `training_args.bin` is HuggingFace's `TrainingArguments` default rather than an authorial choice. Earlier drafts stated that this default "does not reach LoRA initialization" without saying why. The mechanism is a call order in the installed libraries, read at the byte: `train_native.py` hands `peft_config` to `DPOTrainer`; TRL 0.12.2's `DPOTrainer.__init__` wraps the model with `get_peft_model` at `dpo_trainer.py:376` and only reaches `super().__init__` — the `transformers` `Trainer` constructor, whose first action of consequence is `set_seed(self.args.seed)` at `trainer.py:424` — at line 640. PEFT 0.20.0's `reset_lora_parameters` (`lora/layer.py:334` (peft 0.20.0; the line number is version-specific)) draws *A* with `kaiming_uniform_` from the default torch generator, passing no generator of its own, and zeroes *B*. Every draw *after* line 424 — the data order (`SeedableRandomSampler`, seeded from `torch.initial_seed()` = 42) and dropout — is seeded; the 224 draws of `lora_A` are the only unseeded randomness in the training graph, and `run_meta.json` records no seed at all. The same order holds across every TRL release we examined at the byte — 34 releases from v0.7.11 (2024-02-16) through v1.10.0 (2026-08-13), in all of `DPOTrainer`, `SFTTrainer`, and `GRPOTrainer` where each exists (95 trainer constructors, each reaching `get_peft_model` before the `Trainer` constructor's `set_seed`; verified by re-derivation of the execution order, not file line order; the constructor positions, a minimal reproduction, and the suggested repair are stated for maintainers in Appendix G) — so any TRL-based LoRA run that passes `peft_config` and does not seed manually shares the property. We found no prior report of the ordering in the TRL or PEFT issue trackers, and we have not audited how many published results it affects. The consequences are measured in the Results.

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

*Note.* The two arms are the preregistered comparison. The base reference rows have been moved to Failure 5. The null arm's per-replicate rows are not all retained: `data/ruler_noise.jsonl` holds 5 of its 40 replicates, so this row, and every figure that depends on the null arm, is the analysis-time result rather than one regenerable from the retained file (Appendix C).

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

Failure 2 pinned the verifier to one interpreter per machine — Python 3.11.9 on the original and replication machines (the pin recorded in every Table 2 row's verifier record) and Python 3.12.10 on the positive-control machine — under each of which a function whose signature references `List` or `Optional` without importing it raises `NameError` at definition time; the semantics are unchanged through Python 3.13, and it is Python 3.14's deferred annotation evaluation that produced the Failure 2 disagreement. The benchmark's AceCode prompts carry annotated signatures; the training corpus's 13 seed tasks do not. The harness counts these failures separately (Method, *A Declared Counterfactual Metric*), and applying that count to every arm gives a decomposition the earlier drafts did not make.

The null arms fail on an un-imported annotation 10.2–11.1 times per 155-generation replicate, and the original adapter fails 11.1 times — at the null level in both sessions (session A's null 11.1, session B's 10.2). The three retrains fail 2.1, 2.1, and 2.6 times (each against its null: *t* = −8.7, −8.8, −13.8; all *p* < 2 × 10⁻⁷). Counting those failures as passes, the retrains' gains fall from +9.61/+10.90/+8.77 pp to **+4.40/+5.65/+3.66 pp** — still significant in every case (Table 2) — so **54%, 48%, and 58% of the raw gain is the adapter learning to clear a verifier check that the benchmark's tasks, not the training tasks, impose** (shares against each retrain's same-session null; against session A's *n* = 40 null, retrains 1 and 2 give 57% and 51%). Per task, the gain on `ace_oss_11023`, `ace_oss_23069`, `ace_oss_4327`, and `ace_oss_23132` (null typing-failure rates 53%, 54%, 40%, and 22% of draws) is entirely typing: +56/+50/+43, +29/+35/+27, +39/+40/+39, and +23/+20/+15 pp raw against 0, 0, −3/−1/−1, and −1/−4/0 pp forgiven (Appendix E). The construct-valid gain is concentrated on two tasks with negligible typing failures — `ace_oss_17851` (1.7% of null draws; +44/+44/+39 pp forgiven) and `ace_oss_24748` (0.0%; +45/+44/+33 pp) — and is accompanied by a consistent loss on `ace_oss_3243` (−25/−22/−31 pp).

Where the behavior came from is the more interesting question, because it is not in the data. Across the 918 pairs, 773 rejected halves fail on a wrong answer (`AssertionError`), 17 on a `NameError` (none involving a `typing` name), and the remaining 128 on type, index, syntax, value, timeout, and other runtime errors (an earlier draft's 866 counted every traceback that quoted the failing `assert` line, including crashes inside the candidate); **no chosen or rejected half in the corpus contains an import statement of any kind, and none has an annotated signature**. The adapters could not have learned `from typing import List` from a contrast that never presented it. Serving the one adapter retained on the present machine (the positive control, below) against its null on three annotated benchmark tasks, five draws each, the null arm imported `typing` in 7 of 15 completions and omitted it in 7 (one dropped the annotation), while the adapted arm imported it in 12 of 15 and dropped the annotation in 2 (one draw unclassified). The adapter did not suppress annotations; it completed them with the import the base model already supplies about half the time. Since nothing in the corpus contrasts on imports, the most economical reading is that preference optimization sharpened a pre-existing mode of the base model (cf. Yue et al., 2025, on verifiable-reward training as sharpening) whose selection was incidental to the training signal — a reading from 15 draws under a chat template that is not the harness's, offered as a mechanism to test rather than a result.

Two things follow. The retrain result stands, at about half its stated size: +3.7 to +5.6 pp (Table 2: +3.66, +4.40, +5.65 pp) against a preregistered minimum detectable effect of 2.98 pp, with *p*-values of .0023, 1.9 × 10⁻⁴, and .010. And a measured gain on an execution-verified benchmark is a statement about the model *and the verifier jointly* until it has been decomposed against the verifier's known idiosyncrasies — the point the reward-hackability literature makes for tests that accept wrong programs (Rajan, 2026; Ray, 2026), which applies equally, in the opposite direction, to a verifier that rejects right ones for an environmental reason.

### The Adapter Under Test Was One Draw From an Uncontrolled Distribution

The obvious reading of Table 2 — that the original training run simply landed badly — is supported by a measurement of the training procedure itself.

Running the training command twice on the same machine, with the same data, the same code, and the same recorded seed, produces two adapters that are **orthogonal in weight space and equal in magnitude** *(replication)*. Over the effective update Δ*W* = (*BA*)·α/*r* across all 224 adapted layers, computed in float64: mean cosine similarity **0.0042** (*SD* 0.0044, minimum −0.0087), mean magnitude ratio 1.0019, mean relative difference 1.4127. Two equal-magnitude orthogonal vectors must give exactly √2 = 1.41421, and the three metrics are mutually consistent to four decimals.

The decisive detail is *which* factors differ. LoRA initializes *A* from a generator and *B* to exactly zero. *B* must therefore differ between any two runs whose optimization differed at all, so *B* alone would be consistent with mere kernel non-determinism. But of 224 `lora_A` tensors, **0 are bitwise identical across the two runs**, with mean cosine −0.0005. The runs did not drift apart during training; they never started from the same place. This is the signature the Method now explains: the adapter is initialized before the seed is set.

Both runs converged equally well — train loss 0.5821 and 0.5831, runtimes 753.7 s and 757.7 s, reward accuracies 0.925–0.975 in both. Two orthogonal solutions, of equal magnitude and equal training quality.

The measurement instrument for this claim was itself verified on known answers before its output was believed: compared against itself, the tool returns cosine exactly 1.000000 with zero variance; compared against a 50,000× amplified control, it recovers a ratio of 50000 with cosine 1.0. In float32 it had returned a cosine of 1.0049 — an impossible value — which was caught only by the self-comparison control and fixed by computing in float64 *(replication)*. The same self-comparison and amplified-control pattern was reused, and re-verified rather than assumed, for the export path exercised by the positive-control adapter below: `export_adapter.py`'s own spot check confirms the amplified-control comparison returns cosine 0.0000 against the null and 0.9668 for the adapted-vs-null comparison, on the adapter reported in the next section.

**Orthogonality Is Predicted, Not Anomalous.** Earlier drafts presented the orthogonality as surprising. It is a consequence of two facts, one from the Method and one measured here. First, *A* is drawn at random and differs between runs. Second, *A* barely trains. In the only adapter retained on the present machine — the positive control, trained at 40× the original learning rate for three epochs — 95.5% of `lora_A` entries still lie inside the kaiming-uniform initialization box |*a*| ≤ 1/√fan_in, the entries' standard deviation is 1.02× that of the initial uniform distribution, and their kurtosis is 2.05 against 1.80 for a uniform and 3.00 for a Gaussian (each statistic an unweighted mean over the 224 adapted layers; pooled over all entries, which weights the larger `down_proj` tensors by their size, the in-box share is 94.7%). At the original recipe the movement is bounded rather than measured: 57 steps at a peak rate of 5 × 10⁻⁶ with six warm-up steps and a cosine schedule sum to Σ*lr* = 1.425 × 10⁻⁴ (exactly 28.5 × 5 × 10⁻⁶; an earlier draft's 1.47 × 10⁻⁴ counted one warm-up step too many), and an Adam step moves a coordinate by at most about *lr* in the typical case and 3.16·*lr* in the worst case (Kingma & Ba, 2015), so no element of *A*, whose scale is 1/√(3·4096) ≈ 0.009, could have moved more than 1.6% (typical) or 5.0% (worst case) of its own magnitude. The learned update is therefore Δ*W* ≈ *B*·*A*₀: a readout *B*, trained on the data, applied to a random, effectively frozen 16-dimensional projection *A*₀ of the layer's input (Zhu et al., 2024; Hayou et al., 2024). Two runs share the update that *B* learns and differ in the projection, and the expected cosine between the same matrix projected onto two independent random *r*-dimensional row subspaces of a *d*ᵢₙ-dimensional space is *r*/*d*ᵢₙ: 16/4096 = 0.0039 for the attention and gate/up projections, 16/14336 = 0.0011 for `down_proj`, and 0.0035 averaged over the seven adapted modules. A simulation of the model (random uniform *A*₁, *A*₂; Δ*W*ᵢ ∝ *G A*ᵢᵀ*A*ᵢ for a common *G*) returns 0.0039 ± 0.0005 and 0.0011 ± 0.0002. The measured 0.0042 ± 0.0044 is that number. Orthogonality in weight space is the wrong place to look for what the runs share; the next section looks in behavior.

**This Weight-Space Result Is Already in Print.** Nikolich, Kiselev, Platonov, and Romanova (2026, §3.4), training attention-only LoRA on Qwen3-4B-Instruct under six objectives including DPO, at two seeds and three learning rates, report that the same loss at two seeds yields a Δ*W* cosine of only 0.07 (at 5 × 10⁻⁷) to 0.36 (at 5 × 10⁻⁵); attribute it to LoRA's random initialization of *A* — across seeds the top output direction *u*₁ still agrees at 0.99 while the top input direction *v*₁ agrees at 0.07; and find no loss barrier when interpolating between the two seeds' deltas (midpoint +0.004), which their Figure 2 summarizes as "different weights, same basin" and their text as "functionally the seeds are the same solution." The cross-seed near-orthogonality of same-task LoRA updates, its attribution to the random *A*, and the functional sameness of the seeds in aggregate are therefore published results, and this article does not claim them. Their cosines rise with learning rate and sit well above the 0.004 measured here; they report no expectation for where the floor lies and no measurement of whether *A* left its initialization, so the two results cannot yet be placed on one curve. What that paper does not report, and what this section and the next add, is narrower: an analytic expectation for the cross-seed cosine and its per-module value (*r*/*d*ᵢₙ: 0.0039 at the 4,096-wide modules against a measured 0.0042 ± 0.0044 — the floor against which any published cross-run LoRA cosine, theirs included, should be read); the displacement of `lora_A` from its initialization, measured rather than assumed; the call order (Method) that leaves that initialization unseeded under TRL; and, in the next section, agreement between seeds at the level of individual tasks, corrected for the instrument's reliability, on an execution-verified generative benchmark — which is where the content of "same basin" is tested in behavior rather than read off a loss curve.

### Three Orthogonal Adapters, One Function

If Δ*W* is a random projection of a common update, the three retrains should not merely agree in their mean gain; they should agree task by task. The retained rows record every draw's outcome per task, so the per-task *delta profile* of each arm — its 31-vector of pass-rate changes against its same-session null — can be compared across arms without new generations. Table 2b reports the result, with each profile's split-half reliability (odd- versus even-position replicates in `data/ruler_noise.jsonl`, splitting the arm and its null alike, Spearman–Brown corrected) as the ceiling any correlation between two profiles can reach.

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

*Note.* Split-half reliabilities of the delta profiles: retrains .945, .888, .688 (primary) and .915, .821, .586 (forgiven); original adapter .209 (session A) and .519 (session B); positive control .927 / .922. Disattenuated *r* = *r*/√(rel₁·rel₂); a value near 1 means the two profiles are indistinguishable at the instrument's own reliability. Permutation *p* from 20,000 shuffles of task labels, one-sided (upper tail) — unlike the two-sided Welch tests of Tables 1 and 2; the two-sided values are roughly double (rows 4–7: .36 / .031, .69 / .66, .008 / .012, and .033, .034, .0010 / .143, .147, .0065), and no conclusion changes. Each profile is the arm's pooled per-task pass rate over all draws of all its replicates minus the same quantity for its same-session null — `ctl-null` for retrains 1 and 2, `ctl-null3` for retrain 3, `llama3-forged-null-rep` for session A — and *r* is Pearson's.

The three retrains' profiles agree at the reliability ceiling: disattenuated *r* = 1.06, 0.99, and 1.02 on the primary metric and 1.11, 0.96, and 0.99 on the typing-forgiven metric. Fifteen tasks move up and three move down under all three adapters (twelve and three on the forgiven metric), the same two tasks carry the construct-valid gain, and the same task carries the loss. Three adapters that share no direction in weight space — cosine 0.004 — implement, to within what a 40-replicate instrument can resolve, the same function on this benchmark. This is the opposite of the expectation the seed-variance literature supplies: models with identical aggregate scores routinely differ at the item level (McCoy et al., 2020; D'Amour et al., 2022; Marx et al., 2020), and any source of non-determinism is expected to produce full run-to-run diversity (Dodge et al., 2020; Bouthillier et al., 2021; Picard, 2021; Summers & Dinneen, 2021; Zhuang et al., 2022). Here the per-task profile is invariant to the one unseeded draw in the training graph. The weight-space degrees of freedom the initialization consumes are, on this evidence, coordinates rather than content: at this learning rate the data determine the function, and the initialization chooses the basis in which it is written.

**What Is Claimed Here, Against What Is Already Known.** Read against Nikolich et al. (2026), the previous section's weight-space result is confirmation and this section's is the claim. That paper establishes aggregate functional sameness across seeds — no loss barrier along the interpolation path between two seeds' deltas, on a math benchmark — and does not report per-task or per-item agreement between seeds, any reliability correction, or an execution-verified code task with hidden tests. The expectation it leaves standing is the seed-variance literature's: Summers and Dinneen (2021) find that any source of non-determinism produces full run-to-run diversity, and Bui, Savova, and Wang (2025) find low per-instance consistency across seeds for full fine-tuning on GLUE. Table 2b is the contrary case: three runs that share no weight-space direction agree on which of 31 tasks rise, which fall, and by how much, at the ceiling a 40-replicate instrument can resolve, on a generative benchmark scored by execution. The claim is accordingly narrow — per-task behavioral identity across the one unseeded draw, at this recipe, on this benchmark, bounded as Limitation 15 states — and it is offered as a counterexample to the standing default, not as a new phenomenon.

### The Null Adapter Is Not a Weak Retrain

The original adapter's profile is weakly reliable (split-half .21 in session A, .52 in session B) but real — its two sessions' profiles correlate at .47 (one-sided permutation *p* = .004; .008 two-sided), so the redistribution Failure 5 reports is a property of the adapter, not of a session. It is not, however, a scaled-down version of the retrains' profile. Against retrain 1 it correlates at −.07 (session A) and .17 (session B) on the primary metric, neither distinguishable from zero, and at .08 and .39 on the forgiven metric, the latter significant (one-sided permutation *p* = .016; .031 two-sided) but far below the .97 the retrains reach with each other. Whatever the original run produced, it moved behavior in a direction mostly unrelated to the direction every healthy run finds. This bears on the Discussion's attribution of the original null: a corrupted update would be expected to point somewhere arbitrary, and this one does; but so would a number of other failure modes, and the profile cannot tell them apart.

### The High-Learning-Rate Regime Leaves the Seed-Invariant Solution

The positive control — the same corpus at 40× the learning rate for three epochs, reported in full below — reaches the retrains' raw mean gain (+11.40 pp at *n* = 9) but not their profile. Its profile is highly reliable (split-half .93) and correlates with the retrains' at only .38, .38, and .56 (primary) and .27, .27, and .49 (forgiven); its per-task deltas have a standard deviation of 33 pp against 15–18 pp for the retrains, with swings of +73, +69, and +64 pp on its three largest gains and −60, −38, and −31 pp on its three largest losses (Appendix E); and its typing-forgiven gain is +2.0 pp (*p* = .23). Its update is about 26× the retrains' in Frobenius norm per layer (0.53 versus 0.02). The same data, pushed harder, leave the solution that every low-rate run finds and arrive at a different one, with the same aggregate and a different shape — the signature of a regime boundary between an effectively linear adaptation, in which the learned function is determined by the data, and a non-linear one, in which it is not. Where the boundary lies, and whether two high-rate runs would agree with each other as the low-rate runs do, is not measured here; it is the first experiment in *Planned Experiments*.

**What Is Not Isolated.** Which variable separates the original run from the retrains remains open, and this revision narrows it by one: the initialization draw is now known not to matter at this recipe, because three different draws produced one function. The original and the replication still differ in the GPU, the CUDA/torch stack, and the PEFT version (0.14.0 recorded on the original adapter's model card; 0.20.0 on the replication and on the positive-control run below), and the versions of TRL and transformers used for the original run were never recorded, so they cannot be excluded either. Establishing the cause requires a version matrix, not another retrain, and no claim about a specific library is made here.

### The Positive Control (Preregistered, In Flight)

Earlier drafts of this article listed as outstanding "an adapter trained at a deliberately high learning rate for multiple epochs, served through the same path, with a decision rule fixed in advance." That run's marginal evidentiary value is lower than when the limitation was first written — Table 2's three retrains, at the *original* recipe, already demonstrate the pipeline transmits adaptation at a large, repeatable magnitude — but the paper had still listed it as open, and it is reported here as far as it has run.

**Design**, preregistered in `data/prereg_positive_control.json` before training began: learning rate 2 × 10⁻⁴ — approximately 40× the original 5 × 10⁻⁶, itself sourced from a QLoRA recipe rather than chosen as a LoRA-specific default — combined with 3 epochs rather than 1, so that the run is an unambiguous positive control rather than a fourth ordinary retrain. Same 918-pair corpus, same LoRA configuration (r=16, α=32, dropout 0.05, same seven target modules), same frozen benchmark. 40 replicates per arm, same-session, interleaved rather than sequential, Welch's *t*-test at α=.05. Decision rule fixed before training: success iff *p* < .05 **and** the observed effect is at least +5.00 pp.

**Training**, executed on a third machine (RTX 5080, Blackwell architecture) not used in any prior part of this record: reward accuracy at 1.00 for the tail of training, train loss converging to 0.121, three full epochs over 918 pairs (171 optimizer steps). `run_meta.json`, written by the training script itself rather than transcribed, matches the preregistration in every field.

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

The interpreter is now resolved in one place, recorded in the dataset receipt, and refuses to fall back to the launching interpreter — a silent fallback would restore the defect while every artifact continued to assert that a pin was in force. That holds of the *resolution* and did not hold of the *record*: Failure 8, found after this section was written, reports the same mechanism degrading its identity field to a constant whenever the pinned interpreter cannot be launched. The condition this paragraph claims to have closed — every artifact asserting a pin that is not in force — was reached by a route it did not anticipate, and is closed there rather than here.

The trained and null arms carry an identical verifier record in all four fields, so **the primary comparison is not exposed to this confound at all.** The base reference arm is, and that is part of Failure 5.

### Measurement-Integrity Failure 3: A Saturated Benchmark

The same adapter evaluated in this study had been evaluated once before, on an earlier 10-task benchmark. That evaluation returned pass@3 = 0.9 on all ten runs across both arms without exception, and pass@1 means of .880 (trained) versus .888 (null). The instrument had reached its ceiling — a prior characterization found pass@20 equal to pass@3 equal to 0.9000, with 7 of 10 tasks pinned at ceiling and 1 at floor — and was returning a constant.

An instrument at its ceiling does not announce that it has stopped measuring; it returns a plausible number. The earlier evaluation was consequently uninterpretable, and the project record had described the state as "nothing has run on the real base," which was false in fact (a real run had occurred) and correct in implication (no interpretable result existed). The distinction matters operationally: one description implies training is the next step, the other implies re-measurement is.

The replacement benchmark was screened for tasks inside a [0.2, 0.8] band, frozen with an enforced content hash, and given a measured noise floor.

**Responsiveness at the Arms' Own Operating Point.** Earlier drafts listed as an open limitation that the benchmark's liveness had been established against the base model rather than against the two arms compared here. From the 200 draws per task per arm pooled at analysis time (Appendix C), that is now closed — with the caveat that only the trained arm's draws are still retained in `data/ruler_noise.jsonl`, which holds 5 of the null arm's 40 replicates (25 draws per task), so the null column cannot be regenerated from that file, though it reproduces exactly against the committed record cited in Appendix C: **no task returns 0.00 or 1.00 for any arm; all 31 are strictly interior in both arms; none is within one draw (1/200) of a boundary.** The most extreme interiors are `ace_oss_24748` (trained .1900, Wilson lower bound .1417) and `ace_oss_16070` (trained .8400, Wilson upper bound .8843). Twenty-eight of 31 tasks sit inside the ruler's own [0.20, 0.80] admission band in *both* arms; the three exceptions — `ace_oss_16070`, `ace_oss_24748`, `ace_oss_27102` — fall outside by 4 pp or less, i.e., by 2 to 8 draws out of 200. The full table is Appendix C.

The instrument was live where the comparison was made. The null is not a saturation artifact.

### Measurement-Integrity Failure 4: A Gate That Had Stopped Verifying

The dataset gate re-executes every preference pair before training and writes a receipt of file hashes that the trainer requires. It was found to be failing on its own corpus: 1,269 of 1,279 pairs verified, with 10 returning `no_matching_task`.

The cause was a scope error. The gate resolved tasks only from a hard-coded seed list, while ten pairs appended in a prior measurement had been drawn from a separately screened task pool. Those pairs were unverifiable in principle rather than merely stale, and re-running the gate — which the failure message advised — reproduced the same failure indefinitely.

The gate was extended to resolve tasks from the screened source through the same constructor used at screening time, restoring 1,279/1,279. The receipt was simultaneously extended to fingerprint the task source, on the reasoning that "0 violations" is a statement about a verifier *and a set of tasks*: while the task set was a literal inside the verifier file, the existing hash covered it incidentally; once tasks came from a data file, it no longer did. Tamper tests confirmed that corrupting either new fingerprint entry causes the gate to refuse. The positive-control run's own dataset gate re-verification, performed under a third interpreter (Python 3.12.10, on the environment described above), reproduced 1,279/1,279 with zero violations, giving a third independent confirmation of this corpus's integrity under three different interpreters.

A defect in the same machinery was surfaced by the replication: the fingerprint hashes working-tree bytes, and with `core.autocrlf=true` and no line-ending normalization in `.gitattributes`, the same source file hashes differently depending on how git materialized it. In a live reproduction, a file authored with LF endings hashed to `b28a47cb…`; checked out into a tree where git wrote CRLF, the same 1,485 bytes of source hashed to `15770d4d…` and the gate refused with a `VERIFIER-CHANGED` error, which reads exactly like tampering *(replication)*. Any clone with different line-ending settings, and any Linux or CI runner, hits this.

**CORRECTION (this revision).** The preceding draft ended this paragraph with the claim that the defect "has now been fully resolved by introducing a `.gitattributes` file enforcing `eol=lf` across the repository, ensuring the dataset gate remains robust regardless of the host operating system." **That claim is withdrawn.** The repository-root `.gitattributes` contains exactly one line, `data/*.jsonl merge=union`; `core.autocrlf` is still `true`; and the normalization remains open as residual R-1 in the repository's own residuals note (`poscontrol/RESIDUALS-2026-08-04.md`), whose discharge condition — a normalization landed, the receipt regenerated under it, and a probe showing that `autocrlf=false` and `autocrlf=true` yield the same fingerprint — is unmet. Limitation 7 is therefore still correct that the fingerprint is line-ending dependent. The claim was never checked against the bytes it described, which is the failure this article names in Failure 1's correction above.

### Measurement-Integrity Failure 5: A Reference Arm Measured on a Superseded Instrument

This one reached print. A previous draft of this article carried, in its abstract, a dedicated Results section, and its conclusion, the claim that the export and quantization path cost 3.3–3.8 pp of benchmark accuracy — more than the effect the study was designed to detect. **That claim is withdrawn.** It is an artifact, and it fails on two independent grounds, either of which is sufficient.

*There Was No Export Path in the Null Arm to Cost Anything.* As established in the Design, the null arm is the base model served with no adapter, from the same weight blob and the same template as the trained arm. Nothing was merged, dequantized, or re-quantized for either arm. The premise of the finding — that both arms traverse a lossy path whose cost is visible against the unmodified base — has no referent.

*The Measured Gap Was an Instrument Mismatch.* The base reference was scored 3.9 days before the arms, under the earlier metric, and its 50 replicates are not one population. Within the same base rows, greedy draws score .6323 and sampled draws .5047 — **+12.76 pp on the same model, the same tasks, and the same run.** The base arm also spans two verifier states: 10 rows banked before the interpreter pin (*M* = .5910) and 40 after it (*M* = .5150), with Welch between the two sub-populations at +7.60 pp, *t*(24.1) = 8.22, *p* = 1.9 × 10⁻⁸. They are not poolable.

Peeling both confounds gives a sampler- and verifier-matched base reference of *M* = .4905 (*SD* = .0476, *n* = 40). Against it, **trained is +0.71 pp** (*t*(76.6) = 0.71, *p* = .482) and **null is +0.16 pp** (*t*(69.1) = 0.17, *p* = .864). There is no deficit left to explain. The greedy anchor accounts for −2.55 pp of the apparent gap and pooling the pre-pin rows for a further −1.42 pp. Incidentally, the matched reference's *SD* of .0476 is exactly the figure the preregistration assumed as its sizing floor, and exactly the figure the positive-control preregistration inherited from it.

The mechanism is in code, and naming it is the point of reporting this as a failure rather than an erratum. `analyze_run1.load()` groups replicates by model name alone (`out.setdefault(r.get("model"), []).append(r)`), so all 50 base rows average together across two samplers and two verifier states. The measurement script refuses exactly this pooling for the arms and prints `ignoring N replicate(s) banked under a different verifier`. The guard exists; the analysis path did not inherit it. This does not touch the primary comparison, which never uses the base rows.

Two explanations previously left open are now closed rather than left standing. A chat-template or EOS defect between the arms is excluded by the byte comparison of the two served model definitions, which share a template and stop parameters, and by the shape of the difference profile: the common-mode component of trained − null is +0.55 pp and accounts for 0.49% of the total squared difference, with a 90% interval of [−0.84, +1.94] pp, whereas a template defect would be broad and one-sided. Session drift is excluded by measurement: serving the identical adapter file on different hardware two days later moved the trained arm by +0.42 pp (*p* = .642) and the null arm by +1.00 pp (*p* = .222), so session-to-session variance is on the order of 1 pp — far too small to be a 3.8 pp gap *(replication)*.

One loose thread is retained rather than resolved: the base arm shows a significant downward drift across its own run order (*r* = −.498, *t*(48) = −3.98, *p* = .0002; first half .5489 vs. second half .5115, Welch *p* = .0037), which is unexplained. The two served arms show no such drift. That is a reason not to treat the base arm as a clean reference even after matching, and it is why the base rows are reported here rather than in Table 1, as a reference and not as a comparator.

### Measurement-Integrity Failure 6: A Statement-Level Residual in the Verdict Channel, Demonstrated and Closed

Failure 1's nonce fix shipped with its own honest residual, stated at the time and repeated in every draft's Limitations without ever being tested: "the nonce lives in a module global while the candidate runs in that same namespace, so code written deliberately against THIS harness could still read it back out." No earlier draft demonstrated this. This one does.

```python
print('__PASS__' + _NONCE)
raise SystemExit(0)
```

— a two-line candidate that never defines the requested function and never executes a single test — was accepted as a full pass (`res.ok = True`, `res.passed = res.total`) by the current, unmodified verifier on the `two_sum` seed task. The dynamic nonce cannot close this by construction, independent of how it is implemented: the candidate and any check written into the same namespace share that namespace on identical terms, so no string, however long, closes a channel the candidate can read directly.

What closes it is refusing to execute code that exhibits the pattern, before execution — the same move a statement-level taxonomy of malicious code makes for supply-chain security (Ryan et al., 2025): classify specific syntactic patterns into named, independently checkable categories, rather than trust one broad heuristic. `harness_smells.py` implements three categories scoped to this harness's specific residual:

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

### Measurement-Integrity Failure 8: An Identity Check That Collapses to a Constant

The dataset gate refuses to train unless the verifier that produced a receipt is the verifier on disk now, and the verifier's identity includes the interpreter that will execute candidate programs. That last field is not assumed; it is *asked* of the interpreter, which is the right design — Failure 2 exists because ground truth had depended on which script invoked it. The pinned interpreter is launched and asked its own version, and the answer is recorded.

The failure is in what happens when it cannot answer. The launch is wrapped in a handler that catches `OSError` and `subprocess.SubprocessError`, and the version variable is initialized to the string `unknown` before the attempt. On any failure to launch, and equally on any non-zero exit, the recorded identity is the literal `python unknown`.

That value is a constant, and this is the whole defect: **two hosts running genuinely different interpreters both record `python unknown` and therefore compare equal.** The check exists to prove that two machines ran the same interpreter. It passes exactly in the case where it has established nothing about either. It is a fail-open guard of the same species as Failure 4, one layer further in: not a gate that stopped verifying its corpus, but an identity that stopped distinguishing its subjects.

The red witness came from moving the repository. On a second machine that received the working tree by file copy from the original Windows host, `.venv-train/Scripts/python.exe` is present — and is a PE32+ Windows executable the host operating system cannot run. The existence test therefore succeeds, `verify_py()` returns that path and reports the pin satisfied, the subprocess raises `OSError: [Errno 8] Exec format error`, and the handler writes the sentinel:

```
$ file .venv-train/Scripts/python.exe
.venv-train/Scripts/python.exe: PE32+ executable (console) x86-64, for MS Windows
$ python3 -c "import dataset_gate as dg; print(dg.verify_py()); print(dg.interpreter_fingerprint())"
.../.venv-train/Scripts/python.exe
{'interpreter': 'python unknown'}
```

Nothing raised, and the pin reported success while pointing at a binary that cannot execute a single line of the corpus.

Two properties of the same receipt were found alongside it, and both are recorded here because they bear on how any such fingerprint should be built. First, the receipt is **stale on every platform**, independently of the above: it records `forge.py 13d52d9c…`, which matches no encoding of the committed file at the revision the receipt itself was committed at, but is the hash of that file as it stood nineteen days earlier. The verifier was deliberately changed and disclosed (Failure 6); the receipt that certifies it was not regenerated, so the gate refuses on the original host as well.

Second, every hash in the receipt is **dialect-dependent, and the dialect is the recording platform's**. Six of the seven recorded digests equal the SHA-256 of the corresponding committed blob converted to CRLF; none equals the digest of the blob as stored. The seventh is `forge.py`, which matches the CRLF form of the earlier revision just described. The fingerprint is therefore a function of the file *and of the operating system that checked it out* — the residual this article has carried as open since Failure 4, now stated as a measurement rather than a suspicion. A content fingerprint that silently encodes its platform is not a content fingerprint; the repair is to hash a declared canonical form rather than whatever bytes the checkout produced, which leaves every digest already published in this article valid and makes them reproducible off Windows for the first time.

### An 8-Bit Optimizer Artifact Localized by a Massive-Activation Channel

The `adamw_bnb_8bit` entry above is not merely mis-descriptive. Scanning all 224 `lora_A` tensors of the positive-control adapter for elements that moved further than an exact Adam optimizer could have moved them — the bound is the initialization box plus 3.16·Σ*lr* = 0.0540 for that run's schedule (Σ*lr* = 0.01710 over 171 steps with 18 warm-up steps; an earlier draft's 0.0547 counted one warm-up step too many, and the counts that follow are at the corrected bound) — returns exactly one tensor: `layers.1.mlp.down_proj.lora_A`, with 176 such elements (169 at the earlier draft's looser bound). All 176 lie in the columns [2304, 2558], spread over 95 distinct columns and all 16 rank rows; the largest reaches |*a*| = 0.175, twenty-one times the initialization bound of 1/√14336 = 0.0084 and three times the worst-case Adam displacement. Mean per-column max |*a*| is 0.058 inside that window and 0.009 outside it. No other `lora_A` tensor in the adapter has a single such element, and the layer's *B* factor stays well inside its own bound. (One isolated `lora_B` element elsewhere, `layers.31.mlp.up_proj.lora_B` at +0.0557, exceeds the bound; it is a single entry with no block structure — the next-largest |*B*| anywhere is 5.7× smaller — and does not affect the localization claim.) The passage is self-sufficient for reproduction: a scanner written from the quantities stated here — the per-tensor initialization box 1/√fan_in, the bound init + 3.16·Σ*lr*, and the 256-element flat blocking — reading only the published adapter file, returns 176 elements over 95 distinct columns and all 16 rank rows, columns [2304, 2558], the same sixteen flat blocks ≡ 9 (mod 56), and max |*a*| = 0.1750304 at row 9, column 2474.

Two facts locate the cause. The window is the tenth 256-element block (block index 9, zero-based) of the row-major tensor, and 256 is the block size bitsandbytes 0.50.1 uses to quantize optimizer state (`optim/optimizer.py:524`, in `Optimizer2State.init_state`, the class `adamw_bnb_8bit` resolves to, with the same line at `:691`; Dettmers et al., 2022). And a single forward pass of the base model on a code prompt shows that the intermediate channel feeding `down_proj` column 2427 — inside that window — carries an activation of magnitude 386, against 46 for the next largest channel and a median of order 10⁻² across the layer's 14,336 channels: a massive activation of the kind Sun et al. (2024) describe, in the early-layer `mlp.down_proj` where the super-weight literature reports them (Yu et al., 2024, whose index does not include Llama-3-8B; the coordinate here is measured, not cited). Because ∂*L*/∂*A*[:, *j*] scales with the *j*-th input activation, that channel's second-moment state dominates the absmax of its 256-element quantization block, and its neighbours' states underflow the 8-bit dynamic format, inflating their effective step size. The mechanism is inferred from the exact block alignment and the activation measurement; it has not been demonstrated by ablation, and the one-flag test — retrain at a fixed seed with `optim="adamw_torch"` — is listed in *Planned Experiments*.

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

**Table 4**

*Concentration of the 918-Pair Training Bank*

| Level | Clusters | Effective count | Largest share |
|---|---|---|---|
| Task identifier | 13 | 9.93 | 13.1% |
| Chosen, exact text | 407 | 165.64 | 8.5% |
| Chosen, canonical structure | 273 | 90.41 | 9.8% |
| Rejected, canonical structure | 632 | 441.59 | 4.2% |
| (Chosen, rejected) contrast | 767 | 666.41 | 1.4% |

The task-level row reproduces an independently published figure from the corpus builder (effective task count 9.93) to the reported precision, serving as a control on the estimator before its novel rows are trusted.

Preference optimization trains on the *contrast* between chosen and rejected, and at that level the corpus is diverse: 767 distinct contrast structures across the 910 pairs whose two halves both parse (the 8 rejected halves that fail to parse are excluded here, as they are from the rejected-structure row), largest cluster 1.4%. The apparent concentration on the chosen side reflects 13 tasks with converging correct solutions, which is what correctness entails. The corpus is therefore narrow but not collapsed, and the null result is not attributable to structural repetition. Task breadth — 13 tasks, effective count 9.93 — remains the binding constraint on what any result here can generalize to, and it binds the retrain result in Table 2, and the positive-control result above, exactly as much as it binds the null.

### Information Discarded by Pair-Primary Pipelines

A subsidiary finding concerns pipeline economics rather than the comparison. The pipeline sampled *K* candidates per task and emitted at most one preference pair, discarding the remainder. On tasks where every candidate passed, it emitted nothing and recorded the attempt as producing no signal. Instrumentation established that 66% of task attempts produced no training row and that only 16.9% of paid-for generations reached one.

This is a property of the preference-pair format, not of the data. A pair requires both a success and a failure; supervised fine-tuning requires only a success; and prospect-theoretic alignment (KTO; Ethayarajh et al., 2024) requires only a label, making a task on which everything failed a source of genuine negative signal rather than waste. A task with four passing candidates yields zero preference pairs and four supervised examples from generations already purchased and already verified.

The pipeline was accordingly restructured so that an immutable per-candidate trace is primary and each training format is a pure derivation over it. A view can always be rebuilt from the trace; a trace cannot be rebuilt from a view, so emitting pairs first destroys exactly what any alternative objective would require. Unit tests fix the property: four passing candidates yield 0 pairs and 4 supervised rows; four failing candidates yield 4 labeled negatives; and a timed-out candidate never becomes a `rejected` half, a timeout being an absence of information rather than a wrong answer.

The same argument applies to the raw emissions the old builder discarded, and that omission is now visible in the training data itself: because no pair retains what the policy actually emitted, every optimization target in this study's corpus is a reconstruction (see Method, Training data).

---

## Discussion

The trained adapter did not beat its null baseline, the interval excludes effects of the size the study was powered to detect, and the comparison replicated on independent hardware. Three readings were available when only that much was known, and they implied different next actions. Two of them can now be settled.

**The First Reading — That DPO Does Not Help Here — Is Contradicted.** Three adapters retrained from the same code, corpus, and configuration beat their same-session nulls by +8.8 to +10.9 pp, at *p*-values from 3.4 × 10⁻⁸ to 1.4 × 10⁻⁶ (Table 2), with instrument drift excluded by a same-session control. Whatever this pipeline's limits are, "the method produces no benchmark movement" is not one of them. Earlier drafts declined this reading on the grounds that a single checkpoint carries zero training-seed variance by construction; that caution was correct, and the retrains are what it was cautioning about.

**The Second Reading — That the Training Signal Was Too Narrow to Transfer — Is Weakened but Not Eliminated.** The corpus still spans 13 tasks with an effective count of 9.93, and the benchmark, though disjoint, is drawn from the same source distribution. But a corpus too narrow to transfer should be too narrow for every adapter trained on it, and three of four adapters trained on it transferred. Narrowness now bounds *generalization beyond this distribution*; it no longer explains the original null.

**The Third Reading — That the Effect Was Real but Smaller Than 2.34 pp — Is Superseded by the Equivalence Result and Then by Table 2.** TOST rejects a true aggregate effect of ±2 pp or larger for the original adapter. That adapter's effect is small. Other adapters from the same recipe have effects an order of magnitude larger.

What is left is a fourth reading: **something in the original training run, and not the initialization draw, produced an adapter unlike the ones the same command produces now.** The seed is now positively exonerated rather than merely acquitted. Three unseeded runs, beginning in mutually orthogonal random subspaces, agree with each other to within 1.3 pp in aggregate and — the stronger statement this revision adds — agree task by task at the reliability ceiling of the instrument (Table 2b). A bad initialization draw cannot explain an outcome that three independent draws do not produce; and because we can now say *why* the draws do not matter at this recipe (Δ*W* = *B*·*A*₀ with *A*₀ frozen and random), the exoneration is mechanistic rather than statistical.

What kind of question the fourth reading is can now be stated more precisely than earlier drafts managed. It is a classification problem, and the parts of a test exist. The healthy class is calibrated: three retrains whose 31-task profiles agree at the reliability ceiling (Table 2b) define, together with their dispersion, what an adapter this recipe produces looks like in behavior space. The candidate classes for a run that left that class are omission — a scaled-down copy of the healthy function, which is what a run that dropped or truncated updates should produce; commission — an uncorrelated direction at preserved norm, which is what a corrupted update should produce and what a norm-matched random adapter produces by construction; and a different solution of the kind the positive control reaches. The statistic is the distance of a candidate's profile from the healthy centroid against the healthy profiles' own dispersion, or, where weights are available, the same comparison on logit deltas; the norm-matched random arm and the function-space comparison in *Planned Experiments* are what fix the commission class and the statistic's scale. On what is already measured, the original adapter does not sit in the omission class: its profile correlates with retrain 1 at −.07 and .17 rather than at a reduced positive value, and its split-half reliability is .21 and .52 against the retrains' .95, .89, and .69. Its weights are not on the machine now available to this project, so the classification can only be behavioral, and it cannot be completed until the random arm is run. None of this names the cause; it replaces a narrative with a test. Nor is the advice to compare adapters in function space rather than weight space new: Ding, Denain, and Steinhardt make the statistical-testing case for representation comparison in *Grounding Representation Similarity with Statistical Testing*, and the climate-modeling community has for a decade accepted non-bitwise-reproducible runs by their statistical indistinguishability from an ensemble of trusted runs (Baker et al., 2015, the CESM ensemble-consistency test). What this project alone can supply is the operational version for a fine-tuning run: the dispersion of healthy retrains as the acceptance region.

The candidate cause earlier drafts named is a silent Windows GPU timeout (`TdrDelay`) aborting CUDA kernels during the original run. The supporting datum is a local replication on the *original* software stack (PEFT 0.14) that beat its null by +10.3 pp (pass@1 .6194 vs .5161) after the timeout was mitigated. **This revision demotes that from a conclusion to a hypothesis**, for three reasons that we would rather state than have a reader find. It rests on a single reported comparison, without the replicate-level treatment Table 2 receives, and it is the one result in this article that is reported only in prose. The vendor documentation for the mechanism does not describe it as silent: Microsoft's WDDM documentation and NVIDIA's own note state that after a timeout the engine or adapter is reset and the CUDA context begins reporting errors, so "a TDR that raised no exception" requires a specific path — plausibly the Windows 8-and-later per-engine reset with packet resubmission — that nobody has characterized for a PyTorch training loop. And the artifact evidence is equivocal in a way the profile analysis now makes visible: the null adapter's per-task profile is weakly reliable and unrelated to the retrains' (Table 2b), which is consistent with a corrupted update but equally consistent with several other failure modes, and no published work distinguishes a hardware-corrupted fine-tune from a merely different one on the basis of its behavior or its weights.

The TDR hypothesis now has a mundane competitor for the one property it was invoked to explain — a silent, non-Adam update that raised no exception. The 8-bit optimizer artifact reported in the Results is such an update: deterministic, located at an address fixed by the base model's own activation statistics before training begins, software in origin, and present in a run whose training record says `adamw_bnb_8bit` without complaint. The instance on this machine is functionally near-inert and occurred in a run that succeeded, so it is not offered as the cause of the original null. It is offered as proof that the class exists without a driver fault, in a form that can be tested in about fifty minutes — four `--max-steps 20` runs one optimizer flag apart — on a machine without administrator rights, whereas the TDR hypothesis requires rights this machine does not have and a mechanism the vendor's documentation describes as raising errors rather than staying silent. Two recommendations follow that the evidence supports and earlier drafts omitted. Use 32-bit optimizer state for the LoRA parameters: on roughly 42 million adapter parameters the 8-bit saving is about 0.3 GB, which is nothing against a 16 GB card, and it removes the inferred cause of the one block this article can show moved past the Adam bound. And assert that bound on every finished adapter — max |*A* − *A*₀| and max |*B*| at most 3.16·Σ*lr* per tensor — since it is Kingma and Ba's (2015) own trust region rather than anything new, and a low-rate LoRA run sits so far inside it that the check costs a CPU scan and separates cleanly.

We therefore conclude only that the original run differed from the retrains in something other than its seed, that a silent driver-level abort remains the leading named candidate but no longer the only one, and that the general lesson stands independently of which candidate is right: an execution-grounded pipeline is only as objective as the hardware executing it, and when prevention is unavailable the honest fallback is detection — the posture the positive-control run adopts, and the one the silent-data-corruption literature (Ma et al., 2025; Altenbernd et al., 2026) arrives at for datacenter training, where nobody has yet looked at a consumer GPU under a display driver.

**A second general lesson, new to this revision, concerns what the gain was made of.** Roughly half of the retrains' benchmark movement was the model learning to satisfy a property of the verifier — an import required by the pinned interpreter, on prompts whose annotated signatures invite its omission — rather than a property of the task. The behavior is not in the training corpus, and the absence is total rather than approximate: of the 918 pairs, none contrasts on typing — no rejected half fails on a `typing` name, and no half of the 1,836 contains an import statement or an annotated signature — so the pipeline did not teach it from any contrast it was shown. How preference optimization on a corpus with zero typing content taught the policy to stop tripping the verifier's typing check on annotated benchmark prompts — taking typing failures from 10.2–11.1 per 155-generation replicate in Table 2's null arms (12.9 in the primary comparison's null, 14.7 in the positive control's, under its own pin) and about 11 in the original adapter to 2.1–2.6 in the retrains and 0.1 in the positive control — is therefore the open question, and this revision sharpens it rather than resolves it. Two mechanisms produce the same count: the adapter learned to emit the import, or it learned to stop annotating. On the scored rows they are indistinguishable, because no completions were retained (Limitation 9); the only evidence between them is the 15-draw probe in the Results, run under a chat template that is not the harness's, and "the preference signal sharpened a mode the base model already had" (cf. Yue et al., 2025) is a hypothesis resting on that probe alone. The construct-valid effect survives at +3.7 to +5.6 pp by the counter's bound, and the practice we would recommend from this is narrow and cheap: before attributing a benchmark delta to a training intervention, decompose it against the failure modes the verifier itself imposes, using counters the harness can record for free. The reward-hackability literature audits verifiers that accept wrong programs (Rajan, 2026; Ray, 2026); the mirror-image error — a verifier that rejects right ones for an environmental reason, and a model that learns to clear it — is the same class of failure and, on this evidence, the more likely one when a pipeline's training and evaluation prompts come from different distributions.

### On the Value of the Null

The result's usefulness rests on the apparatus, not on the number. Eight components of that apparatus were found to be reporting confidently while not measuring: a verdict channel the candidate could write, a residual in that same channel that survived the first fix and was only demonstrated as exploitable in a later revision, a verifier whose ground truth depended on its caller, a benchmark at its ceiling, a gate certifying data it could no longer parse, an analysis path that pooled a reference arm across two instruments, and — added here — a training-configuration record whose seed, checkpointing flag, warm-up count, and optimizer name did not describe the run they were written for, and an interpreter identity that recorded the same constant whether or not it had obtained one. Each produced well-formed output. None raised an exception. Any of the first five would have yielded a publishable-looking number with no content; the sixth did, in a previous draft of this article, for several weeks; the first's *fix* did, in the form of an unverified claim that a container already existed, for every draft before this one; and the seventh's `seed = 42` is why two drafts of this article said the initialization was uncontrolled without being able to say why. The fifth's *fix* is a further instance, found while preparing this revision: the preceding draft reported Failure 4's line-ending defect as resolved by a `.gitattributes` rule that the repository does not contain, and that claim is withdrawn where it was made.

A ninth belongs here in substance if not in form, because it is the one that changed a headline number. The retrain gain of +8.8 to +10.9 pp was not a measurement failure in the sense of the others — the instrument reported exactly what it was built to report — but it was a *construct* failure: about half the movement was the model clearing an environmental check rather than solving more tasks, and the article stated the whole of it as evidence that the pipeline transmits adaptation. The harness had recorded the counter that decomposes it since before the retrains were run. Nobody had applied it to those arms. The lesson we take is that a free diagnostic left uncomputed is indistinguishable, in its effect on a published claim, from a diagnostic that does not exist.

That last point is not a confession appended for candor. It is the strongest available evidence for the article's thesis. The Failure 5 defect was found by a reader who recomputed a published figure from the raw rows rather than reading the number, which is the only procedure that would have caught it. The Failure 1 container claim was found the same way, applied to prose instead of arithmetic: by reading the file the claim described rather than the sentence describing it. Every earlier draft's arithmetic was correct; every published statistic reproduced from the raw rows to four decimal places. Neither defect was in the calculation. Both were in what had been silently asserted — pooled data in one case, an unbuilt container in the other — before the calculation, or the claim, began.

We take the general lesson to be that in execution-grounded training the objectivity of the reward is the easy part. A test suite genuinely does decide correctness without appeal to opinion, though execution verified code can still be flawed or insecure (Liu et al., 2023). What is not thereby guaranteed is that the verdict which reaches the training file is the verdict the interpreter produced, and every failure documented here lived in that gap. The literature on reward hacking concerns itself largely with optimization pressure discovering unintended maxima of a specified objective (Amodei et al., 2016; Gao et al., 2023; Skalse et al., 2022). The failures reported here required no optimization pressure at all — they were latent in the plumbing, and one of them, demonstrated for the first time in this revision, was exploitable by a two-line literal that needed only to read a variable already sitting in its own namespace.

This suggests two practices. For any automated reward, the channel carrying the verdict should be treated as adversarial with respect to the artifact being judged, independently of whether that artifact is believed to be adversarial; the candidate need not intend to cheat for a writable verdict channel to corrupt a dataset. And no two measurements should be compared until something mechanical has confirmed they were produced by the same instrument — the guard that would have caught Failure 5 already existed in this codebase and simply was not on the path the published figure took, and the same class of guard, elsewhere in this codebase, is what caught this revision's own mid-run edit to the verifier before it could corrupt a row.

### Relation to Security-Smell and Verified-Generation Research

The failures reported here have direct counterparts in adjacent software-security research, and naming them situates this project's methodology rather than merely decorating it.

The work of M. R. Rahman, A. Rahman, and colleagues on security smells in shared code and configuration scripts (M. R. Rahman et al., 2019; A. Rahman et al., 2021) treats a detectable-but-unexploited pattern — a hard-coded secret, a disabled certificate check — as a defect in its own right, independent of whether anyone has yet exploited it. That is exactly the posture Failure 6 takes toward the nonce residual: the pattern was named as a smell at the time of the nonce fix, and this revision's contribution is to show the smell was load-bearing rather than cosmetic, the same escalation the replication study made for IaC scripts (A. Rahman et al., 2021) — a re-run, under different conditions, surfacing what the original methodology had named but not demonstrated. Their finding that automated secret-detection tooling is "not enough… it's not just about false positives" (M. R. Rahman et al., 2022) is the same argument this article makes about execution-grounded reward in different words: a tool that reports confidently against its own stated metric can still fail at the thing it exists to guarantee, for reasons the metric never surfaces. And their case that security metrics are worthless before the measuring instrument is itself validated — "if you cannot measure it, you cannot secure it" (M. R. Rahman et al., 2025) — is this article's noise-floor and benchmark-ceiling methodology, restated for a different kind of instrument and a different kind of measurement.

A separate strand of work to which M. R. Rahman contributes points at a stronger remedy than the one this article implements. Erfan et al.'s (2026) work on AI-assisted, Dafny-based formally verified code generation pairs generation with a machine-checked proof of correctness against a specification, rather than sampling behavior against a finite, hidden test suite. Every failure in this article's verifier — a forgeable channel, an interpreter-dependent harness, a namespace a candidate can read from — is a failure specific to *execution-based* verification, where a candidate and its judge necessarily share a runtime. A specification the candidate cannot satisfy by exploiting the harness's own execution environment closes the entire class Failure 6 has only narrowed to its currently demonstrated instances. Adopting that approach here would require a formal specification per benchmark task in place of a hidden assert-based test, which this project's 31-task ruler does not have and this revision does not attempt to build; it is named as the more principled fix this project's own defense-in-depth posture has, so far, deliberately deferred rather than solved, in the same spirit `domains/sql/runtime.py`'s own comment already names for a different verifier in this codebase.

One further paper with M. R. Rahman as a co-author bears on this article's own instrument discipline without being adopted outright. An earlier draft cited a second, on coarse- versus fine-grained LLM-based malicious-package detection, for the distinction Failure 5 turns on — an aggregate number (base-model pass rate, pooled across two verifier states) hid a fine-grained confound (the interpreter pin) that only a per-row audit surfaced; no primary record of that paper could be located in arXiv or Crossref, so the citation is withdrawn and the distinction rests on Failure 5's own evidence. The FALCON self-reflection loop for turning threat intelligence into deployable detection rules (Mitra et al., 2025) is structurally close to this pipeline's own actor-verify-pair loop, aimed at a different artifact; noting the structural similarity does not constitute using their method, and none of their specific techniques were implemented in this pipeline beyond the statement-level classification approach credited above.

### Relation to Data-Quality Concerns

An adjacent hazard is that verified correctness and data diversity are separable properties. Execution filtering guarantees that retained programs pass their tests; it does not prevent the retained set from being behaviorally repetitive, and exact deduplication does not detect renaming. This concern is sharpened by evidence that training on recursively generated data degrades models when diversity collapses (Shumailov et al., 2024). In the present corpus the concern was tested and not substantiated at the contrast level, though the corpus is narrow at the task level. We note it as a variable requiring independent measurement rather than an assumption inherited from the presence of a verifier.

---

## Limitations

The following constrain interpretation and are stated as bounds on the claim rather than as caveats.

1. **One checkpoint per arm in the primary comparison, and it was unseeded.** The primary result cannot support a claim about DPO as a method; it characterizes one adapter, drawn from a distribution the code does not control (Dodge et al., 2020; Bouthillier et al., 2021; Picard, 2021). This is now measured rather than assumed, and its mechanism traced to a library call order (see Method and Results).
2. **The replication replicates the measurement, not the training.** Both the original run and the replication of it serve the same adapter GGUF, verified by hash on both machines. Training-seed variance is zero in both.
3. **Which stack variable is worth 10 pp is not isolated**, though the search space is now smaller. The retrains differ from the original run in GPU, CUDA/torch stack, at least one library version, and initialization; initialization is excluded by Table 2b, since three orthogonal draws produce one function. No version matrix has been run, and no claim is made that any particular library caused the difference.
3a. **The typing decomposition is an upper bound, not a re-execution.** `aggregate_if_typing_imported` counts a failure as a pass when its only error is a `NameError` on a `typing` name; it does not re-run the completion with the import supplied, so a completion that would fail for a second reason after the import is credited anyway. The 48–58% shares are therefore upper bounds on the artifact, and the construct-valid gains of +3.7 to +5.6 pp lower bounds on the residual effect. A re-execution arm would settle it and has not been run.
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

That null belongs to one adapter. Retraining from the same code, data, and configuration produced a +8.8 to +10.9 pp improvement three times out of three — of which 48% to 58% (against each retrain's same-session null; 57% and 51% for retrains 1 and 2 against session A's null) is the adapters learning to emit an import that the pinned verifier requires and the benchmark's annotated prompts invite omitting, a statement that appears in none of the corpus's 1,836 halves. Decomposed against that counter, the effect is +3.7 to +5.6 pp, still above the preregistered minimum detectable effect of 2.98 pp and significant in all three runs, and concentrated on two of thirty-one tasks. Half of a headline number was a property of the instrument, and the counter that shows it had been recorded on every row since before those runs were scored.

The training script that produced all four adapters sets no seed, and this revision says why: TRL wraps the model with PEFT before the `Trainer` constructor sets the seed, so the adapter's input factor is the one unseeded draw in an otherwise seeded graph, in a call order shared by TRL's DPO, SFT, and GRPO trainers as currently shipped. That factor then barely moves during training — 95.5% of its entries, averaged over the 224 adapted layers, remain inside their initialization box even at forty times the studied learning rate — so each run's update is the same learned readout applied to a different random projection, and the measured cross-run cosine of 0.004 is *r*/*d*ᵢₙ, the value that geometry predicts. The three orthogonal adapters are nonetheless the same function: their per-task profiles agree at the reliability ceiling of a 40-replicate instrument, the same fifteen tasks rise and the same three fall, and the same two tasks carry the construct-valid gain. At this recipe the data determine what is learned and the initialization determines only the coordinates it is written in — which exonerates the seed as an explanation of the original null more firmly than the aggregate agreement alone could, and which fails at forty times the learning rate, where the same corpus produces the same mean through a demonstrably different solution.

Four claims from earlier drafts are withdrawn or demoted. An apparent 3.3–3.8 pp cost of the export and quantization path is withdrawn: the null arm traverses no such path, and the gap was a reference arm scored under a superseded sampler and pooled across two verifier states. A claim that the verdict-channel residual had been closed by containerization is withdrawn: the container did not exist, the residual was live, and a statement-level static check closes it instead. A claim that the dataset receipt's line-ending dependence had been resolved by a `.gitattributes` normalization is withdrawn: the rule does not exist in the repository, and the defect remains open (Failure 4, Limitation 7). And the attribution of the original null to a silent GPU driver timeout is demoted from conclusion to leading hypothesis: it rests on one unreplicated comparison, the vendor documentation describes the mechanism as raising errors rather than staying silent, and the null adapter's per-task profile — weakly reliable, and unrelated to the direction every healthy run finds — is consistent with a corrupted update but does not distinguish it from other failures.

The methodological findings are the more transferable contribution. An objective reward is not a trustworthy reward; the interval between the interpreter's verdict and the training corpus contained eight independent mechanisms capable of reporting confidently while measuring nothing, one of which permitted a candidate program to certify its own correctness by reading a variable out of its own execution namespace, one of which recorded a seed that governed nothing, and two of which produced well-formed spurious claims — one arithmetic, one architectural — that survived into earlier drafts of this paper. Even the weights are not exempt: a single 256-element block of one adapter tensor moved further than its optimizer could have moved it, because an 8-bit quantization block happened to contain the model's massive-activation channel. Adjacent software-security research names the same shape of failure in different domains, under the language of security smells and tool-adequacy claims, and one strand of it — formally verified code generation — names a fix stronger than any implemented here. We recommend that execution-grounded pipelines treat the verdict channel as adversarial by default, measure benchmark noise floors and ceilings before reporting differences, decompose any measured gain against the failure modes the verifier itself imposes before attributing it to the task, refuse to compare any two measurements until a machine has confirmed they came from the same instrument, compare adapters in function space rather than weight space when the initialization is random, record the configuration that ran rather than the one requested, retain an immutable per-candidate trace so that the choice of training objective does not have to be made before the data are generated, verify every claim of a completed fix against the bytes it describes before publishing it — and set the seed *before the model is wrapped*, then prove it took.

---

## References

Alistarh, et al. (2018). [Title unverified]. arXiv. https://arxiv.org/abs/1809.10505 [author list and title unverified; identifier as given in Appendix F, not re-fetched; year inferred from the arXiv number; cited for the convergence of sparsified-gradient methods]

Altenbernd, et al. (2026). [Title unverified]. arXiv. https://arxiv.org/abs/2604.00726 [author list and title unverified; identifier as given in the research memo, not re-fetched]

Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., & Mané, D. (2016). *Concrete problems in AI safety*. arXiv. https://arxiv.org/abs/1606.06565

Baker, et al. (2015). A new ensemble-based consistency test for the Community Earth System Model (pyCECT). *Geoscientific Model Development, 8*, 2829. [author list, initials, and identifier unverified — taken from the research memo's citation text]

Bouthillier, X., Delaunay, P., Bronzi, M., Trofimov, A., Nichyporuk, B., Szeto, J., Sepah, N., Raff, E., Madan, K., Voleti, V., Kahou, S. E., Michalski, V., Serdyuk, D., Arbel, T., Pal, C., Varoquaux, G., & Vincent, P. (2021). Accounting for variance in machine learning benchmarks. *Proceedings of Machine Learning and Systems, 3*, 747–769.

Bui, N., Savova, G., & Wang, L. (2025). *Assessing the macro and micro effects of random seeds on fine-tuning large language models*. arXiv. https://arxiv.org/abs/2503.07329

Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H. P. de O., Kaplan, J., Edwards, H., Burda, Y., Joseph, N., Brockman, G., Ray, A., Puri, R., Krueger, G., Petrov, M., Khlaaf, H., Sastry, G., Mishkin, P., Chan, B., Gray, S., … Zaremba, W. (2021). *Evaluating large language models trained on code*. arXiv. https://arxiv.org/abs/2107.03374

Chizat, Oyallon, & Bach. (2018). *On lazy training in differentiable programming*. arXiv. https://arxiv.org/abs/1812.07956 [author initials and arXiv identifier unverified against the primary record]

Crump, et al. [Title unverified]. [author list, year, venue, and identifier unverified; cited in Appendix F for a nonparametric test of treatment-effect heterogeneity]

D'Amour, A., Heller, K., Moldovan, D., Adlam, B., Alipanahi, B., Beutel, A., Chen, C., Deaton, J., Eisenstein, J., Hoffman, M. D., Hormozdiari, F., Houlsby, N., Hou, S., Jerfel, G., Karthikesalingam, A., Lucic, M., Ma, Y., McLean, C., Mincu, D., … Sculley, D. (2022). Underspecification presents challenges for credibility in modern machine learning. *Journal of Machine Learning Research, 23*(226), 1–61. https://arxiv.org/abs/2011.03395

Dettmers, T., Lewis, M., Shleifer, S., & Zettlemoyer, L. (2022). 8-bit optimizers via block-wise quantization. *Proceedings of the 10th International Conference on Learning Representations*. https://arxiv.org/abs/2110.02861

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized LLMs. *Advances in Neural Information Processing Systems, 36*.

Ding, Denain, & Steinhardt. (2021). Grounding representation similarity with statistical testing. [author initials, venue, and identifier unverified]

Ding, Feller, & Miratrix. [Title unverified]. [author initials, year, venue, and identifier unverified; cited in Appendix F for a randomization test for treatment-effect variation]

Dodge, J., Ilharco, G., Schwartz, R., Farhadi, A., Hajishirzi, H., & Smith, N. A. (2020). *Fine-tuning pretrained language models: Weight initializations, data orders, and early stopping*. arXiv. https://arxiv.org/abs/2002.06305

Erfan, M., Chowdhury, M. K. H., Ryan, A., & Rahman, M. R. (2026). *From natural language to verified code: Toward AI-assisted problem-to-code generation with Dafny-based formal verification*. arXiv. https://arxiv.org/abs/2604.22601

Ethayarajh, K., Xu, W., Muennighoff, N., Jurafsky, D., & Kiela, D. (2024). KTO: Model alignment as prospect theoretic optimization. *Proceedings of the 41st International Conference on Machine Learning*.

*FLTrust*. (2020). arXiv. https://arxiv.org/abs/2012.13995 [author list and full title unverified; identifier as given in the research memo, not re-fetched; year inferred from the arXiv number]

Gao, L., Schulman, J., & Hilton, J. (2023). Scaling laws for reward model overoptimization. *Proceedings of the 40th International Conference on Machine Learning*, 10835–10866.

Hayou, S., Ghosh, A., & Yu, B. (2024). *The impact of initialization on LoRA finetuning*. arXiv. https://arxiv.org/abs/2406.08447

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. *Proceedings of the 10th International Conference on Learning Representations*.

Kingma, D. P., & Ba, J. (2015). Adam: A method for stochastic optimization. *Proceedings of the 3rd International Conference on Learning Representations*. https://arxiv.org/abs/1412.6980

Lakens, D. (2017). Equivalence tests: A practical primer for *t* tests, correlations, and meta-analyses. *Social Psychological and Personality Science, 8*(4), 355–362.

Li, Chen, & Zhu. (2023). Memory efficient optimizers with 4-bit states. *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2309.01507 [author initials and identifier unverified against the primary record]

*A Little Is Enough*. (2019). arXiv. https://arxiv.org/abs/1902.06156 [author list and full title unverified; identifier as given in the research memo, not re-fetched; year inferred from the arXiv number]

Liu, J., Xia, C. S., Wang, Y., & Zhang, L. (2023). Is your code generated by ChatGPT really correct? Rigorous evaluation of large language models for code generation. *Advances in Neural Information Processing Systems, 36*.

Ma, J., Pei, H., Lausen, L., & Karypis, G. (2025). *Understanding silent data corruption in LLM training*. arXiv. https://arxiv.org/abs/2502.12340

Marx, C., du Pin Calmon, F., & Ustun, B. (2020). Predictive multiplicity in classification. *Proceedings of the 37th International Conference on Machine Learning*, 6765–6774. https://arxiv.org/abs/1909.06677

McCoy, R. T., Min, J., & Linzen, T. (2020). BERTs of a feather do not generalize together: Large variability in generalization across models with similar test set performance. *Proceedings of the Third BlackboxNLP Workshop on Analyzing and Interpreting Neural Networks for NLP*, 217–227. https://arxiv.org/abs/1911.02969

Mitra, S., Neupane, S., Duclos, M., Mittal, S., Piplai, A., Rahman, M. R., Zieglar, E., & Rahimi, S. (2025). *FALCON: Transforming cyber threat intelligence into deployable IDS rules with self-reflection*. arXiv. https://arxiv.org/abs/2508.18684

*Neural thickets*. (2026). arXiv. https://arxiv.org/abs/2603.12228 [author list and full title unverified; identifier as given in the research memo, not re-fetched; year inferred from the arXiv number]

Nikolich, A., Kiselev, I., Platonov, V., & Romanova, K. (2026). *Weight-space geometry of offline reasoning training*. arXiv. https://arxiv.org/abs/2606.23740

Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences, 115*(11), 2600–2606.

Picard, D. (2021). *Torch.manual_seed(3407) is all you need: On the influence of random seeds in deep learning architectures for computer vision*. arXiv. https://arxiv.org/abs/2109.08203

Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct preference optimization: Your language model is secretly a reward model. *Advances in Neural Information Processing Systems, 36*.

Rahman, A., Rahman, M. R., Parnin, C., & Williams, L. (2021). Security smells in Ansible and Chef scripts: A replication study. *ACM Transactions on Software Engineering and Methodology*. https://doi.org/10.1145/3408897

Rahman, M. R., Rahman, A., & Williams, L. (2019). Share, but be aware: Security smells in Python gists. *Proceedings of the IEEE International Conference on Software Maintenance and Evolution (ICSME)*. https://doi.org/10.1109/ICSME.2019.00087

Rahman, M. R., Imtiaz, N., Storey, M.-A., & Williams, L. (2022). Why secret detection tools are not enough: It's not just about false positives — an industrial case study. *Empirical Software Engineering*. https://doi.org/10.1007/s10664-021-10109-y

Rahman, M. R., Rahman, I., & Williams, L. (2025). If you cannot measure it, you cannot secure it: A case study on metrics for informed choice of security controls. *Journal of Information Security and Applications*. https://doi.org/10.1016/j.jisa.2025.104056

Rajan, S. (2026). *Auditing reward hackability in code RL training environments*. arXiv. https://arxiv.org/abs/2606.16062

Ray, J. (2026). *Before the model learns the bug: Fuzzing RLVR verifiers*. arXiv. https://arxiv.org/abs/2606.01066

Ryan, A., Ifti, J. M., Erfan, M., Rahman, A. A. U., & Rahman, M. R. (2025). *Unveiling malicious logic: Towards a statement-level taxonomy and dataset for securing Python packages*. arXiv. https://arxiv.org/abs/2512.12559

Schiffman. (2026). *Transformers converge to invariant algorithmic cores*. arXiv. https://arxiv.org/abs/2602.22600 [author initials and title unverified; identifier as given in the research memo and still unresolved there, not re-fetched; year inferred from the arXiv number]

Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Bi, X., Zhang, H., Zhang, M., Li, Y. K., Wu, Y., & Guo, D. (2024). *DeepSeekMath: Pushing the limits of mathematical reasoning in open language models*. arXiv. https://arxiv.org/abs/2402.03300

Shazeer, & Stern. Adafactor. [author initials, year, full title, venue, and identifier unverified; cited in Appendix F for Adafactor's update clipping]

Shumailov, I., Shumaylov, Z., Zhao, Y., Papernot, N., Anderson, R., & Gal, Y. (2024). AI models collapse when trained on recursively generated data. *Nature, 631*, 755–759.

Shuttleworth, R., Andreas, J., Torralba, A., & Sharma, P. (2024). *LoRA vs full fine-tuning: An illusion of equivalence*. arXiv. https://arxiv.org/abs/2410.21228

Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology: Undisclosed flexibility in data collection and analysis allows presenting anything as significant. *Psychological Science, 22*(11), 1359–1366.

Skalse, J., Howe, N. H. R., Krasheninnikov, D., & Krueger, D. (2022). Defining and characterizing reward hacking. *Advances in Neural Information Processing Systems, 35*, 9460–9471.

Summers, C., & Dinneen, M. J. (2021). Nondeterminism and instability in neural network optimization. *Proceedings of the 38th International Conference on Machine Learning*, 9913–9922. https://arxiv.org/abs/2103.04514

Sun, M., Chen, X., Kolter, J. Z., & Liu, Z. (2024). *Massive activations in large language models*. arXiv. https://arxiv.org/abs/2402.17762

Topollai, & Choromanska. (2026). [Title unverified]. arXiv. https://arxiv.org/abs/2603.16731 [author initials, title, and identifier unverified; identifier as given in the research memo, not re-fetched; year inferred from the arXiv number]

Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika, 34*(1–2), 28–35.

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association, 22*(158), 209–212.

Woodworth, et al. (2020). Kernel and rich regimes in overparametrized models. *Conference on Learning Theory (COLT 2020)*. [author list, initials, and identifier unverified]

Wortsman, et al. StableAdamW. [author list, year, full title, venue, and identifier unverified; cited in Appendix F for StableAdamW]

Yu, M., Wang, D., Shan, Q., Reed, C., & Wan, A. (2024). *The super weight in large language models*. arXiv. https://arxiv.org/abs/2411.07191

Yuan, W., Pang, R. Y., Cho, K., Li, X., Sukhbaatar, S., Xu, J., & Weston, J. (2024). Self-rewarding language models. *Proceedings of the 41st International Conference on Machine Learning*.

Yue, Y., Chen, Z., Lu, R., Zhao, A., Wang, Z., Yue, Y., Song, S., & Huang, G. (2025). Does reinforcement learning really incentivize reasoning capacity in LLMs beyond the base model? *Advances in Neural Information Processing Systems, 38*. https://arxiv.org/abs/2504.13837

Zhu, J., Greenewald, K., Nadjahi, K., Sáez de Ocáriz Borde, H., Brüel Gabrielsson, R., Choshen, L., Ghassemi, M., Yurochkin, M., & Solomon, J. (2024). Asymmetry in low-rank adapters of foundation models. *Proceedings of the 41st International Conference on Machine Learning*. https://arxiv.org/abs/2402.16842

Zhuang, D., Zhang, X., Song, S. L., & Hooker, S. (2022). Randomness in neural network training: Characterizing the impact of tooling. *Proceedings of Machine Learning and Systems, 4*, 316–336. https://arxiv.org/abs/2106.11872

*Note on the Rahman-group citations: an earlier draft assembled these from a Google Scholar author page, and four of its eight entries carried the wrong first author. Each entry retained here has since been checked against its arXiv or Crossref record for author order, venue, and identifier, and the four misattributed papers now appear under their verified first authors (Erfan et al., 2026; Mitra et al., 2025; A. Rahman et al., 2021; Ryan et al., 2025). One entry that could not be located in any primary record — "Mind the gap: Evaluating LLMs for high-level malicious package detection vs. fine-grained indicator identification," previously listed as Rahman et al. (2026b) — has been removed, together with its mention in the Discussion.*

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

All figures derive from retained artifacts, with one exception recorded in Appendix C: the primary comparison's null arm (`llama3-forged-null`) is present in `data/ruler_noise.jsonl` as 5 of its 40 replicates, so Table 1's null row and every figure that depends on that arm cannot be regenerated from the file as shipped. They are reproduced instead from `poscontrol/ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md` (committed at `878eb6a`), which records the arm at *n* = 40, *M* = .492098, SD = .032727 and carries the full 31-task column; only the per-replicate rows are lost. The comparison is reproduced by:

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

Pooled over all replicates. Trained and null are 200 draws per task (40 replicates × 5 samples). "Base matched" is the sampler- and verifier-matched reference of Failure 5: the 40 base replicates carrying a verifier fingerprint, recomputed greedy-free, at 160 draws per task. The Trained and Base-matched columns are generated from `data/ruler_noise.jsonl` rather than transcribed; the Null column is not, because that file retains only 5 of the primary null arm's 40 replicates (`llama3-forged-null`: 775 draws, 25 per task), so the column cannot be regenerated from that file. It is not, however, transcribed from a lost record: all 31 rows reproduce exactly against `poscontrol/ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md`, committed at `878eb6a`, which carries identical counts for all three columns (Null 3,051 of 6,200; Trained 3,085). What that record does not carry is the 40 per-replicate rows, so replicate-level statistics for this arm remain unrecomputable.

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

Per-task pass-rate change against each arm's same-session null, pooled over that arm's replicates. "Typing" is the share of null-arm draws on that task whose only failure was a `NameError` on an un-imported `typing` name, pooled over the three same-session null arms (10,850 draws = 70 replicates × 155 generations: session A's `llama3-forged-null-rep`, 40 replicates; session B's `ctl-null`, 15; retrain 3's `ctl-null3`, 15). Raw and forgiven columns are the primary metric and the upper-bound counterfactual of the Method. Generated from `data/ruler_noise.jsonl`, not transcribed.

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

Each entry states the question, the design, the prediction that would confirm it, the outcome that would refute it, and the cost on the machine now available (an RTX 5080, 16 GB, on a shared workstation with no persistent storage: 24.3 s per optimizer step, which projects to about 25 min for a 1-epoch run — a projection, since only the 3-epoch run, 69 min, has been timed on this machine; 4 min to export and verify; 2.15 min per null evaluation replicate and 2.76 min per adapter replicate, so 4.91 min per interleaved round, 74 min for a 15-replicate interleaved pair, and 3.3 h for a 40-replicate pair). The entries are numbered in the order they should run, and this revision changes that order: the seeding patch every other entry depends on is listed first, the optimizer ablation is the first experiment, and the regime-boundary study that earlier drafts listed first is demoted behind it. Entries F8–F11 are new. They are listed because this article's own preregistration discipline applies to what it intends to run, not only to what it has run.

**F1. Seeding the initialization, and what remains (prerequisite).** Every other entry depends on a seeded `lora_A`, so this is a patch to be validated rather than an experiment to be run. Add `--seed` to `train_native.py` and call `torch.manual_seed(seed)` immediately before `DPOTrainer(...)`; that placement is sufficient on its own, because the draw happens on the default CPU generator inside `get_peft_model` at `dpo_trainer.py:376`, 264 lines before `super().__init__` reaches `set_seed` at `trainer.py:424` (Method, *Initialization Was Not Controlled, and This Revision Traces Why*). Record `torch.initial_seed()` after wrapping in `run_meta.json`, which at present records no seed at all. Validate before trusting: two `--max-steps 1` runs at one seed, after which `poscontrol/init_vs_training.py` must report 224 of 224 `lora_A` tensors bitwise identical and the step-1 gates of F9 must pass. This validation precedes F2, so that a seeding bug cannot masquerade as displacement everywhere. Two library traps apply to any entry that wraps the model itself (a frozen-*A* control, or the custom optimizer one arm of F2 needs): TRL 0.12.2 calls `model.merge_and_unload()` at `dpo_trainer.py:341–343` when `peft_config` is not `None` and the model is already a `PeftModel`, silently destroying the wrap, so a pre-wrapped model must be passed with `peft_config=None`; and `trl.trainer.utils.peft_module_casting_to_bf16` sits inside the branch that is then skipped (about line 378) and must be called by hand. *Prediction:* all 224 `lora_A` tensors become bitwise identical across the two runs, and the residual Δ*W* disagreement between two seeded 1-epoch runs isolates kernel and 8-bit-optimizer non-determinism. *Refuted if:* `lora_A` still differs, which would mean the call order is not the whole story. What this entry delivers is stated plainly: a one-line, upstreamable library fix and the released-adapter audit of F11, not a theoretical result — and as theory it undercuts itself, since Table 2b shows that at this recipe a seed-invariant function makes an unseeded initialization nearly harmless. *Cost:* two `--max-steps 1` runs, minutes; two 1-epoch trainings (about 25 min each, projected) for the residual-Δ*W* claim; no evaluation needed.

**F2. Is the 8-bit optimizer the cause of the block artifact? (first experiment).** The Results localize the artifact and infer the mechanism (*An 8-Bit Optimizer Artifact Localized by a Massive-Activation Channel*; Limitation 3c); this entry demonstrates or refutes it, and separates bit width from paging and from the kernel. *Design:* four runs at a fixed seed (F1), learning rate 2 × 10⁻⁴, `--max-steps 20`, one optimizer flag apart: `adamw_bnb_8bit`, `adamw_torch`, `paged_adamw_8bit`, and `adamw_bnb_8bit` with `min_8bit_size` raised above 229,376, the largest LoRA tensor (every LoRA tensor here has 16,384, 65,536 or 229,376 elements, all above the default threshold of 4,096, so all 448 are quantized by default). The first three are valid `OptimizerNames` in transformers 4.46.3 and need only an `--optim` flag passed into `DPOConfig`, where `adamw_bnb_8bit` is now hard-coded. The fourth is not a flag: transformers 4.46.3 forwards `optim_args` only to its RMSprop, AdEMAMix and AnyPrecision paths (`trainer.py:1338–1339`), so the optimizer must be constructed directly — `optimizers=(bnb.optim.AdamW8bit(params, min_8bit_size=10**6), None)` passed to `DPOTrainer`, which accepts it at `dpo_trainer.py:236`, with the F1 traps observed — or the default monkeypatched. `paged_adamw_8bit` is the one arm with platform risk on Windows (bitsandbytes' paged path uses managed memory and carries a CPU-fallback warning at `optimizer.py:378`); if it errors it is dropped, since the `min_8bit_size` arm already separates bit width from paging. Before any run, the premises are read from the installed bitsandbytes 0.50.1 rather than inferred: `optim/optimizer.py` sets `min_8bit_size` to 4,096 by default (lines 414, 604), falls back to 32-bit state only when a tensor's element count is below it (502, 674), uses a block size of 256 (524, 691), stores both moments as `uint8` with a per-block absmax, and dispatches to `F.optimizer_update_8bit_blockwise` (570, 736; `functional.py:1169`). *Endpoint*, preregistered before the first run: each arm's 448 tensors are scanned (`adam_bound_scan.py`) for elements beyond the initialization bound plus 3.16·Σ*lr*, with Σ*lr* reconstructed from the run's `training_args.bin` through transformers' own `get_cosine_schedule_with_warmup` and binned by (layer, module, 256-aligned flat block); `init_vs_training.py` confirms the seed held; and, because *A*₀ is now known exactly, per-block maps of *A* − *A*₀ are produced for all 224 tensors. The decision rule: the mechanism is confirmed iff `adamw_torch` yields zero such elements across all 448 tensors while `adamw_bnb_8bit` yields at least 50 inside the block [2304, 2559] (block index 9, zero-based; the observed violating columns in the positive control are [2304, 2558]) of `layers.1.mlp.down_proj.lora_A`. Two mechanism discriminators accompany the ablation. A one-step gradient witness (`grad_witness_hook.py`, about 5 min of GPU) hooks `layers.1.mlp.down_proj.lora_A.grad` and records channel 2427's squared gradient against the median of its 255 block-mates, and the same for channel 198's block [0, 255], whose within-block dynamic range is about 70× smaller and should therefore show a weaker effect or none. A numpy emulator (`quantized_adam_emulator.py`) runs Adam with 256-block absmax-quantized second moments under the bitsandbytes dynamic map on gradient columns with one channel about 100× the others, and separates second-moment underflow from first-moment quantization, from the dynamic map's minimum representable value, and from interplay with gradient clipping. *Prediction:* the block excess vanishes under `adamw_torch` and under the raised `min_8bit_size`, and persists under `adamw_bnb_8bit` and `paged_adamw_8bit`; channel 2427's squared gradient exceeds its block-mates' median by orders of magnitude while channel 198's block shows little or nothing; and the emulator reproduces the over-bound displacement from second-moment underflow alone. *Refuted if:* `adamw_torch` also produces elements beyond the bound (the cause is then clipping, a kernel fault, or a driver event — the bound survives as a detector, the mechanism collapses; the logged `grad_norm` is checked, since `max_grad_norm` is 1.0); the excess is not block-aligned on rerun (a non-reproducible event, which reopens the Discussion's corruption hypothesis); it moves to a different window under a different seed or corpus (not column-conditioned); it follows paging rather than bit width; or the raised `min_8bit_size` does not remove it. *Background, so that the article claims the demonstration and not the mechanism:* the displacement bound |Δ*θ*ₜ| ≤ α(1 − β₁)/√(1 − β₂), which is 3.16α at the defaults, is stated by Kingma & Ba (2015, §2.1), who describe it as a trust region; that a block-wise absmax dominated by an in-block outlier under-resolves the small second moments around it, with moment outliers persisting in particular columns, is published in Li, Chen & Zhu (2023, arXiv:2309.01507), and the wider family of corrections for under-estimated second moments includes Adafactor's update clipping (Shazeer & Stern) and StableAdamW (Wortsman et al.). What this experiment tests is whether the deployed bitsandbytes 8-bit blockwise format violates the bound in a real QLoRA run — a direct test of the accuracy-parity claim of Dettmers et al. (2022, arXiv:2110.02861) — and it runs opposite to the one recent analysis of quantized optimizer state, Topollai & Choromanska (arXiv:2603.16731), who report staleness: updates too small rather than too large. Confirmation would establish a deterministic, address-periodic, model-conditioned software corruption class, reproducible where hardware corruption is not; would discharge Limitation 3c; would give the Discussion's TDR hypothesis a mundane competitor for "a silent non-Adam update with no exception"; and would support a plain recommendation — 32-bit optimizer state for LoRA parameters, where the saving on about 42 M parameters is about 0.3 GB. *Cost:* about 10–12 min per arm, about 50 min of GPU for the four, plus about 5 min for the witness hook and CPU minutes for the scans and the emulator.

**F3. Where the seed-invariant regime ends.** The positive control leaves the solution every low-rate run finds (*The High-Learning-Rate Regime Leaves the Seed-Invariant Solution*); this entry locates the boundary and names its marker. That such a boundary exists is theory — the lazy-to-rich transition of Woodworth et al. (2020) and Chizat et al. (arXiv:1812.07956) — and is not what is at stake; what no paper supplies is its location for preference optimization, in per-item behaviour, as a function of training dose. Nikolich et al. (2026, §3.4) show two seeds landing in one basin by loss interpolation on an aggregate metric, and measure neither per-item agreement nor its dependence on dose. *Design:* train two adapters, seeds fixed and differing within each pair (F1), at each of several learning rates spanning the two recipes already measured (5 × 10⁻⁶ and 2 × 10⁻⁴), logging reward margin and reward accuracy at every step, and compare per-task profiles within and across rates. Add the discriminating arm the earlier version of this entry lacked: two early-stopped high-rate runs at 2 × 10⁻⁴ with `--max-steps 17`, two seeds, stopped while train accuracy is below 0.9 and margins are below 2. *Prediction:* profile agreement between independent runs stays at the reliability ceiling at low rates and falls off above some dose, and the marker of the fall-off is reward-margin saturation — the retrains end at margins near 0.78 and train loss 0.582–0.584, the positive control at margins of 10–11 with accuracy 1.0 from about epoch 1.7 and loss 0.121 — rather than the step size itself. If the early-stopped high-rate pair agree with each other and with the low-rate consensus, saturation is the boundary; if they disagree with each other, step size is. The marker is not *A*-displacement: the earlier version of this entry predicted that the fall-off would track `lora_A` leaving its initialization box, and the positive control refutes that, with 95.5% of `lora_A` entries (averaged over the 224 adapted layers) still inside the box at 40× the rate and three epochs, while at the original recipe the Σ*lr* bound caps movement at 1.6% (typical) to 5.0% (worst case) of an element's magnitude. *Refuted if:* two runs at the original recipe disagree, or two runs at 2 × 10⁻⁴ to completion agree as closely as the retrains do. *Cost:* four 1-epoch trainings (about 25 min each, projected) and two `--max-steps 17` runs, with six 15-replicate interleaved pairs at 74 min each; more than the two sessions the earlier version budgeted.

**F4. A re-execution arm for the typing decomposition.** Re-execute failing completions with the import supplied, rather than crediting them by counter. The gate the earlier version of this entry was waiting on is the work itself: patch `eval.py`'s evaluate loop (about lines 259–271, which discards each completion after `forge.verify`) to retain completions and to store both verdicts per candidate in one row — the drift guard described in the Method forbids obtaining the second verdict by re-running under a second pin later, so the two must be recorded together. The first arm then needs no new interpreter and no GPU: re-score retained completions with `from typing import *` injected as a prelude. The second arm installs Python 3.14 per user (`winget`, python.org with `InstallAllUsers=0`, or `uv python install`), about 10 minutes and no administrator rights, and re-scores under it. The verifier pin is named per machine, since it is Python 3.11.9 on the two machines that produced Tables 1 and 2 and 3.12.10 on the present one; the NameError-at-definition behaviour is the same on every version up to 3.13. Under 3.14 the null's base rate also moves, so only adapter-minus-null within one verifier is interpretable, and the [0.2, 0.8] responsiveness screen was calibrated under the older pin. Retained completions also settle which of two mechanisms the retrains use to avoid the NameError — emitting the import, or ceasing to annotate — which are indistinguishable today (Limitation 3b). *Prediction:* the re-executed gain falls between the raw and forgiven figures, closer to the latter. *Refuted if:* it matches the raw figure, meaning the counter is not identifying what it claims. The general statement this entry makes is that construct-valid gain is the component of a measured gain that is invariant under perturbation of the verifier environment at fixed weights; it repositions Limitation 3a from a bound into a measurement. *Cost:* the harness patch; about 1 h of CPU for the prelude arm and about 10 min to install 3.14; and, because no existing row retains a completion (Limitation 9), one 15-replicate interleaved pair (74 min) per adapter scored with retention on — or none, if the patch lands before the positive control resumes (F7) and leaves the fingerprinted verifier files untouched, in which case its remaining rounds supply the completions.

**F5. Function-space comparison of adapters, as the acceptance statistic (control).** Earlier drafts listed this as a headline test of Table 2b. It is no longer one: Nikolich et al. (2026, §3.4) already report, for a different base (Qwen3-4B, attention-only LoRA, math verification), cross-seed LoRA deltas for six losses including DPO with cosine of only 0.07 to 0.36 across learning rates, shared left singular directions (*u*₁ agreement 0.99 against 0.07 for *v*₁), and no loss barrier along their interpolation — "different weights, same basin"; and Schiffman (arXiv:2602.22600) already shows independently trained transformers embedding one computation in nearly orthogonal subspaces. What this entry delivers instead is the statistic that F6 and F8 consume: a per-prompt logit-delta fingerprint (`function_fingerprint.py`) of each adapter against the base over the 31 benchmark prompts, with the dispersion among healthy adapters — at least two trained at the paper recipe on this machine, since the three retrains' weights are not here — defining an acceptance class for "the update took". That is ensemble-consistency acceptance of the kind climate modelling has used since Baker et al. (2015, pyCECT), ported to function space for a single finished adapter; the novelty is the port and the calibration, not the advice to compare in function space. One confound is recorded up front: fingerprints run on the bitsandbytes 4-bit PEFT path, while every behavioural number in this article is measured on the Q4 GGUF adapter path through Ollama, and the served-artifact gap Appendix B names (the Ollama blob is matched to the exported adapter by name rather than by hash; the repository's one `not_the_served_artifact` check in `heldin_history` runs once) must be closed for every arm rather than once. *Prediction:* high cosine in logit-delta space among healthy adapters alongside the 0.004 weight-space cosine, and healthy-versus-healthy fingerprint distances that form a tight class. *Refuted if:* logit deltas are as orthogonal as the weights, which would make the per-task agreement of Table 2b a coincidence of the metric's coarseness; or healthy-versus-healthy distances overlap corrupted-versus-healthy ones (F8), in which case the statistic cannot serve as an acceptance test. *Cost:* two 1-epoch trainings (about 25 min each, projected; one can be F6's healthy adapter), two exports, and a few minutes of forward passes.

**F6. A norm-matched random adapter as a null arm.** Serve an adapter whose *B* is random with per-layer Frobenius norms matched to a healthy adapter's, and score it interleaved against the base and the healthy adapter. This is the cleanest unclaimed control in the program — no prior use of a norm-matched random adapter as the null for an improvement claim was found — and two corrections to the earlier version of this entry are needed before it can run. First, the order: the only adapter on this machine is the positive control, whose update is about 26× the retrains' in norm, so a healthy adapter at the paper recipe must be trained first (about 25 min, projected; 4 min to export). Second, the construction: the random arm is built (`make_random_adapter.py`) on that healthy adapter's own *A*₀, with a 0.5×-scaled variant, and its intruder-dimension count (Shuttleworth et al., 2024) is reported beside the healthy adapter's, so that the two are not separable by spectral signature before any function is measured. Scoring is a 15-round interleaved chain over null, healthy and random arms (about 115 min), with the 0.5× variant as a fourth arm when the session allows; `poscontrol/run_interleaved.py` must first accept more than two arms (`--arms` is declared with `nargs=2` at line 54; the driver loop already iterates). The classification of the original adapter that the Discussion draws from this is behavioural only: its weights are gone, and of the primary comparison's null arm only 5 of 40 rows are on this machine, so the comparison uses the replication and control sessions' rows. *Prediction:* no aggregate gain, a per-task profile of low split-half reliability and unrelated to the healthy profile, and the original adapter — whose profile is weakly reliable (split-half .21 and .52) and unrelated to the retrains' (*The Null Adapter Is Not a Weak Retrain*) — classifying with the random arm rather than with the healthy class. *Refuted if:* it gains, which would place this pipeline in the regime the *Neural Thickets* study reports (arXiv:2603.12228: 8% to 64% of random σ = 0.005 perturbations match or beat the base across models from 0.5 B to 32 B parameters, Llama-3.1-8B included); or its profile is reliable and correlates with the healthy profile above 0.5. *Cost:* one 1-epoch training plus export, and the chain; about one session.

**F7. Finish the positive control.** Thirty-one further interleaved rounds to reach *N* = 40 per arm under the amendment's terms, reporting per session and pooled. Two things the earlier version of this entry left out. The cost must be sized on the adapter-arm rate (2.76 min per replicate), not the null rate (2.15 min): 31 rounds at 4.91 min per round is about 152 min of evaluation alone, and the 4090 null arm showed occasional server stalls of about 19 min. And the remaining rows must be scored under the committed `forge.py` (f22eede7…), with the served artifact re-exported and re-verified against it, so that the amendment's fingerprint and the scoring fingerprint agree. The amendment permits one alternative, offered here as a documented deviation rather than taken: re-declare *N* = 15 per arm, six more rounds, about 30 min. What the interim data already show is stated so that the completed run cannot be read as having discovered it: at *n* = 9 this is a positive control for the *instrument*, not for the pipeline — 0.1 typing failures per replicate against 14.7 for its null, a raw gain of +11.40 pp, and a typing-forgiven gain of +2.01 pp (*p* = .23). *Prediction:* the preregistered rule (*p* < .05 and at least +5.00 pp) is met on the primary metric and not on the typing-forgiven secondary analysis. *Refuted if:* the primary rule fails at *N* = 40, or the forgiven gain reaches the rule, which would mean the high-rate regime's construct-valid effect was under-read at *n* = 9. *Cost:* about 152 min of evaluation for 31 rounds, plus re-export and verification (4 min); about 30 min under the *N* = 15 option.

**F8. Omission-versus-commission fault injection into LoRA-DPO.** Does "the update took" have a functional definition, and do corrupted updates separate from healthy ones by fault type? No study injecting faults into LoRA training was found. *Design:* `fault_inject.py`, a `TrainerCallback` on `on_pre_optimizer_step` (present in transformers 4.46.3 at `trainer_callback.py:349` and invoked at `trainer.py:2532`), trains two corrupted adapters at the paper recipe and a fixed seed (F1): an omission arm, in which a declared fraction of optimizer steps is dropped by zeroing the gradients before the step, and a commission arm, in which the same fraction of steps has its gradients replaced by random vectors of matched norm. Each is exported and scored in a 15-round interleaved chain against the null and the healthy adapter of F6, and fingerprinted by F5. The phenotype taxonomy is a corollary rather than a discovery and is stated as one: in the lazy regime (Chizat et al., arXiv:1812.07956) an omitted step is a missing term in a linear sum, so omission should give a scaled-down copy of the legitimate function (the convergence of sparsified-gradient methods, Alistarh et al., arXiv:1809.10505, is the same fact); commission injects an uncorrelated direction at preserved norm, which by concentration of measure is indistinguishable from F6's norm-matched random adapter — the reason FLTrust (arXiv:2012.13995) accepts updates by cosine to a trusted reference after norm normalization, and the reason norm-bounded corruptions can evade direction-based detection (*A Little Is Enough*, arXiv:1902.06156). What is new is the empirical separation at LoRA-DPO scale, under a 31-task instrument of reliability 0.2–0.9, and the resulting classification of the original adapter, which the Discussion can then state as the outcome of a named test rather than as a narrative. *Prediction:* the omission arm's profile correlates with the healthy profile at reduced amplitude (same shape, smaller gain); the commission arm's profile has low reliability and near-zero correlation with the healthy profile, like the original adapter's; and the two arms separate from each other and from the healthy class on the fingerprint distance of F5. *Refuted if:* omission and commission do not separate in function space, or the healthy class's own dispersion is as wide as the corrupted-to-healthy distance — either of which means the acceptance statistic cannot do the classification asked of it. *Cost:* two 1-epoch trainings (about 25 min each, projected), two exports, and the chain; with F6, about 5.2 GPU-hours over two sessions.

**F9. Training-time liveness and Adam-bound gates.** Standing assertions on every run, installed with the F1 patch and asserted from F2 onward, rather than an experiment. At `--max-steps 1`: every `lora_B` is nonzero across the 224 layers, and every `lora_A` is bitwise unchanged — ∂*L*/∂*A* = 0 while *B* = 0, so any step-1 change in *A* is a corrupted update. At the end of every run, per tensor: max |*B*| ≤ 3.16·Σ*lr* and max |*A* − *A*₀| ≤ 3.16·Σ*lr*, with Σ*lr* taken from the scheduler's realized sum rather than recomputed by hand (under the cosine-with-warm-up schedule the multiplier sum is exactly *T*/2 for any warm-up length, giving Σ*lr* = 1.425 × 10⁻⁴ for the 57-step recipe and 0.0171 for the 171-step positive control; earlier drafts' 1.47 × 10⁻⁴ and 0.0173 counted one warm-up step too many). The first gate is the training-time generalization of `export_adapter.py`'s 50,000× amplified-adapter liveness control; the second is the check that already flags the layer-1 block of the positive control. The bound is not a new invariant — it is the trust region of Kingma & Ba (2015, §2.1) — and the article claims only the observation that lazy-*A* LoRA keeps healthy runs far enough inside it for the separation to be usable, which makes it a detector needing no replica, no recomputation and no seed, unlike the detectors of the silent-data-corruption literature cited in the Discussion. *Prediction:* every healthy 32-bit-state run passes both gates at all 448 tensors; the 8-bit-state arm of F2 fails the end-of-run *A* gate at exactly one tensor; F8's commission arm passes both, which the gate's construction predicts — it detects over-bound displacement, not wrong-direction updates at preserved norm, and the acceptance statistic of F5 exists for the latter. *Refuted if:* healthy 32-bit runs trip the end-of-run gate, meaning the bound is too tight for usable separation at this recipe (gradient clipping and non-deterministic kernels would be the first suspects); the gate then remains an assertion of Adam's contract but not a detector. *Cost:* none on the GPU; seconds of CPU per run.

**F10. Effect-variation statistics on the existing replicate matrix.** Zero compute, and runnable today: every one of the 334 rows of `data/ruler_noise.jsonl` carries the 31-task `sampled` lists of five binary draws, so the replicate-by-task matrix for every arm in Table 2 is already on disk. `profile_stats.py`, which this entry specifies and which is not yet written, computes: Ding, Feller and Miratrix's randomization test for treatment-effect variation, with the average effect as an explicit nuisance parameter; Crump et al.'s nonparametric test for heterogeneity of the task-level effect; PERMANOVA on replicate-by-task profiles, arm against arm; replicate-bootstrap distances to the centroid of retrains 1–3; and pass@*k* for *k* ≤ 5. This converts the article's ad hoc whole-profile permutation test into named, citable tests, declares the direction of every permutation *p* (Table 2b's are one-sided, upper tail), and freezes one implementation for the profile correlations, which have until now been computed ad hoc. Two constraints fix the implementation: scipy is not installed in `.venv-train` (numpy 2.5.2 is), so every test is a pure-numpy permutation implementation, reusing the Welch and incomplete-beta code already in `poscontrol/compare_replication.py`; and every contrast is against its same-session null, never pooled across machines. *Prediction:* effect variation across tasks is detected for every retrain; PERMANOVA does not separate the three retrains from one another beyond replicate noise but separates each from the original adapter and from the positive control; and effect-variation criteria alone do not separate the original adapter from a norm-matched random adapter (F6), while reliability and correlation do. *Refuted if:* PERMANOVA separates the retrains from one another at the replicate level, in which case the agreement of Table 2b is an artifact of pooling draws; or no effect variation is found, in which case the per-task story is noise around a flat shift. *Cost:* CPU minutes.

**F11. Two external audits.** Both run without a GPU, from this machine (huggingface_hub 0.36.2 is installed and the Hub's model API answers from here), through `scan_public_adapters.py`. *Audit 1 — is the seeding defect in released adapters?* For public TRL-trained LoRA adapters whose cards or `training_args.bin` record a seed, compare `lora_A` bitwise across adapters that report the same seed, base model and rank. If initialization was governed by the recorded seed, such pairs share `lora_A`; the call order traced in the Method predicts they do not. *Audit 2 — is the block signature in the wild?* For public Llama-3-8B QLoRA adapters, split by recorded optimizer (`adamw_bnb_8bit` and `paged_adamw_8bit` against `adamw_torch`), scan `layers.1.mlp.down_proj.lora_A` for elements beyond the initialization bound plus 3.16·Σ*lr*, with Σ*lr* reconstructed from each adapter's recorded schedule, and report whether the excess, where present, sits in the block [2304, 2559]. *Prediction:* same-seed TRL adapters have non-identical `lora_A`, and the share of audited adapters whose recorded seed did not govern initialization is reported as a number; the block excess appears in 8-bit-state adapters on Llama-3-8B and in none trained with 32-bit state. *Refuted if:* same-seed adapters match bitwise, meaning the order has been patched upstream or the authors seeded before wrapping, which confines the defect to this library era; or the block excess is absent from public 8-bit-state adapters — the artifact then depends on something particular to this run, such as the rank, the learning rate, or the corpus — or present in 32-bit-state ones, which would refute F2's mechanism from outside. *Cost:* network and CPU time, bounded by downloads of about 167 MB per full-precision adapter.


---

## Appendix G

### Upstream Defect Report: LoRA's Input Factor Is Initialized Before the Trainer Seeds

This appendix states the seed-order defect of the Method in the form a library maintainer would need, so that the finding is actionable independently of anything else in this article. Every line number below was read from the file at the named tag.

**Component.** `trl`, all `Trainer` subclasses that accept a `peft_config`.

**Summary.** A `seed` passed through `TrainingArguments`/`DPOConfig` does not govern the initialization of the LoRA adapter's input factor. The adapter is constructed before the seed is set, so `lora_A` is drawn from whatever state the global RNG happens to hold. Two runs that are identical in code, data, and recorded seed produce different adapters.

**Mechanism.** Inside the trainer subclass's `__init__`, `get_peft_model(model, peft_config)` is reached — directly in earlier versions, via a `_prepare_peft_model` helper in later ones — before `super().__init__(...)`. The `set_seed(args.seed)` call that the seed is expected to flow through lives in `transformers.Trainer.__init__`, at `trainer.py:424` in transformers 4.46.3, preceded there by the comment that the seed must be set before instantiating the model. PEFT initializes the factor at `lora/layer.py` with `kaiming_uniform_(..., a=math.sqrt(5))` and supplies no `generator`, so the draw comes from the default global generator. `lora_B` initializes to zeros and is unaffected; the defect is confined to `lora_A`, and through it to the subspace the update is written in.

**Affected versions.** Every release audited, across the whole span in which the wrap exists: 34 releases from v0.7.11 (2024-02-16) through v1.10.0 (2026-08-13), covering `DPOTrainer`, `SFTTrainer`, and `GRPOTrainer` wherever each exists — 95 trainer constructors in total. **95 of 95 wrap before they seed. None seeds first.** No release examined carries an explicit seeding call ahead of the wrap. Representative constructor positions, given as (`__init__`, wrap, `super().__init__`):

| Tag | Trainer | `__init__` | `get_peft_model` reached | `super().__init__` |
|---|---|---|---|---|
| v0.7.11 | DPO | 142 | 247 | 379 |
| v0.12.2 | DPO | 217 | 376 | 640 |
| v0.14.0 | DPO | 207 | 323 | 469 |
| v0.14.0 | GRPO | 149 | 198 | 269 |
| v1.0.0 | DPO | 502 | 593 | 729 |
| v1.6.0 | DPO | 501 | 589 | 744 |
| v1.7.1 | DPO | 502 | 614 | 781 |
| v1.8.0 | DPO | 515 | 646 | 839 |
| v1.9.2 | DPO | 516 | 647 | 862 |
| v1.10.0 | DPO | 517 | 652 | 888 |

`GRPOTrainer` does not exist before v0.14.0, which accounts for the seven absent constructors. Where it exists, its only `set_seed(args.seed, device_specific=True)` also falls after `super().__init__` — at lines 874, 991, 1070 and 1083 in v1.7.1, v1.8.0, v1.9.2 and v1.10.0 respectively.

**Reproduction.** Construct the same trainer twice in one process with the same `seed`, then compare the adapter's input factors bitwise:

```python
import torch
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig

def lora_A_bytes(seed):
    args = DPOConfig(output_dir="/tmp/x", seed=seed)
    t = DPOTrainer(model=make_model(), args=args,
                   peft_config=LoraConfig(r=16, lora_alpha=32))
    return {n: p.detach().cpu().numpy().tobytes()
            for n, p in t.model.named_parameters() if "lora_A" in n}

a, b = lora_A_bytes(42), lora_A_bytes(42)
print(sum(a[k] == b[k] for k in a), "of", len(a), "lora_A tensors identical")
```

Expected under a governing seed: all identical. Observed: none identical. Calling `torch.manual_seed(seed)` immediately before each `DPOTrainer(...)` makes them identical, which localizes the defect to the ordering rather than to PEFT's initializer.

**Suggested fix.** Seed before the wrap rather than after it. Setting the seed at the top of the trainer subclass's `__init__`, before the model is prepared, is sufficient and does not disturb the later `set_seed` in `transformers.Trainer.__init__`. A caller can obtain the same effect today without a library change by calling `torch.manual_seed(seed)` immediately before constructing the trainer.

**Why it is easy to miss.** Nothing raises. `training_args.bin` records the seed faithfully, the run is reproducible in data order and in `lora_B`, and aggregate metrics are largely unaffected — this article measures per-task behavioral profiles that agree across the unseeded draw at the instrument's reliability ceiling. The defect is visible only in the weights, and only if two runs are compared bitwise. That is the same shape as the measurement-integrity failures reported in the Results: a record that is true of what it describes and false of what a reader will take it to mean.

**Prior report.** Two independent searches of the project's issues and pull requests, and of the literature, found no description of this ordering. That is a statement about two searches, not a proof of absence.


---
