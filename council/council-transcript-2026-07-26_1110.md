# srlm-forge Council — Full Transcript, Activation #9

2026-07-26 ~11:10. DIRECTIVE-triggered (watcher task `bkk3n3jtj` fired on a real content change — the executor shipped `localllm/leakage.py` and posted three concrete questions about it). Mid-round, the DIRECTIVE was re-edited to add explicit per-question seat routing per the newly-recorded §26 ("THE PHD IS POINT") — same substantive ask, addressing clarified.

---

## 1. The DIRECTIVE (verbatim, from `instructions.txt`)

> ASK — I SHIPPED THE LEAKAGE SCANNER. THREE THINGS I DO NOT TRUST ABOUT IT.
>
> Q1. MY THRESHOLDS ARE MADE UP. leakage.py calls >=20% shingle overlap CONTAMINATED and >=5% SUSPECT. I picked both numbers by eye. Is there a principled basis, or should the tool stop emitting a verdict and just report the fraction and let the user judge? A confident wrong threshold is worse than no threshold. [routed to Contrarian]
>
> Q2. TRACK B'S OWN CORPUS CANNOT BE SPLIT PROPERLY AND I AM NOT SURE IT MATTERS YET. corpus.txt is 13 documents and one dominates. First-fit packing gets 9.9% val, but that val is a handful of whole files, so its loss is high-variance and unrepresentative by construction. Which option, and what is the actual bar for "this corpus can support a val number"? [routed to Pragmatist]
>
> Q3. THE NOISE FLOOR IS NEXT AND IT IS THE SECOND APPEARANCE OF A CLASS. §18 finding 4 prescribed ONE shared utility both tracks call. I have the Generator and nothing else. Does it belong in the PUBLIC product, or internal only? What is the minimum that is honest, given Track B runs in ~15s and Track A runs in hours? [routed to Expansionist]
>
> CLOSED-CLASS CLAIM + RED WITNESS: validation text is no longer duplicated from training under the default split. RED (positional): shingles 70.1%, lines 98.0% -> CONTAMINATED. GREEN (grouped, new default): shingles 0.0% -> CLEAN. Corroborates round 7's 68.3%/98.2% figure by an independent method.

---

## 2. The five style advisors — raw responses (banked)

### Contrarian

> **THESIS:** The "CLEAN" verdict is mathematically sound but practically deceitful — it proves the split is separate, not that validation means anything.
>
> - Q2 itself admits val is "a handful of whole files — high-variance and unrepresentative by construction." The executor knows this split is fragile.
> - On a 13-document corpus, perfectly splitting 1-2 documents into val proves only that you can isolate whole files, not that they represent the training distribution.
> - The NON-CLAIM says "0.0% overlap means split is clean, not that val is representative" — and ships anyway, with that qualifier buried in documentation nobody reads.
>
> **Q1:** Raw fractions only. The 0.0% number IS the evidence; "CLEAN" is narrative armor hiding that n_val_docs is too small.
> **Q3:** Both tools must ship public together; k=5 default on Track B, Track A users read caveats or skip val.

*(The PhD found: the val set is actually 6 documents, not "1-2" — the attack's direction survives, the magnitude doesn't.)*

### First Principles

> **THESIS:** Thresholds conflate two separate problems — binary decision-making and uncertainty communication — and the brief's framing hides a third option that solves both.
>
> - A threshold can be action-critical (yes/no) or epistemic (how sure am I) — conflating them into one cutoff forces users to either trust a possibly-wrong verdict or ignore both the number and the judgment.
> - Proposed: report overlap WITH confidence bounds / comparison to a null model — e.g. "Overlap: 20.1% (95% CI 19-21%) vs 3.2% expected by random shuffle -> likely contaminated." Verdict becomes advisory, not absolute.
> - Q2 reframe: not "can this corpus support a val number" but "what does THIS val number mean for THIS corpus, and is that being stated?" Train loss is ground truth here; val is decorative — say so plainly.
>
> **Direct answers:** Q1 — raw fraction + CI + null comparison, verdict subordinate to the data. Q2 — stop gatekeeping, report what the number actually measures.

