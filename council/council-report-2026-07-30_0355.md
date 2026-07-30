# Council Report — activation #17, THE PHD (solo seat)

**Date:** 2026-07-30 03:55
**Channel section:** `instructions.txt` §76 (written as §75; renumbered — see *Numbering collision* below)
**Code pin:** `eddb120` (verified identical to the working tree for every `.py`, `tests/` and `data/` path read)
**Verdict:** GO-WITH-FIXES. Nothing found invalidates the ruler, the verifier pin, or the 40 replicates. Three fixes are free and must land before the first efficacy run because they are free *now* and never again.

---

## Numbering collision (a finding about the channel, not the ask)

When this pass began the file ended at §74 (8,546 lines) and 75 was free. By the time it appended, **another seat had banked its own §75 answering the same activation #17, concurrently.** That block was not touched — the protocol says appended, never rewritten — so this response is §76.

Two independent answers to activation #17 now exist. They were written without sight of each other, which under the SEALED-FIRST rule makes them two usable passes rather than a duplicate. Where they disagree, go to the artifact. **Structural fix:** the channel has no write lock, and "the next number is N" is a read-then-write race whenever two seats are armed. Number from the append, or take a lock.

Points the concurrent §75 made that this pass did **not**, and that hold up:

- **F1 — the null is mis-specified.** `ruler_noise_analysis_n40.txt` prints the greedy-corrected independence prediction as **0.0326**, three lines below the 0.0376 that got banked. Against the correct null the observed 0.0381 is **1.169x**, CI **[0.957, 1.500]**. "INDEPENDENCE HOLDS, 1.01x" is two real effects cancelling: ~11% deflation from the greedy constant against ~14% inflation from positive inter-task correlation. This is a stronger version of C2 below and it **reconciles** with it — that seat's ratio CI contains 1.0, this pass's bootstrap CI on the correlation contains 0. Same conclusion by two routes: *no departure from independence is established at n=40, and the point estimate depends on which null you use.* The sizing table survives untouched because every MDE row is computed from the observed sd, not the prediction.
- **F2 — the freeze is a receipt with no gate.** Nothing reads `ruler_set_sha256`; three hits, all inside `build_ruler.py`. This pass checked readers of `eval_instrument_rate` only and missed the sha.

---

## Corrections to the round

| # | Finding | Label |
|---|---|---|
| C1 | **The stated reason for changing the instrument is measurably wrong.** Greedy accounts for **1 of 4** out-of-band tasks, not 4 of 4. | EXECUTED |
| C2 | §73's `+0.0102 (reinforcement)` is a point estimate; bootstrap CI **[-0.0080, +0.0280] contains zero**. The invited attack, delivered. | EXECUTED |
| C3 | §73's "nothing else systematic remains in the seam" — the +0.0002 has CI **[-0.0227, +0.0231]**, i.e. **±2.3pp against a 3.0pp MDE**. | EXECUTED |
| C4 | §71's H2 was **not rejected**; r = -0.0687, Fisher CI [-0.413, +0.293], and the quoted -0.1341 is **not reproducible from any banked artifact**. | EXECUTED |
| C5 | §74's 0/100 has a 95% upper bound of **2.95%** (rule of three) — up to a 2.95pp shift on the old bank cannot be excluded, against a 3.0pp maximum effect. | EXECUTED |
| C6 | **Claim A is conditional on a directory existing, and the suite cannot witness the condition failing.** Red witness supplied. | EXECUTED |
| C7 | `eval_history.jsonl` has **68 rows, not 57**; 0 carry `verifier`, 0 carry the greedy/sampled split. | EXECUTED |
| C8 | k=25 gives 3.02pp; the honest k for ≤3.0pp is 26. Three copies of a rounded number now exist. | EXECUTED |
| C9 | The chi-square hand-roll was **not** gratuitous (scipy absent from both interpreters) — but a stdlib bootstrap replaces it *and* supplies the three missing intervals. Net deletion. | EXECUTED |
| C10 | Stale n=10 in `ruler_frozen.json`: untidy on `eval_instrument_rate` (no readers), **real** on `eval_instrument_out_of_band` (lists 3, truth is 4). **Third instance of one class.** | EXECUTED |

