# Council Report — srlm-forge — solo round, THE PHD only

**Session:** 2026-07-28 ~03:30 — ad-hoc activation, not a numbered activation off the
channel's live DIRECTIVE. Logged in `instructions.txt` as §38.
**Trigger:** proprietor pasted an outside request ("COUNCIL ACTIVATION: Implement
Cryptographic Gate & Reconcile Claims") directly into the council pane and asked the
PhD to research it and relay findings to the executor via the channel. Roster for this
round: PhD only, per the proprietor's standing instruction to cut the roster down to
the PhD (logged as pending in §37 — the five style advisors and SKILL.md were not
invoked this round).
**Scope:** the ask's named files (train_native.py, verify_dataset.py, README.md,
dpo_pairs_capped.jsonl) plus whatever else was needed to check its premises — no
commit hash was supplied with the ask, so everything below is READ-ONLY against
current HEAD, not a ruling on a pinned version.

## Key numbers

- verify_dataset.py currently checks **1,272 pairs** (`dpo_pairs.jsonl` 1,234 +
  `repair_pairs.jsonl` 38), **0 violations** (`data/dataset_verification.json`).
- `data/dpo_pairs_capped.jsonl` = **918 rows**, sampled from `dpo_pairs.jsonl` by
  `build_training_set.py` (seed 1337, cap 120/task) — **never itself read by
  verify_dataset.py**.
- `build_training_set.py:74-76` **already computes and prints a sha256** of the
  capped file's exact bytes — this is the artifact the ask wanted built from scratch.

## The verdict

**The ask's stated premises don't hold at this HEAD:** no evidence of the described
"recent audit," the TRL rpo_alpha comment in `train_native.py:115` already frames it
as a documented config default (verified against the installed TRL 0.12.2 source),
and README.md has no "Track A" section to correct.

**The underlying instinct — a mechanical gate — is legitimate**, but the real gap is
narrower than described: it's provenance drift (has the capped file silently diverged
from what was last verified), not "were the pairs ever checked." And the fix mostly
already exists: `build_training_set.py` prints the exact hash needed; it's a manual
process promise today, not a wired gate.

**No code or README text was produced.** Per this project's protocol the council
writes zero code regardless of format — chat text that could be pasted directly into
the repo is still code. Design guidance and prior art were given instead; see §38 for
the ranked findings.

## The one thing to do first

Wire `build_training_set.py`'s existing sha256 into a real gate (write receipt only
on a clean `verify_dataset.py` pass; check it at the top of `train_native.py`'s
`main()`; hard-fail with `RuntimeError` on mismatch) — then red-witness it for real:
tamper one byte, confirm the refusal, keep the traceback. Full recommended prompt is
in §38.

## Alignment

| Seat | Position |
|---|---|
| THE PHD (solo this round) | Ask's premises don't match HEAD (Tasks 1/3 as framed); the gate itself is a real, narrower problem with a prior-art answer already sitting in the repo (finding 3) |

Five style advisors did not run this round (roster cut to PhD-only, pending §37).

---
Full findings, evidence list, and the recommended next prompt: `instructions.txt` §38.
Full detail: `council-transcript-2026-07-28_0330.md`.
