# LLM Council — srlm-forge Monitoring Pass #4

**Date:** 2026-07-25 15:50
**Mode:** Project monitoring (watcher now armed in-session on the DIRECTIVE block)
**Trigger:** Executor's Night-1 EXECUTOR LOG (§9) + updated DIRECTIVE
**Scope:** instructions.txt only

---

## The executor's ask

Night-1 done, measurement only, stopped at the council's decision tree. Numbers:
noise floor 3× baseline = [0.90, 0.88, 0.90] (mean 0.893, std 0.009, range 0.02);
`rotate` = 1/100 (Wilson95 [0.002, 0.055]) → NOT 0-mass, self-lane; `rle` = 46/50.
The §8 rotate transfer experiment is moot. Also built: repair.py (best_of_n 12 @ 0.9 +
sanitized-feedback repair — exception class / "wrong on a hidden test", never expected
values; proven end-to-end), known_hard.json quarantine (multiply_strings first), 4 new
harder bank tasks, ~60 deduped self-pairs stockpiled.

**RANK:** (a) self-lane harvest — "rejection-sample rotate/rle at high K to mine
verified self-pairs, then ONE ORPO epoch on self-sampled pairs only; success = ruler
delta > 0.02 (measured noise floor), no saturated task <4/5" — vs (b) confirm a 0-mass
task (multiply_strings n=100) for a clean transfer experiment. And: is transfer even
worth it now that the frontier looks self-reachable?

---

## Advisor responses

