# An Objective Reward Is Not a Trustworthy Reward: Measurement-Integrity Failures, a Replicated Null, and an Unreproducible Checkpoint in Execution-Verified Preference Training

**Treston Malachi Cuzzort** — Independent Researcher — *first author; pipeline, experiment, and original analysis*
**the second investigator** — *independent replication, adversarial review, and the diagnostics of Sections 4.2–4.4*
August 2026 — **REVISION v4** (responding to an independent replication on separate hardware, 2026-08-04 → 2026-08-05)

---

**What changed in v4.** The title changed: v3 was *"An Objective Reward Is Not a Trustworthy Reward: Measurement-Integrity Failures and a Null Result in Execution-Verified Preference Training."* The paper is no longer only a null; it is a null that replicated, a subsidiary finding that did not survive audit, and a checkpoint that does not reproduce. Specifically:

1. **The export-path finding is withdrawn.** It appeared in the abstract, in its own Results subsection, and in the Conclusion, and it is wrong two independent ways. (i) The null arm *is* the base model: the two served Modelfiles differ in exactly one functional line, the `ADAPTER` directive, and name the same base weight blob `sha256-8d2bf4416eb1…cb13d`, the same `TEMPLATE`, and the same four `PARAMETER` lines. An arm that traverses no export path cannot pay an export cost. (ii) The base reference was scored under the superseded greedy-anchored sampler — greedy draws score +12.76 pp above sampled draws *within the base arm's own rows* — and pooled 10 pre-pin rows with 40 post-pin rows across two verifier states (Welch p = 1.9e-8). Matched on sampler and verifier, the gap is +0.71 pp (p = .48) for the trained arm and +0.16 pp (p = .86) for the null. Section 4.2 now reports the retraction and the mechanism instead of the finding.
2. **The primary null replicated independently**, on different hardware, in a different session, with the arms interleaved replicate-by-replicate rather than run as sequential multi-hour blocks: +0.065 pp, p = .9420, 95% CI [−1.709, +1.839], against the original's +0.548 pp, p = .5140, 95% CI [−1.117, +2.214]. Each point estimate falls inside the other's interval. New Section 4.3.
3. **The same code, the same 918 pairs, and the same hyperparameters, retrained, produce +9.7 to +11.0 pp.** Three retrains, each against a same-session interleaved null, land at +9.658, +10.950, and +9.938 pp — and are statistically indistinguishable from each other. The adapter under test is not. New Section 4.4. What variable separates the two training environments is **not isolated**, and the paper says so rather than guessing.
4. **LoRA initialization in `train_native.py` is unseeded.** The script contains no seeding call; the `seed: 42` in `training_args.bin` is HuggingFace's `TrainingArguments` default. Two runs of the identical command produce `lora_A` factors that are 0/224 bitwise identical with mean cosine −0.000474. Limitation 1 is therefore stronger than v3 stated: the single checkpoint is not merely unreplicated, it is not the checkpoint the same command would produce again.
5. **Limitation 4 is discharged.** Benchmark responsiveness is now measured at the arms' own operating point: 0 of 31 tasks at 0.00 or 1.00 for any arm, 31/31 strictly interior, every 95% Wilson interval at n = 200 excluding both bounds. The per-task table is Appendix C.
6. **[AUTHOR TODO] blocks that v3 could not close are closed** from retained artifacts: the null-arm specification, the full training configuration (effective batch 16, 57 optimizer steps, `warmup_ratio` 0.1 *with* `warmup_steps` 0), that the adapter is non-zero (224/224 `lora_B` non-zero, mean ‖ΔW‖_F ≈ 0.020), and that the two arms are provably different models (served blob name = SHA-256 of `adapter.gguf`; per-task permutation p < 5e-5).
7. **Reproducibility defects are disclosed** rather than left implicit: `train_native.py` does not run on current TRL and the paper named no TRL version; Appendix B's first command does not exist; raw completions were never retained; `run_meta.json` records every hyperparameter and zero library versions. New Section 4.11.
8. **The Discussion's four readings are re-scored against the new evidence.** Reading 1 ("the method does not help here") is positively excluded. Reading 2 (signal too narrow to transfer) is weakened. Reading 4 (pairs carried little usable gradient) survives only in a run-specific form.

**What did not change:** the null itself. Every published figure in Table 1 and Appendix A recomputes from the raw rows to four decimals, the largest deviation anywhere being 0.0405 on the degrees of freedom (74.0 vs 73.959468, a rounding artifact) [ZCD §4.4]. The four measurement-integrity failure narratives, the concentration analysis, the corpus-bookkeeping questions, and the preregistration's temporal-precedence limitation are unchanged and were **not re-examined** by the replication; their absence from the corrections above means they were not audited, not that they were audited and passed.

**\[AUTHOR TODO — abstract.\] This revision was prepared against the markdown export of v3, which does not contain the abstract. The abstract's subsidiary-finding sentence still asserts the export-path cost and must be replaced. Proposed replacement: "A subsidiary claim in an earlier version of this work — that the export and quantization path cost 3.3–3.8 pp — is withdrawn; the apparent gap was a reference arm scored under a superseded sampler and pooled across two verifier states."**

**Red [AUTHOR TODO] blocks now mark only what remains genuinely open:** the 43→13 task-flow table and $K$; the train/benchmark contamination check; interpreter provenance for the benchmark screening; corpus bookkeeping (918 / 1,244 / 1,279 / 2,200 and the 10 unverifiable pairs); the study history of adapter `f416f3f9` including the discarded 10-task run; a contemporaneous third-party timestamp anchor or none; the AceCode-87K/89K naming; the rejected-half failure-reason histogram; the source of the effective-task-count figure; the timing of this pipeline's construction relative to Baker et al. (2025); and the version-matrix experiment that would isolate the +10 pp.

**Citation convention for artifacts.** Every number introduced or corrected in v4 carries a bracketed pointer to the artifact that produced it: `[ZCD §x]` = the zero-compute diagnostics, `[REP]` = the replication result, `[FINAL]` = the pooled-null summary, `[CTL]` = the same-session control verdict, `[FINDING]` = the unseeded-init finding, `[RES R-n]` = the residuals register, `[RETRAIN]` = the retraining logs, `[TPD]` = the recovered `training_args.bin` readout. Full paths are in Appendix D.

## Introduction

Preference-based fine-tuning of language models conventionally requires
human annotators to rank model outputs. Direct preference optimization
(DPO; Rafailov et al., 2023) removes the separately trained reward model
from this loop but not the preference labels. Self-rewarding approaches
(Yuan et al., 2024) go further, using the model itself as the judge,
which introduces a well-documented hazard: a model that scores its own
output can improve its score without improving its behavior (Amodei et
al., 2016; Gao et al., 2023; Skalse et al., 2022).

Code generation admits a stronger alternative. A candidate program can
be executed against hidden unit tests, and the verdict is supplied by
the interpreter rather than by any model's opinion. This is the premise
of the pipeline studied here: sample $K$ candidates for a task, execute
each against tests the model never sees, take a passing candidate as
*chosen* and a demonstrably failing one as *rejected*, and train on the
resulting preference pairs. The reward is objective by construction.

This paper reports what happened when that pipeline was measured
properly, and it makes two claims. The first is methodological and, we
argue, the more transferable: an execution-grounded reward is objective
in the sense that its ground truth does not depend on anyone's judgment,
but it is not thereby *trustworthy*. Between the interpreter's verdict
and the training file lie several mechanisms—a harness that runs the
candidate, a channel that reports the outcome, a dataset builder, a gate
that certifies the data, and a benchmark that scores the result—and
several of these proved capable of failing in ways that produce a number
rather than an error. Producing the empirical result below required
finding and closing four such failures. In the two most serious cases a
component continued to emit well-formed output after it had stopped
measuring what it claimed to measure: a verdict that could be forged by
the candidate, a verifier whose answer depended on which script invoked
it, a benchmark returning its ceiling regardless of input, and a gate
whose error message prescribed a remedy that could not succeed. The
first two failed silently in the verdict itself; the third was silent in
a different sense — a correct instrument pointed at tasks on which it
could no longer discriminate; the fourth failed loudly with a
misdirecting remedy. These are heterogeneous defects found in one
project because they were looked for, not a systematic enumeration of
failure modes. This is the failure mode that preregistration,
adversarial witness testing, and measured noise floors exist to catch.

A fifth incident of the same class is reported in this revision, and it
is the paper's own. An earlier version of this work reported that the
export and quantization path cost 3.3–3.8 pp of benchmark accuracy. That
finding is withdrawn in Section 4.2. The reference arm it rested on had
been scored under a superseded sampler and pooled across two verifier
states, and the analysis script that pooled it did not inherit a
refusal-to-pool guard that the measurement script already enforced for
the two arms under test. The result was a well-formed, plausible, and
entirely spurious number, produced by a component that had stopped
measuring the same thing — which is the exact defect class this paper
documents, surviving into a draft of the paper that documents it.

The second claim is empirical and negative: on the benchmark used, the
trained adapter did not beat its null baseline, and the confidence
interval excludes effects of the size the study was designed to detect.
That null has now been reproduced independently, on different hardware,
in a different session, with the two arms interleaved replicate by
replicate rather than run as sequential blocks: +0.065 pp, p = .9420,
95% CI [−1.709, +1.839] against the original +0.548 pp, p = .5140,
95% CI [−1.117, +2.214] [REP]. The null is honestly bounded—one
checkpoint per arm, a narrow task distribution—and its value rests on the
apparatus that produced it rather than on the number itself.

The scope of that null has also narrowed, in a way the original draft
anticipated. Retraining from the same code, the same 918 preference pairs
(byte-identical, SHA-256 `85fc0bdc…`), and the same hyperparameters
produces adapters that beat the same null by +9.7 to +11.0 pp, three
times out of three [FINAL]. The null is therefore a null about one
artifact, not about the procedure that was supposed to produce it — which
is what Limitation 1 said before any of this evidence existed. What
differs between the two training environments is not isolated by this
work, and Section 4.4 states that limit rather than filling it with a
guess.