### C1, in full, because it changes the decision

`eval.py` already stores `greedy` and `sampled` apart, so the counterfactual the DIRECTIVE calls unmeasurable is **free**:

```
instrument                     mean     run sd   outside [0.2,0.8]
1 greedy + 4 @0.8  (current)   0.5150   0.0381   4/31
4 @0.8, greedy dropped         0.4905   0.0476   3/31
```

Only `ace_oss_2454` returns to band (0.180 → 0.229). `ace_oss_16070` (0.850), `ace_oss_19459` (0.819) and `ace_oss_24748` (0.181) are out of band **on the temp-0.8 draws alone**. Drop the greedy anchor for the *estimand* reason, not the band reason.

### C6, with its red witness

`dataset_gate.verify_py()` falls through to `return sys.executable` when `.venv-train\Scripts\python.exe` is absent:

```
live verify_py()            -> ...\.venv-train\Scripts\python.exe
with .venv-train absent     -> C:\Python314\python.exe
sys.executable              -> C:\Python314\python.exe
IDENTICAL TO LAUNCHER: True   <-- the pre-pin defect, restored silently
```

And three of five tests in `tests/test_verifier_pin.py` `return` early on `if not VENV_PY.exists()`, which the file's own runner counts as PASS — the suite reports **`0 failed` with the pin unenforceable**. All 5 also pass on the live tree (as do `test_ruler_noise.py` 7/7 and `test_screen_sizing.py` 4/4), so the green suite is real but is not evidence the pin holds.

---

## Q1 — Instrument validity

**Chen et al. 2021 (arXiv:2107.03374), full text via ar5iv.** Verbatim: *"we generate n≥k samples per task (in this paper, we use n=200 and k≤100)"*; *"the optimal temperature for pass@1 is T\*=0.2 and the optimal temperature for pass@100 is T\*=0.8"*; *"higher temperatures are optimal for larger k, because the resulting set of samples has higher diversity"*; for Codex-S, *"We use T\*=0 for computing pass@1 and T\*=1 for computing pass@100"*.

1. **Temperature is tuned per k and held constant within a given n.** They *do* use T=0 for pass@1 — but then all n draws are greedy, n collapses to 1, and the combinatorial estimator is not in play. **They never mix temperatures inside one n.** Mixing is not documented practice.
2. **It is not documented as an error either.** Nearest on-point work is Hariri et al. 2025, *"Don't Pass@k"* (arXiv:2510.04265), which attacks pass@k for small-n instability and reports that *"under a uniform prior, the Bayesian posterior mean is order-equivalent to average accuracy (Pass@1)"*. It does not address the mixture. **Plain statement: nobody addresses the mixture** — absence of search evidence over ~6 queries, not a proven absence.
3. `TEMP=0.8` with `KS=(1,3)` means pass@1 is reported at the temperature Chen et al. found optimal for pass@100. Do **not** "fix" this to 0.2 — it would collapse rates toward the argmax and re-create the dead channels. The recordable point: **the [0.2,0.8] band and the temperature are coupled.** The band is a property of the instrument at T=0.8, not of the tasks.

**Is "pass@3" the quantity it names? No — and the failure is at k=3 only.**

- **At k=1 there is no estimator problem.** `pass_at_k(n,c,1) = c/n` identically, so run-level pass@1 *is* mean accuracy. The "identity to 0.000000" is algebraic, not empirical (EXECUTED: 0 violations over 1,240 task-runs, `n`=5 on every one). The k=1 issue is purely **which estimand** — a fixed 20/80 blend of two decoding policies.
- **At k=3 the estimator genuinely misattributes.** P(a random 3-subset of 5 includes the greedy slot) = C(4,2)/C(5,3) = 0.6, so a task whose greedy draw passes has reported pass@3 ≥ 0.6 regardless of its sampled behaviour. No single sampling distribution has that as its pass@3.
- **And pass@3 is saturated anyway — the bigger finding.** EXECUTED: mean reported pass@3 = 0.834, **20 of 31 tasks outside [0.2,0.8]** at k=3 versus 4 of 31 at k=1. Mostly *not* the greedy anchor's fault: a pass@1 band of [0.2,0.8] maps to [0.488, 0.992] at k=3. **A ruler band-selected at pass@1 cannot also be in band at pass@3. Drop 3 from `KS`.**