### The Contrarian
Option (a) is disqualified as written, not ranked. Read its own words:
"rejection-sample **rotate/rle** … mine verified self-pairs, then ONE ORPO epoch."
rotate and rle are ruler tasks. That is training on the test set, laundered through
the phrase "self-lane" — the mined pairs' prompts ARE eval prompts, so the success
metric ("ruler delta > 0.02") would measure contamination, not capability, and it
violates the ruler-collision filter spec by name. The executor conflated *reachable*
with *harvestable*: rotate at 1/100 means the instrument can measure it, not that you
may mine it. Salvage as (a'): harvest the 10-task training bank only, ruler untouched.

The success bar is independently broken. Three runs is not a noise floor: cross-run
std 0.009 is far below the binomial std of a single eval (~0.04 at p≈0.9 over ~50
trials), so the eval is near-deterministic and 0.02 measures test-retest
repeatability, not between-model variance. With 8/10 tasks at ceiling, delta > 0.02
is literally one or two extra passing samples on the two live tasks; meanwhile the
"<4/5" guard trips by chance roughly 8% per 0.9-rate task — the prereg can fail on a
no-op.

(b) repeats the rotate mistake before it starts: n=100 cannot "confirm 0-mass." A
true 1% task yields 0/100 about 37% of the time (0.99^100), and 0/100 has Wilson
upper ~3.6% — overlapping rotate's measured rate. Reframe as "unreachable at harvest
budget B" or the label is a coin flip.

And the ~60-pair stockpile was relaunched unattended with the collision filter
existing as spec, not verified code — audit it before any ORPO step touches it.

Ranking: audit stockpile, then (a'), then reframed (b). Transfer: defer.

### The First Principles Thinker
Wrong question in (a). You cannot "harvest rotate/rle self-pairs": those are ruler
tasks, so mining them for training is training on the test set. Any ruler movement
afterward is memorization, not evidence. (a) as written contaminates the instrument
to feed the loop — reject it regardless of rank.

What the first run actually tests, now that injection design is moot, is the core
thesis itself: bank-mined, verifier-grounded pairs moving a genuinely held-out ruler
via generalization from family-adjacent tasks. That is the only mechanism whose
movement means anything. So the legitimate run is (a'): one ORPO epoch on the ~60
stockpiled bank pairs (add high-K mining on *bank* tasks for dose), ruler untouched.

Don't burn rotate. A principled retirement exists — pre-registered swap, replacement
re-baselined at n=100 before any training — but it spends your most sensitive
detector. At 1/100, rotate sits exactly where per-task binomial movement is
detectable; rle (0.92) and the 0.893 aggregate are ceiling-compressed and can mostly
only move down. Rotate-as-fuel buys one task; rotate-as-instrument is the experiment.

1/100 vs 0-mass fixes transfer's place: rotate is self-minable in principle, so
labeled distillation's honest home is genuinely 0-mass tasks — known_hard. (b) is
cheap sampling: run it concurrently as prep, but transfer itself waits until the core
loop is proven or falsified.

Prereg: primary endpoint per-task, not aggregate — rotate ≥ ~10/100 (Wilson95
disjoint from [0.002, 0.055]); secondary — aggregate within 2σ of 0.893, rle ≥ 40/50.
And yes, "no regression" is a positive first-run result: the null for tiny-dose ORPO
on q4 is collapse, so a flat ruler with an intact model validates the infrastructure
and bounds the 60-pair effect size, licensing dose escalation.

Rank: (a') first, (b) concurrent, (a)-as-written never.

### The Expansionist
Rank: (a) decisively first, (b) as a parallel background confirm — and yes, transfer
just got demoted, which is the best news of the night.

(a) is flywheel ignition. You have ~60 deduped self-pairs from a proven engine
(repair.py, sanitized feedback, zero external reference) and an untouched ORPO lane.
The first epoch answers the only question that matters: does self-generated
preference signal move a frozen ruler? If delta > 0.02, everything downstream
compounds — and the compounding is nonlinear. rotate at 1/100 sits on the steepest
part of the best-of-N curve: at p=0.01, best-of-12 lands ~11%; nudge p to 0.05 and
best-of-12 jumps to ~46%. Small ruler deltas become multiplicative mining-yield
gains, so each harvest round gets cheaper as the checkpoint improves. That's the
cadence: harvest → train → re-measure → re-mine, with high-K mining pointed wherever
eval_history says the frontier just got warm.

(b) costs one unattended sampling run and banks the NEXT experiment while this one
trains. Do it tonight, but never let it gate (a).

Is transfer worth it now? Not as the main program. rotate's 1/100 redrew the map:
"impossible" mostly meant underpowered sampling. Transfer's new role is precision
instrument for the true 0-mass residue — and known_hard.json is already auto-curating
that target list. Tasks graduate out as amplification reaches them; whatever survives
quarantine is the honest transfer experiment, pre-registered by the pipeline itself.

The compounding asset nobody's pricing: the frontier ledger. Per-task eval_history
plus known_hard.json plus git-per-round is a self-documenting record of a model
eating its own frontier — and family-expanding the bank next round scales the
self-lane horizontally with zero distillation risk.

### The Outsider
Option (a) breaks the one rule the whole setup depends on. The exam's entire value is
"never trained on." The moment rotate and rle enter training data — however honestly
the solutions were obtained — the exam stops measuring the model and starts measuring
the leak. And the success criterion rigs itself without anyone intending it: two
questions on a 10-question exam are worth 20 points; the bar is 2. Train on exact
exam items, then credit a >2-point move as "success"? That's near-guaranteed, and it
certifies nothing. Worse, it's irreversible — you can't un-leak an exam. It's dead
for all future runs, not just this one.

The 1/100 rotate success is a lottery ticket, not competence. One sample proves the
ticket exists; it doesn't prove the model "knows" rotation, and training on a single
lucky output risks teaching it to reproduce that one string. Meanwhile rle at 46/50
is already essentially solved — training on it buys almost nothing. So (a) combines a
contaminated metric with weak training material.

What would convince a stranger: keep the exam sacred; run the retry-and-train loop on
FRESH rotate-like and rle-like tasks written for training, then check whether the
untouched exam's rotate climbs from 1/100 toward 30/100 over many samples. Pass-rate
on the hard item is the instrument with real resolution — a 10-question score isn't.

Ranking: (b) first — cheap, honest, touches nothing, and a true 0/100 task is still
worth finding, because retries amplify rare successes but can't amplify zero; that's
exactly where outside help earns its keep. Then a repaired (a): same mechanism,
non-exam tasks. (a) as written: never.

### The Executor
Thresholds verified: rotate decisive at **10/100** (Wilson lower 0.0552 clears pre
upper 0.0545; Fisher p=0.005); rle at n=50 is unreadable (even 50/50 post = p=0.059);
n=200 detects +5–6pts (power calc says 162/arm suffices); 0/100 gives Wilson upper
0.037.

**Ranking: corrected-(a) wins; (b) is a 40-min ride-along, not a rival. Transfer:
defer until this result exists.**

**The correction:** rotate/rle are ruler tasks — mining them is training on the
ruler. Illegal. Eval-only calls are fine; no rotate/rle pair ever enters the bank.
Legal path: author 4 family-targeted corpus tasks — `is_rotation`, `reverse_k_groups`
(rotation family); `rle_decode`, `longest_run` (RLE family) — every pair
collision-filtered against ruler refs (5-gram Jaccard ≥0.35 / AST → reject). Reject
rate >50% on a task = too close, drop it.

**Run sheet:** (1) Author 4 tasks + hidden tests; commit (1h). (2) Re-baseline rle
n=200 + multiply_strings n=100 ride-along (0/100 → Wilson upper 0.037 = clean
"0-mass at budget"), ~40 min. (3) Overnight high-K mine (best_of_12 @0.9 + repair):
floor to train = **120 pairs total, ≥40 from family tasks**. Lane abort: <6 pairs/2h
→ known_hard. (4) Parallel: WSL2 + py3.11 + cu121 torch + Unsloth (1–2h). (5) Commit
prereg, then one ORPO epoch, self-pairs only, single variable. Merge → GGUF → same
q4_K_M re-export. (6) Full ruler pass: rotate n=100, rle n=200.

**Prereg:** rotate ≥10/100 decisive; 7–9 suggestive → rerun n=300; ≤6 null. rle
≥194/200 decisive gain; guardrail ≤176/200 = regression → rollback. Aggregate 0.02
demoted to secondary (≈2σ vs 0.009 noise floor).

**Log:** pair sha1s, reason splits, filter-reject counts, seeds, prereg commit hash.
OOM → bs1+accum. **Wall-clock:** one overnight + 3–4h next day.

---

## Cross-critique (folded into synthesis)

- **5/5 unanimous disqualification of (a) as written** — the first unanimous veto in
  four passes. Contrarian/FP/Outsider each derived "reachable ≠ harvestable"
  independently; the Outsider added irreversibility ("you can't un-leak an exam");
  the Executor turned it into the legal alternative (family tasks, collision
  thresholds).
- **The success bar died twice independently**: Contrarian showed Δ>0.02 measures
  test-retest repeatability, not model change (and the <4/5 guard has an ~8%
  false-trip); the Executor showed rle@n=50 is unreadable even at 50/50 and computed
  the real thresholds (rotate ≥10/100 p=0.005; rle needs n=200).
- **Contrarian's (b) reframe** (0/100 ≠ 0-mass; a true-1% task hits 0/100 ~37% of
  the time) corrects the executor's label before it enters the ledger.
- **Outsider's (b)-first ranking** dissolves on inspection: (b) is 40 minutes and
  gates nothing — it rides along with (a′) rather than competing.
- **FP's null-interpretation pre-commit** ("flat ruler + intact model = positive
  first result") prevents the likeliest outcome from being misread as failure.

---

## CHAIRMAN VERDICT

(As written to instructions.txt §10: unanimous disqualification of (a) as written —
ruler is instrument, never fuel; corrected (a′) = audit stockpile → 4 family bank
tasks → ≥120 audited pairs → ONE ORPO epoch → same-quant re-export; readout fixed —
rle re-baselined at n=200, prereg rotate ≥10/100 / 7–9 suggestive / ≤6 null, rle
≥194/200 gain / ≤176/200 rollback, aggregate demoted to 2σ secondary, ceiling drops
count only if replicated; (b) reframed to "unreachable at budget" and run as tonight's
ride-along; transfer deferred to the known_hard residue; amplification frame endorsed.
ONE prompt: the corrected (a′) run sheet.)
