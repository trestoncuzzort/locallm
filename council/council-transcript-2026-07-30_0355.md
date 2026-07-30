# Council Transcript — activation #17, THE PHD (solo seat)

**Date:** 2026-07-30 03:55 · **Channel section:** `instructions.txt` §76 · **Pin:** `eddb120`
Sole seat. No advisors, no Asshole, no chairman (retired by proprietor mandate 2026-07-28). One pass, one ruling.

---

## 1. Order of work

1. Read `OPERATING PROTOCOL` (:1-97) and `DIRECTIVE` #17 (:98-245).
2. Verified the pin: `git diff --stat eddb120 563dd66` → `instructions.txt`, 1 line. No `.py`/`tests/`/`data/` differs; working tree clean for those paths. **Reading the tree was reading the pin.**
3. Read sections 71-74 (:8153-8546) by line range, not by reading the 8.5k-line file.
4. Read the code at the pin: `eval.py`, `dataset_gate.py`, `forge.py`, `ruler_noise.py`, `build_ruler.py`, `screen_tasks.py`, `tests/test_verifier_pin.py`.
5. Ran 11 read-only checks against the banked artifacts (below).
6. Climbed the research ladder: `WebSearch` → `WebFetch` on arxiv/ar5iv. **Stopped at step 1** — it worked for every question. Browser seats never opened.
7. Wrote §76, this transcript, and the report.

**Cost-ladder note.** Seats A (9222) and B (9223) were **not** contacted and **not** tested. §62 recorded all three ports closed; nothing this round required them, so no claim is made about their state and no finding came from a logged-in model.

---

## 2. Executed checks (all read-only; no generation, no training, no GPU, no state mutated)

| # | Check | Result |
|---|---|---|
| E1 | `git diff --stat eddb120 563dd66` | `instructions.txt` only, 1 line |
| E2 | Independent recomputation of the noise floor from `data/ruler_noise.jsonl` — own incomplete-gamma bisection, no reuse of `ruler_noise.py` | mean **0.515000**, sd **0.038067**, CI **[0.0312, 0.0489]**; full k-table reproduced to the published digit (6.7/4.8/3.4/3.0pp at k=5/10/20/25). **Matches §73.** |
| E3 | Verifier-version census of `ruler_noise.jsonl` | 50 rows: 40 `3.11.9`, 10 pre-pin |
| E4 | The `0.2·greedy + 0.8·temp0.8` identity | 0 violations over 1,240 task-runs; `n`=5 on every one. **Algebraic, not empirical** |
| E5 | Greedy constancy | 0 of 31 tasks non-constant across 40 runs. Confirms §73 |
| E6 | Bootstrap (2,000 resamples, stdlib `random`, seed 7) on mean pairwise correlation | **+0.0075, 95% CI [-0.0080, +0.0280] — contains zero** → C2 |
| E7 | Paired seam CI over 31 tasks | +0.0002, sd 0.0625, **CI [-0.0227, +0.0231]**; eval-instrument-minus-confirmed +0.0247, CI [-0.0161, +0.0655] → C3 |
| E8 | H2 reproduction attempt | r = **-0.0687**, Fisher CI **[-0.413, +0.293]**; the quoted **-0.1341 not reproducible from any banked artifact** → C4 |
| E9 | Greedy-free instrument, measured from the `sampled` field of the same 40 replicates | mean **0.4905**, sd **0.0476**, **3/31** out of band (only `ace_oss_2454` returns); pass@3 mean **0.834**, **20/31** out of band, 0.6 floor for greedy-passing tasks → C1, Q1 |
| E10 | Claim A's fallback branch + test sensitivity | `verify_py()` with `_VENV_PY` repointed → `C:\Python314\python.exe` == `sys.executable`; `test_verifier_pin.py` reports **`0 failed`** in that state with **3 of 5 tests skipping-as-PASS**. Live tree: 5/5, 7/7, 4/4 → C6 |
| E11 | Environment + reader census | scipy absent from **both** interpreters (`.venv-train` 3.11.9: numpy yes/scipy no; system 3.14.6: numpy+requests yes/scipy no) → C9. `grep` over `*.py`: nothing **reads** `eval_instrument_rate` → C10. `eval_history.jsonl`: **68 rows**, 0 with `verifier`, 0 with greedy/sampled, 67 at n_tasks=10 → C7. Rule of three on 0/100 → **2.95%** → C5 |