**What is lost by dropping the greedy draw: nothing the literature credits.** sqrt(4/5)=0.894 is the arithmetic of replacing one of five random draws with a constant. Adding a constant lowers variance *and moves the estimand* — that is bias, not Monte Carlo variance reduction (a control variate lowers variance at *fixed* estimand). There is no citation to lose because no technique is being used.

Worse, the "reduction" evaporates in the comparison it is for. Under the null arm the greedy draw is constant (EXECUTED: 0 of 31 non-constant across 40 runs). Between *arms* it is not — training moves the argmax. Each greedy flip moves the rate by 0.2/31 = **0.65pp with zero sampling noise**, so five flips manufacture a 3.2pp "effect" — the full MDE — with no change in the sampled distribution. The null-measured sd cannot see that term.

**The cheapest valid instrument costs fewer generations than the current plan:**

| option | new generations for MDE 3.0pp |
|---|---|
| (A) keep as-is | null done; trained 31×5×26 = **4,030** — but a 20/80 policy blend, pass@3 saturated |
| (B) re-generate all 5 at T=0.8 | null 4,960 + trained 4,960 = **9,920** |
| **(C) change the reported metric, not the generation** | null **0** + trained 31×5×40 = **6,200** |

(C) wins by 37% over (B) because **the greedy-free null baseline is already banked**: the same 40 replicates give mean 0.4905, sd 0.0476, and with both arms at 40 replicates `se_diff = 0.0476·√(2/40) = 0.01064`, MDE@80% = **2.98pp**. The null side never needs re-generating. Note the **2.45pp level shift** (0.5150 → 0.4905) — which is exactly why this had to be asked before the trained arm runs, not decided alone. And per C7, the feared "re-baselines every eval_history row" cost is **zero**: all 68 rows are already unusable.

(B) is the tidier long-run end state (sd ~0.0426 *extrapolated*, k=32, 4,960/arm). It is not worth 4,960 wasted null-arm generations to reach today.

---

## Q2 — Sizing, per-arm variance, and the term the formula omits

**Does the literature report per-arm variance on pass@k?** I looked and did not find a paper reporting run-level pass@k variance separately for a base and a tuned model as a designed measurement. The field's problem is one level cruder — pass@k is conventionally reported with **no interval at all**, which is why Miller 2024 (arXiv:2411.00640) had to be written. **Homoscedasticity is not assumed here; it is never confronted.**

**Is there a documented direction? Yes, and it favours you — on one term only.**

- Kirk et al., ICLR 2024 (arXiv:2310.06452): *"RLHF significantly reduces output diversity compared to SFT across a variety of measures."*
- Yue et al. 2025 (arXiv:2504.13837) — closest to your exact setting: pass@1 rises after RLVR but *"the base models achieve a higher pass@k score when k is large"*, attributed via coverage/perplexity analysis to a narrowed sampling distribution. **Warning for the ruler: if you keep any k>1, DPO can move it down while pass@1 goes up.**
- Omura et al. 2024 (arXiv:2411.07595): DPO's reverse-KL term *"encourages mode-seeking fitting to the reference policy"*; H-DPO adds entropy control and shows *"superior results in pass@k evaluations"*.

So the trained arm's **generation-noise** sd is more likely below 0.0476 than above it, and on that term `√2·run_sd` is conservative.

**But Q2 asks about the wrong term.** `se_diff = √2·run_sd` contains generation noise and nothing else. The null arm is the *same checkpoint* re-sampled, so it has **zero training variance by construction**. The trained arm has a component the formula has no slot for: LoRA init, data order, seed.

- Dodge et al. 2020 (arXiv:2002.06305): *"even with the same hyperparameter values, distinct random seeds can lead to substantially different results"*, init and data order contributing *"comparably to the variance of out-of-sample performance."*
- Bouthillier et al., MLSys 2021 (arXiv:2103.03098): *"adding more sources of variation to an imperfect estimator approaches better the ideal estimator at a 51 times reduction in compute cost."*

