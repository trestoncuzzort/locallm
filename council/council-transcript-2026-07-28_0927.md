# Council Transcript — srlm-forge — THE PHD audits §44-§47 — 2026-07-28 ~09:24-09:27

## A channel-ordering mistake, corrected

The council session's first write appended the PhD's §50 response between the existing
§47 and §48 instead of at the true end of the file — a mechanical slip, not a content
error. It was caught immediately by re-checking the numbered-section list, and the file
was reassembled (via a clean split-and-recombine, not a rewrite of any section's
content) so §48 → §49 → §50 sit in the order they actually happened. No section's text
was altered in the fix, only its position. Recorded here because the project's own
channel discipline treats "append, never silently reorder" as load-bearing, and this
is the correction being made visible rather than quietly fixed.

## Roster and mechanism

Standing rule as of this session: always spawn the real PhD (a genuine `Agent` tool
call, `subagent_type: general-purpose`, `model: opus`, real `WebSearch`/`WebFetch`) for
a channel-update review, rather than the council session answering inline. This round
did that. Both browser research seats (9222/9223) were confirmed down again before
briefing — literature search ran on `WebSearch`/`WebFetch` only.

## The brief given to the PhD

Four executor log entries to audit (§44-§47), each claiming to close findings from his
own prior round (§43):
- §44: closed the reward-hack finding with a real red witness through `forge.verify()`;
  corrected a noise-floor number from §43.
- §45: closed the receipt-scope finding — the sha256 receipt now covers the whole of
  `forge.py`, not just the data files, so changing the verifier itself invalidates it.
- §46: closed five more findings (the `split_health` corpus mismatch, the cap-isn't-the-
  skew-fix correction, the gate-chokepoint fix, transport-failure-scored-as-wrong-answer,
  timeout-scored-as-failure) — notably catching a bug in its own first attempt at the
  gate-coverage test by running the case expected to pass and watching it fail.
- §47: costed and sourced the one remaining item (a wider eval instrument to replace the
  saturated 10-task ruler) but did not yet run the screen. Flagged two explicit open
  decisions for PhD input: a two-stage screening design (n=10 then n=100) and whether to
  sample the candidate pool randomly or take the first N.

The PhD was told explicitly to treat his own §43 as a "peer's sealed prior work to
audit, not ground truth to assume correct" — the same discipline the executor had just
demonstrated by independently re-deriving §43's own numbers rather than trusting them.

## Why this isn't duplicated here in full

As with the previous round, the complete verbatim response — 11 ranked findings, 13
corrections to the round, all self-verified citations and their caveats, mandatory
non-claims, 10 leftover risks, and the full recommended next prompt — was written into
`instructions.txt` as §50, the channel of record. Reproducing it here in full would
create a second copy that could drift from the canonical one; this transcript records
the *mechanism and collision*, not a duplicate of the content.

## The live collision (why this round is time-sensitive)

While the PhD sub-agent was running, the executor independently launched the actual
screening job (§48, §49) — he never saw either. Two things the PhD found bear directly
on the live run and were surfaced in a council-session timing note prepended to §50,
ahead of his own text, so they'd be visible before being buried in the full response:

1. **Stage-1 rejection power.** The PhD's finding 3 shows a Wilson-CI-exclusion rule
   can't reject *anything* at n=10 (the minimum workable n is 16); the executor's actual
   run uses n=8, narrower still. Whether this matters in practice depends on whether
   `screen_tasks.py`'s stage-1 rule is a formal Wilson exclusion or a simpler "exact
   0/8 or 8/8" heuristic — the channel doesn't specify, and the PhD didn't read the
   script. Flagged as something to confirm, not a ruling.
2. **Task-count target.** The PhD's finding 4 independently derives a real requirement
   of ~112-174 movable tasks for a genuine +3%-power verdict at k=5 — a corrected 5.1x
   over §47's ~30. The executor's own §49 entry, written without knowledge of this
   correction, already projects the *live run* would yield ~130 admitted if allowed to
   run its full 400-candidate draw — landing almost exactly inside the PhD's corrected
   range. But the run's configured *target* is 30, and §49's phrasing ("far past what is
   needed") suggests it may stop there. If it does, the instrument would come out
   under-powered by roughly 4-5x relative to the project's own stated goal, and that gap
   might not be caught until someone re-derives the power math after the fact.

The council session's role here was pointing at the collision, not resolving it — the
timing note is explicit that this is "a pointer, not a ruling," and that the executor
should reconcile the two independently rather than the council instructing an action.

## Headline shape (see §50 for the complete findings)

1. The §44 reward-hack fix generalizes only by a naming coincidence (all 13 current
   tasks name their `run_tests` parameter identically to the entry function) and is
   demonstrated, live, to fail against the exact task shape (bare-assert tests calling
   the function by global name) that §47's own import source uses.
2. The screening plan's cost estimate was off by ~25,000x against the pool it named.
3. The two-stage screen as designed can't reject anything at n=10 — and a free,
   zero-GPU alternative was already present in the downloaded AceCode data (precomputed
   same-family-model pass rates in the `inferences` column).
4. The task-count target was 5.1x too low, traced to a variance mismatch between the
   saturated task the estimate borrowed from and the new, deliberately-high-variance
   tasks being screened for.
5. A selection-on-noise risk in reusing screening draws as the training/eval baseline
   (winner's-curse structure) — fix costs nothing if decided now.
6. Random sampling (not first-N) is confirmed correct with hard evidence: the AceCode
   corpus is perfectly blocked by source with zero interleaving.
7. The license check holds at the top layer; one layer down, 39.4% of the corpus
   descends from an unlicensed upstream — recommend restricting the import to the one
   stratum with unbroken MIT provenance.
8-11. Receipt-scope residue (the verifier hash still doesn't cover `verify_dataset.py`'s
   own violation-defining function), an estimator-choice non-error in §44's own
   "correction," a self-corrected mistake in the PhD's own prior round, and an
   overclaim on the screening criterion's contamination-filtering side effect.

## Recommended next prompt

See `instructions.txt` §50, final section — written before the screen had launched,
so it reads as "do not start the screen" where the live state is now "already running."
The council session's timing note above the PhD's response in §50 is the reconciliation
pointer; the executor decides how to actually proceed.

---
Chat summary and pointer: see the council's reply in this session.
Channel entry (complete, canonical): `instructions.txt` §50.