---

## 3. Citation ledger

Fold into `council/phd-research-log.txt` if that file is to be maintained — appending to it was outside the three writes this activation authorised.

### VERIFIED — primary source opened this pass

**arXiv:2107.03374** — Chen et al. 2021, *"Evaluating Large Language Models Trained on Code."*
Fetched **full text via `ar5iv.labs.arxiv.org`** after the `abs` page proved insufficient (it carries only the abstract). Extracted verbatim: the estimator `pass@k := E[1 − C(n−c,k)/C(n,k)]`; *"we generate n≥k samples per task (in this paper, we use n=200 and k≤100)"*; *"the optimal temperature for pass@1 is T\*=0.2 and the optimal temperature for pass@100 is T\*=0.8"*; *"higher temperatures are optimal for larger k, because the resulting set of samples has higher diversity"*; Codex-S *"We use T\*=0 for computing pass@1 and T\*=1 for computing pass@100"*; *"top p=0.95 for all sampling evaluation in this work."*
**Applied:** the whole of Q1 (a). Establishes that temperature is tuned per k and held constant within one n, and that greedy-for-pass@1 means *all* n draws greedy — so the mixture is not documented practice.

**arXiv:2504.13837** — Yue et al. 2025, *"Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?"*
*"the base models achieve a higher pass@k score when k is large"*; coverage and perplexity analyses attribute the improved pass@1 to a narrowed sampling distribution.
**Applied:** Q2's direction question — closest published analogue to verifier-grounded training. Also the warning that any k>1 on this ruler can move *down* while pass@1 moves up.

**arXiv:2310.06452** — Kirk et al., ICLR 2024, *"Understanding the Effects of RLHF on LLM Generalisation and Diversity."*
*"RLHF significantly reduces output diversity compared to SFT across a variety of measures."*
**Applied:** Q2, the documented direction for the trained arm's generation-noise sd.
**Scope note:** the abstract does **not** separate per-input from across-input diversity; I did not fetch the body to check which is measured. Cited for direction only.

**arXiv:2411.00640** — Miller 2024, *"Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations."*
The `abs` page carried title/author only; the **HTML full text** yielded the five recommendations. Rec 4 verbatim: *"When two models are being compared, conducting statistical inference on the question-level paired differences, rather than the population-level summary statistics"*; and *"paired differences represent a 'free' reduction in estimator variance when comparing two models."* Rec 3: *"Reducing variance by resampling answers and by analyzing next-token probabilities."*
**Applied:** Q2 design piece 2, and the two-SEs distinction (task-level vs replicate-level).
**Note:** the PDF fetch (`/pdf/2411.00640v1`) returned undecodable binary. The HTML route worked. Recorded so it is not re-attempted via PDF.

**arXiv:2103.03098** — Bouthillier et al., MLSys 2021, *"Accounting for Variance in Machine Learning Benchmarks."*
*"adding more sources of variation to an imperfect estimator approaches better the ideal estimator at a 51 times reduction in compute cost."*
**Applied:** the single most decisive recommendation of this round — spend the trained arm's fixed generation budget across 2-3 seeds rather than more replicates of one. VERIFIED at abstract level.

**arXiv:2002.06305** — Dodge et al. 2020, *"Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping."*
*"even with the same hyperparameter values, distinct random seeds can lead to substantially different results"*; init and data order contribute *"comparably to the variance of out-of-sample performance."*
**Applied:** Q2 — that the omitted training-seed term is not small.

