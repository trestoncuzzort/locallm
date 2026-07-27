# srlm-forge Council — Full Transcript, Activation #12

2026-07-26 ~19:35. DIRECTIVE-triggered (watcher task `bkk3n3jtj`). Note: the PhD's first pass this round was cut off mid-analysis by an API session limit and produced no usable output beyond "I'll start by reading the actual code"; it was re-run from scratch. Separately, a git branch mix-up briefly checked the working directory out to the public `main` branch, making `instructions.txt` disappear from disk for part of the round — resolved by the proprietor/executor; the DIRECTIVE and history were re-confirmed unchanged against the restored `protocol/merge-moonwalker` branch before this round's work resumed.

---

## 1. The DIRECTIVE (verbatim, key parts)

> ASK — I TOOK YOUR STANDING CHECKLIST ITEM AND APPLIED IT TO MYSELF FIRST. This round I modified two mechanisms and wrote the first tests this repo has ever had. So the questions are about THOSE, before I build the permutation null on top of them.
>
> Q1 [PhD]. test_detectors.py exists and passes 4/4, with the old broken sampler kept as a regression oracle. But I wrote the tests, and I am the one who shipped both bugs. Your finding 2 proved my instinct for test inputs is exactly the instinct that misses these bugs. So: what does this suite still not cover? The one I can name and have not tested is the "always says CLEAN on real-world near-duplicates" case, because I have no oracle for it.
>
> Q2 [PhD]. Nobody has checked whether OTHER parameters share the stride/round-number alignment risk. Candidates: block_size=128, batch_size=32, eval_interval=250, WINDOW=25, EVAL_BATCHES=40, and the 90/10 split fraction. Is there a general way to sweep for this class, or is it necessarily per-parameter reasoning?
>
> Q3 [Contrarian, PhD auditing]. The bench_device numbers: CPU-only is 7.5x slower at small, 23.8x at default, 84.9x at large. Is "CPU gets the small model by default" the right call, or is shipping a deliberately weaker model to GPU-less users a worse failure than making them wait 5.4 minutes?
>
> CLOSED-CLASS CLAIM + RED WITNESS: the fingerprinter no longer produces false overlap on clean corpora as size grows. RED (crc32): rising with size, up to 0.0293% at 2MB. GREEN (blake2b-64): 0.0000% at all three sizes.

---

## 2. The five style advisors — raw responses (banked)

### Contrarian

> **THESIS:** "Weaker model vs. longer wait" is a false binary masking a silent downgrade; both fail without transparency to the user about which they're getting and why.
>
> Names 4 uncovered test gaps for Q1: real-world near-duplicates, `WINDOW=25` alignment risk (hand-picked, same instinct that caused the last two bugs), non-uniform k-gram distributions (current tests are synthetic-random only), invented thresholds (0.20/0.05 still uncalibrated).
>
> **Q3:** the real decision is whether to DISCLOSE to CPU users that they got a smaller model — a silent downgrade is worse than a disclosed wait either way.

*(The PhD: `WINDOW=25` checked directly across a range — no risk found, the guarantee holds at 100% everywhere. But the "0.20/0.05 uncalibrated" call was confirmed and found worse than stated — real clone overlap lands inside that exact range.)*

### First Principles

> **THESIS:** the test suite validates structural properties (HOW the detector works), not semantic correctness (WHETHER it works) — the near-duplicate gap is fundamentally unfalsifiable by writing more self-authored tests, since any new test still encodes the author's own intuition.
>
> Proposes reframing the tool's CLAIM: stop asserting "correct," start asserting "achieves X% recall/precision against labeled benchmark D at threshold T."
>
> Q2 reframe: the lesson isn't "strides are dangerous," it's "any constant chosen without a documented rationale is suspect."
>
> `[VERIFY]` whether a labeled near-duplicate dataset exists in the repo already.

*(The PhD: this diagnosis was exactly right and became the actual resolution — external taxonomy instead of a labeled dataset OR self-invented mutations. `[VERIFY]` answered: no such dataset exists in the repo.)*

### Expansionist

> **THESIS:** turn the CPU penalty into transparency — show CPU users a live time-to-completion estimate before they commit, making it an informed choice rather than a silent downgrade or an unexplained wait.
>
> For Q2: build a general property ("detector output invariant under parameter sweep") that any new parameter automatically gets tested against.
>
> `[VERIFY]` whether time estimates stay predictable across corpus sizes.

*(The PhD: `[VERIFY]` answered — yes, predictable to within 7% across a 16x corpus-size range. This became a load-bearing part of the final Q3 recommendation.)*

### Outsider

> **THESIS:** a 4-test suite passing, self-written, after shipping 2 bugs in one session by the same author with the same blind test-writing instinct, is evidence that shipping without external signal should stop.
>
> Notes the CPU benchmark reveals the project is quietly shipping "two products under one name."
>
> **Q3 direct:** smaller CPU defaults is the wrong call — it creates a hidden quality tier; either CPU support is genuinely in scope or it isn't.

