# Council Report — srlm-forge · Pass #4

**Date:** 2026-07-25 15:50 · **Trigger:** executor's Night-1 log (§9) · **Scope:** instructions.txt only
**Deliverable:** self-lane vs transfer ranking → written to channel §10 · DIRECTIVE watcher armed this pass

## The ask
Night-1 flipped the plan: rotate = **1/100** (NOT 0-mass → self-lane), rle = 46/50, noise floor
±0.02 (3 runs). Rank: (a) self-lane harvest — "rejection-sample rotate/rle at high K, mine
verified self-pairs, one ORPO epoch; success = ruler Δ > 0.02" — vs (b) confirm a 0-mass task
(multiply_strings n=100) for a clean transfer experiment. Is transfer even worth it now?

## Key numbers
rotate 1/100 (Wilson95 [0.002, 0.055]) · rle 46/50 · ~60 pairs stockpiled · veto 5/5

## Verdict

**THE HEADLINE — first unanimous veto in four passes:**
**Option (a) as written is disqualified, not ranked.** rotate and rle are RULER tasks. Mining
them for training pairs is training on the test set, laundered through the phrase "self-lane" —
the post-training "delta" would measure contamination, and an exam cannot be un-leaked.
**Reachable ≠ harvestable.** Rotate-as-fuel buys one task; rotate-as-instrument is the
experiment. (Eval-only sampling of ruler tasks stays fine.)

**Corrected run (a′):** audit the stockpile (accrued unattended; collision filter was spec, not
code) → author 4 family-targeted BANK tasks (is_rotation, reverse_k_groups, rle_decode,
longest_run; collision-filtered, >50% rejects = drop) → mine the expanded bank with repair.py to
≥120 pairs → ONE ORPO epoch → same-quant re-export.

**Success bar fixed (it was broken twice):**
- Δ>0.02 is test-retest repeatability, not model variance; aggregate demoted to secondary.
- rle at n=50 is UNREADABLE (even 50/50 post = p=0.059) → re-baseline at n=200.
- Prereg: rotate ≥10/100 decisive (p=0.005) / 7–9 suggestive / ≤6 null; rle ≥194/200 gain,
  ≤176/200 rollback; ceiling drops count only if replicated ×2.
- **Flat-but-intact = positive** for a first-ever run (the realistic null is collapse).

**(b) reframed:** n=100 cannot "confirm 0-mass" (a true-1% task returns 0/100 ~37% of the
time). Honest label: "unreachable at harvest budget." Run multiply_strings n=100 as a
ride-along; transfer deferred to whatever survives known_hard quarantine.

## The one thing to do first
Audit the ~60-pair stockpile — sha1 dedup verified, provenance present, collision filter as
running code, eyeball 10. Nothing trains until the fuel is clean.

## Alignment map
| Member | Position |
|---|---|
| Contrarian | Veto: test-set training laundered as "self-lane"; Δ>0.02 measures repeatability; audit the stockpile |
| First Principles | Veto: rotate-as-fuel vs rotate-as-instrument; null = positive first result; per-task prereg endpoints |
| Expansionist | (a′) = flywheel ignition; amplification not implantation — p 0.01→0.05 ≈ 4× mining yield |
| Outsider | Veto: "you can't un-leak an exam"; 1/100 is a lottery ticket; success bar rigs itself |
| Pragmatist* | Verified thresholds (rotate ≥10/100 p=0.005; rle needs n=200); 4 family tasks; 120-pair floor; ~1 overnight |

\* Renamed from "The Executor" on 2026-07-25.

---
Full responses: `council-transcript-2026-07-25_1550.md` · Channel record: instructions.txt §10
*(Backdated .md conversion of the original HTML report, per proprietor mandate.)*
