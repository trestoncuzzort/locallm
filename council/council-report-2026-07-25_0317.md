# Council Report — srlm-forge · Pass #3

**Date:** 2026-07-25 03:17 · **Trigger:** expanded #2 directive relayed by proprietor · **Scope:** instructions.txt only
**Deliverable:** smallest ruler-moving proof design → written to channel §8

## The ask
Ruler live (0.88 / 0.90; rotate 0/5; rle 4/5; conciseness pairs gated off; dedup on; overnight
loop accumulating pairs). Design the injection with: (1) source of verified chosen; (2) honesty
incl. no circular "pipeline wrote both the task and its answer"; (3) **the smallest change that
proves it moves the ruler above baseline noise, before investing in scale.**

## Key numbers
Aggregate SE ±4.6 pts (95% CI ~±9) at 50 samples · 8/10 tasks at ceiling · 0/5's true-rate CI
reaches ~45% · rotate n=100: ≥5 passes = decisive (Fisher ~0.03)

## Verdict

**Agrees (4/5 independently — the instrument problem):**
- **The ruler cannot detect the proof being asked for.** Aggregate pass@1 is ceiling-compressed
  fake resolution; the only detectable event is the frontier task itself.
- **0/5 is not zero.** rotate's true rate could be as high as ~45% — it may be self-lane after
  all. Measure at n=100 before designing around "can't."
- Pre-registration is mandatory; results reported either way.
- The near-duplicate laundering trap is the experiment's #1 failure mode.

**Clashes:** n=20 (Pragmatist) vs n=100 (First Principles/Outsider) on the frontier task —
chairman sided with n=100 (zero-background detector, costs under an hour). Pause the overnight
loop vs let it spin — resolved by training only on the curated pack.

**Blind spots caught:**
- **The builder is a leakage channel** (Outsider): aiming packs at observed ruler failures turns
  the test set into a dev set — ruler v1 is partially burned; seal a blind v2 after.
- **Nobody audits the tests**: weak corpus tests admit wrong references → mutation-adequacy on
  test suites too.
- **A flip needs a control** (First Principles): an unrelated-family pack of identical size must
  NOT move rotate, else "any training wobbles the ruler."

**Recommendation:** Two nights, measurement before training. Night 1: 3× baseline eval reruns +
rotate n=100 / rle n=50 — if rotate >0/100, reroute to self-lane and stop. Night 2 (only if
0/100): pre-registered ~150-pair rotate-family repair pack (corpus-origin tests, provenance
triple, ruler-collision filter), one ORPO epoch on the pack alone, same-quant re-export, two
post-eval runs; success = rotate ≥5/100 twice + aggregate ≥0.84 + no ceiling regression.

## The one thing to do first
Night 1 — pin the instrument, train nothing: 3× baseline reruns, then rotate at n=100.

## Alignment map
| Member | Position |
|---|---|
| Contrarian | Six-sample instrument, unmeasured noise floor; pre-register similarity thresholds; snapshot the corpus |
| First Principles | n=100 first (0/5 CI reaches 45%); proof = two-arm specificity, not movement |
| Expansionist | The flip is run #1 of a template: frontier ledger, family tags, growth chart, versioned rulers |
| Outsider | "88% is fifty coin flips in a lab coat"; builder is the leak; who audits the tests? |
| Pragmatist* | ~7h run sheet: 150-pair pack, ORPO 1 epoch, prereg file, collision filter, abort criteria |

\* Renamed from "The Executor" on 2026-07-25.

---
Full responses: `council-transcript-2026-07-25_0317.md` · Channel record: instructions.txt §8
*(Backdated .md conversion of the original HTML report, per proprietor mandate.)*
