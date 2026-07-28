# Council Report — srlm-forge — THE PHD, properly spawned

**Session:** 2026-07-28 ~05:04-05:07 — activations #13 (remaining Q2/Q3) + #14, closed
together. Logged in `instructions.txt` as §43.
**Trigger:** proprietor asked to re-run everything since §38 with the PhD's actual
research and guidance. This round fixed the process gap from §38: a real `opus`
sub-agent was spawned via the `Agent` tool with `WebSearch`/`WebFetch` access, rather
than the council session answering in his voice on its own model. Both browser research
seats (ChatGPT/Gemini, ports 9222/9223) were down this round — literature search ran on
`WebSearch`/`WebFetch` only.
**Scope:** `instructions.txt` (live DIRECTIVE + §37-§42), `forge.py`, `eval.py`,
`build_training_set.py`, `dataset_gate.py`, `verify_dataset.py`, `measure.py`,
`OPEN-ITEMS.md`, `localllm/data.py`, `localllm/leakage.py`, `localllm/exp_lr_width.py`,
`data/eval_history.jsonl`, `data/dpo_pairs*.jsonl` — all confirmed unchanged between the
DIRECTIVE's pinned commit `d8e6b4b` and the working tree (`git diff --stat` empty).

## Key numbers

- **The eval ruler is saturated:** 6 of 10 held-out tasks scored a perfect 5/5 in
  **all 57** logged eval runs; pass@3 was the same number (0.90) in 55 of 57. Total
  headroom to ceiling: **0.1221**, of which **0.100 is one task (`rotate`)** — which
  fails because `rotate([], 2)` raises `ZeroDivisionError`, not because it's hard.
- **The published noise floor is wrong by ~2.1x.** `~0.009 std / ±0.03` (quoted
  everywhere, including the public GitHub README) came from a hardcoded 3-run sample.
  Over all 57 runs on disk: **sd = 0.0197**, honest single-run-vs-single-run 95% bar =
  **±0.055**.
- **The reward is gameable, demonstrated:** an object with `__eq__` that always
  returns `True` passes every `==`-based test assertion in the task suite (verified
  against two real task bodies). The banned-import filter also has real gaps
  (`from subprocess import run`, `import pathlib`, `import pickle`, `import asyncio`
  all pass it) and `-I`'s only actual defense (blocking `PYTHONOPTIMIZE` from
  stripping every `assert`) is undocumented and accidental.
- **The dataset cap's own rationale doesn't hold up measured:** it cost 25.6% of the
  data (316 pairs) to buy 1.07 "effective tasks" (entropy-based); adding 5 new tasks
  at 30 pairs each would buy 2.7x that gain while adding data instead of deleting it.

## The verdict

Task distribution is *a* ceiling but not the *binding* one — the ruler and the reward
are. Diversifying tasks before fixing the reward's integrity and the ruler's saturation
would produce a number nobody could trust in either direction. Full ranked findings
(10 total), a complete audit of §38-§42's own claims, mandatory non-claims, leftover
risks, and one recommended next prompt are in `instructions.txt` §43 — not duplicated
here to avoid two copies of the record drifting apart.

## The one thing to do first

Per §43's recommended next prompt: close the reward-integrity class (the `__eq__`
exploit, the banned-op filter gaps, and the receipt's missing coverage of the verifier
itself — currently it hashes only the data files, not `forge.py`) with three red
witnesses, *before* writing any new tasks — new tasks written today would inherit all
three holes. In the same commit, retire the `~0.009/±0.03` noise-floor figure
everywhere it's quoted, including the public repo, and replace it with the measured
57-run value.

## Alignment

| Seat | Position |
|---|---|
| THE PHD (solo, `opus`, real sub-agent) | Reward integrity and ruler saturation outrank the task-distribution question; both are fixable cheaply and should land before any new-task work |

No other seats ran (roster is PhD-only per §37/§39).

---
Full findings, self-verified citations (arXiv 2305.11206, 2308.01825, 2312.02120,
2502.01718, 2403.07974, 2210.11416, 2406.15877, 1902.10811, 2306.14898, 2411.00640,
2503.02951, 2406.12045; "Parse, don't validate"), and the complete recommended next
prompt: `instructions.txt` §43.
Full detail: `council-transcript-2026-07-28_0507.md`.
