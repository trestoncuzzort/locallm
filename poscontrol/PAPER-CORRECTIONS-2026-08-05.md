# Corrections memo for `srlm-forge-arxiv-v3.md`

**To:** Treston Malachi Cuzzort, author
**Date:** 2026-08-05
**Target of every citation:** `C:\Users\t\Downloads\srlm-forge-arxiv-v3.md` (1,045 lines). Line
numbers below are that file's.
**Nature of this document:** a list of proposed edits with the artifact that proves each one. You are
the author; every item is a proposal you can accept, modify, or reject. Where the evidence supports
what you wrote, that is said as plainly as where it does not.

**Artifacts cited (all read for this memo):**

| tag | path |
|---|---|
| `ZCD` | `C:\Users\t\source\srlm-forge\poscontrol\ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md` (§ ids and computation ids `S0`–`S10`, `F1`–`F11` are that file's) |
| `REP` | `C:\Users\t\source\srlm-forge\poscontrol\REPLICATION-RESULT-2026-08-05.txt` |
| `RES` | `C:\Users\t\source\srlm-forge\poscontrol\RESIDUALS-2026-08-04.md` (R-1 … R-6) |
| `RETRAIN` | `C:\Users\t\source\srlm-forge\poscontrol\retrain.log` (27 lines) |
| `TPD` | `…\scratchpad\adapter-transfer\TRAINING_PARAMS_derived.txt` and the `training_args.bin` it reads |
| `MANIFEST` | `…\scratchpad\adapter-transfer\MANIFEST.txt` |
| `EXPORT` | `…\scratchpad\adapter-transfer\dpo_adapter_native\export\export_report.json` |
| `MODELFILES` | `…\scratchpad\adapter-transfer\modelfile_forged.txt`, `modelfile_null.txt` |
| `GIT` | branch `replication/2026-08-04` in `C:\Users\t\source\srlm-forge`, commits `3ff32b24`, `fad2f184`, `91ce12c7`, `878eb6a1`; author's commit `eecdb2e` |
| `THIS-SESSION` | two read-only computations run for this memo, quoted verbatim where used (adapter tensor scan; `training_args.bin` field readout) |

---

## 1. Summary — what changed, and what did not

Nothing in the primary result changed. Table 1, the Welch test, the paired analysis, the degrees of
freedom, and the p-value are all correct: your published figures reproduce from your own raw rows to
four decimals, with the largest deviation anywhere being 0.0405 on df (74.0 vs 73.959468, a rounding
artifact) — `ZCD` §4.4, computation `S8`. Your 40 null-arm rows were delivered on 2026-08-04 and are
now committed as `eecdb2e`; they were unpushed, not absent. The null also replicated independently on
different hardware in a different session with the arms interleaved: +0.065 pp, p = .9420, 95% CI
[−1.709, +1.839] (`REP`). Same sign as the original, each point estimate inside the other's interval,
both null.

Three things changed. First, **the export-path finding is wrong and should be withdrawn.** The null
arm is not a model that traversed an export path — it is the base model. Its served Modelfile is
byte-identical to the trained arm's except for one `ADAPTER` line, including the same base weight
blob (`sha256-8d2bf4416eb1…cb13d`), the same `TEMPLATE`, and the same four `PARAMETER` lines
(`ZCD` §1.1, `MODELFILES`). There is no separate path for the null to traverse and therefore no cost
it can have. The reported 3.3–3.8 pp gap was the *base reference arm* being scored with the old
greedy-anchored sampler and pooled across two verifier states; matched on sampler and verifier the
gap is +0.71 pp (p = .48) trained and +0.16 pp (p = .86) null (`ZCD` §3.3). Second, **several
[AUTHOR TODO] blocks are now answerable from retained artifacts** — the null-arm specification, the
training configuration and optimizer-step count, whether the adapter is non-zero, whether the arms
are different models, and benchmark responsiveness at the arms' operating point (Limitation 4).
Third, **the design turns out to be cleaner than the paper describes it**: the trained-vs-null
comparison is a pure A/B on one adapter directive with nothing else differing, which is a stronger
claim than "both traverse an identical export path."

What did not change: the null itself, its interval, the four failure narratives (not re-examined in
this work — see §5), the concentration analysis (not re-examined), the corpus bookkeeping questions,
and the preregistration's temporal-precedence limitation.

---

## 2. MUST-CORRECT — statements the artifacts contradict

### MC-1 — Introduction, the subsidiary-finding sentence (lines 56–62)

**Currently reads:**

> A subsidiary empirical finding is broader in scope: the export and quantization path required to
> serve the adapter cost 3.3–3.8 pp of benchmark accuracy — 1.4–1.6 times the achieved sensitivity,
> exceeding the pre-specified MDE — a cost that would have been silently attributed to training had
> the comparator not been fixed in advance.

**Why it is wrong.** Two independent routes, either of which is sufficient:

1. *There is no export path in the null arm.* `ollama show --modelfile` for `llama3-forged-null`
   and for `llama3-forged` differ in exactly one functional line — the `ADAPTER` directive — out of
   102 and 103 lines. Both name the same base weights blob
   `sha256-8d2bf4416eb1ffa998c6453fbe70300fe3832fbd0a8c913740923c11118cb13d`; the `TEMPLATE` block,
   the four `PARAMETER` lines (`num_keep 24`, three `stop` tokens) and the `LICENSE` block are
   byte-identical. The null carries no `ADAPTER` line at all. (`ZCD` §1.1 / computation `A1`;
   source files `MODELFILES`.) The export-side Modelfiles say the same thing:
   `Modelfile.null` is the single line `FROM llama3:8b-instruct-q4_K_M` (`ZCD` `A2`). No merge, no
   dequantization, no re-quantization of base weights occurred for either arm; only the *adapter*
   was converted to GGUF (`EXPORT` `checks.convert`: `exit 0`, `adapter_tensors 448`,
   `gguf_tensors 448`, `match true`).
2. *The measured gap was an instrument mismatch.* Within the base arm's own rows, greedy draws score
   0.6323 (980/1550) and sampled draws 0.5047 (3129/6200) — **+12.76 pp on the same model, same
   tasks, same run**. The base arm also pools 10 rows banked before the interpreter pin (M = .5910)
   with 40 pinned rows (M = .5150); Welch between those two sub-populations is +7.597 pp,
   t = 8.217, df = 24.1, **p = 1.9e-8**. Peeling both confounds gives a sampler- and
   verifier-matched base reference of **M = .4905, SD = .0476, n = 40**, against which
   **trained is +0.706 pp (t = 0.707, df = 76.6, p = 0.482, CI [−1.28, +2.69])** and **null is
   +0.157 pp (t = 0.172, df = 69.1, p = 0.864, CI [−1.66, +1.98])**. (`ZCD` §3.3, computations
   `S5b`, `S6`, `F2`.)
3. *Corroborating, and it also disposes of the session-drift reading.* Serving the **identical**
   adapter GGUF (`sha256 4107cf60…436a`, verified by `sha256sum` on both machines) two days apart
   moved the trained arm by +0.517 pp (p = .573) and the null arm by +1.000 pp (p = .222) — neither
   significant. Real session-to-session variance is ≈1 pp, far too small to be a 3.8 pp gap
   (`REP` "CROSS-RUN"; `GIT` `3ff32b24` body).

**Proposed replacement:**

> A subsidiary methodological finding concerns the reference arm rather than the comparison. The
> unmodified base model was scored 3.9 days before the two arms, under the earlier greedy-anchored
> sampler and across two verifier states, and on those numbers both arms appeared to sit 3.3–3.8 pp
> below it. Matched on sampler and verifier, that gap disappears: the corrected base reference is
> 49.05% and neither arm is distinguishable from it (+0.71 pp, p = .48 trained; +0.16 pp, p = .86
> null). The apparent deficit was an instrument mismatch between a reference measured on an older
> metric and two arms measured on the current one — a fifth incident of the same class this paper
> documents, and one that survived into a draft of this paper before it was caught.

*(That last clause is optional. It is offered because the finding is of the paper's own declared
type — a well-formed number produced by a component that had stopped measuring the same thing — and
because the paper's value rests on that class of disclosure.)*

---

### MC-2 — The v3 change-log header, export-path clause (line 5)

**Currently reads:**

> the export-path gap now carries the alternative reading (possible chat-template/EOS serving defect
> — a candidate fifth failure)

**Why it is wrong.** The candidate fifth failure named there is excluded by byte comparison, not by
argument: the two arms' `TEMPLATE` blocks and stop parameters are identical (`ZCD` §1.1). A
template/EOS defect would produce a large one-sided uniform shift; the common-mode component of the
trained−null profile is +0.55 pp and explains **0.49% of ΣΔ²**, with a 90% CI on the common-mode of
[−0.844, +1.941] pp — a uniform shift larger than about 2 pp is excluded by the data (`ZCD` §3.4,
computations `F11`, `F4`).

**Proposed replacement:**

> the export-path gap is withdrawn: the null arm is the base model served without an adapter, and the
> apparent gap was the base reference being scored on the older greedy-anchored sampler and pooled
> across two verifier states

---

### MC-3 — Method, Design, and its [AUTHOR TODO] (lines 148–167)

**Currently reads:**

> The arms were an adapted model (*trained*) and its own null baseline (*null*), both produced
> through the identical export and quantization path from the same base model. The null baseline,
> rather than the unmodified base model, was designated the comparator in the pre-specified plan, so
> that any difference attributable to the export path itself would be differenced out of the
> comparison.

and the TODO:

> **\[AUTHOR TODO: Specify the null arm precisely — reviewers flagged this as the paper's single most
> damaging gap. State exactly what is loaded at inference for the null arm (a zero-/randomly-
> initialized adapter merged and exported? the base weights pushed through the merge-and-export
> machinery with no adapter?), and describe the export path mechanically (e.g., dequantize-merge in
> safetensors $\to$ GGUF re-quantization to q4_K_M $\to$ Ollama serving), including why it degrades a
> model that begins 4-bit.**

**Why it is wrong, and why the correction helps you.** No merge-and-export machinery was applied to
either arm's base weights. The null is the base model re-tagged (`FROM llama3:8b-instruct-q4_K_M`,
nothing else); the trained arm is the same base blob with one GGUF LoRA attached at serve time. The
TODO's own premise — an export path that "degrades a model that begins 4-bit" — has no referent.
What the artifacts show is a *stronger* design than the paper claims: not "two arms whose export
costs cancel," but "the same weights, the same template, the same stop tokens, one `ADAPTER` line
different." (`ZCD` §1.1, `A1`, `A2`; `EXPORT`.) The replication used the same construction
independently — `poscontrol/served/Modelfile.rep` is `FROM llama3:8b-instruct-q4_K_M` +
`ADAPTER …\served\adapter.gguf` and `Modelfile.repnull` is the `FROM` line alone, with
`sha256sum adapter.gguf = 4107cf60…436a` matching the served blob name in your Modelfile.

**Proposed replacement (Design paragraph, and delete the TODO):**

> A two-arm between-model comparison with 40 independent evaluation replicates per arm, fixed in
> advance. The arms differ by exactly one directive in the served model definition. The *trained* arm
> is the base model with the LoRA adapter attached at serve time as a GGUF adapter
> (`FROM llama3:8b-instruct-q4_K_M` + `ADAPTER adapter.gguf`); the *null* arm is the same base model
> with no adapter (`FROM llama3:8b-instruct-q4_K_M`). Neither arm's base weights were merged,
> dequantized, or re-quantized: the base weight blob is byte-identical between the arms
> (`sha256-8d2bf4416eb1…cb13d`), as are the chat template, the four serving parameters, and the
> license block; the only functional difference in a 103-line versus 102-line `ollama show
> --modelfile` diff is the `ADAPTER` line. Only the adapter itself was converted, from PEFT
> safetensors to GGUF, tensor-for-tensor (448 in, 448 out). The unmodified base model was scored
> separately as a reference point; that reference is not sampler- or verifier-matched to the arms and
> is discussed in Section 4.2.

---

### MC-4 — Results §"The Export Path Cost More Than Training Gained" (lines 385–417)

The section title and its first paragraph are the load-bearing false claim.

**Currently reads (first paragraph):**

> Both adapted arms scored below the unmodified base model: trained $-3.26$ pp and null $-3.81$ pp
> relative to base. Because the null baseline traverses the identical export and quantization path
> while carrying no learned adaptation, this difference is attributable to that path rather than to
> training. It exceeds the pre-specified minimum detectable effect (ratios 1.1–1.3 against 2.98 pp)
> and the achieved sensitivity (ratios 1.4–1.6 against 2.34 pp): the path cost more than any effect
> the study was designed to detect.

**Proving artifacts:** as in MC-1 — `ZCD` §1.1 (no path exists for the null), §3.3 (`S5b`, `S6`,
`F2`) for the decomposition, `REP` for the ≈1 pp session-variance bound.

**Proposed replacement for the whole section, retitled:**

> #### The Apparent Base-vs-Arms Gap Was an Instrument Mismatch
>
> On the numbers as first computed, both arms scored below the unmodified base model: trained
> −3.26 pp (p = 7.4e-4) and null −3.81 pp (p = 1.8e-5). That comparison is invalid, and the reason is
> a fifth instance of this paper's own theme.
>
> The base reference was measured on 2026-07-29, 3.9 days before the arms, under the earlier metric.
> Its rows carry a temperature-0 greedy draw that the arms' rows do not: within the same base rows,
> greedy draws score 0.6323 and sampled draws 0.5047, a difference of +12.76 pp on the same model and
> the same tasks. The base arm also spans two verifier states — 10 rows banked before the interpreter
> pin (M = .5910) and 40 after it (M = .5150), Welch p = 1.9e-8 between them — because the run was
> restarted from replicate 1 when the pin landed, which is also why the base arm has 50 replicates and
> the arms have 40.
>
> Peeling both confounds gives a sampler- and verifier-matched base reference of M = .4905
> (SD = .0476, n = 40). Against it, trained is +0.706 pp (t = 0.707, df = 76.6, p = 0.482) and null is
> +0.157 pp (t = 0.172, df = 69.1, p = 0.864). There is no deficit left to explain. The greedy anchor
> accounts for −2.55 pp of the apparent gap and pooling the pre-pin rows for a further −1.42 pp.
>
> Two candidate explanations are therefore withdrawn rather than left open. A chat-template or EOS
> defect between the arms is excluded by byte comparison of the two served Modelfiles, which share a
> template and stop parameters, and by the shape of the difference profile: the common-mode component
> of trained − null is +0.55 pp and accounts for 0.49% of the total squared difference, with a 90%
> interval of [−0.84, +1.94] pp, whereas a template defect is broad and one-sided. Session drift is
> excluded by measurement: serving the identical adapter file on different hardware two days later
> moved the trained arm +0.52 pp (p = .57) and the null arm +1.00 pp (p = .22), so session-to-session
> variance is on the order of 1 pp.
>
> The finding this section retains is methodological, not empirical: a reference arm measured under a
> superseded metric produces a well-formed, plausible, and entirely spurious effect, and the analysis
> script that pooled it (Appendix B) did not inherit the refusal-to-pool guard that the measurement
> script already enforced for the arms.

**Also delete the section's [AUTHOR TODO]** (lines 411–417). Its three requests are now either moot
(EOS/template diff — done by Modelfile byte-diff, `ZCD` §1.1; per-task delta profile — `ZCD` §3.2,
Table in §2) or answered (the n = 50 vs n = 40 question — the base run's replicate ids run
`1..10, 1..10, 11..40`; the first ten are the pre-pin rows and the run was restarted under the pin,
`ZCD` §5.2). The one part that remains unclosed is per-draw generation metadata (stop reason, token
counts); the harness records none (`ZCD` §6 C9), so that request cannot be answered from retained
artifacts and should be moved to Limitations or dropped.

---

### MC-5 — Conclusion, export-path sentence (lines 826–828)

**Currently reads:**

> The export and quantization path — or a serving-stack difference not yet excluded — cost 3.3–3.8
> pp, 1.4–1.6 times the achieved sensitivity.

**Proposed replacement:**

> An apparent 3.3–3.8 pp deficit of both arms against the unmodified base model proved to be an
> instrument mismatch — a reference arm scored under a superseded sampler and pooled across two
> verifier states — and is withdrawn; matched on sampler and verifier, neither arm differs from the
> base (+0.71 pp and +0.16 pp, both n.s.).

**Proving artifact:** `ZCD` §3.3.

---

### MC-6 — Limitation 4 (lines 777–783)

**Currently reads:**

> 4. **Benchmark responsiveness verified on the base model.** That 27 of 31 channels are live was
>    established against the base model, not against the two arms compared here — which operate 3–4
>    pp lower, where export-path degradation could push individual tasks to floor.
>    **\[AUTHOR TODO: Close this with the zero-compute per-task table: 31 tasks $\times$ 3 arms pass
>    rates from the retained 200 draws per task per arm, flagging channels dead at the arms'
>    operating point.**

**Why it is wrong.** Two of its three clauses fail. The "3–4 pp lower" premise is the withdrawn gap
(MC-1/MC-4). And the table the TODO asks for has been computed: from the retained 200 draws per task
per arm, **0 of 31 tasks sit at 0.00 or 1.00 for any arm; 31/31 are strictly interior for trained,
null and base; 0 of 31 are within one draw (1/200) of a boundary; and every task's 95% Wilson
interval at n = 200 excludes both 0 and 1 in both arms.** The most extreme interiors are
`ace_oss_24748` (trained 0.1900, Wilson lower 0.1417) and `ace_oss_16070` (trained 0.8400, Wilson
upper 0.8843). 28 of 31 sit inside the ruler's own [0.20, 0.80] admission band in *both* arms; the
three that step outside do so by ≤4 pp, i.e. 1–8 draws out of 200. (`ZCD` §2, §2.1, §2.2;
computations `S3`, `F1`. The full 31 × 3 table with per-arm k/n is `ZCD` §2 and can be lifted into an
appendix as-is.)

**Proposed replacement:**

> 4. **Benchmark responsiveness, verified at the arms' operating point.** Of the 31 benchmark tasks,
>    none returns 0.00 or 1.00 for any arm, all 31 are strictly interior in both arms, none is within
>    one draw of a boundary, and every task's 95% Wilson interval at n = 200 excludes both bounds.
>    Twenty-eight of 31 remain inside the [0.20, 0.80] screening band in both arms; the three
>    exceptions are outside by 4 pp or less. The instrument was live where the comparison was made,
>    so the null is not a saturation artifact. The per-task table appears in Appendix C.

This also discharges the preregistration's own `what_this_CANNOT_show` entry, quoted in `ZCD` §2.2:
*"That the ruler is unsaturated for THIS pair of arms. 27 channels are clearly live and 4 are weak;
that was measured on the base model, not on these two."* If you want to keep a limitation here, the
honest residual is narrower: responsiveness is measured at these two arms' operating points, not at
arbitrary ones.

---

### MC-7 — Appendix A, the rounding [AUTHOR TODO] and the `t` line (lines 973, 990–995)

**Currently reads (the TODO):**

> **\[AUTHOR TODO: Reconcile two rounding residuals against the unrounded artifacts: from the rounded
> means, the CI recomputes to $[-1.11,+2.22]$ rather than the reported $[-1.12,+2.21]$ (consistent
> with unrounded $d=0.545$), and $p$ at $t=0.659$, df 74 is $\approx.512$ rather than .514. State the
> rounding convention or correct the bounds.**

and (line 973):

> - $t = .0055 / .008354 = 0.659$ (0.66 to two decimals)

**Why it needs changing.** There is no residual to reconcile: the published bounds are right and the
apparent discrepancy comes from recomputing them out of rounded means. Recomputed from the raw rows,
the difference is +0.548250 pp, SE 0.836039 pp, **t = 0.655816**, df = 73.959468, p = 0.513978,
95% CI [−1.117496, +2.213996] — which rounds to exactly the published +0.55, t = 0.66, df 74.0,
p = .514, CI [−1.12, +2.21]. Every published digit checks out; the largest deviation in an 18-row
comparison is 0.0405 on df. (`ZCD` §4.2, §4.4; computations `S6`, `S8`. The Student-t tail was
implemented from scratch and cross-checked against Simpson integration of the t density, agreement
< 5e-14, `ZCD` §S0.)

**Proposed replacement (delete the TODO; amend the `t` line):**

> - $t = 0.0054825 / 0.00836039 = 0.6558$ (0.66 to two decimals)
>
> All figures in this appendix are computed from the unrounded per-replicate rates and then rounded
> for display; recomputing them from the rounded means in Table 1 yields $[-1.11, +2.22]$ and
> $p \approx .512$, which are artifacts of the display rounding and not the reported values.

---

### MC-8 — Table 1's base row and caption (lines 346–352)

**Currently reads:**

> | Base (reference)  | 50  | .5302 | .0467 |
>
> Run-level pass@1 by arm on the frozen 31-task benchmark.

**Why it needs changing.** The arithmetic is correct — those 50 rows do mean .5302 (`ZCD` §4.1) —
but the row is not comparable to the two above it: it pools two samplers and two verifier states
(MC-4). Presenting it in the same table under a caption that says "by arm" invites exactly the
inference that has to be withdrawn.

**Proposed replacement:**

> | Arm                                  | $n$ |  $M$  | $SD$  |
> |:-------------------------------------|:---:|:-----:|:-----:|
> | Trained (adapter)                    | 40  | .4976 | .0415 |
> | Null (baseline)                      | 40  | .4921 | .0327 |
> | Base (reference, as first measured)  | 50  | .5302 | .0467 |
> | Base (reference, matched instrument) | 40  | .4905 | .0476 |
>
> Run-level pass@1 on the frozen 31-task benchmark. The two arms are the preregistered comparison.
> The base reference is not preregistered and was measured 3.9 days earlier; the "as first measured"
> row blends a greedy draw into each replicate and pools two verifier states, and the "matched
> instrument" row restricts to the 40 base replicates scored under the pinned interpreter and
> recomputes them greedy-free, which is the only base figure comparable to the arms (Section 4.2).

Note that the sizing assumption survives this change well: the matched base reference's SD is .0476,
which is the exact figure you preregistered as the assumed floor (`ZCD` §3.3 table).

---

## 3. SHOULD-ADD — TODOs now answerable, and evidence that strengthens the paper

### SA-1 — Null-arm specification (discharges the Design TODO, MC-3)

Covered by the replacement text in MC-3. Reviewers called this "the paper's single most damaging
gap"; it closes to two Modelfiles and a diff.

### SA-2 — Training configuration and optimizer steps (discharges the Discussion TODO, lines 703–707)

The Discussion TODO asks for "batch size, gradient accumulation, warmup, total optimizer steps." All
are recoverable. Values read directly from the original run's `training_args.bin` this session
(`THIS-SESSION` readout; the same fields are transcribed in `TPD`):

```
per_device_train_batch_size = 2          gradient_accumulation_steps = 8
num_train_epochs            = 1.0        max_steps  = -1  (epoch-bounded)
learning_rate               = 5e-06      lr_scheduler_type = COSINE
warmup_ratio                = 0.1        warmup_steps = 0
optim                       = ADAMW_BNB (adamw_bnb_8bit)   bf16 = True
max_grad_norm               = 1.0        seed = 42        data_seed = None
```

plus, from `run_meta.json`: beta 0.1, `rpo_alpha` 1.0, `max_length` 1024, `max_prompt_length` 512,
LoRA r/alpha/dropout 16/32/0.05, seven target modules.

On the step count: `TPD` correctly refuses to state it as measured, because no `trainer_state.json`
survived (`MANIFEST` "MISSING ITEMS" 2) and the arithmetic gives **57 or 58** depending on an
unrecorded `drop_last`. That ambiguity is now resolved empirically: a retrain from the same corpus
and the same configuration reports **57** optimizer steps — `RETRAIN` line 14 shows the progress bar
running `1/57 … 57/57` and line 26 the completed `train_runtime`. (`RES` R-5 records the same.)

**Proposed text (Method, Training procedure):**

> Effective batch size 16 (per-device 2 × gradient accumulation 8) over 918 pairs for one epoch,
> giving 57 optimizer steps; cosine schedule with `warmup_ratio` 0.1 over those steps; `max_grad_norm`
> 1.0; bf16; `adamw_bnb_8bit`; seed 42, with data order following the same seed. The step count is
> stated as observed: no `trainer_state.json` survived the original run, so it was confirmed by
> retraining from the same gated corpus and configuration, which reported 57 steps.

### SA-3 — The adapter is not zero (discharges the Method TODO, lines 212–219)

The TODO's stated worry is that "at lr $5\times10^{-6}$ for one epoch the adapter could be
indistinguishable from zero." It is not. Computed this session directly from
`dpo_adapter_native/adapter_model.safetensors` (the file whose SHA-256 `f416f3f9…e556` is the one
your preregistration records), over the effective update $\Delta W = (BA)\cdot\alpha/r$ per layer:

```
lora_A tensors: 224 | lora_B tensors: 224 | lora_B all-zero: 0 | lora_B non-zero: 224
layers with dW computed: 224 | min ||dW||_F: 0.007717  max: 0.038920  mean: 0.020016
  q_proj     n=32 mean||dW||_F=0.017466      o_proj     n=32 mean||dW||_F=0.018334
  k_proj     n=32 mean||dW||_F=0.008846      gate_proj  n=32 mean||dW||_F=0.033102
  v_proj     n=32 mean||dW||_F=0.009396      up_proj    n=32 mean||dW||_F=0.033687
                                             down_proj  n=32 mean||dW||_F=0.019281
zero-norm dW layers: 0
```

Two further pieces of evidence for the same TODO. (a) Training dynamics: the retrain's
`rewards/accuracies` rise from 0.3875 at epoch 0.09 to **0.9125–0.9750 over the last six logged
points**, with `rewards/margins` reaching **0.73–0.85** and `rewards/rejected` going negative from
epoch 0.52 onward (`RETRAIN` lines 15–25). The preference objective was decisively achieved, which is
a stronger statement than the loss curve can make and one the paper currently declines to make at
all. (b) Your own 50,000× amplification control was verified independently: all 224 `lora_B` tensors
scale by exactly 50000.0 and all 224 `lora_A` by exactly 1.0, the set of distinct per-tensor ratios
over all 448 tensors is `{1.0, 50000.0}`, and every tensor has non-zero norm (`ZCD` §1.3, `A3`).

**Proposed text (Method, replacing the TODO):**

> Two checks bound the concern that a single epoch at this learning rate leaves the adapter
> indistinguishable from zero. All 224 LoRA $B$ matrices are non-zero, and the Frobenius norm of the
> effective update $\Delta W = (BA)\alpha/r$ averages 0.0200 across the 224 adapted layers
> (per-module means 0.0088 for `k_proj` to 0.0337 for `up_proj`; no layer has zero norm). And a
> retrain from the same corpus and configuration reaches chosen-over-rejected reward accuracies of
> 0.91–0.98 with implicit-reward margins of 0.73–0.85 by the final quarter of the single epoch. The
> preference objective was achieved; what did not transfer is the benchmark effect.

### SA-4 — Arms-are-different verification (Limitation 9, lines 801–814)

Limitation 9 currently states that "no verification that the two arms are functionally different
models has yet been reported." Three independent lines now exist:

* **Artifact chain.** The `ADAPTER` line in the live `llama3-forged` Modelfile names blob
  `sha256-4107cf60ebced937bb7c80bde0faceb23f8e662990c0b91888cf5931f968436a`, which is
  character-for-character the SHA-256 computed over `adapter.gguf` (83,917,120 bytes). That GGUF was
  converted tensor-for-tensor (448 = 448) from `adapter_model.safetensors`, whose digest `f416f3f9…`
  is the value your preregistration recorded 26.15 minutes before the first trained replicate.
  (`ZCD` §1.2, §5.3.)
* **Behavioural, whole-profile.** Permuting whole replicate rows between arms (20,000 relabelings,
  seed 20260804), the summed per-task χ²(1) statistic is **observed 84.915** against a null of mean
  32.213, sd 7.992, 95th percentile 46.249, **maximum 76.577** — p < 5e-5, i.e. the observed value
  exceeds every one of 20,000 permutations. Two tasks survive Bonferroni at 0.05/31: `ace_oss_32606`
  (0.335 vs 0.505, p = 0.00057) and `ace_oss_23132` (0.615 vs 0.765, p = 0.00118). (`ZCD` §1.4, `F9`,
  `F8`.)
* **Behavioural, independent counter.** The arms differ in how often they emit code that raises
  `NameError` on an unimported `typing` annotation: trained 463/6200 draws (7.47%) vs null 515/6200
  (8.31%); Welch on the 40 per-run counts t = −2.736, df = 77.92, p = 0.0077 (permutation p = 0.00924,
  Mann-Whitney p = 0.0137). (`ZCD` §1.4, `F6`.)

**Proposed replacement for Limitation 9's second sentence and TODO:**

> That the two arms are functionally different models is verified three ways: the served adapter blob
> is named with the SHA-256 of the exported adapter file, which was converted tensor-for-tensor from
> the preregistered checkpoint; a permutation test over whole replicate rows separates the arms'
> 31-task profiles at p < 5e-5, with the observed statistic exceeding all 20,000 permutations; and an
> independent behavioural counter (unimported-`typing` failures) separates them at p = 0.0077. What
> remains unverified is exact-output agreement: the harness retained no completions, so the rate at
> which the arms emit identical text is not computable for either run. The positive-control adapter
> and its decision rule are unchanged and remain outstanding.

Note one honest residual you may want to keep: **no row attests which model served it** — the 130
replicate rows carry no model digest, adapter hash, or Ollama version, so the chain is artifact-level
plus statistical rather than per-row (`ZCD` §1.5, §6 C5, computation `S10`).

### SA-5 — Independent replication of the null (new, Results)

**Proposed text:**

> The comparison was repeated on different hardware, in a different session, with the arms
> interleaved replicate by replicate rather than run as sequential blocks, and with the full verifier
> fingerprint recorded on every row. The trained arm scored M = .5027 (SD = .0401) and the null
> M = .5021 (SD = .0396): +0.065 pp, t(78.0) = 0.073, p = .942, 95% CI [−1.709, +1.839]. The original
> and the replication agree in sign, each point estimate falls inside the other's interval, and both
> are null. Both runs serve the same adapter GGUF, so this replicates the measurement, not the
> training: training-seed variance remains zero in both.

**Proving artifact:** `REP`; `GIT` `3ff32b24` body. The interleaving also removes a confound the
original data cannot: in the original run the arms were back-to-back blocks (trained 16:51–19:22,
null 19:24–20:50), so any step change at the handover is perfectly aliased with arm (`ZCD` §3.4,
§5.1, §6 C11).

### SA-6 — The null is bounded, not merely unmeasured (TOST)

Equivalence testing at the preregistered margin gives **p = 0.0024 at ±2.98 pp** (statistically
equivalent) and p = 0.0433 at ±2.00 pp, with the 90% TOST interval [−0.844, +1.941] pp; at ±1.00 pp
(p = 0.2953) and ±0.50 pp (p = 0.5229) it is not resolved at n = 40. (`ZCD` §4.5, `F4`.) This turns
"we failed to find a difference" into "a true aggregate effect of ±2 pp or larger is rejected at
α = .05, and anything below ±1 pp is not resolved at this n," which is a stronger and more defensible
version of the claim the paper already makes. Distribution-free confirmation is available if wanted:
permutation p = 0.5184 over 200,000 relabelings, Mann-Whitney p = 0.4318 (`ZCD` §4.5, `F3`).

### SA-7 — The confound-free metric makes the null more null

Re-running the primary on the harness's own upper-bound metric `aggregate_if_typing_imported` gives
trained 0.5723 (SD 0.0403) vs null 0.5752 (SD 0.0302): **−0.29 pp, t = −0.364, df = 72.3, p = 0.7168**
— the sign of the difference flips. The entire +0.55 pp raw difference is carried by the trained arm
making fewer unimported-`typing` errors, and none of it by solving more tasks. (`ZCD` §4.5, `S6`.)
This is worth stating: it is a rare case where a robustness check makes a null result cleaner rather
than merely surviving.

### SA-8 — "No aggregate effect" is not "no effect" (Discussion)

The adaptation redistributed per-task performance while leaving the aggregate flat: the common-mode
component of trained − null is +0.55 pp and explains **0.49% of ΣΔ²**; signs split 15 up / 14 down /
2 flat (sign-test p = 1.0); the sd of Δ expected from sampling noise alone if the arms were the same
model is 4.69 pp against an observed 7.93 pp, implying a **true per-task effect sd of 6.39 pp**.
(`ZCD` §3.2, §3.4, `F11`.) The paper's Discussion would be sharper for saying this: the training did
change the model's behaviour task by task; what it did not change is the mean.

### SA-9 — A mechanism for the fourth reading (lines 692–711), with its limits stated

Your fourth reading is that "the pairs carried little usable gradient." Two retained-artifact
observations support it with a specific mechanism, and one commonly-offered third observation could
not be verified for this memo — that distinction is kept explicit below because the mechanism is
suggestive, not proven.

**Supported:**

1. *The objective was achieved while the benchmark did not move.* Reward accuracies of 0.91–0.98 and
   margins of 0.73–0.85 by the last quarter of the epoch (`RETRAIN` lines 15–25) against a benchmark
   effect of +0.55 pp (p = .51) originally and +0.07 pp (p = .94) on replication. Whatever the pairs
   separated, the model learned to separate it, and the benchmark does not score it.
2. *The optimization targets are reconstructions, not emissions.* Loading the trained corpus reports
   `918 pairs …; 0 carry verbatim completions, 918 fall back to re-fenced source` (`RETRAIN` line 4;
   `RES` R-6). `train_native.training_target()` prefers a `<field>_raw` verbatim completion and falls
   back to `f"```python\n{ex[field]}\n```"`; no row in `dpo_pairs_capped.jsonl` carries the raw
   field, so **every one of the 918 chosen and 918 rejected targets is executable source re-wrapped
   in a fence**. The function's own docstring names this as a reconstruction: *"That is a
   RECONSTRUCTION, not the original bytes — close, because ACTOR_SYSTEM forbids prose, but not
   identical."* Whatever presentation the policy actually emitted — prose, alternative fences,
   commentary — was stripped by `extract_code()` before banking and is not what the model was pushed
   toward.

**Correction to a tempting version of this argument.** It is *not* supportable, from these bytes,
that fence presentation is what separates chosen from rejected. `training_target()` applies the
identical `` ```python `` wrapper to both halves, so presentation is common-mode across the pair and
cannot carry the DPO gradient. What presentation *can* affect is the NLL term: with
`rpo_alpha` = 1.0 the objective adds a weighted likelihood term on the chosen completion only (your
own Method says so), and that term is trained toward a normalized fenced block rather than toward
anything the policy emitted. So the defensible statement is that part of the gradient budget went to
a presentation target that is an artifact of the corpus builder, while the contrast term saw only
`extract_code()` output on both sides.

**Proposed text (expansion of the fourth reading):**

> A fourth reading, raised in review, is that the pairs carried little usable gradient. Two retained
> artifacts support it with a specific mechanism. First, the objective was achieved: a retrain from
> the same corpus and configuration reaches chosen-over-rejected accuracies of 0.91–0.98 with margins
> of 0.73–0.85 within one epoch, while the benchmark effect is +0.55 pp in the original run and
> +0.07 pp on replication. The model learned to separate the pairs; the benchmark does not measure
> what separates them. Second, none of the 918 pairs retained the verbatim completion the policy
> emitted: the loader reports `0 carry verbatim completions, 918 fall back to re-fenced source`, so
> every optimization target is `extract_code()` output re-wrapped in a fence. The contrast term
> therefore sees only executable source on both sides, and the NLL term added by `rpo_alpha` = 1.0 is
> trained toward a normalized presentation that is an artifact of the corpus builder rather than a
> property of the policy. This is a candidate mechanism, supported by two observations and not
> proven; the decisive test is the rejected-half failure-reason histogram, which has not been run.

*(If the live generation observation referenced in the dispatch — trained emitting bare code where
null emits fenced code — is reproducible on your machine, it would be a third supporting
observation. It is listed under STILL OPEN as O-9: no artifact for it exists in the set read for this
memo, and the one on-disk generation comparison, `EXPORT`'s `spot` block from 2026-07-28, shows
**both** arms emitting fenced code on the same prompt. That block is a single non-benchmark prompt
and does not settle the question either way.)*

### SA-10 — Answer the n = 50 vs n = 40 question in the text

The base arm's replicate ids run `1..10, 1..10, 11..40`, with an 18.72-minute gap at the boundary:
the run was restarted from replicate 1 when the interpreter pin landed, and the first ten rows are
the ones with no `verifier` key. That accounts for 50 rows and for the non-monotone timestamps
(the two arms are both strictly monotone). (`ZCD` §5.2.)

### SA-11 — Retire the "experiments pending" framing for the Table 1 figures (lines 3–5)

The header currently reads **"REVISION v3 (responding to adversarial review round 2, ten reviewers)"**
and **"What changed in v3 (paper-side fixes; experiments pending)"**. For the Table 1 figures the
experiments are not pending: your 40 null-arm rows exist, were delivered on 2026-08-04, are committed
as `eecdb2e`, and reproduce every published figure to four decimals (`ZCD` §4.4; `GIT` `fad2f184`
body). The positive control *is* still pending, so the phrase should be scoped rather than deleted —
e.g. "paper-side fixes; the positive-control run remains pending."

---

## 4. DISCLOSE — reproducibility defects the paper should state

### D-1 — No TRL version is stated, and the training code does not run on a current install

The draft names no TRL, transformers, or tokenizers version anywhere (verified by search across all
1,045 lines; zero matches). `train_native.py` passes `rpo_alpha` to `DPOConfig`, which current TRL
(1.9.2, installed fresh 2026-08-04) rejects:
`TypeError: DPOConfig.__init__() got an unexpected keyword argument 'rpo_alpha'` — the script dies at
config construction before any training begins. Reproducing the run requires `trl==0.12.2`, which
pins `transformers==4.46.3` and `tokenizers==0.20.3`. The code names 0.12.2 in a comment; nothing
enforces it. (`RES` R-5, with the live reproduction; `RETRAIN` is the successful second run after
`pip install trl==0.12.2`.)

**Proposed text (Method or Appendix B):** state the pin explicitly — "trained with `trl` 0.12.2,
`transformers` 4.46.3, `tokenizers` 0.20.3; `rpo_alpha` was removed from `DPOConfig` in later TRL, so
the script does not run unmodified on a current install."

### D-2 — Appendix B's first command does not exist

Appendix B (line 1002) instructs `python build_ruler.py verify`. `build_ruler.py`'s argparse accepts
only `{nominate, confirm, freeze}` (`build_ruler.py:393–401`, verified this session). A reviewer
following the paper's reproduction section fails at step one. (`RES` R-4.)

### D-3 — The published analysis script pools what the measurement script refuses to pool

`analyze_run1.load()` groups replicates by `model` alone (`analyze_run1.py:142–149`, the line being
`out.setdefault(r.get("model"), []).append(r)`), so all 50 base rows average into the published
base M = .5302 across two samplers and two verifier states. `ruler_noise.cmd_measure` explicitly
refuses that pooling for the arms and prints "ignoring N replicate(s) banked under a different
verifier." The guard exists; the analysis path does not inherit it. **This is the mechanism that
produced the withdrawn export-path finding**, and the paper should say so rather than leave the
retraction unexplained. It does not touch the primary comparison, which never uses the base rows.
(`RES` R-2; `ZCD` §6.1.1.)

### D-4 — Raw completions were never retained

A string-field census of the delivered rows found the longest string in the entire file is 61
characters (a filesystem path); no completions, prompts, generated code, or diffs exist anywhere in
the retained artifacts. Exact-output agreement between arms is therefore not computable for the
original run **or** for the replication, and cannot be computed retroactively for either. The paper's
Limitation 9 TODO asks for that agreement rate; it requires a new run with retention enabled.
(`ZCD` §6 C3; `RES` R-3.)

### D-5 — The dataset gate's fingerprint is line-ending dependent, and it fired

`dataset_gate.verifier_fingerprint()` hashes working-tree bytes. With `core.autocrlf=true` and no
`.gitattributes` normalization, the same source file has two different hashes depending on how git
materialized it. Live reproduction 2026-08-04: `task_bank.py` authored with LF hashed to
`b28a47cb…c736`; checked out into a tree where git wrote CRLF it hashed to `15770d4d…d8b3`, and the
gate refused with a VERIFIER-CHANGED error on byte-identical source (1,485 bytes, 30 CRLF, 0 bare
LF; the LF-normalized digest of the CRLF file equals the receipt value exactly). Any clone with
different line-ending settings — or any Linux/CI runner — gets a gate refusal that reads like
tampering. (`RES` R-1.) This is worth disclosing precisely because the paper advertises the receipt
as integrity machinery (Failure 4; Limitations 6–7).

### D-6 — Replicate rows carry no serving attestation

Enumerating the union of all row keys across the 130 rows: no model digest, adapter hash, Modelfile
or template, Ollama version or server build, generation seed, prompt, completion, ruler-set hash,
wall-clock duration, or GPU state. Thirteen probes for
`adapter|sha|gguf|modelfile|template|ollama|prompt|completion|output|text|response|seed|digest`
return none. The original rows record the interpreter only; the replication rows carry a fuller
verifier fingerprint (`data/screen_results.jsonl`, `forge.py`, `screen_tasks.py`, `task_bank.py`,
plus the interpreter). (`ZCD` §5.4, `S10`; `REP`.) Four items close with recording changes and no
compute (C5, C7, C8, C9 in `ZCD` §6).

### D-7 — What the model was optimized toward is a reconstruction

See SA-9(2). Worth a sentence in Method independent of the Discussion use: the corpus stores
fence-stripped `extract_code()` output, so the DPO targets are re-fenced reconstructions rather than
the policy's emissions, for all 918 pairs. (`RES` R-6; `RETRAIN` line 4;
`train_native.training_target()` docstring.)

---

## 5. UNCHANGED — what the evidence confirms

These were checked and survive. Where something was *not* checked, that is said, so this list is not
mistaken for a broader audit than it is.

1. **Table 1's two arm rows, and every statistic derived from them.** Recomputed from the raw rows:
   trained M 0.497580 SD 0.041526, null M 0.492098 SD 0.032727, difference +0.548250 pp, SE 0.836039
   pp, t = 0.655816, df = 73.959468, p = 0.513978, CI [−1.117496, +2.213996]. Published values are
   the correctly-rounded forms of every one. (`ZCD` §4.1, §4.2, §4.4.)
2. **The paired secondary analysis.** +0.548387 pp, sd of the 31 paired differences 7.9271 pp,
   t(30) = 0.385170, p = 0.702829, CI [−2.359304, +3.456079] — matching the published +0.55,
   t = 0.39, p = .703, [−2.36, +3.46]. Two different ways of forming the per-task rate agree exactly.
   (`ZCD` §4.3.)
3. **Nothing was fabricated, and nothing was cleaned.** The delivered 130-row file is a byte-exact
   prefix-superset of the repo's 95-row file: the first 95 lines are identical line-for-line and the
   delivered file adds exactly 35 `llama3-forged-null` rows. `gen_errors_total = 0` on all 130 rows —
   no transport failure was absorbed into any score. (`ZCD` §5.5; `MANIFEST` PROVENANCE; `eecdb2e`.)
4. **Row-level integrity.** For all 130 rows the stored `aggregate["pass@1"]` reproduces exactly from
   `per_task` as `round(mean(correct/n), 4)` — 0 mismatches — and `correct == greedy + sum(sampled)`
   in all 4,030 per-task cells — 0 violations. The 31 task ids appear in identical order in all 130
   rows and equal the 31 ids in `ruler_frozen.json`. (`ZCD` §2, `S1`.)
5. **The frozen benchmark and its hash.** `ruler_frozen.json` and `ruler_frozen.BEFORE_REFREEZE.json`
   hold the same 31 ids, the same 31 `task_sha256` values, the same band, and the same
   `ruler_set_sha256 74560a4c…413d` — which is the value recorded in the preregistration. The
   re-freeze changed metadata, not tasks. (`ZCD` §5.5.)
6. **The preregistration's ordering relative to the arms.** `written_at 2026-08-02T16:25:28`, 26.15
   minutes before the first trained replicate and 179.28 minutes before the first null replicate.
   (`ZCD` §5.3.) The separate limitation about author-writable timestamps is untouched by this and
   stands.
7. **Run-level dispersion is what an independent-Bernoulli model predicts.** Trained observed SD
   0.04153 vs predicted 0.03736 (ratio 1.111); null 0.03273 vs 0.03770 (ratio 0.868). No large
   over-dispersion is inflating the picture, and both arms came in below the preregistered 0.0476.
   (`ZCD` §3.2, `F10`.) The Discussion's binomial-floor argument (≈0.035 bracketing both arm SDs) is
   consistent with this.
8. **The variance-ratio statement.** F(39,39) = 1.6101 two-sided p = 0.1413; robust Brown-Forsythe
   t = 1.538, df = 74.6, p = 0.1284. No significant change in spread, as the paper says. (`ZCD` §4.5,
   `F5`.)
9. **The trained and null arms share an identical verifier record in all four fields**, so the
   primary comparison is not exposed to the interpreter confound at all. (`ZCD` §5.4.)
10. **The 50,000× amplification control is exactly what it claims.** Re-verified independently
    (`ZCD` §1.3, `A3`).
11. **Not re-examined in this work, and therefore neither confirmed nor questioned here:** the four
    failure narratives and Table 2, the interpreter-disagreement measurement (172/310 vs 154/310),
    the concentration table and its estimator, the corpus bookkeeping numbers, the pipeline-economics
    figures (66% / 16.9%), and the bibliography. Their absence from the MUST-CORRECT list means they
    were not audited, not that they were checked and passed.

---

## 6. STILL OPEN — with what would close each

| id | open item | what closes it |
|---|---|---|
| O-1 | **The positive control** (lr 2e-4, multiple epochs, same serving path, 40 replicates) and its pre-fixed decision rule, Limitation 9. | The run. Note its second branch — "no movement reframes the paper around an export path that silently discards adaptation" — is now much less likely a priori, since the arms are demonstrably different models and the export path is one `ADAPTER` line. |
| O-2 | **Training-seed variance is still zero in both runs.** Both the original and the replication serve the same adapter GGUF (`4107cf60…436a`, hashed on both machines), so the replication replicates the measurement, not the training. One checkpoint per arm remains. | 2–3 independently seeded training runs per arm. A seed-42 retrain finished at 2026-08-05 01:34 (`poscontrol/adapter_replication/`) and a second was still running at 01:43 (`poscontrol/retrain2.log`); `poscontrol/compare_adapters.py` exists to compare effective updates $\Delta W$ against the original adapter, but **no output of it exists on disk as of this memo — that comparison is PENDING and no result is asserted here.** |
| O-3 | **The rejected-half failure-reason histogram**, the count of pairs rejected only by the exact-type check, and the truncation rate — the decisive test for the fourth reading (SA-9). | Re-verification pass over the 918 pairs; zero GPU compute. |
| O-4 | **Exact-output agreement between arms.** | Retention of completions (or per-draw output hashes) plus a re-run (`ZCD` §6 C3; `RES` R-3). |
| O-5 | **The base arm's unexplained within-run downward drift** — Pearson r = −0.498 over its own run order, t = −3.980, df = 48, p = 0.0002; first half 0.5489 vs second half 0.5115, Welch p = 0.0037. The two served arms show no such drift. This is a reason not to treat the base arm as a clean reference even after matching. | Re-measuring the base arm greedy-free under the current stack (~2 h at observed cadence), or recording the serving stack per row (`ZCD` §3.4, §6 C8, `F7`). |
| O-6 | **Contemporaneous third-party timestamp anchor** for the preregistration, and the complete study history including the discarded 10-task run. | Unchanged by this work; the paper's own TODO stands. |
| O-7 | **Corpus bookkeeping**: 918 / 1,244 / 1,279 / 2,200, the 10 unverifiable pairs, whether any were among the trained 918, and gate-repair timing relative to the adapter. | Unchanged by this work; the paper's own TODO stands. |
| O-8 | **Interpreter provenance for the base screening**, the 43→13 task-flow table, and $K$. Partially informed: the arms' rows carry a `3.11.9` verifier with `pinned_away_from_launcher: false`; the base's 40 pinned rows carry `3.11.9` with launcher `3.14.6`; the base's 10 pre-pin rows carry no verifier key at all. Also note a count to reconcile: the paper says 27 responsive / 4 out-of-band on the base model, while the base rows as published give 26/31 in band (5 outside). Those are different measurements — screening-time versus these 50 rows — but the paper should say which it is quoting. | The screening-time record; `ZCD` §2.2 gives the row-derived counts. |
| O-9 | **The bare-code vs markdown-fence generation difference between arms.** No artifact for this exists in the set read for this memo, and the one on-disk generation comparison (`EXPORT` `spot`, 2026-07-28, prompt *"Write a Python function that returns the sum of a list of numbers."*) shows **both** arms emitting a fenced block. Treated as PENDING; not used to support SA-9. | A recorded generation comparison over a sample of benchmark prompts, with the outputs retained. |
| O-10 | **Two zero-compute closers** left over from the diagnostics: `sha256sum` of the served Ollama blob itself (currently the link rests on Ollama's content-addressing convention plus a name match), and `ollama show llama3:8b-instruct-q4_K_M --modelfile` to confirm the base reference was served with the same template and stop parameters as the arms. | One command each on the machine holding `~/.ollama/models/blobs` (`ZCD` §6 C1, C2). |

---

## 7. Suggested order of application

MC-3 first (it defines the null arm, and MC-1, MC-4, MC-5 and MC-6 all lean on that definition), then
MC-4, then the three sentences that quote its number (MC-1, MC-2, MC-5), then MC-6 and MC-8, then
MC-7. The SHOULD-ADD items are independent of each other except SA-9, which should follow SA-3.