The vulnerability class itself is documented at frontier scale: Baker et
al. (2025) report that during reinforcement-learning training an agent
discovered an `exit(0)` exploit that terminated the environment before
unit tests ran, and a `raise SkipTest` variant, both of which became
systemic once found; Zhong et al. (2025) measure models' propensity to
exploit test cases directly. What this paper adds is case-level
documentation from the opposite end of the scale: the same class of hole
was present in a small single-developer pipeline and required *no*
optimization pressure to exploit—a two-line literal sufficed—which means
the channel is unsound before any model ever pushes on it. **\[AUTHOR
TODO: State when this pipeline was built relative to Baker et al. (2025)
(March 2025). If construction post-dates that publication, the marginal
value of independently exhibiting the class is smaller and the text
should say so.** The reward-hacking literature largely concerns
optimization pressure discovering unintended maxima of a specified
objective (Amodei et al., 2016; Gao et al., 2023; Skalse et al., 2022);
the failures here were latent in the plumbing regardless of the
optimizer. We therefore restate as practice what these findings jointly
imply: for any automated reward, the channel carrying the verdict should
be treated as adversarial with respect to the artifact being judged,
independently of whether that artifact is believed to be adversarial.

## Background and Related Work

##### Preference optimization and execution-grounded reward.

DPO (Rafailov et al., 2023) optimizes a policy directly on preference
pairs, eliminating the reward-model stage of RLHF. Self-rewarding
pipelines (Yuan et al., 2024) generate those pairs without human labels;
when the judge is a learned model, reward hacking is a first-order
concern (Skalse et al., 2022; Gao et al., 2023). Execution-based
verification replaces the learned judge with unit tests, following the
evaluation methodology of Chen et al. (2021); test suites for the tasks
used here derive from the AceCode-89K corpus (Zeng et al., 2025).
Execution-verified preference training for code is itself an active line
of work: CodeDPO (Zhang et al., 2025) constructs self-generated,
cross-validated preference data at scale and reports gains across five
benchmarks, and PLUM (Zhang et al., 2024) and DSTC (Liu et al., 2024)
train on test-case-derived preferences. Those systems operate at corpus
scales orders of magnitude beyond the 13-task bank studied here, which
is one reason the present null does not contradict their positive
results and should not be read as doing so; the corpus-scale contrast is
discussed in Section 5. KTO (Ethayarajh et al., 2024)
relaxes the pair requirement to per-example labels, a distinction that
becomes material in
Section 4.10.

##### Verifier exploitation in code training.

That execution harnesses can be gamed is established empirical fact, not
hypothesis. Baker et al. (2025) document `exit(0)` and `raise SkipTest`
hacks emerging and becoming systemic during frontier RL training; Zhong
et al. (2025) construct benchmarks that measure test-exploitation
propensity directly; MacDiarmid et al. (2025) trace downstream
misalignment to reward hacking in production RL. This paper's Failure 1
belongs to that documented class. Its marginal contribution is the
setting and the mechanism of discovery: the hole existed in a pipeline
with no optimization pressure applied against it, was found by
adversarial witness testing rather than by observing exploitation, and
was measured to be unexercised before repair.

##### Variance and preregistration.

Fine-tuning outcomes vary substantially with seed, data order, and
stopping point (Dodge et al., 2020; Bouthillier et al., 2021), which
bounds what any single-checkpoint comparison can claim. That literature
assumes the seed is *set*; Section 4.4 reports the case where it is not,
and the checkpoint is one draw from an uncontrolled distribution rather
than from a recorded one. Preregistration
fixes the analysis before the result exists, removing the analyst's
degrees of freedom that produce false positives (Simmons et al., 2011;
Nosek et al., 2018). Both literatures shaped the design below and are
invoked explicitly in the interpretation of the null.

##### Data quality under self-generation.

Execution filtering guarantees that retained programs pass their tests;
it does not prevent the retained set from being behaviorally repetitive,
a concern sharpened by evidence that recursively generated training data
degrades models when diversity collapses (Shumailov et al., 2024).
Section 4.9 measures this directly rather
than assuming it away.

## Method

### Design

A two-arm between-model comparison with 40 independent evaluation
replicates per arm, fixed in advance. **The arms differ by exactly one
directive in the served model definition.** The *trained* arm is the base
model with the LoRA adapter attached at serve time as a GGUF adapter
(`FROM llama3:8b-instruct-q4_K_M` + `ADAPTER adapter.gguf`); the *null*
arm is the same base model with no adapter (`FROM
llama3:8b-instruct-q4_K_M`). Neither arm's base weights were merged,
dequantized, or re-quantized. A unified diff of the two live
`ollama show --modelfile` outputs (103 lines vs 102) returns one hunk
containing one removed line and two added lines: a comment naming the
model, and the `ADAPTER` directive. The base weight blob
(`sha256-8d2bf4416eb1…cb13d`), the `TEMPLATE` block, the four
`PARAMETER` lines (`num_keep 24` and three `stop` tokens), and the
`LICENSE` block are byte-identical between the arms [ZCD §1.1]. Only the
adapter itself was converted, from PEFT safetensors to GGUF,
tensor-for-tensor — 448 in, 448 out, exit 0 [ZCD §1.2].

This is a stronger design than earlier versions of this paper claimed for
it. The pre-specified rationale for comparing against a null arm rather
than the base model was that export-path costs would cancel. What the
artifacts show is that there is no export path on either side to cancel:
the comparison is a pure A/B on one adapter directive with nothing else
differing. The unmodified base model was scored separately as a reference
point; that reference is **not** sampler- or verifier-matched to the arms
and is the subject of the retraction in Section 4.2.

### Materials

##### Base model.

`unsloth/llama-3-8b-Instruct-bnb-4bit`, a 4-bit quantized 8B-parameter
instruction-tuned model, served for inference through Ollama as
`llama3:8b-instruct-q4_K_M`.

##### Training data.

918 preference pairs (`dpo_pairs_capped.jsonl`, SHA-256 `85fc0bdc…`),
stratified with a 120-pair-per-task cap from a larger bank of 1,244. The
pairs span 13 of the 43 tasks in the training pool; the other 30 tasks
produced no pairs, because the pair format emits nothing on a task whose
candidates all pass or all fail
(Section 4.10), so the surviving 13 are selected
for base-model inconsistency — a selection on the outcome variable, not
a sample of the pool. **\[AUTHOR TODO: Provide the task-flow accounting:
43 pool tasks $\to$ tasks with $\geq1$ pass $\to$ tasks with $\geq1$
fail $\to$ tasks contributing pairs $\to$ the capped 918; per-task
candidate counts and pass/fail/timeout/verifier-error histograms; and
the value of $K$ (candidates sampled per attempt). Run the Section 4.9
canonicalizer across the train/benchmark boundary and report the
nearest-neighbor distribution as a contamination check. This item is now
more load-bearing than it was in v3: Section 4.4 reports a +10 pp gain
measured on a benchmark drawn from the same source corpus as the
training tasks, and a contamination check has still not been run.**
Every pair was
verified bidirectionally before training: the chosen completion was
required to pass its hidden tests and the rejected completion was
required to fail them. The full verified corpus comprised 1,279 unique
pairs across 2,200 rows in three files.

One property of the corpus is recorded here because it bears on what the
objective was pointed at. Loading the capped file for training reports
`918 pairs …; 0 carry verbatim completions, 918 fall back to re-fenced
source`: the `chosen_raw`/`rejected_raw` fields that `training_target()`
prefers are absent from every row, so every optimization target is
`extract_code()` output re-wrapped in a fence rather than the text the
policy actually emitted [RES R-6; RETRAIN]. The same wrapper is applied
to both halves of each pair, so presentation is common-mode across the
contrast and cannot carry the preference gradient; what it can affect is
the NLL term contributed by `rpo_alpha` = 1.0, which is trained toward a
normalized presentation that is an artifact of the corpus builder. This
property is identical in the original run and in every retrain, since
they read the same bytes.

##### Training procedure.

Low-rank adaptation (LoRA; Hu et al., 2022) over a quantized base
(Dettmers et al., 2023), rank 16, $\alpha=32$, dropout 0.05, applied to
seven projection modules (`q_proj`, `k_proj`, `v_proj`, `o_proj`,
`gate_proj`, `up_proj`, `down_proj`). One epoch, learning rate
$5\times10^{-6}$, cosine schedule, $\beta=0.1$, `rpo_alpha` $=1.0$ —
with this term active the objective is the RPO variant (the DPO loss
plus a weighted NLL term on the chosen completion), and we name the
method RPO throughout; a falling training loss is therefore expected
from the NLL term alone and is uninformative about the preference term —
maximum sequence length 1,024, maximum prompt length 512,
`adamw_bnb_8bit` optimizer, bf16, `max_grad_norm` 1.0. The resulting
adapter (SHA-256 `f416f3f9…`, 167 MB) is the object under test.

The full optimization schedule, recovered from the original run's
retained `training_args.bin` [TPD], is: per-device batch size 2 ×
gradient accumulation 8 = **effective batch size 16**, over 918 pairs for
one epoch, giving **57 optimizer steps**; `warmup_ratio` 0.1 **and**
`warmup_steps` 0 are both recorded, and both are stated here because the
derived-parameters file lists only the latter, which reads as "no warmup"
and is misleading; `seed` 42, `data_seed` None. The step count is stated
as observed rather than derived: no `trainer_state.json` survived the
original run, and the arithmetic admits 57 or 58 depending on an
unrecorded `drop_last`, so it was confirmed by retraining from the same
gated corpus and configuration, which reported 57 [RETRAIN; RES R-5].

Two facts about the `seed 42` entry are important enough to state in the
Method rather than only in Limitations. It is HuggingFace's
`TrainingArguments` default, not an authorial choice: `train_native.py`
contains **no seeding call of any kind** — `grep -nE
"set_seed|manual_seed|seed" train_native.py` returns nothing. And it does
not govern LoRA initialization: across two runs of the identical command
on identical data, 0 of 224 `lora_A` tensors are bitwise identical, mean
cosine −0.000474 [FINDING]. The consequences are developed in
Section 4.4.

Two checks bound the concern, raised in review, that a single epoch at
lr $5\times10^{-6}$ leaves the adapter indistinguishable from zero. All
224 LoRA $B$ matrices are non-zero, and the Frobenius norm of the
effective update $\Delta W = (BA)\alpha/r$ averages **0.020016** across
the 224 adapted layers (min 0.007717, max 0.038920; per-module means from
0.008846 for `k_proj` to 0.033687 for `up_proj`; zero layers with zero
norm) [ZCD, adapter tensor scan]. And a retrain from the same corpus and
configuration reaches chosen-over-rejected reward accuracies of
0.9125–0.9750 over its last six logged points, with implicit-reward
margins of 0.73–0.85 and `rewards/rejected` negative from epoch 0.52
onward [RETRAIN]. The preference objective was achieved. What Section 4.1
reports is that on this checkpoint it did not transfer to the benchmark.

##### Software stack.

**No library version of the original training run is recorded in any
retained artifact.** `run_meta.json` captures every hyperparameter and
zero library versions, and the original `adapter_config.json` predates
PEFT's `peft_version` field. What can be said is bounded by that:
`train_native.py` names `trl` 0.12.2 in a source comment, nothing
enforces it, and the script passes `rpo_alpha` to `DPOConfig` — an
argument removed in later TRL, so on a current install (1.9.2) it dies at
config construction with `TypeError: DPOConfig.__init__() got an
unexpected keyword argument 'rpo_alpha'` before any training begins
[RES R-5]. The original adapter was therefore produced by *some* TRL
still carrying `rpo_alpha`; which one is not recoverable. The
replication's retrains pinned `trl` 0.12.2 (which pins `transformers`
4.46.3 and `tokenizers` 0.20.3) and record `peft` 0.20.0, `torch`
2.6.0+cu124, Python 3.11.9. That the two environments differ is a fact;
that the difference is the cause of anything is not established, and
Section 4.4 does not claim it.

##### Benchmark.

A frozen 31-task set (SHA-256 over task contents `74560a4c…`) screened
from the AceCode-89K corpus (Zeng et al., 2025) **\[AUTHOR TODO: verify
the corpus name and version actually used against the dataset artifact —
review noted the canonical release may be AceCode-87K** to select tasks
whose base-model pass rate fell inside a $[0.2, 0.8]$ band, i.e., tasks
on which a change can register. The task set is disjoint from the
43-task pool from which training pairs were drawn. Each replicate
sampled 5 completions per task at temperature 0.8 with no greedy anchor,
yielding 155 generations per replicate and 12,400 generations across the
two arms. The frozen set is stable across the one re-freeze on disk:
`ruler_frozen.json` and `ruler_frozen.BEFORE_REFREEZE.json` hold the same
31 task ids, the same 31 `task_sha256` values, the same band, and the
same `ruler_set_sha256 74560a4c…413d`, which is the value recorded in the
preregistration; the re-freeze changed metadata, not tasks [ZCD §5.5].

### Measures

The primary outcome was greedy-free run-level pass@1. An earlier version
of the metric blended one greedy draw with four sampled draws in a fixed
20/80 ratio. This was abandoned before the present study on grounds of
estimator validity: the unbiased pass@$k$ estimator of Chen et al.
(2021) assumes $n$ independent, identically distributed draws, and a
fixed-ratio policy blend violates that assumption. The blend was
therefore a change of estimand rather than a variance reduction, and the
greedy anchor was removed. **The base reference arm was scored before
that change and retains the greedy anchor. This is the fact that
Section 4.2 turns on, and it is stated here rather than there because it
is a property of the measure, not of the result.**

The benchmark's noise floor was measured rather than assumed, and was
measured twice because the metric changed between measurements. Under
the earlier greedy-anchored blend, repeated evaluation of an unchanged
model yielded a run-level standard deviation of 0.0283 across 10
replicates. After the blend was abandoned, a greedy-free
characterization gave 0.0476, and this larger value was used for sizing.
The two floors are floors of different estimands: replacing one of five
i.i.d. draws per task with a deterministic greedy draw scales the
per-task sampling variance by exactly $4/5$, an SD factor of
$\sqrt{0.8}\approx0.894$ — so the blend mechanism predicts a blended
floor of $0.0476\times0.894=0.0426$, not the observed 0.0283. The
mechanism therefore explains only part of the gap, and the honest
statistical statement is that the gap itself is within sampling error:
with roughly ten replicates per characterization,
$F(9,9)=(0.0476/0.0283)^2=2.83$ falls below the two-sided 5% critical
value of 4.03, so the two floors are not statistically distinguishable,
and sizing on the larger figure is simply the conservative choice. Two
further cautions apply. Run-level variance is a property of the
(benchmark $\times$ model) pair, not of the benchmark alone —
Table 1's arms on one benchmark span
SDs of .0327–.0476 — so any single "floor" is at best an approximation
to the variance governing a given comparison. And the consequence for
interpretation must be stated plainly: the minimum detectable effect,
and the later claim that the confidence interval excludes it, are
defined relative to this pre-specified target; under a smaller assumed
floor the same interval would not have excluded the corresponding
target. One observation is offered without a causal claim attached: the
sampler- and verifier-matched base reference constructed in Section 4.2
has SD .0476, numerically identical to the preregistered assumption
[ZCD §3.3]. **\[AUTHOR TODO: Report the replicate count behind the 0.0476
characterization, state which benchmark and which model state produced
each floor, and say whether the 0.0476 assumption and the matched base
reference are the same measurement or a coincidence. If the 0.0283 figure
was measured on the earlier 10-task instrument near its ceiling, a
suppressed SD is a ceiling artifact ($p_i(1-p_i)\to0$) and must be
labeled as such rather than attributed to the blend.**

Run-level dispersion in both arms is close to what an
independent-Bernoulli model predicts, so no large over-dispersion is
inflating the picture: trained observed SD 0.04153 against a predicted
0.03736 (ratio 1.111), null 0.03273 against 0.03770 (ratio 0.868)
[ZCD §3.2].

### Analysis Plan Fixed in Advance

The analysis plan was written to a versioned file
(`prereg_track_a_run1.json`) and committed to version control before the
first replicate was scored. It fixed the arms, the metric, the replicate
count (40 per arm), the statistical test (Welch's $t$-test on run-level
pass@1, two-sided, $\alpha=.05$, each arm retaining its own variance),
and the stopping rule (fixed $N$; no interim analysis; no early stopping
on the observed effect). Every hash recorded in it—the benchmark set,
the adapter, the dataset files, the verifier fingerprint—was derived
programmatically from the live artifacts rather than transcribed. Its
recorded `written_at` is 2026-08-02T16:25:28, which is 26.15 minutes
before the first trained replicate and 179.28 minutes before the first
null replicate; the base reference arm's rows predate it by 3.9 days,
which is why the base arm is labeled "reference only" by the analysis
script and why it is not one of the preregistered arms [ZCD §5.3].

The plan additionally recorded, in the same file and before any result
existed, what the study *could not* show. This practice follows the
preregistration literature's rationale (Nosek et al., 2018; Simmons et
al., 2011): the constraints on interpretation are least self-serving
when fixed before the number is known. One of those entries — *"That the
ruler is unsaturated for THIS pair of arms"* — is discharged by
Section 4.7 and Appendix C, and another — the arms-are-different
verification — by Section 4.1 and Limitation 9.

This paper does not use the word *preregistered* for this plan: the plan
lives in a version-controlled private repository, and git commit
timestamps are author-writable, so temporal precedence is
author-attested rather than independently verifiable. A public deposit
made now would establish existence at deposit time, not precedence.
**\[AUTHOR TODO: Two items restore or replace the stronger claim. (1) If
any contemporaneous third-party anchor of the original commit exists —
an OpenTimestamps proof, a public push recorded by GitHub's events API,
a Zenodo/OSF DOI dated then, or a dated communication to a third party
containing the file hash — cite it here and the word can return to the
title. (2) Independent of (1), add a complete study history: every
evaluation ever run on adapter f416f3f9, including the discarded 10-task
evaluation of Failure 3, with benchmark version, verifier version,
interpreter, outcome, and the date each inclusion/exclusion decision was
made. The file name prereg_track_a_run1.json invites the question of
what run 0 was; answer it.**

##### Sizing.

With an assumed standard deviation of 0.0476 and $n=40$ per arm, the
standard error of the difference is 1.064 pp, giving a minimum
detectable effect of 2.98 pp at 80% power. Observed variability came in
below the assumption (0.0415 and 0.0327), yielding an observed standard
error of 0.836 pp and an achieved sensitivity of 2.34 pp. The study was
therefore somewhat better powered than planned, which bears on the
interpretation of the null.

### Verifier Integrity

Candidates execute in an isolated subprocess (`python -I`) under an
8-second timeout with a coarse banned-operation filter. This is defense
in depth and explicitly *not* a sandbox. Return values are type-checked
against a fixed set of plain builtins by exact type rather than by
`isinstance`, so that a subclass with an overridden `__eq__` cannot
satisfy a test it should fail.

Two further properties were established in the course of this work and
are reported in the Results, because in both cases the property did not
hold when first examined: the interpreter executing candidates is pinned
rather than inherited from the calling script, and the verdict channel
is hardened against the literal forgery described there (the residual in
that section means it is not closed against an adaptive candidate).

Each replicate row records the verifier that scored it. The trained and
null arms share an identical verifier record in all four fields
(`version` 3.11.9, `pinned_away_from_launcher` false, `launcher_version`
3.11.9), so **the primary comparison is not exposed to the interpreter
confound at all** [ZCD §5.4]. The base reference arm's rows do not share
that property, which is half of the reason for the retraction in
Section 4.2.

## Results

### Primary Comparison

The trained adapter did not outperform its null baseline
(Table 1).

| Arm                                  | $n$ |  $M$  | $SD$  |
|:-------------------------------------|:---:|:-----:|:-----:|
| Trained (adapter)                    | 40  | .4976 | .0415 |
| Null (baseline)                      | 40  | .4921 | .0327 |
| Base (reference, as first measured)  | 50  | .5302 | .0467 |
| Base (reference, matched instrument) | 40  | .4905 | .0476 |

Run-level pass@1 on the frozen 31-task benchmark. The two arms are the
preregistered comparison. The base reference is not preregistered and was
measured 3.9 days earlier; the "as first measured" row blends a
temperature-0 greedy draw into each replicate and pools two verifier
states, and the "matched instrument" row restricts to the 40 base
replicates scored under the pinned interpreter and recomputes them
greedy-free, which is the only base figure comparable to the arms
(Section 4.2) [ZCD §3.3, §4.1].

The difference between trained and null arms was $+0.55$ pp, 95% CI
$[-1.12, +2.21]$, $t(74.0)=0.66$, $p=.514$. The effect did not reach the
pre-specified minimum detectable effect of 2.98 pp, nor the achieved
sensitivity of 2.34 pp, and was not significant at $\alpha=.05$. The two
arms' variances differ by a ratio of 1.61 ($SD$ ratio 1.27), which is
within what chance produces at these sample sizes ($F(39,39)=1.61$,
two-sided $p=.1413$; robust Brown-Forsythe $t=1.538$, df 74.6,
$p=.1284$); Welch's test was fixed in the plan precisely so that
no assumption of equal variances would be required either way
[ZCD §4.5].

A secondary paired analysis, in which the two arms were compared task by
task across the 31 benchmark tasks, gave the same point estimate with a
wider interval: $+0.55$ pp, 95% CI $[-2.36, +3.46]$, $t(30)=0.39$,
$p=.703$. The paired analysis is reported second because the plan
designated the run-level test as primary; selecting whichever test
yields the more favorable result after seeing both is the specific
practice preregistration is intended to prevent.

The upper bound of the primary confidence interval ($+2.21$ pp) falls
below the pre-specified minimum detectable effect. Two qualifications
bound what this means. First, the assumption-free statement is simply
that effects above $+2.21$ pp are excluded at one-sided $\alpha=.025$;
whether that makes the null "informative" is relative to the MDE fixed
at sizing, and at these numbers the upper bound falls below the achieved
sensitivity whenever $|t|\lesssim0.81$, so the comparison to the
sensitivity adds little beyond the $p$-value. Second, the exclusion
holds under the run-level estimand only, which treats the 31 tasks and
the single checkpoint as fixed constants: the paired per-task interval
above contains the MDE, so no exclusion of the design target survives
generalization over tasks. Smaller effects are not excluded under any
estimand.

Three checks added in this revision bound the null more tightly than the
$p$-value alone, and one of them makes it more null rather than less.

*Distribution-free confirmation.* A permutation test over 200,000
relabelings gives $p=.5184$ and Mann-Whitney $U=881.5$, $z=0.786$,
$p=.4318$. The Welch $p$ is not a normality artifact [ZCD §4.5].

*Equivalence.* Two one-sided tests at the preregistered $\pm2.98$ pp
margin give $p=.0024$ (statistically equivalent); at $\pm2.00$ pp,
$p=.0433$; at $\pm1.00$ pp, $p=.2953$ and at $\pm0.50$ pp, $p=.5229$ —
not resolved. The 90% TOST interval is $[-0.844, +1.941]$ pp. The
defensible statement is therefore stronger than "we failed to find a
difference": a true aggregate effect of $\pm2$ pp or larger is rejected
at $\alpha=.05$, and anything below $\pm1$ pp is not resolved at $n=40$
[ZCD §4.5].

*The confound-free metric flips the sign.* Re-running the primary on the
harness's own upper-bound metric `aggregate_if_typing_imported` — which
forgives failures caused by an unimported `typing` generic, the defect
class of Failure 2 — gives trained .5723 (SD .0403) against null .5752
(SD .0302): $-0.29$ pp, $t=-0.364$, df 72.3, $p=.7168$. The entire
$+0.55$ pp raw difference is carried by the trained arm making fewer
unimported-`typing` errors, and none of it by solving more tasks
[ZCD §4.5].

**No aggregate effect is not no effect.** The two arms are demonstrably
different models, and the adaptation redistributed per-task performance
while leaving the mean flat. The common-mode (uniform) component of the
trained − null profile is $+0.55$ pp and explains **0.49% of $\Sigma
\Delta^2$**; the signs split 15 up / 14 down / 2 flat (sign test
$p=1.0$); and the SD of $\Delta$ expected from sampling noise alone if
the arms were the same model is 4.69 pp against an observed 7.93 pp,
implying a true per-task effect SD of **6.39 pp** [ZCD §3.2, §3.4]. That
the arms are different models is established three ways and is no longer
an open item: the `ADAPTER` line in the live trained Modelfile names blob
`sha256-4107cf60…436a`, which is character-for-character the SHA-256
computed over `adapter.gguf` (83,917,120 bytes), itself converted
tensor-for-tensor from the safetensors checkpoint whose digest the
preregistration recorded [ZCD §1.2]; a permutation test over whole
replicate rows separates the arms' 31-task profiles at $p<5\text{e-}5$
(observed summed $\chi^2$ 84.915 against a null of mean 32.213, SD 7.992,
maximum over 20,000 permutations 76.577; 2 tasks survive Bonferroni)
[ZCD §1.4]; and an independent behavioral counter — the rate of code
raising `NameError` on an unimported `typing` annotation — separates them
at trained 463/6200 versus null 515/6200, $t=-2.736$, df 77.92,
$p=.0077$ [ZCD §1.4]. The two arms' per-task rates nevertheless correlate
at $r=.9057$ ($\rho=.9028$), which is what a modest perturbation of one
model looks like and not what two unrelated models look like [ZCD §3.1].

### Withdrawn: The Apparent Base-vs-Arms Gap Was an Instrument Mismatch

*This subsection replaces the v3 subsection titled "The Export Path Cost
More Than Training Gained." The finding reported there is withdrawn. It
is replaced rather than deleted, because a withdrawn finding with its
mechanism named is evidence about the apparatus, and quietly removing it
would destroy exactly the record this paper argues for keeping.*

On the numbers as first computed, both arms scored below the unmodified
base model: trained $-3.26$ pp ($p=7.4\text{e-}4$) and null $-3.81$ pp
($p=1.8\text{e-}5$), and that difference was attributed to the export and
quantization path on the reasoning that the null arm traverses it while
carrying no learned adaptation. Two independent facts each falsify that
attribution.

**First, the null arm traverses no export path.** It is the base model
served without an adapter. Its Modelfile and the trained arm's differ in
exactly one functional line, and both name the same base weight blob,
template, stop parameters, and license (Section 3.1; [ZCD §1.1]). The
export-side Modelfile for the null is the single line `FROM
llama3:8b-instruct-q4_K_M`. No merge, dequantization, or re-quantization
of base weights occurred for either arm; only the adapter was converted.
An arm that is byte-for-byte the base model cannot have paid a cost for
being exported, so there is no quantity for the reported 3.3–3.8 pp to
measure.

**Second, the measured gap decomposes into two instrument mismatches.**
The base reference was scored on 2026-07-29, 3.9 days before the arms,
under the superseded metric. Its rows carry a temperature-0 greedy draw
that the arms' rows do not: within the same base rows, greedy draws score
0.6323 (980/1550) and sampled draws 0.5047 (3129/6200) — **+12.76 pp on
the same model, the same tasks, and the same run**. The base arm also
spans two verifier states: 10 rows banked before the interpreter pin
($M=.5910$) and 40 after it ($M=.5150$), Welch between them $+7.597$ pp,
$t=8.217$, df 24.1, $p=1.9\text{e-}8$. This also answers the question v3
left open about sample sizes: the base arm's replicate ids run
`1..10, 1..10, 11..40` with an 18.72-minute gap at the boundary, because
the run was restarted from replicate 1 when the pin landed — which is why
the base arm has 50 replicates and the two arms have 40 [ZCD §3.3, §5.2].

Peeling both confounds gives a sampler- and verifier-matched base
reference of $M=.4905$ (SD .0476, $n=40$). Against it, **trained is
$+0.706$ pp** ($t=0.707$, df 76.6, $p=.482$, 95% CI $[-1.28, +2.69]$) and
**null is $+0.157$ pp** ($t=0.172$, df 69.1, $p=.864$, 95% CI
$[-1.66, +1.98]$). There is no deficit left to explain. Of the apparent
gap, the greedy anchor accounts for $-2.55$ pp and pooling the pre-pin
rows for a further $-1.42$ pp [ZCD §3.3].

Two candidate explanations that v3 left open are therefore withdrawn
rather than carried forward. A chat-template or EOS defect *between the
arms* is excluded by byte comparison of the two served Modelfiles, which
share a template and stop parameters, and by the shape of the difference
profile: a template defect is broad and one-sided, whereas the
common-mode component of trained − null is $+0.55$ pp, accounts for 0.49%
of the total squared difference, and has a 90% interval of
$[-0.84, +1.94]$ pp, so a uniform shift larger than about 2 pp is
excluded by the data [ZCD §3.4]. Session drift is excluded by
measurement: serving the identical adapter GGUF (`sha256 4107cf60…436a`,
hashed on both machines) on different hardware two days later moved the
trained arm by $+0.517$ pp ($p=.573$) and the null arm by $+1.000$ pp
($p=.222$), so session-to-session variance is on the order of 1 pp — far
too small to be a 3.8 pp gap [REP].

**The mechanism, named.** `analyze_run1.load()` groups replicates by
`model` alone, so all 50 base rows average into the published
$M=.5302$ across two samplers and two verifier states.
`ruler_noise.cmd_measure` explicitly refuses that pooling for the arms
and prints `ignoring N replicate(s) banked under a different verifier`.
The guard exists; the analysis path did not inherit it
[RES R-2; `analyze_run1.py:144,153`]. This is why the finding is reported
here as an incident rather than a correction: a component produced a
well-formed, plausible number after it had stopped measuring the same
thing, which is the defect class the rest of this section documents. It
does not touch the primary comparison, which never uses the base rows.

One residual is kept rather than closed. Even after matching, the base
arm shows an unexplained within-run downward drift over its own run order
($r=-0.498$, $t=-3.980$, df 48, $p=.0002$; first half .5489 versus second
half .5115, Welch $p=.0037$), which the two served arms do not show
(trained $r=+0.141$, $p=.386$; null $r=-0.291$, $p=.069$). That is a
reason not to treat the base arm as a clean reference at all, and it is
why no positive claim is made here about arms-versus-base beyond "no
detectable difference" [ZCD §3.4]. Nothing on any row records the Ollama
version, server build, or GPU state across the 91.35-hour gap between the
base measurement and the arms, so the matched comparison holds *given* an
unchanged serving stack, which is plausible and unverified [ZCD §6, C8].

### Independent Replication of the Primary Comparison

The primary comparison was repeated by the second author on different
hardware (NVIDIA RTX 4090), in a different session, from the same served
artifacts, with two design changes that the original run could not
supply: the arms were **interleaved replicate by replicate** rather than
run as sequential blocks, and the full verifier fingerprint — the hashes
of `forge.py`, `screen_tasks.py`, `task_bank.py`, and
`data/screen_results.jsonl`, plus the interpreter — was recorded on every
row [REP; CTL].

The interleaving addresses a confound the original data cannot remove. In
the original run the trained arm ran 16:51–19:22 and the null arm
19:24–20:50 on 2026-08-02, back-to-back with a 2.10-minute handover, so
any step change in machine state at the handover is perfectly aliased
with arm. Within-block drift tests find none, which is evidence against a
block artifact but not proof [ZCD §5.1, §3.4, §6 C11].

| Run | Arm | $n$ | $M$ | $SD$ |
|:---|:---|:---:|:---:|:---:|
| Original (2026-08-02, RTX 4080, sequential blocks) | trained | 40 | .4976 | .0415 |
| Original | null | 40 | .4921 | .0327 |
| Replication (2026-08-04/05, RTX 4090, interleaved) | trained | 40 | .5027 | .0401 |
| Replication | null | 40 | .5021 | .0396 |

Original: $+0.548$ pp, SE 0.836, $t(74.0)=0.656$, $p=.5140$, 95% CI
$[-1.117, +2.214]$. Replication: $+0.065$ pp, SE 0.891,
$t(78.0)=0.073$, $p=.9420$, 95% CI $[-1.709, +1.839]$ [REP]. The two runs
agree in sign, each point estimate falls inside the other's interval, and
both are null. (The replication ran 41 trained replicates and 40 null;
the arm-versus-arm comparison above uses 40 of each [REP], while the
pooled tables of Section 4.4 use all 41 [FINAL]. The difference is
immaterial: 41 rows give $M=.5018$, SD .0401 [CTL].)

A third measurement, run in a later session on the same machine with the
arms again interleaved, returns the same answer at smaller $n$: the
adapter under test scored $M=.5067$ (SD .0325, $n=15$) against a
same-session null at $M=.5071$ (SD .0455, $n=15$), a difference of
$-0.044$ pp, $t(25.3)=-0.030$ [CTL]. The null result has now been
obtained in three independent sessions on two machines, and in four
separate contrasts counting both the arm-versus-arm and the pooled-null
comparisons of the replication session (Section 4.4) [FINAL].

What this replicates and what it does not: **the measurement, not the
training.** Both runs serve the same adapter GGUF, verified by
`sha256sum` on both machines, so training-seed variance is zero in both.
One checkpoint per arm remains one checkpoint per arm.

### The Checkpoint Does Not Reproduce

Three further adapters were trained from the same `train_native.py`, the
same `dpo_pairs_capped.jsonl` (byte-identical, SHA-256 `85fc0bdc…`), and
the same hyperparameters, on the replication machine, and each was
evaluated against a null arm interleaved with it in the same session.

| Adapter | $n$ | $M$ | $SD$ | Effect vs pooled null | $t$ |
|:---|:---:|:---:|:---:|---:|---:|
| Under test (original), 2026-08-04 | 41 | .5018 | .0401 | $-0.483$ pp | $-0.60$ |
| Under test (original), 2026-08-05 control | 15 | .5067 | .0325 | $+0.003$ pp | $0.00$ |
| Retrain 1 | 40 | .6032 | .0405 | $+9.658$ pp | $11.94$ |
| Retrain 2 | 40 | .6161 | .0400 | $+10.950$ pp | $13.64$ |
| Retrain 3 | 15 | .6060 | .0351 | $+9.938$ pp | $9.63$ |

Effects are against the **pooled null**, $n=70$, $M=0.5066$, SD 0.0414,
measured across three separate sessions at .5021 / .5071 / .5183 — the
instrument is stable to about 1.6 pp across sessions [FINAL]. The same
conclusion holds against the strictly same-session nulls: retrain 1
$+9.612$ pp ($t(22.8)=7.19$) and retrain 2 $+10.903$ pp ($t(22.6)=8.18$)
against the null measured alongside them, and $+9.656$ pp and $+10.947$
pp against the adapter under test measured alongside them [CTL].

Two properties of this result matter more than its size.

**The three retrains are statistically indistinguishable from each
other.** Pairwise: retrain 1 − retrain 2 $=-1.291$ pp ($t(78.0)=-1.44$),
retrain 1 − retrain 3 $=-0.280$ pp ($t(28.9)=-0.25$), retrain 2 − retrain
3 $=+1.012$ pp ($t(28.5)=0.92$) [FINAL]. None is significant.

**And they are orthogonal in weight space.** `train_native.py` contains
no seeding call — `grep -nE "set_seed|manual_seed|seed"` returns nothing
— and the `seed: 42` recovered from the original `training_args.bin` is
HuggingFace's `TrainingArguments` default rather than an authorial
choice. Comparing two adapters produced by the identical command minutes
apart on the same machine, over the effective update
$\Delta W=(BA)\alpha/r$ in float64 across 224 layers: mean cosine
**0.004177** (SD 0.004431, min −0.008700), mean magnitude ratio
**1.001948**, mean relative difference **1.412689** against
$\sqrt2=1.414214$, which is exactly what two equal-magnitude orthogonal
vectors must give; the three statistics are mutually consistent
($\sqrt{1+1.001948^2-2\cdot1.001948\cdot0.004177}=1.4127$). Split by
factor: `lora_A`, which is drawn from a seeded RNG before a single step
is taken, is **0/224 bitwise identical** with mean cosine $-0.000474$;
`lora_B`, which initializes to exactly zero, is 0/224 with mean cosine
$-0.001459$. `lora_B` differing is uninformative on its own — it must
differ if training differs at all — but `lora_A` differing means **the
runs did not start from the same place** [FINDING]. Both runs converged
equally well (train loss 0.5821 and 0.5831; runtimes 753.7 s and 757.7 s;
reward accuracies 0.925–0.975 in both).

The instrument behind those numbers was verified on known answers before
it was trusted on an unknown one: comparing an adapter with itself
returns `mean cos = 1.000000` with zero variance, and comparing against
the author's 50,000× amplified control recovers a ratio of exactly 50000
with cosine 1.0 — a control that also caught a real defect, since in
float32 the tool returned a cosine of **1.0049**, which is
mathematically impossible; every figure above is post-fix, computed in
float64 [FINDING]. The author's own amplification artifact was
independently re-verified in the same pass: all 224 `lora_B` tensors
scale by exactly 50000.0, all 224 `lora_A` by exactly 1.0, and the set of
distinct per-tensor ratios over all 448 tensors is $\{1.0, 50000.0\}$
[ZCD §1.3].

**What follows, stated at the strength the evidence supports.**

1. *The pipeline can produce an adapter that moves this benchmark by
   roughly 10 pp.* Same code, same 918 pairs, same hyperparameters, same
   serving construction, three times out of three.
2. *A random-draw or lottery reading of the difference is excluded.*
   Three adapters that share no direction in weight space nevertheless
   agree on the benchmark to within about 1 pp, while the adapter under
   test sits about 10 pp below all three. If the benchmark score were a
   lottery over initializations, the three would scatter. They do not.
3. *The difference is therefore systematic between the two training
   environments — and this work does not isolate which variable it is.*
   The retrains differ from the original run in hardware, driver, CUDA
   and torch build, and library stack simultaneously. The leading
   suspect is the library stack: the original `adapter_config.json`
   predates the `peft_version` field, while the retrains record PEFT
   0.20.0, and `run_meta.json` recorded zero library versions on either
   side. **That is a hypothesis, not a finding. No claim is made here
   that any particular library version caused the difference.**
   Establishing it requires a version matrix — the same corpus and
   configuration trained under enumerated stacks, one factor varied at a
   time — not another retrain.
4. *The serving path transmits adaptation.* The preregistered decision
   rule for the pending positive control had two branches: movement at or
   above the MDE would confirm that the path transmits adaptation, and no
   movement would reframe the paper around an export path that silently
   discards it. A differently-trained adapter through the same one-line
   `ADAPTER` construction moves the benchmark by 10 pp. The second branch
   is excluded.

**What does not follow.** The 10 pp does not license a claim about RPO,
DPO, or execution-verified preference training in general. It was
measured on one base model, one 31-task benchmark drawn from the same
source corpus as the training tasks, one hardware and software
configuration, and one 13-task training corpus with an effective task
count of 9.93. The contamination check between the training pool and the
benchmark has still not been run (Section 3.2 TODO), and it is more
important now than it was when the headline was a null. And it does not
retroactively make the null wrong: the adapter under test was measured
correctly, four times, and it does not move this benchmark.

### Measurement-Integrity Failure 1: A Forgeable Verdict

The verifier reported its verdict by printing a sentinel string to
standard output, and the parent process accepted a candidate when the
subprocess exited zero and the sentinel appeared in `stdout`. The
candidate's code is placed first in the generated harness and therefore
executes at module level before the tests are defined. A candidate
consisting solely of

    print("__PASS__ 0.0")
    raise SystemExit(0)

satisfied both conditions and was scored as passing, despite never
defining the requested function. Both halves of the verdict were
writable by the artifact under judgment.

This falsifies, as implemented, the pipeline's central claim that the
model does not score itself. It is a reward-hacking channel in the sense
of Skalse et al. (2022), differing from the usual case in that no
optimization pressure was required to exploit it; a single literal
string sufficed.

The defect was repaired by requiring the parent process to supply a
128-bit nonce per run, captured by a prelude executing before the
candidate and removed from the environment so that candidate code cannot
read it, with the sentinel emitted only after the test function returns.
Verification before and after appears in
Table 2; the nonce-bearing attack variants did
not exist as tests prior to the repair and are marked accordingly.

| Candidate                                     |  Before  | After |
|:----------------------------------------------|:--------:|:-----:|
| Correct solution                              |   pass   | pass  |
| Incorrect solution                            |   fail   | fail  |
| Forged sentinel                               | **pass** | fail  |
| Forged sentinel + guessed nonce               |    —     | fail  |
| Forged sentinel + nonce read from environment |    —     | fail  |

Verifier response to honest and forged candidates, before and after
repair. Dashes indicate attack variants constructed as part of the
repair, for which no pre-repair test exists. The table is scoped to
non-adaptive candidates; per the residual below, an adaptive candidate
is not excluded.

Whether the channel had ever been *exploited* was measured rather than
assumed: the literal sentinel string appeared in 0 of 2,200 banked rows
and appears in no prompt the model receives. This establishes that the
specific forgery was absent from the banked corpus, not that no
semantically equivalent forgery could exist; no search for functional
equivalents was conducted. The banked rows are also not the full
exposure window: the 2,200 rows contain 1,279 unique pairs, and every
candidate that ever passed through the forgeable verifier — including
discarded candidates and all benchmark generations — was exposed.
Because per-candidate traces did not yet exist
(Section 4.10), the full exposure window is
unmeasurable; within the measurable banked corpus, the hole was
unexercised. All 1,279 pairs were re-verified under the repaired
verifier and passed: every chosen completion passes and every rejected
completion fails under the closed channel. This confirms the pass/fail
labels; it does not retroactively certify any property the repaired
verifier does not check.

A residual is documented rather than claimed closed: the nonce resides
in a module-level variable within the namespace where candidate code
executes, so a candidate written deliberately against this harness could
still retrieve it. Eliminating that requires genuine isolation, not a
better sentinel.

### Measurement-Integrity Failure 2: Ground Truth Dependent on the Interpreter

The verifier launched candidates using the interpreter of whichever
script invoked it. Some pipeline components re-executed under a pinned
Python 3.11 environment while others ran under the system Python 3.14,
meaning the process that admitted benchmark tasks and the process that
scored them could disagree about ground truth.

The magnitude was established by replaying 310 benchmark completions
through both interpreters with identical inputs: 172/310 passed under
3.14 and 154/310 under 3.11, with all 18 disagreements running the same
direction, concentrated on 6 of 31 tasks. The cause was deferred
evaluation of annotations, under which a function signature referencing
an unimported `typing` generic raises at definition time on one version
and is harmless on the other. The permissive reading converted five
benchmark tasks into dead channels at a pass rate of 1.000.

The interpreter is now resolved in one place, recorded in the dataset
receipt, and refuses to fall back to the launching interpreter—a silent
fallback would restore the defect while every artifact continued to
assert that a pin was in force.

Of the four failures, this one is, to our knowledge, undocumented in the
code-evaluation literature and is general beyond this pipeline: any
execution-verified corpus whose task signatures reference typing
generics inherits interpreter-version-dependent ground truth, and an
18/310 (5.8%) one-directional flip rate is large relative to the effects
such corpora are used to detect. Measuring the disagreement rate at
corpus scale across interpreter versions requires no GPU and is the
natural next study. The same defect leaves a live behavioral trace in the
primary comparison: 7.47% of trained draws and 8.31% of null draws raise
`NameError` on an unimported `typing` annotation, and forgiving those
failures flips the sign of the primary difference (Section 4.1)
[ZCD §1.4, §4.5]. **\[AUTHOR TODO: Interpreter provenance is still
required for the screening path: state which interpreter screened the
frozen 31-task benchmark, whether the freeze post-dates the pin (and if
not, re-screen under the pin and report the delta), and reconcile the
task counts — 6 disagreement tasks and 5 dead channels here versus the
27 responsive / 4 out-of-band split in Failure 3, noting that the 50 base
rows as published give 26/31 in band. For the scoring path the question
is closed: the 12,400 primary-comparison generations carry an identical
four-field verifier record on all 80 rows (3.11.9, not pinned away from
the launcher), and the replication's rows additionally carry source
hashes** [ZCD §5.4; REP].

### Measurement-Integrity Failure 3: A Saturated Benchmark

The same adapter evaluated in this study had been evaluated once before,
on an earlier 10-task benchmark. That evaluation returned pass@3 $=0.9$
on all ten runs across both arms without exception, and pass@1 means of
.880 (trained) versus .888 (null). The instrument had reached its
ceiling—a prior characterization found pass@20 equal to pass@3 equal to
0.9000, with 7 of 10 tasks pinned at ceiling and 1 at floor—and was
returning a constant.

An instrument at its ceiling does not announce that it has stopped
measuring; it returns a plausible number. The earlier evaluation was
consequently uninterpretable, and the project record had described the
state as "nothing has run on the real base," which was false in fact (a
real run had occurred) and correct in implication (no interpretable
result existed). The distinction matters operationally: one description
implies training is the next step, the other implies re-measurement is.

The replacement benchmark was screened for tasks inside a $[0.2, 0.8]$
band, frozen with an enforced content hash, and given a measured noise
floor. Of its 31 tasks, 27 are clearly responsive at screening time, and
4 sit outside the band; these were retained and flagged rather than
dropped, because dropping tasks on the basis of the measurement being
reported biases the next round.

That the replacement instrument was still live **at the operating point
where the comparison was actually made** is now measured rather than
assumed, from the retained 200 draws per task per arm: 0 of 31 tasks
return 0.00 or 1.00 for any arm; 31/31 are strictly interior for trained,
null, and base; 0 of 31 are within one draw (1/200) of a boundary; and
every task's 95% Wilson interval at $n=200$ excludes both bounds. The
most extreme interiors are `ace_oss_24748` (trained .1900, Wilson lower
.1417) and `ace_oss_16070` (trained .8400, Wilson upper .8843). Twenty-eight
of 31 remain inside the $[0.2, 0.8]$ screening band in both arms, and the
three that step outside do so by 4 pp or less, i.e. by 1–8 draws out of
200 [ZCD §2.1, §2.2]. The full 31 × 3 table is Appendix C. This
discharges Limitation 4 of the previous revision and the
preregistration's own `what_this_CANNOT_show` entry.

### Measurement-Integrity Failure 4: A Gate That Had Stopped Verifying

The dataset gate re-executes every preference pair before training and
writes a receipt of file hashes that the trainer requires. It was found
to be failing on its own corpus: 1,269 of 1,279 pairs verified, with 10
returning `no_matching_task`.

The cause was a scope error. The gate resolved tasks only from a
hard-coded seed list, while ten pairs appended in a prior measurement
had been drawn from a separately screened task pool. Those pairs were
unverifiable in principle rather than merely stale, and re-running the
gate—which the failure message advised—reproduced the same failure
indefinitely.

The gate was extended to resolve tasks from the screened source through
the same constructor used at screening time, restoring 1,279/1,279. The
receipt was simultaneously extended to fingerprint the task source, on
the reasoning that "0 violations" is a statement about a verifier *and*
a set of tasks: while the task set was a literal inside the verifier
file, the existing hash covered it incidentally; once tasks came from a
data file, it no longer did. Tamper tests confirmed that corrupting
either new fingerprint entry causes the gate to refuse.

Unlike Failures 1–3, this gate failed loudly: its defect was
diagnosability — an alarm whose prescribed remedy reproduced the failure
— not silent corruption, and in that respect it is the integrity
machinery working. A second, narrower defect in the same machinery was
found during the replication and is disclosed in Section 4.11: the
fingerprint hashes working-tree bytes, so line-ending normalization
changes it, and the gate refuses on byte-identical source [RES R-1].
**\[AUTHOR TODO: Close the corpus bookkeeping this
failure exposes: were any of the 10 unverifiable pairs among the trained
918? Was the gate repaired before or after adapter f416f3f9 was trained,
and if after, what receipt did the trainer accept? Reconcile in one
paragraph the four corpus numbers — 918 trained, 1,244 bank, 1,279
unique, 2,200 rows (921 duplicate rows unexplained; 35 pairs outside the
bank).**

### Training-Data Concentration

Because a repetitive training corpus would render a null result
indistinguishable from a corpus consisting of one program repeated,
structural concentration was measured before the comparison was
interpreted. Programs were parsed and their identifiers canonicalized
before hashing, so that renaming does not create apparent diversity.

| Level                         | Clusters | Effective count | Largest share |
|:------------------------------|:--------:|:---------------:|:-------------:|
| Task identifier               |    13    |      9.93       |     13.1%     |
| Chosen, exact text            |   407    |     165.64      |     8.5%      |
| Chosen, canonical structure   |   273    |      90.41      |     9.8%      |
| Rejected, canonical structure |   632    |     441.59      |     4.2%      |
| (Chosen, rejected) contrast   |   767    |     666.41      |     1.4%      |

Concentration of the 918-pair training bank. Effective count is the
inverse Simpson index of the cluster distribution.

The task-level row reproduces a figure computed separately by the corpus
builder (effective task count 9.93) to the reported precision, serving
as a consistency check on the estimator before its novel rows are
trusted. **\[AUTHOR TODO: State the source of that figure. If it comes
from this project's own pipeline logs it is an internal consistency
check, not an independent control, and must not be described as
independent.**

Preference optimization trains on the *contrast* between chosen and
rejected, and at that level the corpus is diverse: 767 distinct contrast
structures across 918 pairs, largest cluster 1.4%. The apparent
concentration on the chosen side reflects 13 tasks with converging
correct solutions, which is what correctness entails. The corpus is
therefore narrow but not collapsed at the level this analysis measures:
exact-text and canonical-AST repetition are excluded under the chosen
canonicalizer, while behavioral equivalence, test-equivalence, and
gradient-level redundancy remain unmeasured. Task breadth—13 tasks,
effective count 9.93—remains the binding constraint on what any result
here can generalize to, and that now applies to the +10 pp of
Section 4.4 exactly as it applies to the null.

*This section was not re-examined by the replication; it is reproduced
from v3 unchanged.*

### Information Discarded by Pair-Primary Pipelines

A subsidiary finding concerns pipeline economics. The pipeline sampled
$K$ candidates per task and emitted at most one preference pair,
discarding the remainder. On tasks where every candidate passed, it
emitted nothing and recorded the attempt as producing no signal.
Instrumentation established that 66% of task attempts produced no
training row and that only 16.9% of paid-for generations reached one.

This is a property of the preference-pair *format*, not of the data. A
pair requires both a success and a failure; supervised fine-tuning
requires only a success; and prospect-theoretic alignment (KTO;
Ethayarajh et al., 2024) requires only a label, making a task on which
everything failed a source of genuine negative signal rather than waste.
A task with four passing candidates yields zero preference pairs and
four supervised examples from generations already purchased and already
verified.

The pipeline was accordingly restructured so that an immutable
per-candidate *trace* is primary, and each training format is a pure
derivation over it. A view can always be rebuilt from the trace; a trace
cannot be rebuilt from a view, so emitting pairs first destroys exactly
what any alternative objective would require. Unit tests fix the
property: four passing candidates yield 0 pairs and 4 supervised rows;
four failing candidates yield 4 labeled negatives; and a timed-out
candidate never becomes a rejected half, a timeout being an absence of
information rather than a wrong answer.

*This section was not re-examined by the replication; it is reproduced
from v3 unchanged.*

### Reproducibility Defects Disclosed

Five defects were found by attempting to reproduce this work from the
code and artifacts as published. They are reported here because a paper
that argues for treating measurement machinery as adversarial should
disclose where its own machinery does not reproduce.

1. **The training code does not run on a current install.**
   `train_native.py` passes `rpo_alpha` to `DPOConfig`, which current TRL
   (1.9.2, installed fresh 2026-08-04) rejects with
   `TypeError: DPOConfig.__init__() got an unexpected keyword argument
   'rpo_alpha'`; the script dies at config construction before any
   training begins. Reproduction requires `trl==0.12.2`, which pins
   `transformers==4.46.3` and `tokenizers==0.20.3`. The code names 0.12.2
   in a comment; nothing enforces it, and no version appeared anywhere in
   the previous revision of this paper [RES R-5].
2. **Appendix B's first command does not exist.** The draft instructed
   `python build_ruler.py verify`; the CLI accepts only
   `{nominate, confirm, freeze}`. A reader following the reproduction
   section failed at step one. Appendix B is corrected below [RES R-4].
3. **Raw completions were never retained.** A census of every
   string-valued field in the retained replicate rows finds a maximum
   string length of 61 characters — a filesystem path. No completions,
   prompts, generated code, or diffs exist in any retained artifact, so
   exact-output agreement between the arms is not computable for the
   original run or for the replication, and cannot be computed
   retroactively for either. It requires a new run with retention enabled
   [ZCD §6 C3; RES R-3].
4. **Replicate rows carry no serving attestation.** Enumerating the union
   of all row keys returns no model digest, adapter hash, Modelfile or
   template, Ollama version or server build, generation seed, prompt,
   completion, ruler-set hash, wall-clock duration, or GPU state;
   thirteen probes for such fields return none. The chain tying a
   replicate to a served model is therefore artifact-level plus
   statistical rather than per-row [ZCD §5.4, §6 C5]. Four of the gaps
   close with recording changes and zero additional compute.
5. **The dataset gate's fingerprint is line-ending dependent, and it
   fired.** `dataset_gate.verifier_fingerprint()` hashes working-tree
   bytes. With `core.autocrlf=true` and no `.gitattributes`
   normalization, the same source file hashes two ways depending on how
   git materialized it: `task_bank.py` authored with LF hashed to
   `b28a47cb…c736`, and checked out where git wrote CRLF it hashed to
   `15770d4d…d8b3`, at which point the gate refused with a
   VERIFIER-CHANGED error on byte-identical source (1,485 bytes, 30 CRLF,
   0 bare LF; the LF-normalized digest of the CRLF file equals the
   receipt value exactly). Any clone with different line-ending settings,
   or any Linux CI runner, gets a refusal that reads like tampering
   [RES R-1].

`run_meta.json` records every hyperparameter and zero library versions,
which is what forced the PEFT version of the original run to be inferred
from field presence rather than read. That gap is the reason Section 4.4
cannot name the variable it would most like to name.

## Discussion

The trained adapter did not beat its null baseline, and the interval
excludes effects of the size the study was powered to detect. That result
has now been obtained in three independent sessions on two machines,
twice with the arms interleaved. Four readings were available in
the previous revision, and we distinguish them because they imply
different next actions. Two of them are now excluded or weakened by
evidence that did not exist then, and one new reading is added.

**The first reading — that the training method does not help here — is
positively excluded.** The previous revision said this reading was not
supportable from one checkpoint, and gave the correct reason: a single
training run has zero training-seed variance by construction, so the
variance of the estimate contains no term for the quantity that varies
most between training runs — initialization, data order, and stopping
point (Bouthillier et al., 2021; Dodge et al., 2020). The point was
sharpened by what the replicates sample: with per-task pass
probabilities near 0.5, the analytic binomial floor
$\sqrt{\sum_i p_i(1-p_i)/(5\cdot31^2)}\approx0.035$ brackets both
observed arm SDs, so the 40 replicates sample the generation RNG and
nothing else — the interval contains no term for training seed, corpus
construction, or task sampling, and could be narrowed arbitrarily by
buying replicates. That argument was right, and it is now not merely an
argument: three adapters retrained from the same code, the same 918
pairs, and the same hyperparameters beat the same null by +9.658,
+10.950, and +9.938 pp (Section 4.4). Whatever the null is about, it is
not about a procedure that cannot move this benchmark.

**The second reading — that the training signal was too narrow to
transfer — is weakened but not eliminated.** The corpus spans 13 tasks
with an effective count of 9.93, and the benchmark, though disjoint, is
drawn from the same source distribution. That reading is consistent with
the concentration analysis, which found the corpus narrow at the task
level while diverse at the contrast level, and consistent with the
published positive results for execution-verified preference training:
CodeDPO (Zhang et al., 2025) reports gains from corpora constructed at
scales orders of magnitude larger. What weakens it is that the three
retrains carry exactly the same narrowness and transfer anyway, at 10 pp.
Corpus breadth was therefore not the binding constraint on *whether*
something transfers in this setting. It remains the binding constraint on
what any of these results generalize to — including the +10 pp, which is
measured on a benchmark drawn from the same source corpus as the training
tasks, with no contamination check run.

**The third reading — that the effect was real but smaller than 2.34
pp — is now bounded.** Equivalence testing rejects a true aggregate
effect of ±2 pp or larger at $\alpha=.05$; effects below ±1 pp are not
resolved at $n=40$ (Section 4.1). Against the 10 pp scale of the
retrains, the adapter under test is not a weak version of the same thing.

**The fourth reading — that the pairs carried little usable gradient —
survives only in a run-specific form.** Two observations supported it:
the preference objective was decisively achieved (reward accuracies
0.91–0.98, margins 0.73–0.85 within one epoch) while the benchmark did
not move, and none of the 918 pairs retained the completions the policy
actually emitted, so every optimization target is `extract_code()` output
re-wrapped in a fence, with the presentation term entering only through
the `rpo_alpha` NLL component (Section 3.2). Both observations remain
true. What they can no longer support is a claim about the *corpus*: the
retrains read the same bytes and transfer. So the defensible version is
narrower — in this particular run the update landed somewhere the
benchmark does not score — and that is close to a restatement of the
finding rather than an explanation of it. **\[AUTHOR TODO: The
rejected-half failure-reason histogram, the count of pairs rejected only
by the exact-type check (Section 3.5), and the truncation rate at
`max_seq_length` 1024 are still the decisive measurements here, and they
require no GPU.**

**A fifth reading is added: the checkpoint is one draw from an
uncontrolled distribution — and the evidence says that is not sufficient
either.** `train_native.py` sets no seed, and two runs of the identical
command produce `lora_A` factors with mean cosine −0.000474, so the
adapter under test is not the adapter the same command would produce
again (Section 4.4). The natural inference is a lottery: some draws work,
this one did not. The data refuse that inference. Three draws that share
no direction in weight space agree on the benchmark to within about 1 pp,
while the adapter under test sits 10 pp below all three. A lottery over
initializations does not produce that pattern. Something systematic
differs between the two training environments, and this work does not
isolate what. The candidate list — library stack, driver and CUDA build,
hardware, and any silent change in the corpus loading path — is
enumerable and testable by a version matrix; naming a winner from the
evidence in hand would be a guess, and none is offered.

We therefore regard the second reading as partially live, the fourth as
live only in its run-specific form, the fifth as the most probable
location of the answer, and the first as excluded. The study's own
pre-specified plan recorded the first as untestable before any data
existed, which was correct, and it is testable now only because someone
else ran the training three more times.

### On the Value of the Null

The result's usefulness rests on the apparatus, not on the number. Four
components of that apparatus were found to be reporting confidently
while not measuring: a verdict channel the candidate could write, a
verifier whose ground truth depended on its caller, a benchmark at its
ceiling, and a gate whose failure message prescribed a remedy that
reproduced the failure. The first three produced well-formed output and
raised no exception; any of them would have yielded a
publishable-looking number with no content. The fourth failed loudly but
misdirected, which is a distinct hazard: an alarm that names the wrong
cause consumes the attention that would have found the right one.

A fifth belongs on that list, and it is this paper's own. The
export-path finding of the previous revision was produced by an analysis
script that pooled a reference arm across two samplers and two verifier
states, in a codebase where the measurement script already refused
exactly that pooling for the arms under test. It produced a number of
plausible size, in the expected direction, with a mechanism ready to
explain it — and it was wrong. The general form is worth stating: a
guard that exists in one code path is not a property of the system, and
the place a stale instrument does the most damage is the *reference*
arm, which nobody preregisters because it is "only" context.

We take the general lesson to be that in execution-grounded training the
objectivity of the reward is the easy part. A test suite genuinely does
decide correctness without appeal to opinion. What is not thereby
guaranteed is that the verdict which reaches the training file is the
verdict the interpreter produced, and every failure documented here
lived in that gap. The reward-hacking literature concerns itself largely
with optimization pressure discovering unintended maxima of a specified
objective (Amodei et al., 2016; Gao et al., 2023; Skalse et al., 2022).
The failures reported here required no optimization pressure at all;
they were latent in the plumbing, and one of them was exploitable by a
two-line literal.

This suggests a practice: for any automated reward, the channel carrying
the verdict should be treated as adversarial with respect to the
artifact being judged, independently of whether that artifact is
believed to be adversarial. The candidate need not intend to cheat for a
writable verdict channel to corrupt a dataset. Concretely, this means
maintaining adversarial witness tests—known-forged candidates that must
fail, alongside known-good candidates that must pass—and running them on
every invocation of the verifier, so that a regression in the verdict
channel surfaces as a test failure rather than as a corrupted corpus.

Four further practices are added from the replication, each of which
changed a conclusion in this paper. Never compare arms measured in
different sessions without a same-session control — that single omission
is what produced the withdrawn finding. Verify a measurement tool on a
known answer before trusting it on an unknown one — the adapter
comparison tool returned a cosine of 1.0049, an impossible value, and was
caught only because it was run against an adapter compared with itself
and against a 50,000× amplified control. Check that every arm carries the
same verifier fingerprint before comparing them. And interleave arms
rather than running them as sequential blocks, so that session drift
cannot be aliased with the quantity under test.

### Relation to Data-Quality Concerns

An adjacent hazard is that verified correctness and data diversity are
separable properties. Execution filtering guarantees that retained
programs pass their tests; it does not prevent the retained set from
being behaviorally repetitive, and exact deduplication does not detect
renaming. This concern is sharpened by evidence that training on
recursively generated data degrades models when diversity collapses
(Shumailov et al., 2024). In the present corpus the concern was tested
and not substantiated at the contrast level, though the corpus is narrow
at the task level. We note it as a variable requiring independent
measurement rather than an assumption inherited from the presence of a
verifier.

## Limitations

The following constrain interpretation and are stated as bounds on the
claim rather than as caveats.

1.  **One checkpoint per arm, and it is not a reproducible checkpoint.**
    The result cannot support a claim about DPO as a method. It
    characterizes this adapter. That sentence was written before any of
    the evidence in Sections 4.3 and 4.4 existed, and it is now the
    load-bearing sentence of the paper: retraining from the same code,
    corpus, and hyperparameters produces adapters that beat the same null
    by 10 pp. The limitation is also stronger than "unreplicated."
    `train_native.py` sets no seed; the `seed 42` in the training
    arguments is a framework default that does not reach LoRA
    initialization; and two runs of the identical command produce
    `lora_A` factors that are 0/224 bitwise identical. The checkpoint
    under test is therefore not the checkpoint the same command would
    produce again [FINDING].

2.  **Narrow task distribution.** 13 training tasks, effective count
    9.93; 31 benchmark tasks from one source corpus, one programming
    language. The benchmark is disjoint from the training pool by task
    id, but no contamination analysis across the train/benchmark
    boundary has been run, and this bounds the +10 pp of Section 4.4 as
    much as it bounds the null.

3.  **Single hardware and software configuration — and the stack
    variable is unisolated.** One GPU, one base model, one quantization
    scheme, one serving stack. This is now the paper's largest open
    question rather than a routine caveat: adapters trained from the same
    code and data on a second machine, under a second library stack, beat
    the null by 10 pp, and the two environments differ in hardware,
    driver, CUDA/torch build, and library versions simultaneously.
    `run_meta.json` recorded zero library versions, and the original
    `adapter_config.json` predates the `peft_version` field, so the
    original stack cannot be fully reconstructed from retained artifacts.
    No claim is made in this paper about which variable is responsible.

4.  **Benchmark responsiveness, verified at the arms' operating point.**
    Of the 31 benchmark tasks, none returns 0.00 or 1.00 for any arm, all
    31 are strictly interior in both arms, none is within one draw of a
    boundary, and every task's 95% Wilson interval at $n=200$ excludes
    both bounds. Twenty-eight of 31 remain inside the $[0.2, 0.8]$
    screening band in both arms; the three exceptions are outside by 4 pp
    or less. The instrument was live where the comparison was made, so
    the null is not a saturation artifact (Appendix C). The residual is
    narrower than the previous revision's: responsiveness is established
    at these arms' operating points, not at arbitrary ones.

5.  **The verifier is not a sandbox.** It is a subprocess with a filter,
    and the nonce residual described in
    Section 4.5 is open.

6.  **The dataset receipt is unsigned, and its fingerprint is
    line-ending dependent.** It defends against drift and accident, not
    against modification of the receipt itself; and because it hashes
    working-tree bytes, a checkout under different line-ending settings
    produces a refusal on byte-identical source (Section 4.11)
    [RES R-1].

7.  **Coverage claims are bound by their mechanisms.** Where this paper
    reports that a class of defect was closed, the claim extends to what
    the corresponding automated check enforces on every run, and no
    further.

8.  **Failures 1 and 4 were repaired by the author of the code under
    test, and the repairs remain independently unreplicated.** The
    independent work reported here covered the measurement and the
    training, not the four repairs; the four failure narratives and
    Table 2 were not re-examined.

9.  **The primary interval measures decoding Monte Carlo error for two
    fixed artifacts.** It contains no term for training seed, corpus
    construction, or task sampling (see the Discussion's binomial-floor
    calculation). That the two arms are functionally different models is
    no longer open and is verified three ways (Section 4.1): the served
    adapter blob is named with the SHA-256 of the exported adapter file,
    which was converted tensor-for-tensor from the preregistered
    checkpoint; a permutation test over whole replicate rows separates
    the arms' 31-task profiles at $p<5\text{e-}5$, the observed statistic
    exceeding all 20,000 permutations; and an independent behavioral
    counter separates them at $p=.0077$. The dedicated positive-control
    adapter (lr $2\times10^{-4}$, multiple epochs) has still not been
    run, but its decision rule is answered in substance: a
    differently-trained adapter through the identical serving
    construction moves the benchmark by 10 pp, so the branch under which
    "no movement reframes the paper around an export path that silently
    discards adaptation" is excluded. Two items remain genuinely open —
    exact-output agreement between the arms, which no retained artifact
    can supply because completions were never retained, and per-row
    attestation of which model served each replicate.

10. **The replication replicates the measurement, not the training.**
    Both the original run and the replication serve the same adapter
    GGUF, hashed identically on both machines, so training-seed variance
    is zero in both. The three retrains were trained and evaluated on one
    machine only, and whether three orthogonal adapters would still agree
    on a *different* benchmark is untested.

11. **The exploit class in Failure 1 was already documented** at
    frontier scale (Baker et al., 2025; Zhong et al., 2025) when this
    work was performed. The finding is confirmatory case documentation
    from a minimal setting, not a novel vulnerability class.

12. **A subsidiary finding of the previous revision was wrong.** The
    export-path cost reported in v3 was an instrument artifact and is
    withdrawn (Section 4.2). It stood through two rounds of adversarial
    review before it was caught by an independent audit of the raw rows.

## Conclusion

Execution-verified preference training on 918 pairs produced no
detectable improvement over its own null baseline on a 31-task frozen
benchmark: $+0.55$ pp, 95% CI $[-1.12, +2.21]$, against an achieved
sensitivity of 2.34 pp. That null replicated on independent hardware in
a different session with the arms interleaved ($+0.065$ pp, $p=.9420$)
and again in a same-session control ($-0.044$ pp), and equivalence
testing rejects a true aggregate effect of $\pm2$ pp or larger. The
analysis plan was fixed in advance, the benchmark's noise floor is
measured, its channels are verified live at the arms' own operating
point, and effects above the interval's upper bound of $+2.21$ pp are
excluded under the run-level estimand; the paired-over-tasks analysis
excludes nothing above $+3.46$ pp.

The null is a null about one artifact, which is what this paper's own
Limitation 1 asserted before there was evidence for it. Three adapters
retrained from the same code, the same 918 preference pairs, and the same
hyperparameters beat the same null by $+9.7$ to $+11.0$ pp and are
statistically indistinguishable from one another despite being orthogonal
in weight space. Which variable separates the two training environments
is not isolated by this work, and no cause is claimed for it; the
experiment that would isolate it is a version matrix over the training
stack, not another retrain.

A subsidiary claim of the previous revision is withdrawn. The export and
quantization path did not cost 3.3–3.8 pp; the null arm is the base model
served without an adapter and traverses no such path, and the apparent
gap was a reference arm scored under a superseded sampler and pooled
across two verifier states by an analysis script that did not inherit a
guard the measurement script already enforced. Matched on sampler and
verifier, neither arm differs from the base ($+0.71$ pp and $+0.16$ pp,
both n.s.).

The methodological findings are the more transferable contribution. An
objective reward is not a trustworthy reward; the interval between the
interpreter's verdict and the training corpus contained four failure
incidents, two of which corrupted or could have corrupted the reported
verdict silently — one permitting a candidate program to certify its own
correctness with a printed string, the other making ground truth depend
on the interpreter version — and a fifth incident of the same class was
committed by this paper's own analysis path and survived into print. We
recommend that execution-grounded pipelines treat the verdict channel as
adversarial by default, measure benchmark noise floors and ceilings
before reporting differences, retain an immutable per-candidate trace so
that the choice of training objective does not have to be made before the
data is generated, seed and record every stochastic component of training
including adapter initialization, record the library stack alongside the
hyperparameters, and interleave arms so that session drift can never be
aliased with the effect under test.

This paper is not finished. The version-matrix experiment, the corpus
bookkeeping, the task-flow accounting, the contamination check, and the
study history are open, and are marked as such throughout.

## Acknowledgments and Disclosure

The original experiments were conducted on a single consumer workstation
(NVIDIA RTX 4080, 16 GB VRAM). The independent replication, the three
retrains, and the diagnostics of Sections 4.2–4.4 were conducted by the
second author on separate hardware (NVIDIA RTX 4090) between 2026-08-04
and 2026-08-05, from the first author's code and data. Analysis code,
instrumentation, and drafting were produced with AI assistance (Claude,
Anthropic) under the authors' direction; all reported numbers were
produced by executed code, and the raw artifacts are retained. Code,
data, preregistration, the replication bundle, and the complete working
record are retained in a private repository and are available from the
authors.

<div class="thebibliography">

99

Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., and
Mané, D. Concrete problems in AI safety. *arXiv preprint
arXiv:1606.06565*, 2016.

Baker, B., Huizinga, J., Gao, L., Dou, Z., Guan, M. Y., Madry, A.,
Zaremba, W., Pachocki, J., and Farhi, D. Monitoring reasoning models for
misbehavior and the risks of promoting obfuscation. *arXiv preprint
arXiv:2503.11926*, 2025.

Bouthillier, X., Delaunay, P., Bronzi, M., Trofimov, A., Nichyporuk, B.,
Szeto, J., Sepah, N., Raff, E., Madan, K., Voleti, V., Kahou, S. E.,
Michalski, V., Serdyuk, D., Arbel, T., Pal, C., Varoquaux, G., and
Vincent, P. Accounting for variance in machine learning benchmarks.
*Proceedings of Machine Learning and Systems*, 3:747–769, 2021.

Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H. P. de O., Kaplan, J.,
Edwards, H., Burda, Y., Joseph, N., Brockman, G., et al. Evaluating
large language models trained on code. *arXiv preprint
arXiv:2107.03374*, 2021.

Dettmers, T., Pagnoni, A., Holtzman, A., and Zettlemoyer, L. QLoRA:
Efficient finetuning of quantized LLMs. In *Advances in Neural
Information Processing Systems*, volume 36, 2023. arXiv:2305.14314.

Dodge, J., Ilharco, G., Schwartz, R., Farhadi, A., Hajishirzi, H., and
Smith, N. A. Fine-tuning pretrained language models: Weight
initializations, data orders, and early stopping. *arXiv preprint
arXiv:2002.06305*, 2020.

Ethayarajh, K., Xu, W., Muennighoff, N., Jurafsky, D., and Kiela, D.
KTO: Model alignment as prospect theoretic optimization. In *Proceedings
of the 41st International Conference on Machine Learning*, 2024.
arXiv:2402.01306.

Gao, L., Schulman, J., and Hilton, J. Scaling laws for reward model
overoptimization. In *Proceedings of the 40th International Conference
on Machine Learning*, pages 10835–10866. PMLR, 2023.

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang,
L., and Chen, W. LoRA: Low-rank adaptation of large language models. In
*International Conference on Learning Representations*, 2022.
arXiv:2106.09685.

Liu, Z., Zhang, S., Liu, Y., Liu, B., Yang, Y., and Wang, Z. DSTC:
Direct preference learning with only self-generated tests and code to
improve code LMs. *arXiv preprint arXiv:2411.13611*, 2024.

MacDiarmid, M., Wright, B., Uesato, J., Benton, J., Kutasov, J., Price,
S., Bouscal, N., et al. Natural emergent misalignment from reward
hacking in production RL. *arXiv preprint arXiv:2511.18397*, 2025.

Nosek, B. A., Ebersole, C. R., DeHaven, A. C., and Mellor, D. T. The
preregistration revolution. *Proceedings of the National Academy of
Sciences*, 115(11):2600–2606, 2018.

Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., and
Finn, C. Direct preference optimization: Your language model is secretly
a reward model. In *Advances in Neural Information Processing Systems*,
volume 36, 2023. arXiv:2305.18290.

Shumailov, I., Shumaylov, Z., Zhao, Y., Papernot, N., Anderson, R., and
Gal, Y. AI models collapse when trained on recursively generated data.
*Nature*, 631:755–759, 2024.

Simmons, J. P., Nelson, L. D., and Simonsohn, U. False-positive
psychology: Undisclosed flexibility in data collection and analysis
allows presenting anything as significant. *Psychological Science*,
22(11):1359–1366, 2011.

Skalse, J., Howe, N. H. R., Krasheninnikov, D., and Krueger, D. Defining
and characterizing reward hacking. In *Advances in Neural Information
Processing Systems*, volume 35, 2022. arXiv:2209.13085.

Welch, B. L. The generalization of "Student's" problem when several
different population variances are involved. *Biometrika*,
34(1–2):28–35, 1947.

Yuan, W., Pang, R. Y., Cho, K., Li, X., Sukhbaatar, S., Xu, J., and
Weston, J. Self-rewarding language models. In *Proceedings of the 41st
International Conference on Machine Learning*, 2024. arXiv:2401.10020.

Zhang, D., Diao, S., Zou, X., and Peng, H. PLUM: Preference learning
plus test cases yields better code language models. *arXiv preprint
arXiv:2406.06887*, 2024.

Zhang, K., Li, G., Dong, Y., Xu, J., Zhang, J., Su, J., Liu, Y., and
Jin, Z. CodeDPO: Aligning code models with self generated and verified
source code. In *Proceedings of the 63rd Annual Meeting of the
Association for Computational Linguistics*, 2025. arXiv:2410.05605.

Zhong, Z., Raghunathan, A., and Carlini, N. ImpossibleBench: Measuring
LLMs' propensity of exploiting test cases. *arXiv preprint
arXiv:2510.20270*, 2025.

Zeng, H., Jiang, D., Wang, H., Nie, P., Chen, X., and Chen, W. AceCoder:
Acing coder RL via automated test-case synthesis. *arXiv preprint
arXiv:2502.01718*, 2025.

## Appendix A: Statistical Detail

Welch's $t$-test (Welch, 1947) was used rather than the pooled-variance
alternative because the arms are not assumed to share a variance: a
training intervention that changes the spread of outcomes has changed
the model, and pooling would absorb that change into the denominator.

Given trained ($M=.4976$, $SD=.0415$, $n=40$) and null ($M=.4921$,
$SD=.0327$, $n=40$):

- Standard error of the difference:
  $\sqrt{.0415^2/40 + .0327^2/40} = .00836$ (0.836 pp)

- Welch–Satterthwaite degrees of freedom: 74.0

- $t = 0.0054825 / 0.00836039 = 0.6558$ (0.66 to two decimals)

- Two-sided $p = .514$

- 95% CI: $0.55 \pm (1.993 \times 0.836) = [-1.12, +2.21]$ pp

All figures in this appendix are computed from the unrounded
per-replicate rates and then rounded for display. Recomputing them from
the rounded means in Table 1 instead yields $[-1.11, +2.22]$ and
$p\approx.512$; those are artifacts of display rounding and not the
reported values. An independent recomputation from the raw rows gives
difference $+0.548250$ pp, SE $0.836039$ pp, $t=0.655816$,
df $=73.959468$, $p=0.513978$, 95% CI $[-1.117496, +2.213996]$, and the
paired secondary $+0.548387$ pp, SD of the 31 paired differences
$7.9271$ pp, $t(30)=0.385170$, $p=0.702829$, CI $[-2.359304, +3.456079]$
— every published digit is the correctly-rounded form of these, with a
maximum deviation across an 18-field comparison of 0.0405 on df
[ZCD §4.2, §4.3, §4.4].

Sizing at the pre-specified $SD$ of .0476 gives a standard error of
1.064 pp and a minimum detectable effect of approximately
$2.8 \times 1.064 = 2.98$ pp at 80% power. The observed standard error
of 0.836 pp corresponds to an achieved sensitivity of 2.34 pp.

The $t$ distribution was implemented directly (regularized incomplete
beta by continued fraction; critical values by bisection on the
resulting CDF), as no scientific computing library was installed in the
analysis environment. The implementation self-checks against known
critical values—$t_{.975}(10)=2.228$, $t_{.975}(78)=1.991$, and a
two-sided $p$ of .0546 at $t=2.0$ with 30 degrees of freedom—and aborts
before reporting if any check fails. The independent recomputation cited
above used a second from-scratch implementation on an interpreter that
also lacked scipy, cross-checked against direct Simpson integration of
the $t$ density with agreement below $5\times10^{-14}$ on every reported
$p$-value [ZCD §S0].

## Appendix B: Reproduction

All figures derive from retained artifacts. The comparison is reproduced
by:

    python build_ruler.py freeze     # re-freeze / confirm the benchmark content hash
                                     # (the CLI accepts nominate | confirm | freeze;
                                     #  the `verify` subcommand named in v3 does not exist)
    python verify_dataset.py         # re-verify all pairs; write the receipt
    python ruler_noise.py measure --runs 40 --model <arm>
    python analyze_run1.py           # the pre-specified comparison

Two warnings apply to anyone running these. `analyze_run1.py` groups
replicates by model name alone and will pool replicates banked under
different samplers or different verifier states; the base reference arm
must not be read from its output without partitioning first
(Section 4.2). And `verify_dataset.py`'s fingerprint hashes working-tree
bytes, so a checkout with different line-ending settings will produce a
VERIFIER-CHANGED refusal on unmodified source (Section 4.11).

Training is reproduced by `python train_native.py` **only under
`trl==0.12.2`** (which pins `transformers==4.46.3` and
`tokenizers==0.20.3`); on later TRL the script raises
`TypeError: DPOConfig.__init__() got an unexpected keyword argument
'rpo_alpha'` before training begins. The run consumes 918 pairs at
effective batch 16 for one epoch = 57 optimizer steps. Note that it sets
no random seed: adapters produced by repeated invocations are not
expected to match, bitwise or in subspace (Section 4.4).

Artifacts retained: the preregistration
(`data/prereg_track_a_run1.json`); the frozen benchmark with its content
hash (`data/ruler_frozen.json`); per-replicate raw outcomes
(`data/ruler_noise.jsonl`); the verified corpus and its receipt
(`data/dpo_pairs_capped.jsonl`, `data/dataset_verification.json`); the
concentration measurement (`data/bank_concentration.json`); and the
adapter under test with its training metadata (`dpo_adapter_native/`,
including `training_args.bin`, from which the full optimization schedule
of Section 3.2 was recovered).

Each replicate comprised 155 generations (31 tasks $\times$ 5 samples)
and required approximately 151 s. The two arms together consumed 12,400
generations. **\[AUTHOR TODO: This appendix still does not reproduce the
served arms byte-for-byte: add the conversion command line for the
adapter GGUF, the Ollama and llama.cpp versions, and the
temperature-0.8 determinism story. The Modelfiles themselves are now
specified in Section 3.1 (`FROM llama3:8b-instruct-q4_K_M` plus, for the
trained arm, one `ADAPTER` line), which is the part that was previously
unspecified.**

## Appendix C: Per-Task Pass Rates at the Arms' Operating Point

Pooled over replicates: trained and null are 200 draws per task
(40 replicates × 5 samples); "base (as published)" is 250 draws per task
(50 replicates × 5, including one temperature-0 greedy draw per
replicate); "base (matched)" is the 40 base replicates carrying a
verifier fingerprint, recomputed greedy-free (160 draws per task). Source:
[ZCD §2]. Row-level integrity was checked first: for all 130 rows the
stored `aggregate["pass@1"]` reproduces from `per_task` as
`round(mean(correct/n), 4)` with 0 mismatches, and
`correct == greedy + sum(sampled)` in all 4,030 per-task cells with 0
violations.

| # | task id | trained k/200 | trained | null k/200 | null | T−N (pp) | base k/250 | base | base matched k/160 | base matched | flags |
|---|---------|---------------|---------|------------|------|----------|------------|------|--------------------|--------------|-------|
| 1 | ace_oss_11023 | 97/200 | 0.4850 | 76/200 | 0.3800 | +10.5 | 114/250 | 0.4560 | 64/160 | 0.4000 |  |
| 2 | ace_oss_11739 | 97/200 | 0.4850 | 104/200 | 0.5200 | −3.5 | 99/250 | 0.3960 | 79/160 | 0.4938 |  |
| 3 | ace_oss_14121 | 104/200 | 0.5200 | 121/200 | 0.6050 | −8.5 | 161/250 | 0.6440 | 92/160 | 0.5750 |  |
| 4 | ace_oss_15186 | 147/200 | 0.7350 | 129/200 | 0.6450 | +9.0 | 184/250 | 0.7360 | 105/160 | 0.6562 |  |
| 5 | ace_oss_15273 | 108/200 | 0.5400 | 107/200 | 0.5350 | +0.5 | 141/250 | 0.5640 | 73/160 | 0.4562 |  |
| 6 | ace_oss_16070 | 168/200 | 0.8400 | 162/200 | 0.8100 | +3.0 | 217/250 | 0.8680 | 136/160 | 0.8500 | T, N, B outside [.2,.8] |
| 7 | ace_oss_17851 | 112/200 | 0.5600 | 92/200 | 0.4600 | +10.0 | 83/250 | 0.3320 | 65/160 | 0.4062 |  |
| 8 | ace_oss_17880 | 141/200 | 0.7050 | 114/200 | 0.5700 | +13.5 | 174/250 | 0.6960 | 99/160 | 0.6188 |  |
| 9 | ace_oss_19459 | 148/200 | 0.7400 | 158/200 | 0.7900 | −5.0 | 211/250 | 0.8440 | 131/160 | 0.8187 | B outside [.2,.8] |
| 10 | ace_oss_19944 | 55/200 | 0.2750 | 63/200 | 0.3150 | −4.0 | 62/250 | 0.2480 | 50/160 | 0.3125 |  |
| 11 | ace_oss_21695 | 75/200 | 0.3750 | 60/200 | 0.3000 | +7.5 | 123/250 | 0.4920 | 61/160 | 0.3812 |  |
| 12 | ace_oss_23069 | 78/200 | 0.3900 | 55/200 | 0.2750 | +11.5 | 103/250 | 0.4120 | 53/160 | 0.3312 |  |
| 13 | ace_oss_23132 | 123/200 | 0.6150 | 153/200 | 0.7650 | −15.0 | 193/250 | 0.7720 | 108/160 | 0.6750 | Bonferroni-significant |
| 14 | ace_oss_23388 | 57/200 | 0.2850 | 74/200 | 0.3700 | −8.5 | 67/250 | 0.2680 | 49/160 | 0.3063 |  |
| 15 | ace_oss_2454 | 49/200 | 0.2450 | 49/200 | 0.2450 | +0.0 | 46/250 | 0.1840 | 36/160 | 0.2250 | B outside [.2,.8] |
| 16 | ace_oss_24748 | 38/200 | 0.1900 | 56/200 | 0.2800 | −9.0 | 37/250 | 0.1480 | 29/160 | 0.1812 | T, B outside [.2,.8] |
| 17 | ace_oss_27102 | 49/200 | 0.2450 | 38/200 | 0.1900 | +5.5 | 104/250 | 0.4160 | 44/160 | 0.2750 | N outside [.2,.8] |
| 18 | ace_oss_28031 | 149/200 | 0.7450 | 121/200 | 0.6050 | +14.0 | 179/250 | 0.7160 | 93/160 | 0.5813 |  |
| 19 | ace_oss_28113 | 58/200 | 0.2900 | 53/200 | 0.2650 | +2.5 | 61/250 | 0.2440 | 53/160 | 0.3312 |  |
| 20 | ace_oss_31420 | 139/200 | 0.6950 | 139/200 | 0.6950 | +0.0 | 175/250 | 0.7000 | 98/160 | 0.6125 |  |
| 21 | ace_oss_31439 | 137/200 | 0.6850 | 140/200 | 0.7000 | −1.5 | 190/250 | 0.7600 | 113/160 | 0.7063 |  |
| 22 | ace_oss_3243 | 62/200 | 0.3100 | 72/200 | 0.3600 | −5.0 | 127/250 | 0.5080 | 61/160 | 0.3812 |  |
| 23 | ace_oss_32606 | 67/200 | 0.3350 | 101/200 | 0.5050 | −17.0 | 84/250 | 0.3360 | 65/160 | 0.4062 | Bonferroni-significant |
| 24 | ace_oss_33450 | 64/200 | 0.3200 | 61/200 | 0.3050 | +1.5 | 112/250 | 0.4480 | 48/160 | 0.3000 |  |
| 25 | ace_oss_34760 | 72/200 | 0.3600 | 83/200 | 0.4150 | −5.5 | 91/250 | 0.3640 | 73/160 | 0.4562 |  |
| 26 | ace_oss_35622 | 150/200 | 0.7500 | 133/200 | 0.6650 | +8.5 | 203/250 | 0.8120 | 120/160 | 0.7500 | B outside [.2,.8] |
| 27 | ace_oss_36489 | 118/200 | 0.5900 | 113/200 | 0.5650 | +2.5 | 153/250 | 0.6120 | 81/160 | 0.5062 |  |
| 28 | ace_oss_4327 | 103/200 | 0.5150 | 109/200 | 0.5450 | −3.0 | 149/250 | 0.5960 | 99/160 | 0.6188 |  |
| 29 | ace_oss_4862 | 131/200 | 0.6550 | 118/200 | 0.5900 | +6.5 | 175/250 | 0.7000 | 100/160 | 0.6250 |  |
| 30 | ace_oss_633 | 111/200 | 0.5550 | 116/200 | 0.5800 | −2.5 | 165/250 | 0.6600 | 94/160 | 0.5875 |  |
| 31 | ace_oss_869 | 78/200 | 0.3900 | 81/200 | 0.4050 | −1.5 | 126/250 | 0.5040 | 61/160 | 0.3812 |  |
| — | **pooled** | 3085/6200 | **0.4976** | 3051/6200 | **0.4921** | **+0.55** | 4109/7750 | **0.5302** | 2433/4960 | **0.4905** | |

The two Bonferroni-significant tasks at $\alpha=0.05/31$ are
`ace_oss_32606` ($\chi^2=11.864$, $p=0.00057$) and `ace_oss_23132`
($\chi^2=10.519$, $p=0.00118$); 8 of 31 reach uncorrected $p<.05$ against
1.55 expected by chance [ZCD §1.4].

## Appendix D: Replication Artifacts and Citation Keys

The bracketed keys used throughout this revision resolve as follows. All
paths are in the replication bundle.

| key | artifact |
|:---|:---|
| `[ZCD §x]` | `ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md` — artifact-only diagnostics; §1 arms-are-different, §2 per-task table, §3 delta profiles and the instrument-mismatch decomposition, §4 the recomputed primary comparison, §5 timeline and provenance, §6 the eleven checks that could not be performed. Appendices A and B of that file carry the verbatim machine output and the source that produced it. |
| `[REP]` | `REPLICATION-RESULT-2026-08-05.txt` — original versus replication, and the cross-run stability of the same served artifact. |
| `[FINAL]` | `FINAL-SUMMARY-2026-08-05.txt` — the pooled null ($n=70$) and every adapter against it. |
| `[CTL]` | `CONTROL-VERDICT-2026-08-05.txt` — the same-session interleaved control, plus the per-arm verifier fingerprint audit. |
| `[FINDING]` | `FINDING-unseeded-lora-init-2026-08-05.md` — the unseeded-initialization finding with its instrument controls. |
| `[RES R-n]` | `RESIDUALS-2026-08-04.md` — six reproducibility defects, each with a live reproduction and a discharge condition. |
| `[RETRAIN]` | `retrain.log`, `retrain2.log`, `retrain3.log`, `adapter3-chain.log` — the three retraining runs, their step counts, and their reward dynamics. |
| `[TPD]` | `TRAINING_PARAMS_derived.txt` and the `dpo_adapter_native/training_args.bin` it reads. |

Everything cited is reproducible from the retained data by the scripts in
that bundle (`final_summary.py`, `compare_replication.py`,
`control_verdict.py`, `fingerprint_audit.py`, `compare_adapters.py`,
`init_vs_training.py`, `run_interleaved.py`). Adapter binaries are not
included; they are hundreds of megabytes and rebuildable from the code
plus the gated corpus.

## References

- Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., & Mane, D. (2016). Concrete problems in AI safety. arXiv:1606.06565.
- Baker, B., Huizinga, J., Gao, L., Dou, Z., Guan, M. Y., Madry, A., Zaremba, W., Pachocki, J., & Farhi, D. (2025). Monitoring reasoning models for misbehavior and the risks of promoting obfuscation. arXiv:2503.11926.
- Bouthillier, X., et al. (2021). Accounting for variance in machine learning benchmarks. *Proceedings of Machine Learning and Systems*, 3, 747-769.
- Chen, M., et al. (2021). Evaluating large language models trained on code. arXiv:2107.03374.
- Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized LLMs. NeurIPS 36. arXiv:2305.14314.
- Dodge, J., et al. (2020). Fine-tuning pretrained language models: Weight initializations, data orders, and early stopping. arXiv:2002.06305.
- Ethayarajh, K., Xu, W., Muennighoff, N., Jurafsky, D., & Kiela, D. (2024). KTO: Model alignment as prospect theoretic optimization. ICML 41. arXiv:2402.01306.
- Gao, L., Schulman, J., & Hilton, J. (2023). Scaling laws for reward model overoptimization. ICML 40, 10835-10866.
- Hu, E. J., et al. (2022). LoRA: Low-rank adaptation of large language models. ICLR. arXiv:2106.09685.
- Liu, Z., Zhang, S., Liu, Y., Liu, B., Yang, Y., & Wang, Z. (2024). DSTC: Direct preference learning with only self-generated tests and code to improve code LMs. arXiv:2411.13611.
- MacDiarmid, M., Wright, B., Uesato, J., Benton, J., Kutasov, J., Price, S., Bouscal, N., et al. (2025). Natural emergent misalignment from reward hacking in production RL. arXiv:2511.18397.
- Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *PNAS*, 115(11), 2600-2606.
- Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct preference optimization: Your language model is secretly a reward model. NeurIPS 36. arXiv:2305.18290.
- Shumailov, I., et al. (2024). AI models collapse when trained on recursively generated data. *Nature*, 631, 755-759.
- Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology. *Psychological Science*, 22(11), 1359-1366.
- Skalse, J., Howe, N. H. R., Krasheninnikov, D., & Krueger, D. (2022). Defining and characterizing reward hacking. NeurIPS 35. arXiv:2209.13085.
- Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika*, 34(1-2), 28-35.
- Yuan, W., et al. (2024). Self-rewarding language models. ICML 41. arXiv:2401.10020.
- Zeng, H., Jiang, D., Wang, H., Nie, P., Chen, X., & Chen, W. (2025). AceCoder: Acing coder RL via automated test-case synthesis. arXiv:2502.01718.
- Zhang, D., Diao, S., Zou, X., & Peng, H. (2024). PLUM: Preference learning plus test cases yields better code language models. arXiv:2406.06887.
- Zhang, K., Li, G., Dong, Y., Xu, J., Zhang, J., Su, J., Liu, Y., & Jin, Z. (2025). CodeDPO: Aligning code models with self generated and verified source code. ACL 2025. arXiv:2410.05605.
- Zhong, Z., Raghunathan, A., & Carlini, N. (2025). ImpossibleBench: Measuring LLMs' propensity of exploiting test cases. arXiv:2510.20270.

---

## FOR THE AUTHOR

**This is a proposal, not a replacement.** It is your paper. Every change
below is one you can reject, and where the evidence did not force a
change your text is carried through verbatim — the Introduction, the four
failure narratives, the concentration section, the pair-primary section,
the Value-of-the-Null section, and most of the Method are yours, edited
only where a number or a cross-reference moved.

**What changed, in order of how much it costs you.**

1. *The export-path finding is withdrawn.* It was in your abstract, its
   own Results section, and your Conclusion. It is gone from all three
   and replaced by Section 4.2, which reports the retraction and names
   the mechanism (`analyze_run1.load()` groups by model name alone and
   pools what `ruler_noise.py` refuses to pool). I wrote it as a fifth
   incident of your own declared failure class rather than as an erratum,
   because that is what it is, and because a paper that argues for
   disclosing broken instruments is stronger for disclosing its own. If
   you would rather it be a plain correction, cut the framing sentences
   in the Introduction and in "On the Value of the Null" — the section
   itself stands either way.
2. *Two sections were added:* 4.3 (independent replication) and 4.4 (the
   retrains and the unseeded initialization). Section 4.4 is where the
   paper's center of gravity has moved, and it is deliberately written to
   stop short of a cause.
3. *Your Limitation 1 is now the load-bearing sentence in the paper.*
   "The result cannot support a claim about DPO as a method. It
   characterizes this adapter." You wrote that before there was any
   evidence for it. There is now: three retrains from your code, your
   918 pairs, your hyperparameters, +9.7 to +11.0 pp. The revision says
   so out loud, in the Introduction, the Discussion, the Limitations, and
   the Conclusion. That is not a correction to your draft. It is the part
   of your draft that turned out to be most right.
4. *Six [AUTHOR TODO] blocks are gone* because their answers were sitting
   in your own retained artifacts — the null-arm specification, the
   training configuration and the 57 steps, the adapter-is-non-zero
   check, arms-are-different, benchmark responsiveness at the arms'
   operating point (Limitation 4, discharged), and the Appendix A
   rounding question (there was no discrepancy; your published digits are
   all correct). The TODOs that remain are the ones only you can close.

**What is still your call.**

- *The title.* I proposed: "An Objective Reward Is Not a Trustworthy
  Reward: Measurement-Integrity Failures, a Replicated Null, and an
  Unreproducible Checkpoint in Execution-Verified Preference Training."
  Your v3 title is recorded in the v4 changelog. A shorter alternative if
  that one is too long for arXiv's taste: "An Objective Reward Is Not a
  Trustworthy Reward: Measurement-Integrity Failures and a Null About One
  Artifact."
- *Whether the retrains belong in this paper at all.* An argument exists
  for splitting them into a second paper and leaving this one as the
  null plus the incident log. I kept them in because the null's scope is
  not honestly stateable without them, but the choice is yours.
- *Whether to name the second author on the paper or in the
  acknowledgments only.* I wrote the byline with the replication and
  review credit attached; either is defensible and it is your call.
- *The abstract.* It is not in the markdown export I worked from, so I
  could not edit it. It still carries the export-path claim. Proposed
  replacement text is in the v4 changelog block at the top.
- *The three sections marked "not re-examined by the replication."* I
  added that note to the concentration and pair-primary sections so no
  reader mistakes silence for endorsement. Delete the notes if you find
  them noisy.

**The one experiment that would close the biggest remaining question.**

Not another retrain. A **version matrix**: train the same 918 pairs with
the same configuration under enumerated stacks, varying one factor at a
time — `peft` version first, since your `adapter_config.json` predates
the `peft_version` field and the retrains record 0.20.0; then `trl` /
`transformers`; then torch/CUDA; then hardware. Three or four cells would
likely be enough to bracket it. Add an explicit `set_seed()` before the
model is wrapped and confirm `lora_A` goes bitwise identical across two
runs first, so that the matrix is measuring the stack and not the
initialization lottery. Until that runs, "which variable is worth 10 pp"
is the honest open question of this paper, and the revision says exactly
that everywhere it comes up.