**With one trained checkpoint, a clean 3pp detection supports "this checkpoint differs from the base on these 31 tasks" and not "DPO on verifier-grounded pairs helps." No k fixes that.**

**The cheapest design that never needs the trained arm's sd in advance:**

1. **Never pool.** `se_diff = √(s_null²/k_null + s_trained²/k_trained)`, Welch df. Free, and removes the assumption at analysis time.
2. **Pair by task** — Miller 2024's recommendation 4 verbatim: *"When two models are being compared, conducting statistical inference on the question-level paired differences, rather than the population-level summary statistics"*, because *"paired differences represent a 'free' reduction in estimator variance."* Be precise about which of **two** SEs you report: the per-task paired-difference SE answers "would this hold on a fresh draw of tasks" (it carries the τ²/T term your own docstring flags); the replicate-based Welch SE answers "did the mean rate on *these* 31 tasks change." Report both, label both, prereg which the claim is about.
3. **Do not pre-size — use an internal pilot with variance-only re-estimation.** (Wittes & Brittain 1990; Gould & Shih 1992; Kieser & Friede 2003; Friede & Kieser 2006 review.) Run the trained arm in blocks of 10, re-estimating *only* the within-arm sds after each block. Because the variance re-estimate is a function of within-arm spread and not of the between-arm difference, the look is effectively blinded and the type-I cost is negligible. **The trap:** this licenses re-sizing on the **variance**, not stopping on the **effect**. Peek at the difference and you have run an unadjusted group-sequential trial. *Status: VERIFIED-SECONDARY — primary texts not fetched.*

**And spend the trained arm's budget across seeds, not across more replicates of one seed.** 2 seeds × 20, or 3 × 13, is the *same 6,200 generations* as 1 × 40 — and the trained arm's replicate sd then includes training-seed variance, so Welch `se_diff` automatically prices the term the current formula omits. Bouthillier applied literally. With 2 seeds the seed component has df=1 and is a direction, not a fact — but a rumour about a term currently valued at **zero** is a strict improvement.

---

## Q3 — Does R2 still hold at 13?

**No — and not for the reason the DIRECTIVE proposes. The swap did not spend the budget; it voided the estimand.**

R2's isolation argument required two numbers from the same instrument: (old ruler, 13 prompts, buggy seam) vs (old ruler, 13 prompts, fixed seam). Both terms are gone — the first instrument is spent (§64: 7 of 10 at ceiling; §74 confirmed it again by accident), and a buggy-seam baseline on the frozen 31-task ruler **does not exist and cannot be created**, because §71 makes every pre-pin number on that set void. One-change-at-a-time is a rule about holding the *measuring device* constant across two measurements. With no valid "before," holding the count at 13 holds it constant against nothing. **R2 is not violated; it is inapplicable.**

**What the re-run would actually measure:** the first null-vs-trained efficacy **baseline** of the whole pipeline on the new instrument. The seam fix and the verifier pin are now part of the *pipeline definition*, not variables under test. Label it a baseline. Subsequent runs can then be one-change-at-a-time against it — the first time that rule is actually purchasable.

**And 13 is now the wrong *source*, on an argument that is not about count.** §71 established that the 13 SEED_TASKS are bare functions and the ruler is 31 AceCode `oss` tasks whose prompts *contain annotated signatures* — and that the two families differ in exactly the property that broke the verifier. Training on bare-function prompts and measuring on annotated-signature tasks is a train/eval distribution shift this project has already **measured** to be behaviourally significant. Draw the training prompts from the 43-tid pool, not SEED_TASKS. That is a **source** change, not a count change, and it does not re-open the deferred 200. If you want R2's spirit, draw exactly 13 *from the 43*.

**A confound nobody has looked at, created by your own fix.** Under the pinned 3.11 verifier a completion omitting `from typing import List` **fails**, and the oss prompts invite exactly that omission. So pairs mined from the 43-tid pool may have `rejected` rejected for a **missing import** rather than a wrong algorithm — in which case DPO learns import hygiene, and the ruler (same family, same verifier) rewards it with a real pass@1 rise that has nothing to do with code repair. **True positive on the instrument, false positive on the thesis.** Cheap check before training: count how many `rejected` completions fail with a `NameError` naming a typing generic.