**arXiv:2411.07595** — Omura, Fujita & Kataoka 2024, *"Entropy Controllable Direct Preference Optimization."*
DPO's reverse KL *"encourages mode-seeking fitting to the reference policy"*; *"minimizing reverse KL divergence could fail to capture a mode of the reference distribution"*; H-DPO showed *"superior results in pass@k evaluations for mathematical tasks."*
**Applied:** Q2, that the mechanism is recognised for DPO specifically and not only RLHF.
**HONESTY FLAG:** the abstract does **not** say "reduces entropy" in those words. "Mode-seeking → lower entropy" is *my* reading. Flagged in §76 rather than stated as the paper's claim.

**arXiv:2406.10229** — Madaan et al. 2024, *"Quantifying Variance in Evaluation Benchmarks."*
Quantifies seed variance across initialisations and monotonicity during training; encourages practitioners to *"carefully factor in variance when comparing models."* Not code-specific (MMLU-centric); does not mention HumanEval in the abstract.
**Applied:** supporting only. Explicitly **not** used as the "per-arm pass@k variance" citation Q2 asked for, because it is not that.

**arXiv:2510.04265** — Hariri, Samandar, Hinczewski & Chaudhary 2025, *"Don't Pass@k: A Bayesian Framework for Large Language Model Evaluation."*
pass@k *"often produces unstable and potentially misleading rankings, especially when the number of trials (samples) is limited"*; proposes Dirichlet posteriors; *"under a uniform prior, the Bayesian posterior mean is order-equivalent to average accuracy (Pass@1)."*
**Applied:** independent support for making pass@1 (= mean accuracy) the headline metric and demoting pass@3. **Does not address the greedy/sampled mixture** — checked, and that absence is part of the Q1 answer.

### VERIFIED-SECONDARY — primary text NOT fetched, do not quote as read

**Internal pilot / blinded sample size re-estimation:** Wittes & Brittain 1990 (originated the internal pilot for parallel-group normal outcomes); Gould & Shih 1992 (blinded re-estimation); Kieser & Friede 2003 (procedures that do not inflate type I); Friede & Kieser 2006, *"Sample Size Recalculation in Internal Pilot Study Designs: A Review"* (Biometrical Journal).
Confirmed to exist and to say what is attributed, via a Medical College of Wisconsin annotated bibliography (`tr057.pdf`) and Wiley listings. Also surfaced: type-I inflation is non-negligible mainly for small internal pilots and when *reductions* in planned n are allowed.
**Applied:** Q2 design piece 3. Method treated as sound; exact inflation figures treated as unread.

### CHECKED AND RULED OUT / NOT CONFIRMED

**arXiv:2305.01210** — Liu et al., EvalPlus. The `abs` page does **not** carry the decoding setup; full text not fetched. **UNVERIFIED for the specific question asked** (whether it uses greedy for pass@1 and separate sampling for higher k). Consequence, stated in §76: the claim "no code-eval harness mixes greedy with sampled draws inside one n" rests on Chen et al. plus absence of search evidence over ~6 queries — it is **not a survey**.

**Search-only, not cited as evidence:** `mbrenndoerfer.com` and `runloop.ai` blog posts on pass@k, and an LM-Evaluation-Harness gloss about binomial vs bootstrap uncertainty. Consistent with the ruling but secondary web writing, deliberately kept out of §76's citation list.

### CARRIED FORWARD — not re-fetched this pass

Everything in `council/phd-research-log.txt` from rounds 1-2, including the Flan-based basis for the deferred "200 prompts" recommendation and the **UNVERIFIED — DO NOT CITE** flag on arXiv:2603.20100. Per the standing rule, prior transcripts' settled points were cited, not re-derived. §62 itself was **not** re-read.

---

## 4. Reasoning notes worth keeping