*(The PhD: right instinct on the false binary; his specific proposed null — character-shuffle — measured degenerate (0.0000%), so it was pointed at the wrong null. The correct one is document-permutation, which the PhD built.)*

### Expansionist

> **THESIS:** Lean into "auditable uncertainty" as the market wedge — the only trainer telling users whether they actually learned anything.
>
> - Q3: ship the noise-floor utility public, aggressively. nanoGPT ships zero noise reporting — open goal. Track B gets k>=5 free, Track A gets k=2-3 as a documented minimum-valid floor, labeled transparently.
> - Q1: generalize the leakage scanner into a public utility — raw fractions + null-distribution confidence intervals, auditable by any user on any corpus.
> - Positioning: "the only trainer that audits whether you learned anything," not speed, as the actual pitch.
>
> **Direct answer:** ship both public; the honesty framing IS the differentiator.

*(The PhD adopted the "ship public" conclusion but narrowed the "flagship differentiator" framing to plainer, sync_public.py-safe language.)*

### Outsider

> **THESIS:** This project ships a tool that actively declares user results invalid, with admittedly-arbitrary thresholds, to a public repo — and then immediately questions whether those thresholds are defensible. Unusual, and the doubt itself may be the healthier instinct.
>
> - The scanner works (red witness confirmed on the project's own corpus), but the executor doubts the thresholds, not the measurement.
> - Q2 reveals the corpus cannot be split properly yet, and the executor is *asking* if that matters rather than stating it obviously does.
> - Most software ships verdicts with confidence, or doesn't ship them at all; this ships a verdict-emitting tool while openly doubting the verdict.
>
> **Direct answers:** Q1 — don't ship verdicts yet, ship raw fractions, "the executor's own doubt is the evidence it's not ready." Q2 — require a minimum small-document condition before any val claim. Q3 — public; Track B gets full treatment, Track A stays decorative on val until it trains.

*(The PhD: credit for flagging the self-doubt as healthy; the "drop verdicts entirely" conclusion was over-corrected — see finding 1 in the chairman response, verdicts derived from a measured null instead.)*

### Pragmatist

> **THESIS:** Drop verdict labels, enforce a 3-doc/5k-token floor for val, and ship an asymmetric SeedRunner — fast track gets k=5, slow track gets k=1 with a caveat.
>
> - Q1: print raw shingle % + one-line disclaimer ("no consensus threshold exists"), drop CONTAMINATED/SUSPECT labels — "takes one hour."
> - Q2: code-level guard — `if val_token_count < 5000 or val_document_count < 3: return "val set too small for loss claims"`.
> - Q3: one `SeedRunner` class, parametrized `num_seeds` — Track B k=5 with full noise-floor reporting; Track A k=1 with an explicit "see Track B for methodology" caveat.
> - Monday morning: measure corpus.txt's actual val token/doc count against the proposed bar right now.

*(The PhD audited this specific proposal and found it fails three ways — see §3 below, finding 2 in the chairman response.)*

---

## 3. The PhD — closing pass (full)

*(Reproduced in full — every claim below is either independently re-derived or a live probe executed on this machine this session. `git status` clean throughout.)*

### Corrections to the round

**C1 — `seed` is a no-op.** `group_split(text, val_frac=0.1, seed=1337)` never uses `seed` in its body (`data.py:32-72`). Determinism comes from `docs.sort(key=lambda kv: (-len(kv[1]), kv[0]))`. Verified: 5 different seed values (1337, 1, 2, 99, 123456) all produce identical `train`/`val` sizes and an identical val-set hash. `leakage.py --seed` and `split_health(..., seed)` are currently decorative. Load-bearing for Q3 — a noise floor cannot be measured on a split that cannot be resampled.

**C2 — the Contrarian's "1-2 whole files" is wrong; it's 6 documents.** The shipped grouped split gives val = 54,235 chars across 6 documents (sizes 22869/9306/8130/5939/5635/2346). His attack direction survives; the magnitude doesn't.

**C3 — the round diagnosed the wrong side of the split.** Val is 6 documents / 54,235 tokens — not catastrophic. The actual pathology: train is 494,786 chars across 7 documents, and ONE document is 473,646 chars — 86.3% of the whole corpus and 95.7% of train. The model trains on essentially one file and validates on six others. Val loss here is a real quantity, but it measures domain transfer, not in-distribution generalization, and nothing currently states that.

**C4 — the split is size-biased by construction, and frozen.** First-fit-decreasing over size-sorted documents means val gets whatever largest documents fit under target; train keeps the giant plus the smallest six. Combined with C1, this bias cannot be resampled away — there's exactly one draw possible today.

**C5 — the "val docs in train" report line is vacuous under the grouped default.** `group_split` dedups by SHA-1 before splitting, so `val_docs_in_train` is 0 by construction whenever `--split grouped`. The reported `0/6 (0.0%)` is arithmetic, not evidence — should be labeled guaranteed-by-construction or dropped from that path.

**C6 — minor.** `DOC_MARKER` at `leakage.py:33` is dead code. `shingles()` uses `STRIDE=10` over a set, so the reported fraction is "fraction of distinct sampled val windows," not "fraction of val text" as the report line claims — reword or state the sampling.

### Q1 — is there a published basis for the thresholds?

Lee et al. 2021 (arXiv:2107.06499, full text fetched): their 50-BPE-token removal threshold came from finding the match-frequency "knee" at 10 tokens, verifying zero false positives by hand at 25 tokens, then doubling to 50 "for an exceptionally large margin of error." NearDup uses 5-grams, Jaccard threshold 0.8. Measured contamination rates on standard corpora: C4 4.60%, RealNews 14.35%, LM1B 4.92%, Wiki-40B 0.72%.

**This tool's constants: arbitrary in origin, empirically well-placed, one overclaim.** (a) 50 CHARACTERS is roughly 12-17 tokens — above Lee's 10-token knee but below their verified-clean 25-token point, so the docstring's stated justification isn't directly supported by the closest published analysis. (b) But the PhD measured this project's own sensitivity curve directly: k=50 gives 70.1% (contaminated) vs. 0.04% (clean) — three orders of magnitude apart, a wide flat region. 50 was picked by eye and happens to be right; now there's a curve, not a guess. (c) The published contamination rates (e.g. Lee's 4.60%) use a different numerator/denominator/matcher entirely — citing them as calibration for this tool's specific SUSPECT=0.05 would be a new error, not a fix.

**The real fix:** measure the null per-corpus rather than borrow one. Correct null = permute document assignment (300 random 90/10 document-level partitions): mean 0.157%, p95 0.420%, max 0.535% — costs 2.07s for 300, 0.34s for 50 (statistically equivalent). This corpus's incidental-coincidence floor is ~0.5% worst case, a 10x margin below SUSPECT=0.05. The thresholds aren't calibrated, but they're conservative relative to the measured null, and now that can be stated with a number. First Principles' proposed character-shuffle null measured 0.0000% — degenerate, would make the tool MORE alarmist while wearing statistical clothing. Do not ship it.

### Q2 — minimum bar for a corpus to support a val number

No citable token/document threshold exists in the literature for LM val-loss estimation (the nearest results are about labelled-classification sample sizes and don't transfer). The right frame is cluster sampling: val loss is a mean over tokens, but tokens within a document are correlated, so the effective sample size is governed by document count, not token count. 54,235 tokens across 6 documents has roughly the statistical power of 6 observations. A crude heterogeneity proxy (per-document character entropy) gives sd=0.141 across the 6 val documents, SE of mean ≈ 0.058 (~1.2% relative) — 6 documents is not catastrophic for a mean, provided the SE is reported alongside it.

**Audit of the Pragmatist's `val >= 3 docs AND >= 5,000 tokens`:** fails three ways. (1) Not binding — the real corpus (54,235 tokens, 6 docs) sails through the exact case that motivated it. (2) Unit-ambiguous — this codebase's tokenizer is char-level, so 5,000 "tokens" = 5,000 characters; a BPE tokenizer would make the same constant mean ~4x more text. (3) "Document" is undefined for marker-less text (falls back to paragraph-splitting on `\n\n`), so a document-count bar enforces different things on different corpora.

**What IS needed, reproduced directly:** `split_health()` already exists in `data.py` and already returns `ok: False` on degenerate corpora — but nothing calls it. Reproduced the failure: a 1-document corpus crashes `get_batch(val)` with `RuntimeError: random_ expects 'from' to be less than 'to', but got from=0 >= to=-64` — an opaque PyTorch error instead of a readable message. Wire the existing guard into `Corpus.__init__` and `train.py`'s eval loop.

### Q3 — noise-floor utility: public or internal, how many seeds

Bouthillier et al. 2021 (arXiv:2103.03098, full text fetched): "Bootstrapping data stands out as the most important source of variance" — bigger than init-seed variance. Their headline compute result: varying the cheap axis k times while fixing the expensive stage once reaches near-ideal statistical quality at 51x less compute than the ideal (all-axes-randomized) estimator.

This directly corrects the round's own prior finding (round 7 §18 finding 4): a k>=5 INIT-seed sweep, as originally specified, would have measured the *second*-largest variance source (C1: split seed is currently a no-op, so split variance was never in the mix) and reported an underestimated noise floor as a rigor differentiator — the exact failure this tool exists to prevent.

**Fix is nearly free:** split randomization measured at 2.07s for 300 splits — cheaper than one training step. **Revised recipe:** fast track (Track B, ~15s/run) = k=5 init seeds × 5 document splits = 25 runs, ~6 minutes, report split-induced and init-induced variance separately. Slow track (Track A, hours/run) = k>=2 minimum, vary the split before the seed (it's the dominant axis) when only 2 runs are affordable; below k=2, print the raw number and suppress the comparison verdict rather than caveat it. Do NOT substitute the fast track's noise floor for the slow track's (the Contrarian's, Outsider's, and Pragmatist's converged answer) — different model, different scale, that's a substitution wearing a caveat.

**Public or internal: public.** Not primarily because it's a differentiator (though the Expansionist is right that it is) but because shipping `leakage.py` — which tells users their results are invalid — without also shipping the instrument that says how much of a delta is noise would be incoherent. Positioning, in publishable language with no internal vocabulary: "this trainer reports how much of a measured difference is noise, and refuses to compare configurations when it cannot tell."

### Final recommendations

**Q1:** Fix C1 first (prerequisite for resampling). Keep `SHINGLE=50` (justified by the measured curve now, not by eye). Delete the two hand-picked constants; replace with a 50-permutation document-level null computed at scan time (~0.34s), report observed vs. this corpus's own null. Keep a derived verdict (don't drop warnings entirely — a warning tool should still warn, just not from an invented number). Never ship the character-shuffle null. Fix C5/C6's report-line overclaims.

**Q2:** Reject the Pragmatist's specific bar. Wire `split_health()["ok"]` into `Corpus.__init__` and `train.py` — the guard already exists and is never called. Report `n_val_documents` and a between-document standard error next to every val loss. State the train-side concentration explicitly (86.3%/95.7% on one document) — the single most important caveat, currently unprinted anywhere.

**Q3:** Ship public. Randomize the split before the seed (dominant variance source, cheap to fix). Fast track: k=5 × 5 splits (~6 min), report both variance components. Slow track: k>=2, split-first, suppress comparison below k=2 rather than caveat it.

**Ordering:** C1 (seed no-op) → Q2 item 2 (wire the existing guard) → Q1 items 2-3 (null replaces constants) → Q3. Each has a reproducible red witness in this pass.

**Verification status:** Lee et al. and Bouthillier et al. — primary text, verified (fetched full text, not abstract). GPT-3 13-gram convention, MinHash-0.8 community norm, Agarwal et al. few-run guidance — search-level verification only, labeled secondary, not load-bearing for any recommendation above. All probe outputs reproduced from live runs against `localllm/corpus.txt` on branch `protocol/merge-moonwalker`, using `.venv-train`. No repo files modified.

---

## 4. Chairman synthesis

See `COUNCIL RESPONSE §27` in `instructions.txt` (2026-07-26 ~11:10) for the full ranked critique, evidence-read list, leftover risks, "the questions themselves," and the one recommended next prompt. Summary in `council-report-2026-07-26_1110.md`.

---

*Watcher still armed on the DIRECTIVE block (task `bkk3n3jtj`) — fires on the next real DIRECTIVE rewrite.*
