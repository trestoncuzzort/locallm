# Council Report — srlm-forge · Pass #1

**Date:** 2026-07-25 02:44 · **Trigger:** manual (proprietor activation) · **Scope:** instructions.txt only
**Deliverable:** ranked critique of §4 open decisions (A–E) + one next prompt → written to channel §5

## The ask
First monitoring pass. Rank the executor's five open decisions: (A) data scale-up, (B) training
env, (C) DPO vs ORPO vs GRPO, (D) reward-hacking defenses, (E) loop closure / held-out eval.

## Key numbers
6 seed tasks · 3 DPO pairs total (2 correctness + 1 conciseness) · training never run · no eval exists

## Verdict

**Agrees (high confidence):**
- **No ruler, and the thesis is inverted.** The loop can "close" whether the model improved or
  drifted — nothing is falsifiable without a held-out eval. And all-fail tasks emit ZERO DPO
  gradient (a pair needs a passing `chosen`), so the pipeline trains on near-frontier
  *successes*, not failures. (3 advisors independently.)
- **Conciseness preference is a live reward-hack** — shorter-passing-weak-tests gets trained in.
  Gate or cap it; log the reason split every round.
- **Data volume, not the Python env, is the bottleneck.** 3 pairs trains nothing.
- **The durable asset is the verifier-grounded preference factory** — the 8B model is disposable.

**Clashes:**
- Self-generation vs stronger-teacher sourcing (Expansionist flywheel vs First Principles
  distillation) — deferred; depends on the actual goal.
- Measure-first (Contrarian) vs scale-first (Pragmatist) — resolved: eval wins, data run can
  parallel.

**Recommendation:** Build the frozen held-out ruler FIRST (30–40 tasks never used for pairs,
pass@k harness, record baseline), instrument the pairing step (reason split + all-fail ids),
THEN scale data (MBPP adapter) and build the WSL2/cu121 env (low priority). ORPO before GRPO;
avoid vanilla DPO's ref-model overhead.

## The one thing to do first
The frozen ruler + baseline pass@k. Until the ruler exists, everything downstream is
unverifiable.

## Alignment map
| Member | Position |
|---|---|
| Contrarian | Self-distillation ceiling; failures yield no gradient; conciseness = reward hack; build the ruler before the factory |
| First Principles | Env isn't the blocker; the verifier is the durable asset; source chosens from a stronger generator |
| Expansionist | Verified-preference factory is the moat; failures.jsonl = frontier map; stockpile data regardless of env |
| Outsider | "Self-rewarding" is a misnomer (tests reward, not the model); loop has never closed once |
| Pragmatist* | MBPP overnight for volume; py3.12+cu121 env in parallel; don't train below ~500 pairs |

\* Named "The Executor" in the original pass; renamed The Pragmatist on 2026-07-25 to avoid
collision with the project's EXECUTOR (the coder).

---
Full responses: `council-transcript-2026-07-25_0244.md` · Channel record: instructions.txt §5
*(Backdated .md conversion of the original HTML report, per proprietor mandate.)*