*(The PhD: confirmed via external practice — no comparable tool (Ollama/llama.cpp/LM Studio) silently substitutes a weaker asset for slow hardware; all disclose and let the user choose.)*

### Pragmatist

> **THESIS:** concrete, buildable answers to all three.
>
> - Q1: build synthetic near-duplicates via token mutation (15% token replacement, line-shuffling), run through the detector, assert nonzero detection distance.
> - Q2: vary each parameter ±1, hash the output; if the hash changes, flag alignment risk.
> - Q3: `if device==CPU and estimated_time>300s: auto-downsize to small`.

*(The PhD: all three specific proposals were found unsound as written. Q1's mutation percentage is another hand-picked number — the same anti-pattern being hunted. Q2's method fires on every parameter by construction and discriminates nothing. Q3's threshold silently downgrades this project's own dev machine's default size.)*

---

## 3. The PhD — closing pass (full, reproduced from the tool output)

*(All measurements run live on this machine, this session, after confirming the correct branch. Zero repo writes. Probe scripts in scratchpad.)*

### Corrections to the round

1. **Contrarian's `WINDOW=25` suspicion — measured, and cleared.** Swept window 21–29, SHINGLE 46–54: the `w+k-1` guarantee holds at 100% for every value tested. Not special.
2. **The Pragmatist's Q2 probe is wrong as specified.** "Hash the output, flag if it changes" fires on all six parameters by construction (they're all *supposed* to change output) and discriminates nothing. Corrected to a discontinuity test against each parameter's own neighborhood.
3. **The Pragmatist's Q3 rule collides with its own data.** `bench_device_result.json` records CPU/default at 324.2s — 8% *above* the proposed 300s threshold. The rule as written downgrades the shipped default on this actual development machine, not just weak hardware.
4. **"5.4 minutes" was measured on a Ryzen 9 7900X.** A CPU-only user (no discrete GPU) is more likely on materially slower hardware — the council was reasoning about the CPU population from the fastest CPU in the building.
5. **Contrarian's "0.20/0.05 thresholds are uncalibrated" — confirmed, worse than stated.** Real Type-1/Type-2 clones measure 22.4%–26.3% overlap — inside the CONTAMINATED threshold's own margin.
6. **First Principles' `[VERIFY]` — answered no.** No labeled near-duplicate dataset exists anywhere in the repo.
7. **Expansionist's `[VERIFY]` — answered yes.** A 16x corpus-size change moves ms/step by only 6.6–7.2%; a live time estimate is stable and cheap (~2-4s) to compute.
8. **The test suite's own docstring overstates itself.** Claims "every test runs against both implementations, the old one must FAIL" — actually 3 of 4 tests PASS on the known-broken old sampler; only the phase-invariance test enforces the rule.
9. **`shingles()` scales linearly but holds every fingerprint as a Python int in memory** — fine at the current corpus size, would need attention well before 1GB.

### Q1 — the oracle problem

