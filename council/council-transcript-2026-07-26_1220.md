# srlm-forge Council — Full Transcript, Activation #10

2026-07-26 ~12:20. DIRECTIVE-triggered (watcher task `bkk3n3jtj`). Follow-up round after last round's seed-no-op finding was fixed and verified with a red witness.

---

## 1. The DIRECTIVE (verbatim, key parts)

> ASK — YOUR SEED FINDING IS FIXED. NOW A PROTOCOL QUESTION I WILL NOT DECIDE ALONE, PLUS THE TWO ITEMS I DID NOT BUILD.
>
> Q1 [PhD + Pragmatist]. The proprietor set a performance goal: 4 minutes to 1. I got 238s -> 163s by engineering alone, then hit a wall — GPU saturates at 4 workers. Reaching 60s requires shrinking the experiment (2000 steps -> ~800, 7 sweep LRs -> 4), but prereg's own rule says a changed protocol is a NEW preregistration. Is there a principled way to pick the step count and sweep grid, or should I ship a separate, differently-labeled fast profile?
>
> Q2 [PhD]. Your finding 1 prescribed a 50-permutation document-level null. Before I build it: on a corpus of 10,000 small documents, is it still ~0.3s and meaningful, or does it degenerate?
>
> Q3 [Expansionist, PhD auditing]. The revised noise-floor recipe (5x5=25 runs) is now buildable. Given Q1's pressure for cheaper experiments, is 5x5 the right shape?
>
> CLOSED-CLASS CLAIM + RED WITNESS: `seed` now genuinely resamples the document split. RED (old): 5 seeds -> identical val set. GREEN (fixed): 5 distinct splits (7/9/11/9/11 val docs), all within 9.6-9.9% of target; same seed twice -> byte-identical.

---

## 2. The five style advisors — raw responses (banked)

### Contrarian

> **THESIS:** Shrinking step count to meet a time budget inverts the causal chain — the schedule reverse-engineers the statistics.
>
> - No power analysis shown for 800 steps; the effect might be mid-convergence, not just noisier.
> - 7->4 LRs isn't cosmetic — if the true optimum lives between two grid points, a smaller sweep simply misses it.
> - Warns the "two-profile" label gets forgotten in months and the fast profile gets cited as equivalent.
>
> **Q1:** No principled basis without a power calc. Ship canonical at 2000/7 unchanged; relegate any fast variant to debugging-only.
> **Q3:** 25 runs defensible only if a variance-ratio check against a smaller design (e.g. 3x3=9) actually shows you need 5x5.

*(The PhD: the mid-convergence concern CONFIRMED by a real 68-run experiment; the "smaller grid misses the optimum" concern REFUTED — same winning LR at every step count tested.)*

### First Principles

> **THESIS:** "1 minute" is an iteration-velocity/UX proxy, not a rigor goal — so a separately-labeled fast profile satisfies the real goal without touching the canonical claim.
>
> - Reframes Q2: not "does it degenerate at 10k docs" case-by-case, but "what invariant property must ANY valid permutation null have" — his candidate: Type I error control under document-level shuffling.
> - `[VERIFY]` his own tag: guesses the null "stabilizes at ~50+ documents."
>
> **Direct answers:** Q1 — ship a separate fast-profile preregistration, canonical stays untouched. Q2 — test the invariant once, don't case-check.

*(The PhD: the "~50+ documents" guess is wrong — the real cliff is derived, not guessed, and sits at ~1/val_frac documents, i.e. 10 at the shipped val_frac=0.1.)*

### Expansionist

> **THESIS:** Adaptive sequential testing beats fixed grids — one preregistered stopping rule cuts both Q1's speed problem and Q3's run count.
>
> - Proposes: preregister a stopping RULE (e.g. "stop when CI on effect size <= 0.005, or N>=15") instead of a fixed N — argues this isn't a protocol change since the rule, not the result, is preregistered.
> - Also proposes applying the same idea to Q1's LR sweep — stop once the top-2 LRs "look clearly separated."
> - `[VERIFY]` his own tag: unsure whether sequential/resampling nulls degrade less gracefully than character-shuffle for Q2.
>
> **The structural idea:** one mechanism serving both Q1 and Q3's cost pressure.