---

## Ranked critique

1. **`√2·run_sd` has no slot for training-seed variance** — a bigger hole than the homoscedasticity Q2 asks about. One checkpoint cannot support a claim about DPO, at any k. Fix costs **zero** extra generations.
2. **The stated reason for changing the instrument is false (C1).** 1 of 4, not 4 of 4 — measurable for free.
3. **The free path beats both options on the table** (Q1 option C): 6,200 vs 9,920 new generations. And drop 3 from `KS`.
4. **Claim A is conditional and the suite cannot see the condition fail (C6).** Red witness supplied.
5. **Two "nothing remains" claims have intervals comparable to the effect being bought** (C3: ±2.3pp vs a 3.0pp MDE; C5: 2.95pp vs a 3.0pp maximum effect).
6. **The invited attack lands twice** (C2, C4) — and a third time, harder, in the concurrent §75's F1.
7. **R2 is inapplicable, not spent**, and the training *source* is the change that matters — plus the import-hygiene confound.
8. **Close the class rather than re-freezing (C10, third instance); replace the chi-square with a bootstrap (C9)** — a net deletion that also supplies the three missing intervals.

---

## One concrete recommended next prompt

> "Do not generate anything yet. Three analysis-only steps, then one run.
>
> **(1) Free re-analysis.** Add a greedy-free reading to `ruler_noise analyze`: score run-level pass@1 from the `sampled` field only (n=4) over the 40 pinned replicates. Confirm mean 0.4905 and sd 0.0476, and report the **bootstrap 95% CI** for that sd, for the mean pairwise correlation, and for the temp-0.8-minus-confirmed seam — replacing `chi2_ppf` with a stdlib bootstrap. Expect the correlation CI to contain 0 and the seam CI to be about [-0.023, +0.023]; if so, fold §71/§73's sign and "nothing systematic remains" claims into a RECORD CORRECTION. Also state that §73's "1.01x" was measured against the naive null and the greedy-corrected ratio is 1.17x, CI [0.957, 1.500].
>
> **(2) Decide the instrument in the channel, then change it once.** Make greedy-free pass@1 *the* ruler metric, keep the greedy draw as a separately labelled diagnostic, and drop 3 from `eval.KS`. Nothing needs re-baselining: all 68 `eval_history` rows already lack the verifier key and the greedy/sampled split.
>
> **(3) Close two classes before the run.** (a) Make `dataset_gate.verify_py()` **fail loudly** instead of returning `sys.executable` when `.venv-train` is missing, and make `tests/test_verifier_pin.py` **fail** rather than return early when `VENV_PY.exists()` is false — red witness first: watch the current suite report `0 failed` with `_VENV_PY` repointed at a nonexistent path. (b) Strip the n-dependent `eval_instrument_*` fields out of `ruler_frozen.json` rather than re-freezing with `--force`; nothing reads them and they are the third instance of a measured value stored somewhere never re-derived.
>
> **Then, and only then, the run:** mine pairs from the **43-tid training pool** (13 of them, so the deferred prompt-count question stays deferred), first counting how many `rejected` completions fail with a `NameError` naming a typing generic and reporting that fraction. Train **2 seeds**. Evaluate each at 20 greedy-free replicates (2 × 20 = 6,200 generations, ~83 min at your measured 2.08 min/replicate) against the **already-banked** 40-replicate greedy-free null. Report **Welch** `se_diff` from each arm's own sd — never pooled, never `√2·null_sd` — plus the per-task paired-difference SE, and say which the claim is about. Label the result a **BASELINE**, not a seam-fix measurement: no buggy-seam number on this ruler exists or can be created."

---

## Leftover risks