**Why C1 is the finding of the round.** The DIRECTIVE's argument for changing the instrument rested on "greedy is the SOLE mechanism putting tasks outside the band." The observation behind it is true; the causal claim is not. `eval.py` already stores `greedy` and `sampled` in separate fields, which makes the counterfactual a **re-analysis, not a measurement** — zero GPU. Doing it showed 3 of 4 out-of-band tasks stay out of band with greedy removed entirely. The instrument should still change, but for the estimand reason, and the correct reason produces a different and cheaper design (option C) than the reason as stated.

**Why option (C) beats (B) on cost, which was not obvious going in.** (B) — resample all 5 at T=0.8 — requires **re-measuring the null arm from scratch** (4,960 generations) because the level shifts by 2.45pp. (C) — keep generating exactly as now, but score pass@1 from the four sampled draws and report greedy separately — has its null arm **already measured at n=40** in the banked data. 6,200 new generations vs 9,920. The efficiency win comes entirely from a schema decision the executor already made in §71 for a different reason ("keeping `greedy` apart from `sampled` is what lets those two causes be told apart"). That decision paid off twice.

**Why the k=1 / k=3 split matters.** The DIRECTIVE treats the mixture as one problem. It is two. At k=1 `pass_at_k(n,c,1) = c/n` identically, so there is no estimator at all — the issue is purely which estimand (a 20/80 policy blend). At k=3 the combinatorial estimator genuinely misattributes, and *separately* the metric is saturated by construction: a [0.2,0.8] pass@1 band maps to [0.488, 0.992] at k=3, so 20/31 tasks are out of band no matter what the greedy draw does. Conflating the two would have produced a weaker recommendation.

**Why Q2 got redirected.** The formula `se_diff = √2·run_sd` was described as assuming both arms share a run-level sd. True, but the sharper problem is that it has **no term at all** for training-seed variance, and the null arm has zero by construction (same checkpoint). Answering the question as posed would have blessed a design that spends 6,200 generations sharpening the wrong term. The fix costs zero generations, which is why it outranks everything else.

**What was nearly over-claimed and got deleted.** An early draft argued for switching `TEMP` to 0.2 on the ground that Chen et al. found it optimal for pass@1 and that it would lower the noise floor. Deleted: T=0.2 collapses rates toward the argmax and re-creates the dead-channel problem the band selection exists to prevent. What survives is the narrower and defensible point — the band and the temperature are coupled, and no convention pins both.

**The tension between C2 and the concurrent §75's F1, and how it resolves.** That seat computed the *correctly specified* independence null as 0.0326 (greedy-corrected) rather than 0.0376, making the observed 0.0381 a **1.17x excess** — which implies positive covariance. This pass's bootstrap says the mean pairwise correlation is indistinguishable from zero. These reconcile: that seat's own ratio CI is **[0.957, 1.500]**, which contains 1.0. **Both routes reach the same place — no departure from independence is established at n=40, and the point estimate depends on which null you pick.** F1 is the stronger framing and this pass did not find it; it is credited in the report.

---

## 5. Channel hygiene incident

Written as §75. At the start of this pass the file ended at §74 (8,546 lines) and 75 was free — verified before writing, as instructed. By append time **another seat had banked its own §75 answering the same activation #17**, concurrently (~980 lines). That block was **not modified**; the protocol says appended, never rewritten. This response was renumbered **§76** and the collision recorded in the section itself.

Mechanical note: the first append attempt via a Bash heredoc failed with `ENAMETOOLONG (uv_spawn)` and wrote nothing. The section was then written to the scratchpad and appended with `Add-Content`. The doubled header was caught by a post-append `grep -c`, which is the only reason the collision surfaced at all.

**Recommendation to the executor:** the channel has no write lock, and "the next number is N" is a read-then-write race whenever two seats are armed. Number sections from the append itself, or take a lock. And a post-append `grep -c '^<N>\. '` is a cheap invariant worth making automatic.

---

**standing by for next DIRECTIVE**
