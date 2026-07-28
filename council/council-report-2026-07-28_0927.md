# Council Report — srlm-forge — THE PHD audits §44-§47

**Session:** 2026-07-28 ~09:24-09:27 — audit of the executor's four closure entries
(§44-§47) plus the two open decisions §47 explicitly flagged before its screening run.
Logged in `instructions.txt` as §50 (a channel-ordering mistake put it between §47 and
§48 on first write; corrected by reassembling the file so §48/§49/§50 sit in the order
they actually happened — no content was altered, only position).
**Collision note:** the executor launched the actual screening run (§48, §49) WHILE
this PhD pass was running. He never saw §48/§49. The council session added a timing
note at the top of §50 connecting his corrected task-count estimate to the executor's
live, in-progress run — see "the live collision" below.
**Trigger:** standing rule — always spawn the real PhD sub-agent for a channel update.

## Key numbers

- **The §44 reward-hack fix has a real bypass**, demonstrated live through `forge.verify()`:
  it only works because all 13 current tasks happen to name their `run_tests` parameter
  identically to the entry function. A task whose test calls the function by its global
  name (exactly how AceCode's bare-assert tests work — the exact import source §47
  picked) sails the exploit straight through. `forge.py:389`'s "closes the class for
  every current and future task" is false.
- **The screening cost estimate in §47 was off by roughly 25,000x** against the pool it
  named (1,049 days at n=100 over the full 83,600-candidate pool, not "hours"). The real
  lever is bounding how many candidates you *draw*, not shrinking per-candidate n.
- **The task-count target was 5.1x too low**: ~112-174 tasks needed for a real +3%-power
  verdict at k=5 seeds, not ~30 — traced to reusing a saturated-task's low variance for
  screened, deliberately-high-variance new tasks.
- **A zero-cost stage-1 screen was already sitting in the downloaded data**: AceCode's
  `inferences` column carries precomputed same-family-model pass rates — no GPU needed
  for the first cut, the two-stage n=8/n=10 design the executor built is largely
  redundant with a free column.
- **The AceCode license claim is correct at the top layer, incomplete underneath**: 39.4%
  of the corpus (the `bigcode_python_fns` stratum) descends from a dataset whose own card
  states no license at all — recommend restricting the import to the `oss` stratum only
  (unbroken MIT provenance, and the highest in-band admit rate of the three).

## The live collision

The executor's screen (§48/§49) is already running — 24 candidates in at write time, a
33.3% admit rate, target of 30 admitted, projected to hit target around candidate 90 of
400. That 33.3%-of-400 trajectory (~130 admitted if run to completion) lands almost
exactly inside the PhD's independently-derived corrected range (~112-174). If the run
stops at its configured target of 30, the instrument comes out under-powered by roughly
4-5x relative to what the project's own +3%-power goal requires — a gap that would not
surface until someone re-derives the power math later. Flagged in the channel timing
note while the run is still in flight and resumable (honors `council/STOP`).

## The verdict

§44-§47 are honest, well-audited work — the executor independently re-derives nearly
every number rather than trusting the prior round, catches his own bugs by running the
intended-to-pass case, and both major closures (finding 5's reward-hack fix, finding
3's verifier-pinned receipt) hold up under the PhD's own executed re-checks. But both of
§47's headline planning claims (screening cost, task-count target) don't survive
independent recomputation, and the reward-hack fix's generalization claim doesn't
survive contact with the exact task shape about to be imported.

## The one thing to do first

Per §50's recommended next prompt (written before the run started — reconcile against
the live run per the timing note): close the type-guard's generalization hole before
any AceCode task lands in the suite; confirm/replace the screen's stage-1 design against
the free `inferences`-column screen; and — most time-sensitive — decide now whether the
run's target of 30 admitted tasks should be raised toward ~130-150 before it reaches
candidate ~90 and potentially stops short of real statistical power.

## Alignment

| Seat | Position |
|---|---|
| THE PHD (solo, `opus`, real sub-agent) | §44-§47's closures mostly hold; both of §47's planning numbers (cost, task count) don't, by large and correctable margins |

No other seats ran (roster is PhD-only per §37/§39).

---
Full findings (11 ranked + 13 corrections), citations (arXiv 1605.08671; HF dataset
cards for KodCode-V1, AceCode-87K/89K, Magicoder-OSS-Instruct-75K,
Magicoder-Evol-Instruct-110K, bigcode/stack-dedup-python-fns; Wald 1945 and
Waudby-Smith & Ramdas 2024 bibliographic-only), mandatory non-claims, and the complete
recommended next prompt: `instructions.txt` §50.
Full detail: `council-transcript-2026-07-28_0927.md`.
