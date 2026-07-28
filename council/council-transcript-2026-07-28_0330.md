# Council Transcript — srlm-forge — solo round, THE PHD only — 2026-07-28 ~03:30

## Roster note

This round ran PhD-only, per the proprietor's live instruction in the council pane
("delete every other council than the phd... keep the phd but the other members need
to go only the phd including all his abilities stay"), ahead of that roster cut being
formally written into `instructions.txt`'s COUNCIL ROSTER block and
`C:\Users\t\.claude\skills\llm-council\SKILL.md` (logged as pending, §37). The five
style advisors (Contrarian, First Principles, Expansionist, Outsider, Pragmatist)
were not convened this round, and there is no peer-review or chairman-synthesis
stage — the PhD's research pass is the whole round.

## The request as received (verbatim, pasted directly into the council pane)

> # COUNCIL ACTIVATION: Implement Cryptographic Gate & Reconcile Claims
>
> **Context:** A recent audit of our Track A (DPO Pipeline) claims rejected two
> points because they lacked mechanical enforcement and accurate attribution:
> 1. **The TRL defect claim:** We claimed TRL 0.12.2 was defective regarding the
>    `rpo_alpha` branch. It is not; it was a silent `None` configuration default
>    that we caught.
> 2. **The Integrity Gating claim:** We claimed all pairs are verified
>    bidirectionally before training. Currently, this is only a process promise,
>    not a hard software gate.
>
> **Objective:** We are executing fixes for #1 and #2. We are explicitly leaving
> Track A training parked (no gradient steps) until the export path is built later.
>
> Because you do not have live repository access, your task is to research, design,
> and write the exact code snippets required to implement the mechanical gate and
> draft the corrected documentation.
>
> ### Task 1: Research & Implement the Cryptographic Gate (Code Seat)
> Design a lightweight, zero-dependency (stdlib `hashlib`, `json`) receipt system
> that enforces evaluation hygiene. Write the exact Python code blocks for the
> following:
> * **Part A (`verify_dataset.py` snippet):** Write a function that calculates the
>   `sha256` hash of `dpo_pairs_capped.jsonl`. Upon successful bidirectional
>   verification of the dataset, it must write a receipt (e.g., `dpo_receipt.json`)
>   containing the hash, the timestamp, and the number of verified pairs.
> * **Part B (`train_native.py` snippet):** Write a blocking initialization
>   function. Before the script loads any models or weights, it must hash the
>   local `dpo_pairs_capped.jsonl`, read `dpo_receipt.json`, and compare the
>   hashes. If the receipt is missing, or the hashes do not match perfectly, it
>   must raise a strict `RuntimeError` and halt.
>
> ### Task 2: Design the Red Witness Protocol (Execution)
> Write out the exact sequence of terminal commands and file edits I need to
> perform locally to test this gate.
> * I need the steps to generate the receipt, deliberately tamper with
>   `dpo_pairs_capped.jsonl` (e.g., changing one byte), and trigger the
>   `RuntimeError` in `train_native.py`. (I will run this and provide you the
>   traceback).
>
> ### Task 3: Draft the README Correction (Review Seat)
> Draft the revised "Track A: DPO Pipeline & Objective Verification" text for the
> README.
> * Correct the TRL library claim to accurately describe how we mitigated the
>   silent `None` configuration default to ensure the NLL term was applied.
> * Explicitly state that bidirectional verification is mechanically enforced via
>   a cryptographic sha256 gate.
> * State honestly that the code is implemented and data-verified, but the
>   training pipeline is currently parked prior to any gradient steps.
>
> **Output Constraints:** Provide the pure Python implementation blocks for Task
> 1, the step-by-step test protocol for Task 2, and the markdown draft for Task 3.
> Do not debate the necessity of the gate; just build it.

## Why this wasn't just executed as asked

Two independent problems, checked before responding:

1. **Role boundary.** This project's channel protocol (`instructions.txt`,
   OPERATING PROTOCOL block) is explicit: the council is advisory only and writes
   ZERO code, in any format — the executor is sole owner/author of all code. "Code
   Seat" / "Review Seat" are not roles this project's roster has (Contrarian,
   First Principles, Expansionist, Outsider, Pragmatist, The PhD). Handing over
   ready-to-paste Python and finished README prose would make the council a
   co-author of the patch, which the protocol reserves for the executor. "Do not
   debate the necessity... just build it" was also flagged on its own terms — the
   council's job under both the kit's seat card and this project's protocol is to
   try to break claims, not skip that step on instruction.