Built a clone-type recall table (Type-1/2/3, per the published code-clone taxonomy, implemented mechanically via Python's own `tokenize` — not hand-tuned) on the project's real 10 corpus documents:

```
verbatim (control)                recall 10/10 = 100%   mean overlap 100.0%
Type-1  reformat + strip comments recall  9/10 =  90%   mean overlap  26.3%
Type-2  full identifier rename    recall  0/10 =   0%   mean overlap   0.0%
Type-3  T2 + 10% stmt edits       recall  0/10 =   0%   mean overlap   0.0%
```

Factorial isolation (rename identifiers × replace string literals) pinpointed the cause: renaming every identifier costs almost nothing (22.4% → 24.1%); replacing string literals (~7.4% of the corpus) drops overlap to 0.0%. On this corpus, the ~7% of text that's prose (docstrings) carries essentially all surviving detection signal; the 92% that's actual logic contributes almost none once whitespace is re-rendered.

The proposed external benchmarks were both found to be dead ends: BigCloneBench is Java-only and doesn't run here, and a 2022 critique found 86% false positives in its contested clone categories anyway; SemanticCloneBench/GPTCloneBench is a *semantic* (Type-4) benchmark — the wrong instrument, since this detector would correctly score ~0% on it and that would misreport as failure. The genuinely applicable literature is LLM training-data deduplication (Lee et al. 2021/ACL 2022, fetched and quoted directly from the paper text): "77% of the training examples that NEARDUP removes from C4 have at least one verbatim length-50 match found by EXACTSUBSTR" — a published external number showing a verbatim-only detector misses ~23% of near-duplicates on *prose*. This project's own measurement shows it's far worse on *code* (0%). That same paper's methodology answers "what do you do without an oracle": triangulate with a second, different-failure-mode detector and report disagreement — not chase a labeled set.

**Recommendation:** rewrite the tool's claim entirely — "finds verbatim shared runs ≥74 characters at any offset, 100% recall (measured); does NOT find renamed or rewritten copies, measured 0% recall on identifier-renamed Python." Delete the current report line "Validation looks independent of training. Val loss is usable." Add clone-type recall tests that assert the *zeros* (Type-2 == 0%, Type-3 == 0%) as a pinned known limitation. Longer term: build a second, MinHash/NEARDUP-class detector using Lee et al.'s published constants, and report disagreement between the two.

### Q2 — executed sensitivity sweep

Method corrected first: test for a discontinuity against a parameter's own neighborhood, not for "does the output change" (which fires on everything by construction).

| Parameter | Result | Verdict |
|---|---|---|
| WINDOW=25 | 100% guarantee at every window 21–29 | NO RISK |
| SHINGLE=50 | 100% guarantee at every k 46–54 | NO RISK |
| block_size=128 | No cliff; 129 was actually fastest | NO RISK |
| batch_size=32 | No cliff; 32 was the slowest point measured, inside noise | NO RISK |
| EVAL_BATCHES=40 | Clean 1/√N decay, but CI (0.076) is 72% of the measured 0.1056 effect | UNDERSIZED |
| val_frac=0.10 | **Saturates at 0.14 regardless of requested value (0.15, 0.20 both give 13.73%)** | REAL DEFECT |
| eval_interval=250 | **Couples eval frequency to training data via shared RNG** | REAL DEFECT |

The `val_frac` saturation is invisible to `split_health()['ok']` because its own tolerance constant (`achieved >= requested * 0.5`) is itself a hand-picked number that tolerates the achieved value being half the request. The `eval_interval` coupling: `train.py`'s `estimate_loss()` draws from the global RNG, consuming 40 `randint` calls per eval — measured spread 0.004361 across eval_interval values 248–500, vs. seed-noise floor 0.005359 (0.81x, a real but not-yet-conclusion-changing effect); isolating eval onto its own Generator (the fix, already implemented correctly in `exp_lr_width.py`) gives bit-identical results (spread 0.000000).

**Conclusion:** neither "systematic sweep" nor "per-parameter reasoning" alone suffices. The mechanical sweep cleared four parameters cheaply (~4 minutes) and should be built as a standing tool — but it structurally cannot detect coupling-type defects (no discontinuity exists to find) or wide-saturation-type defects (the cliff was far outside a ±1 window). First Principles' "document why every constant exists" is what would have surfaced the coupling — writing down "eval_interval controls only how often we observe" forces the question of whether that's true. It isn't.

### Q3 — resolving the three-way split

Checked external practice (search-level verification): Ollama, llama.cpp, and LM Studio all adapt the *execution plan* (GPU/CPU layer offload) rather than substitute a smaller asset; LM Studio explicitly discloses a fit estimate before download rather than deciding for the user. No comparable tool silently downgrades quality for speed.

`bench_device.py`'s already-shipped measurement is functionally equivalent to LM Studio's pre-download fit estimate — nothing new needs building, it needs to be surfaced as a disclosed, pre-selected choice. §23's own text already mandates this shape: point 2 requires picking sane defaults, point 3 requires asking "when the tradeoff is genuinely the user's" — a choice between 1 minute and 5.4 minutes on the user's own hardware is definitionally the user's tradeoff, not a decision to make silently.

**Recommendation:** run a trimmed benchmark during install (cheap, stable — 10-25 timed steps give 1.5-2.5% spread). Present the measured result as a pre-selected choice with real numbers. Never silently substitute. Set any time budget from the live measurement, not a hardcoded constant.

### Citations, with verification notes

Byte-verified (fetched paper text directly): Lee et al. 2021/ACL 2022 (arXiv:2107.06499). Formula-confirmed via search, independently reconfirmed by this round's own measurement: Schleimer/Wilkerson/Aiken 2003 (winnowing). Search-level only, explicitly labeled: Krinke & Ragkhitwetsagul 2022 (BigCloneBench critique), Svajlenko & Roy 2015/2016 (BigCloneEval), GPTCloneBench (arXiv:2308.13963), Ollama/llama.cpp/LM Studio's auto-sizing behavior (Ollama's own FAQ returned 404 on direct fetch — flagged, recommendation doesn't depend on the precise figure).

---

## 4. Chairman synthesis

See `COUNCIL RESPONSE §35` in `instructions.txt` (2026-07-26 ~19:35) for the full ranked critique, evidence-read list, leftover risks, "the questions themselves," and the one recommended next prompt. Summary in `council-report-2026-07-26_1935.md`.

---

*Watcher still armed on the DIRECTIVE block (task `bkk3n3jtj`) — fires on the next real DIRECTIVE rewrite.*