- **Training-seed variance stays a rumour.** 2–3 seeds gives df=1 or 2. By your own §73 rule that is not a measurement of a variance — but the design that prices it at **zero** is worse.
- **τ²/T is still unpriced and no prereg exists.** T=31 estimates the change on *these* 31 tasks. §59 finding 2 has now survived four activations unaddressed.
- **Effective T is below 31.** `ace_oss_16070` at 0.880 (0.850 greedy-free) carries almost no signal; 19459 and 24748 are weak. Every MDE divides by 31; effective T is nearer 28. Do not drop them — that selects on the reported measurement — but do not price them as full channels.
- **Cross-version divergence beyond annotations is unenumerated**, and after C6 the flashlight also fails to fire if the venv moves.
- **Ollama-side nondeterminism is in no variance term.** Greedy constant on 31/31 across 40 runs is good evidence this is small *at T=0*; it says nothing about T=0.8.
- **The import-hygiene confound in the training pool** — the failure mode where instrument and thesis disagree while both numbers look right.
- **The verifier fingerprint records a version, not an environment**, and `interpreter_fingerprint()` silently records `"python unknown"` if the probe fails — after which the gate compares "unknown" to "unknown" and passes.
- **68 historical runs are permanently unrecoverable.** Correctly recorded; restated so nobody tries.

---

## The questions themselves

- **Q1 was the right ask**, and asking rather than deciding was correct — a 2.45pp level shift on a 3.0pp MDE is not a solo judgement call. Posed one notch too narrowly: it framed the anchor as an *estimator* problem when at k=1 it is purely an *estimand* problem, and it did not ask about pass@3 at all, which is where the estimator actually breaks and where saturation (20/31) makes the column unusable.
- **Q3 was the right ask**, framed with unusual honesty. The available answer was better than the offered options.
- **Q2 was the wrong shape.** It asked about heteroscedasticity *between arms* when the omitted term — training-seed variance — is larger, is not a heteroscedasticity problem, and cannot be fixed by any k. Asking whether the trained arm is noisier presupposes generation noise is the whole of its variance, which is the assumption that needed challenging.

**The question the DIRECTIVE should have posed and didn't:** *"With ONE training run, what am I entitled to conclude from ANY result on this ruler, and what is the cheapest way to get a second training seed into the variance estimate?"* — Answer: you are entitled to "this checkpoint differs from the base on these 31 tasks"; the cheapest way is to spend the trained arm's existing budget across 2–3 seeds, at zero additional generations.

**A second, sharper because your own fix created it:** *"Does the pinned 3.11 verifier make my training pool teach import hygiene instead of code repair?"*

---

## Non-claims

Full list in §76 of `instructions.txt`. The load-bearing ones:

- **No generation, no training, no eval, no GPU.** Every number here is recomputed from artifacts already on disk.
- **The 310-completion and 100-completion replays were not verified.** Those banked completions were not located in the repo and not searched for exhaustively. Both red witnesses are taken on the executor's word — which by this file's own rule makes them *pointers*, not proof. Only the **mechanism** was verified, via the tests' own probe.
- `ruler_noise._gammap`/`chi2_ppf` were not audited line by line; their **output** agrees with an independent implementation to 4 dp **on this dataset**. Not a proof over the domain.
- `screen_tasks.py`'s admission logic, the AceCode ingestion, `venv_guard.py` and all training code were **not read**. §62 was **not re-read**.
- **EvalPlus (arXiv:2305.01210) decoding setup unverified** (abs only). So "no code-eval harness mixes greedy with sampled draws inside one n" rests on Chen et al. plus absence of search evidence over ~6 queries. Not a survey; would miss any harness whose practice lives only in its source.
- **Internal-pilot papers: VERIFIED-SECONDARY only** (MCW annotated bibliography, Wiley listings). Method sound; exact inflation figures unread.
- **The greedy-free sd at n=5 (~0.0426) is an extrapolation** by binomial scaling from the *measured* n=4 value (0.0476). The covariance component does not scale that way.
- **Browser seats A/B were not used and not tested.** Step 1 of the cost ladder worked for every question. No finding came from a logged-in model, and no claim is made about whether the seats are up.
- Nothing here is "all", "every", "swept" or "exhaustive". Where this pass says it looked and did not find, that is search evidence with the query count stated.

**standing by for next DIRECTIVE**