*(The PhD: the underlying statistics (SPRT, anytime-valid inference) are real and citable, and his instinct that stopping RULES rather than results are what's preregistered is correct — but neither application survives testing. The LR-sweep "stop when it looks separated" version is the classic peeking trap, measured 3.5-6.3x false-positive inflation. The Q3 width-based version avoids that specific trap but introduces a worse one: it stops exactly when the sample looks quiet, biasing the noise-floor estimate 29.6% low.)*

### Outsider

> **THESIS:** The three technical questions mask a structural collision — an external 1-minute deadline meeting a preregistration rule built specifically to prevent post-hoc shrinking.
>
> - Reads Q1 as: the executor asking permission to do the exact thing the rule exists to prevent, dressed as careful technical questions.
> - Notes the large current effect size creates false confidence that power is safe under shrinking — actual power at 800 steps was, at the time of writing, unverified.
> - Raises whether this might not be resolvable by the council at all — might need the proprietor and executor to resolve directly.
>
> **Direct answer:** no principled basis exists yet; ship canonical as preregistered; if 1 minute is mandatory, a separate labeled fast profile, never substituting.

*(The PhD: resolves the collision — the fast profile answers a genuinely different, legitimate question ("reaches lower loss faster") rather than a cheaper version of the canonical claim, so nobody has to trade rigor for speed.)*

### Pragmatist

> **THESIS:** 163s is not actually a problem worth solving further — the effect is already 2.2x the bar with zero overlap, a "slam dunk."
>
> - No shrinking needed to prove the claim — it's already proven.
> - If the 1-minute number is a UX/demo preference rather than a scientific need, add a cheap (~50 LOC estimate) separately-labeled fast-demo mode that never appears in canonical claims.
>
> **Monday morning:** ship the 163s canonical experiment as preregistered, unchanged; add fast-demo mode only if the proprietor confirms it's about feel, not rigor.

*(The PhD: confirms via power calculation — noise would need to inflate 8x before power drops to 50%; the canonical result's implicit false-positive rate is effectively zero over 400,000 simulated draws.)*

---

## 3. The PhD — closing pass (full, reproduced verbatim from the tool output)

*(All numbers below are from live runs on this machine this session. `git status` clean throughout, `HEAD = ec4168a`. Probe scripts left in scratchpad, not the repo.)*

### Corrections to the round

**C1 — self-correction, first.** An initial variance-components simulation drew the split effect once per cell instead of once per split, destroying the nesting the design exists to exploit. Corrected before any Q3 number below was finalized.

**C2 — the headline finding: the shingle sampler is phase-blind.** `leakage.py` samples 50-char shingles at a fixed byte stride starting at position 0. Measured: one real corpus document placed verbatim inside train at all 10 possible byte offsets → detected at exactly 1 of 10 phases (100% at that phase, 0% at the other nine) → **10% detection rate on a case that should read 100% every time.** Round 9's C6 filed this as a wording issue; it is a detection failure. Line overlap catches the same case (99-100%), which is the only reason the tool hasn't looked broken so far — and the docstring names shingle overlap as "the one to trust." Verified fix: content-defined selection (`crc32(window) % 10 == 0`) is phase-invariant (10/10 phases, 100% each). The naive mod-p form has its own flaw per Schleimer/Wilkerson/Aiken 2003 (search-level verification, not primary text this round): unbounded gaps between selected fingerprints — measured max gap 83 chars on this corpus, so a copied passage shorter than that could fall entirely in a gap. Winnowing fixes both and measured cheaper (20,580 fingerprints vs. the current sampler's 54,897, bounded max gap 51 chars).

**C3 — First Principles' "~50+ documents" is wrong, and the shape of the claim is wrong.** Measured across 3 to 1000 equal-sized documents (100 permutations each): there's a real cliff, but it's derivable, not guessed — at ~1/val_frac documents (10, at val_frac=0.1). Below that, `group_split` returns an empty validation set and the null collapses to one degenerate draw. Second finding in the same table: at exactly 13 equal-sized documents, only 13 distinct val sets exist across 100 seeds — permutation count is capped by the number of distinct achievable splits, not by patience.

**C4 — round 9's "wire in split_health()['ok']" is necessary but not sufficient.** `ok` is computed only from achieved validation fraction; the 86.3% train-concentration pathology round 9 flagged as the real headline caveat passes `ok=True` regardless. Needs its own gate on `largest_doc_frac`.

**C5 — round 9's "50 permutations" caps the p-value at 1/51 = 0.0196**, per the exact permutation estimator (Phipson & Smyth). B=200 reaches 0.005 at a measured cost of 2.09s on the current corpus, 31.4s on a 5.26MB one.

**C6 — the Contrarian's demanded power calculation is computable, and was computed.** 200k Monte Carlo draws against the prereg's actual bar: implicit false-positive rate ≈0 over 400,000 sims; minimum detectable effect at 80% power (0.0213) sits almost exactly on the 0.020 bar; observed effect (0.0439) clears it 2.1x; noise would need to inflate 8x before power drops to 50%.

**C7 — the Contrarian's two claims split: one confirmed, one refuted.** 68 real training runs across 4 step counts (400/800/1200/2000 × 17 runs each): the gap decays monotonically, 9.0x from 400 to 2000 steps — confirms mid-convergence risk is real. But the 4-point and 7-point sweep grids pick the identical winning LR at every step count — refutes "the smaller grid might miss the optimum." The 2000-step row reproduces the canonical `exp_lr_width_result.json` numbers exactly, an independent cross-check.

### Q1 — analysis and recommendation

Power-wise, shrinking to 800 steps is safe by a huge margin. But **the estimand changes** — "reaches lower loss at 2000 steps" and "…at 800 steps" are different claims, and the measured 9x decay means the 800-step number systematically overstates the 2000-step one. No published LR-sweep grid convention was found licensing 7→4 points (checked muP/Yang et al. directly — no statement on grid spacing). The Expansionist's sequential-stopping idea is real, citable statistics (Wald's SPRT, anytime-valid confidence sequences) but fails on arithmetic here: stage 1 (the sweep itself) already exceeds the 60s budget on its own before any stopping rule on stage 2 could help — sequential stopping saves at most ~6 runs (162s → ~105s), nowhere near 60s.

**Recommendation:** ship canonical unchanged (2000 steps/7 LRs). Add a separately-labeled fast profile at 800 steps/4 LRs/5 seeds (~56s projected), with a genuinely different claim ("reaches lower loss faster," not "same effect, cheaper") — enforce the label mechanically by writing step count/grid size into the result JSON's own verdict string. Add step-count sensitivity to the canonical prereg's NON-CLAIMS. Do not adopt sequential stopping — sound math, wrong target.

### Q2 — executed test on synthetic corpora

Built a real 10,000-document synthetic corpus (both high- and low-redundancy variants) with the project's own code and ran the actual scanner. **A known-clean split with ordinary boilerplate reads SUSPECT at 19.1%** (one hundredth of a point from CONTAMINATED, zero actual contamination) — false alarm. **A low-redundancy corpus with 20% of val verbatim-duplicated into train reads CLEAN** — miss. The permutation null gets both right (p=0.119 on the false alarm, p=0.005 on the miss). Does NOT degenerate the way character-shuffle did — a genuine zero-redundancy corpus produces an exact zero-sd null, which is the *correct* answer (verified: still flags 1% contamination at p=0.005, still returns p=1.0 on truly clean data) — but this means any z-score-based CI is invalid (dividing by zero sd); must use the exact permutation p-value instead. Cost scales with corpus size, not document count (~30ms/MB/permutation: 2.1s at 550KB, 31s at 5.3MB).

**Recommendation:** build the permutation null — it survives the shape change and gets the 10,000-doc cases right, with four corrections: exact p-value not z-score; B sized by wall-clock budget; refuse (don't report) below the derived feasibility cliff; fix the sampler (C2) first.

### Q3 — audit and corrected recipe

The Expansionist's width-based stopping rule avoids the classic significance-peeking trap (verified: his OTHER proposal, for Q1's sweep, does NOT avoid it — simulated 3.5-6.3x false-positive inflation). But it introduces a worse problem for this specific tool: simulated at his stated parameters, it stops at an average of N=9.55 runs and reports a noise floor **29.6% below the true value** — a fixed N=8 design of comparable size is off by only -3.9%. For a tool whose purpose is "tell the user how much of their delta is noise," a downward-biased noise floor is the one failure mode that must never happen.

Separately, independent of the stopping-rule question: the originally-proposed 5×5=25-run design is dominated. Corrected variance-components simulation shows 10 splits × 2 seeds = 20 runs beats it on both variance components at 20% less compute; 13 splits × 1 seed = 13 runs beats it on the total noise floor alone at roughly half the cost. Reconfirms round 9's "vary the split before the seed" — a 2-splits-×-10-seeds design was the worst configuration tested.

**Recommendation:** fixed N, not sequential. 13×1 (13 runs) if only the total floor is wanted; 10×2 (20 runs) if the split/seed decomposition matters. Both beat the original 25-run design on precision per run.

### Citations — verification notes

Primary, verified by the PhD's own execution (not literature): all measurements above. Search-level only, explicitly labeled, none load-bearing for a final recommendation: Schleimer/Wilkerson/Aiken 2003 (winnowing), Phipson & Smyth 2010 (exact permutation p-value), Howard/Ramdas/McAuliffe/Sekhon 2021 and Wald 1945/1948 (sequential testing), Lan-DeMets (alpha-spending). Yang et al. 2022 (muP) checked directly for a grid-spacing convention — found none; absence-of-citation is itself reported as a finding.

### Non-claims

Not claiming the fast profile has been built or run end-to-end (56.2s is a projection, not a direct measurement). Not claiming the sweep-only timing floor was directly measured — that probe was still running at cutoff, and one stray python process from it may still be resident on the GPU. Not claiming the synthetic corpora represent real-world redundancy levels exactly. Not claiming the inverted-index null-computation optimization is correctness-equivalent to the shipped scanner (it measures something subtly different). Not claiming winnowing has been implemented in the repo — measured as a scratch prototype only.

---

## 4. Chairman synthesis

See `COUNCIL RESPONSE §30` in `instructions.txt` (2026-07-26 ~12:20) for the full ranked critique, evidence-read list, leftover risks, "the questions themselves," and the one recommended next prompt. Summary in `council-report-2026-07-26_1220.md`.

---

*Watcher still armed on the DIRECTIVE block (task `bkk3n3jtj`) — fires on the next real DIRECTIVE rewrite. Operational note carried over from the PhD's own non-claims: check `nvidia-smi` for a stray python process before the next GPU-heavy round.*
