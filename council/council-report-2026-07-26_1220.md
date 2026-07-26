# srlm-forge Council — Report

**Activation #10** · 2026-07-26 ~12:20 · DIRECTIVE-triggered
**Scope:** `localllm/data.py`, `localllm/exp_lr_width.py`, `localllm/leakage.py`, `localllm/train.py` at HEAD, plus live probes and simulations run by The PhD on this machine.

## The question

Three follow-ups after last round's seed fix landed (verified with a red witness): (Q1) the proprietor wants a preregistered LR-vs-width experiment to run in 1 minute; it's at 163s and further speedup requires shrinking the experiment itself, which collides with the project's own preregistration discipline — is there a principled basis, or should this ship as a separate profile? (Q2) does the leakage scanner's proposed permutation-null fix (from round 9) still work on a very differently-shaped corpus (10,000 small documents vs. the current 13)? (Q3) is the proposed 25-run noise-floor design (5 seeds × 5 splits) the right shape, especially under cost pressure from Q1?

## Key numbers

- **Headline finding, not asked for:** the leakage scanner's shingle sampler misses verbatim duplication **9 times out of 10** — a phase-dependent bug in the fixed-stride sampling, confirmed by injecting one real document at all 10 possible byte offsets (detected at exactly 1 of 10).
- On a real synthetic 10,000-document corpus: a **known-clean** split reads SUSPECT at 19.1% (false alarm), while a corpus with **20% of validation verbatim-duplicated into training reads CLEAN** (missed). The permutation null gets both right.
- Power calculation on the canonical LR-width result: false-positive rate ≈0 over 400,000 simulated draws; the observed effect clears the minimum-detectable-effect threshold by 2.1x.
- The Expansionist's sequential-stopping proposal, simulated: inflates false positives 3.5–6.3x when peeking on significance, and biases the noise floor **29.6% low** when stopping on CI width — the one direction this specific tool must never err in.
- A rebalanced fixed design (10 splits × 2 seeds = 20 runs) beats the originally-proposed 25-run design on precision, at 20% less compute.

## The chairman's verdict

**Where the council agrees:** unanimous across all 5 style advisors — do not shrink the canonical experiment. If a faster number is wanted, it has to be a separately-labeled profile that answers a genuinely different question, not a cheaper version of the same claim.

**Corrections that changed the round:** the Expansionist's structurally interesting sequential-stopping idea (which could have unified Q1 and Q3) was tested by simulation and found unsound for both uses — for the LR sweep it's the classic peeking trap; for the noise floor it systematically understates the very quantity the tool exists to report honestly.

**Blind spot the council caught:** this is the second round in a row where a tuning question (thresholds, run count) was asked before a mechanism question (does the underlying measurement even work) — and the mechanism question mattered more both times. Round 9 found the split-seed no-op; this round found the shingle sampler's phase blindness.

**The recommendation:** fix the shingle sampler first — it's a correctness bug, not a tuning question, and everything else in this response assumes it's fixed. Then replace the leakage thresholds with a properly-specified permutation null (exact p-value, budget-sized permutation count, refuse-below-feasibility-cliff). Ship the LR experiment's fast version as an honestly different, separately-labeled claim. Rebalance the noise-floor design toward more splits, fewer seeds.

## The one thing to do first

Fix the shingle sampler's phase blindness (winnowing, or at minimum content-defined selection with a bounded gap) before building anything else this round prescribes — calibrating a broken detector with a good statistical null just produces a well-calibrated broken detector.

## Advisor alignment map

| Seat | Position this round |
|---|---|
| **The PhD** (leads, + inherited audit duty) | Found the phase-blindness bug unprompted. Ran a real power calculation, a real 68-run step-count experiment, and two bias simulations. Rejected sequential stopping for both proposed uses. |
| Contrarian | Demanded a power calculation and flagged step-count/convergence risk — both confirmed correct by execution. |
| First Principles | Correctly reframed "1 minute" as a UX/velocity proxy, not a rigor goal — supports the separate-profile conclusion. |
| Expansionist | Proposed sequential/adaptive stopping as a unifying mechanism for Q1 and Q3 — genuinely tested, found unsound for this specific tool's purpose. |
| Outsider | Named the real tension: an external deadline colliding with a rule built to prevent exactly this — resolved by treating the fast profile as a different question. |
| Pragmatist | Argued 163s is already fine given the huge effect size — the numbers back this up; shrinking wasn't necessary to prove the claim, only to hit an arbitrary time target. |

Full record: `council-transcript-2026-07-26_1220.md`.
