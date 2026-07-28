# Council Transcript — srlm-forge — THE PHD, properly spawned — 2026-07-28 ~05:04-05:07

## Roster and mechanism note

This round corrects a process gap from the previous solo round (§38 / the earlier
transcript `council-transcript-2026-07-28_0330.md`): there, the council session
answered directly, in its own voice, on its own model (Sonnet 5) — not the PhD as the
skill actually specifies him (a dedicated `opus` sub-agent with `WebSearch`/`WebFetch`).
This round fixed that. The council session spawned a real sub-agent via the `Agent`
tool with `subagent_type: general-purpose`, `model: opus`, `run_in_background: true`,
carrying the PhD's role definition, hard rules (advisory only, zero code, self-verify
every citation against its primary source, mandatory NON-CLAIMS since there are no
peer seats to catch what he missed), full read scope, and both open DIRECTIVEs
verbatim.

Both browser research seats were confirmed down before the agent was briefed
(`mcp__seat-a-chatgpt__list_pages` and `mcp__seat-b-research__list_pages` both returned
`Could not connect to Chrome` — ports 9222/9223 not listening). The agent was told not
to attempt them and to rely on `WebSearch`/`WebFetch` only.

## The brief given to the PhD (paraphrased; full prompt not reproduced verbatim here)

Both currently-open channel DIRECTIVEs, in full:

- **Activation #13, remaining open items** (Q1 was already answered in principle by
  §38 finding 6 / §41's scope-based gate design): Q2 — what should `split_health`'s
  eyeballed `achieved >= requested * 0.5` tolerance be derived from, given a
  document-level split on a lumpy corpus can't hit an arbitrary fraction; is deleting
  the boolean gate entirely the right move? Q3 — the sweep for other guards with an
  invented threshold or invented scope elsewhere in the repo, including the
  DIRECTIVE's own named candidate (the new `dataset_gate` is "a chokepoint by
  convention, not by construction").
- **Activation #14** ("is the task distribution the actual ceiling?"): 1,234 verified
  pairs come from 13 LeetCode-shaped tasks; top 3 are 54.0% of the set. Q1 — is there
  published guidance on diversity (distinct tasks) vs volume (pairs per task) for
  execution-feedback preference learning? Q2 — what can "tangible, not just math" mean
  without breaking the deterministic-pure-function reward (parsing/validation/text
  transforms/data reshaping/business logic was the executor's own candidate frontier) —
  does the literature support going further, to I/O-shaped tasks with mocked
  boundaries? Q3 — `eval.py`'s frozen held-out set is confirmed disjoint from the
  training tasks by id but is *also* all algorithmic puzzles; if training diversifies
  but eval doesn't, does a real improvement risk reading as a null result? Move the
  ruler and re-baseline, or freeze it and accept a narrower question?

Required output shape: VERDICT, EVIDENCE READ, FINDINGS (ranked, each EXECUTED or
READ-ONLY, citations self-verified or labelled UNVERIFIED), CORRECTIONS TO THE ROUND
(inherited audit duty over §38-§42), NON-CLAIMS (mandatory, no peer seats), LEFTOVER
RISKS, THE QUESTIONS THEMSELVES, ONE recommended next prompt.

## Why this isn't duplicated here in full

The complete, verbatim response — all 10 ranked findings, the full evidence list, all
self-verified citations with their caveats, the corrections to §38-§42, the mandatory
non-claims, the 8 leftover risks, and the full recommended next prompt — was written
into `instructions.txt` as §43, which is the channel of record between the council and
the executor. Reproducing it here as well would create two copies of the same record
that could drift apart under future edits; this transcript exists to record the
*mechanism* of the round (what was asked, how, on what evidence-gathering budget) and
point at the one canonical copy.

## Headline shape (see §43 for the complete findings)

1. The eval ruler is empirically saturated — 6 of 10 held-out tasks pinned at a
   perfect score across all 57 logged runs; pass@3 nearly constant. This, not task
   diversity, is the binding ceiling, and it answers #14 Q3 in a different shape than
   either option the DIRECTIVE offered.
2. The published noise floor (`~0.009 std / ±0.03`, quoted in the channel, the local
   README, and the *public* GitHub README) is a hardcoded 3-run artifact; the honest
   figure from all 57 runs on disk is roughly 2.1x wider.
3. The dataset-integrity receipt (§39-41) hashes the data files but not `forge.py` —
   so it certifies bytes match a prior state, not that "verified" still means what it
   meant when the receipt was issued.
4. The DIRECTIVE's own claim that `-I` plus the banned-op filter blocks network and
   filesystem "on purpose" is false in both halves — demonstrated by running `python
   -h` and testing the actual regex against real import statements.
5. The reward is gameable today: a constructed `__eq__`-always-true object passes
   real task assertions, demonstrated against two live task bodies. Not claimed to be
   present in the existing dataset — that wasn't scanned this pass.
6. `split_health`'s tolerance ruling: delete the boolean; the deeper bug is that its
   diagnostics are computed on the pre-deduplication corpus while the actual split
   runs post-dedup, so the two numbers an operator is told to judge by describe a
   different corpus than the one that was split.
7. The task-diversity cap's own stated rationale doesn't hold up under an entropy
   measurement performed this pass — quantified in §43 finding 7.
8-10. A citation-backed frontier ruling for "tangible" tasks (mocked I/O boundaries,
   with real prior art on what's affordable at this project's scale), a construction-
   level fix for the gate chokepoint, and an enumerated (not exhaustive) sweep of
   other threshold/scope guards in the repo.

## Corrections to the round, headline

The PhD's inherited audit duty found two arithmetic notes in the executor's own
recent log (§40's "~1e-3" residual actually spans 0.0009-0.0023; §39/§41's pair-count
reconciliation checked out exactly) and one structural note in `OPEN-ITEMS.md` (an
entry's heading and body reference two different items' close status, readable as
"closed" by a skim-prune when it is not). Full text in §43.

## Recommended next prompt

See `instructions.txt` §43, final section — close the reward-integrity class (three
named red witnesses) before writing any new tasks, and retire the outdated noise-floor
figure everywhere it's quoted, including the public repo, in the same commit.

---
Chat summary and pointer: see the council's reply in this session.
Channel entry (complete, canonical): `instructions.txt` §43.
