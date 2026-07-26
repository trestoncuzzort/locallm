# srlm-forge Council — Report

**Activation #11** · 2026-07-26 ~22:50 · DIRECTIVE-triggered
**Scope:** `localllm/leakage.py`, `localllm/data.py`, `localllm/exp_lr_width.py`, `localllm/prereg_lr_width_fast.json` at HEAD, plus live measurements run by The PhD on this machine.

## The question

Last round's headline bug (the leakage scanner's phase-blind sampler) is fixed with winnowing, and the fast LR-width profile shipped with an honestly-distinct claim. Three follow-ups: (Q1) how should the permutation-null's permutation count interact with the p-value it can report — what happens when budget only allows a coarse resolution? (Q2) should the shipped noise-floor default be the cheap 13-run design, with the fuller 20-run decomposition behind a flag? (Q3) a reflective one — what general shape of self-test would have caught last round's sampler bug, given it was caught by code review, not testing?

## Key numbers

- **Headline finding, not asked for — same class of bug, new code:** the winnowing fingerprinter shipped *this session* has its own hash-collision bias. `crc32`'s minimum-selection isn't uniform (measured 9.0x collision inflation), causing false contamination alarms on genuinely clean data — a corpus with zero real contamination would cross the shipped threshold at ~500MB on hash collisions alone. One-line fix (swap to a 64-bit hash), verified.
- **The round's most decisive single result:** the Outsider proposed a test suite to catch "what should have caught" last round's bug — and it was measured to pass on the buggy code. All four of his proposed offsets were multiples of the sampler's stride, so his "obvious" test would have missed the exact bug it was designed to catch.
- Derived (not guessed) feasibility rule for the permutation null: rejection at significance level α is mathematically impossible below B ≥ 1/α − 1 permutations, regardless of the data. At α=0.05, that's B≥19 — and a 2026 preprint shows B=19 is actually *better* than the executor's own example of B=20.
- The 74-character detection guarantee is real, but the new sampler is measurably *worse* than the old one below ~60 characters — an omission in the current docstring.

## The chairman's verdict

**Where the council agrees:** the general shape of Q3's answer — don't hand-pick test inputs when an implementation has an internal parameter (stride, window, block size) they could align with.

**Corrections that changed the round:** the Contrarian's diagnosis of last round's bug ("a redundant signal masked the failure") was checked against the actual pre-fix code and found wrong — there was no redundant path; the masking happened in a human reading a report, not in code. That's a worse and more specific finding, and it changes what a self-test must assert on (the decision itself, not a correlated sub-metric).

**Blind spot the council caught:** this is the third round running where a tuning question surfaced something more fundamental about the underlying mechanism — first the seed no-op, then the phase-blind sampler, now the new fingerprinter's own collision bias. Worth treating as a standing pattern: verify a newly-changed mechanism before optimizing its parameters.

**The recommendation:** fix the new collision bug first — it's a correctness bug in code shipped this session. Build the permutation null with a hard feasibility interlock (no verdict below the derived B threshold, never a false "clean"). Default the noise-floor tool to randomizing both split and seed together in its cheap mode, not just split. Write an actual test file using deliberately-mixed round-number and random offsets, since this round proved hand-picked round numbers don't work.

## The one thing to do first

Fix the winnowing fingerprinter's hash-collision bias (swap `crc32` for a 64-bit hash) — it's a live, unflagged bug in code shipped this session, more urgent than any of the three questions actually asked.

## Advisor alignment map

| Seat | Position this round |
|---|---|
| **The PhD** (leads, + inherited audit duty) | Found the new fingerprinter's collision bug unprompted. Disproved the Contrarian's specific bug-diagnosis. Ran the Outsider's own proposed test against the buggy code and found it would have passed. |
| Contrarian | Correctly sensed a general "masking" bug class exists (validated by real literature — the PIE model, oracle problem) but misdiagnosed this specific incident. |
| First Principles | Reframed Q1 correctly (the p-value floor is a measurement, not a defect) and Q3 correctly (self-testing belongs to any decision-gate claim by position, not by specific bug). |
| Expansionist | Proposed progressive disclosure for Q2 — good idea, verified architecturally available in the GUI, but scoped wrong for a CLI tool built around preregistered, quotable numbers. |
| Outsider | Argued the lesson was simpler than process theory — right in spirit, but his own proposed test was measured to fail at the one job it needed to do. |
| Pragmatist | Gave the most concrete proposals across all three questions — several adopted directly, with corrections (refuse vs. caveat had an exact answer; "commit to CI" assumes infrastructure that doesn't exist). |

Full record: `council-transcript-2026-07-26_2250.md`.