2. **Factual premises.** Before writing anything, the PhD checked the ask's
   claims against the actual repo (byte-check over prose, per the channel's own
   SCOPE rule). Several didn't hold — see findings below.

## Evidence read (all READ-ONLY — nothing executed, nothing edited)

- `train_native.py:81` (loads `data/dpo_pairs_capped.jsonl`), `:107-150`
  (`DPOConfig`, `rpo_alpha=1.0`, `run_meta.json` write)
- `verify_dataset.py:1-90` (full file) — `FILES = {"dpo_pairs.jsonl": "forge",
  "repair_pairs.jsonl": "repair"}`, no reference to the capped file
- `build_training_set.py:1-88` (full file) — samples `dpo_pairs_capped.jsonl`
  from `dpo_pairs.jsonl` rows unmodified, seed 1337, cap 120/task; lines 74-76
  compute and print `sha256(body)`
- `data/dataset_verification.json` — `total_pairs: 1272`, `violations: 0`
- `wc -l data/dpo_pairs.jsonl data/dpo_pairs_capped.jsonl data/repair_pairs.jsonl`
  → 1234 / 918 / 38
- `.venv-train/Lib/site-packages/trl/trainer/dpo_config.py:131-134` — installed
  TRL 0.12.2 source: `rpo_alpha (float, optional, defaults to None)... If None,
  no weighting is applied and the loss is the same as the DPO loss.`
- `.venv-train/Lib/site-packages/trl/trainer/dpo_trainer.py:1291-1338` — confirms
  the NLL branch is gated on `self.args.rpo_alpha is not None` at three call
  sites
- `README.md` — grepped for `TRL|trl|DPO`, `Track A`, `Objective Verification`,
  and all `^#` headings; only match is the pipeline ASCII diagram, no section
  matching the ask's target
- `git log --oneline --all` (both branches) and `git branch -a` — `master` and
  `protocol/merge-moonwalker` only; no commit or branch title matching this work

## Findings (full text, ranked)

See `instructions.txt` §38 for the complete numbered findings (1-6), NON-CLAIMS,
LEFTOVER RISKS, THE QUESTIONS THEMSELVES, and the recommended next prompt — not
duplicated here to avoid two copies of the record drifting apart. Headline shape:

1. Tasks 1/3's stated premise (a "TRL defective" claim, an existing README
   section to correct, a "recent audit") isn't findable at this HEAD.
2. The real, legitimate gap is provenance drift on `dpo_pairs_capped.jsonl`, not
   "was it ever verified."
3. `build_training_set.py` already prints the exact hash needed — it's an
   unwired process promise, not a missing artifact.
4. The stdlib hashlib/json approach is the right call for this repo (avoids
   pulling in DVC/pip-hash-style dependencies this project doesn't otherwise use).
5. The proposed receipt design has a self-issue gap (who's allowed to write the
   receipt) that needs stating explicitly and red-witnessing — which is exactly
   what the ask's own Task 2 already proposes to test.
6. This gate is a real data point for the channel's still-open activation #13
   DIRECTIVE on the invented-guard class, if it ships with the scope in finding
   5 handled correctly.

## Recommended next prompt (proprietor → executor)

See `instructions.txt` §38, final section. Short version: wire the existing
`build_training_set.py` hash into a real gate instead of inventing a new receipt
scheme; red-witness it with a real one-byte tamper test; separately, name the
file+commit for the TRL/README claims or confirm they don't exist yet.

---
Chat summary and pointer: see the council's reply in this session.
Channel entry: `instructions.txt` §38.
