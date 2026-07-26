# srlm-forge Council — Report

**Activation #9** · 2026-07-26 ~11:10 · DIRECTIVE-triggered (watcher fired for real this time)
**Scope:** `localllm/leakage.py`, `localllm/data.py`, `localllm/studio.py`, `train_native.py`, `sync_public.py` at HEAD, plus live probes run by The PhD on this machine.

## The question

The executor shipped a leakage/contamination scanner and doesn't fully trust three things about it: (Q1) the 20%/5% shingle-overlap thresholds were picked by eye — is there a principled basis or should the tool just report the raw fraction? (Q2) Track B's own corpus (13 documents, one dominant) can't be split into a representative val set — what's the actual bar? (Q3) the shared noise-floor utility from round 7 is next — should it be public or internal, and how do you handle Track B training in ~15s vs. Track A taking hours?

## Key numbers

- Shingle-overlap sensitivity curve on this project's own corpus: at the shipped 50-char shingle length, contaminated split = 70.1%, clean split = 0.04% — three orders of magnitude apart. The number was picked by eye and turned out to be well-placed.
- **Headline finding, not asked for:** `group_split()`'s `seed` parameter is a complete no-op — verified with 5 different seed values, identical output every time. Determinism comes from a size-sort, not the seed.
- Corpus reality check: val is 6 documents / 54,235 characters (not "1-2 files" as first assumed) — but **train is 86.3% one single document.** The actual problem isn't val being too small, it's train being too concentrated.
- A permutation-based null (50 random document-level splits) costs 0.34 seconds and gives this corpus's own contamination baseline (~0.16% mean) — cheaper than guessing a threshold.

## The chairman's verdict

**Where the council agrees:** ship the noise-floor utility publicly, in all five style advisors' and the PhD's view — not primarily as a "flagship differentiator" but because a tool that tells users their results are invalid should also ship the instrument that says how much of a delta is noise.

**Corrections that changed the round:** the round's own framing of Q2 (val is too small) was backwards — the pathology is train being 95.7% one document, which nobody named until this pass. The Pragmatist's concrete numeric bar (3 docs / 5,000 tokens) failed three ways on audit: not binding on the actual corpus, unit-ambiguous under a char-level tokenizer, and "document" is undefined for marker-less text. Three of five style advisors converged on "Track A gets k=1 with a caveat, borrow Track B's noise floor" for Q3 — found backwards: varying the *split* (not the seed) is the cheap, dominant variance source per the literature, and it's actually affordable on the slow track too.

**Blind spot the council caught:** the seed no-op. None of Q1-Q3 asked "does the split mechanism even work" — it was one grep away and is now the prerequisite for everything else in this response.

**The recommendation:** Fix the seed no-op first. Wire in a degeneracy guard (`split_health()`) that already exists in the code but is never called — right now a single-document corpus crashes with an opaque PyTorch error instead of a readable message. Replace the two hand-picked leakage thresholds with a per-corpus measured null (cheap, 0.34s) rather than deleting verdicts entirely. Build the noise-floor utility varying splits before seeds.

## The one thing to do first

Fix `group_split()`'s seed no-op — thread a real RNG through document assignment so `--seed` actually resamples the split. Everything else in this response (the measured null, the noise-floor utility) depends on being able to resample.

## Advisor alignment map

| Seat | Position this round |
|---|---|
| **The PhD** (leads, + inherited audit duty) | Found the seed no-op unprompted. Corrected Q2's framing (train concentration, not val size). Replaced made-up thresholds with a measured per-corpus null. Corrected the noise-floor recipe to prioritize split-randomization over seed-randomization. |
| Contrarian | Attacked the "CLEAN" verdict's trustworthiness — direction right, magnitude off (assumed a smaller val set than actually shipped). |
| First Principles | Correctly named Q1 as a false binary (verdict vs. raw fraction) — right instinct, wrong proposed null (character-shuffle, found degenerate). |
| Expansionist | Pushed hardest for public shipping and "honesty as the wedge" positioning — adopted, with the specific framing narrowed. |
| Outsider | Flagged the project's own self-doubt about its thresholds as a healthy instinct worth trusting — folded into the decision to fix rather than discard them. |
| Pragmatist | Wanted concrete, buildable numbers — instinct right, his specific bar (3 docs/5000 tokens) audited and rejected as non-binding and unit-ambiguous. |

Full record: `council-transcript-2026-07-26_1110.md`.
