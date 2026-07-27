# srlm-forge Council — Report

**Activation #12** · 2026-07-26 ~19:35 · DIRECTIVE-triggered (re-run after the PhD's first attempt was cut off by an API session limit; also recovered from a brief git branch mix-up that made `instructions.txt` temporarily disappear from the working directory — resolved before this response was written)
**Scope:** `localllm/leakage.py`, `localllm/test_detectors.py`, `localllm/bench_device.py`, `localllm/data.py`, `localllm/train.py`, `localllm/exp_lr_width.py` at HEAD, plus live probes run by The PhD.

## The question

The executor applied the council's own standing checklist ("verify a new mechanism before tuning it") to himself before asking anything: he fixed last round's hash-collision bug and wrote this repo's first test suite (4/4 passing). Three questions before building further on top: (Q1) what does the 4-test suite still not cover, given the executor wrote it himself and his test-input instincts already caused two bugs? (Q2) is there a systematic way to check other parameters for the same stride/alignment risk, or is it necessarily per-parameter? (Q3) should CPU users get a smaller default model, given CPU is measured 7.5x–84.9x slower than GPU?

## Key numbers

- **Headline finding, not asked for:** the shipped trainer's evaluation draws batches from the same RNG as training, so how often you evaluate changes what you train on. Measured effect (0.0044) is comparable to seed noise (0.0054) — a real reproducibility bug, not yet a wrong-conclusion one. The fix already exists elsewhere in the repo (the experiment harness solved this correctly) and was never carried into the main trainer.
- The leakage detector scores **0% recall on a real Python clone type** (identifier renaming) — not a marginal miss. Isolated the cause: replacing string literals/docstrings (~7% of the corpus) drops detection to zero; renaming every identifier in the code barely matters. The tool detects prose, not logic.
- A proposed CPU-auto-downsize rule (device=CPU, wait>300s → shrink the model) would silently shrink the *default* model size on this project's own development machine — its own measured CPU time (324.2s) exceeds the threshold that was supposed to only catch weak hardware.
- Of six parameters checked for alignment risk, four cleared cleanly via a direct sweep; the other two failures were a different *shape* entirely (a silent saturation cliff, and a hidden RNG coupling) that the sweep method couldn't have found by design.

## The chairman's verdict

**Where the council agrees:** don't silently substitute a weaker model for slow hardware — checked against real practice in comparable tools (Ollama, llama.cpp, LM Studio), none of them do this; they adapt execution, disclose an estimate, and let the user choose.

**Corrections that changed the round:** the Pragmatist's proposed fix for Q1 (synthetic near-duplicates via "15% token replacement") was found to be the same anti-pattern that caused the last two bugs — a hand-picked number invented by the same person who ships the bugs — relocated one level down rather than solved. The fix wasn't to abandon the idea, but to source the mutation *definitions* from an external taxonomy instead of inventing them.

**Blind spot the council caught:** the mechanical "sweep every parameter by ±1" method proposed for Q2 cleared four parameters cleanly but structurally could not have found the round's two real defects — one was a saturation cliff far outside a ±1 window, the other was a hidden coupling with no discontinuity to detect at all. Neither failure mode looks like the other; a single method doesn't cover the class.

**The recommendation:** fix the eval-RNG coupling first (a two-line fix, with the correct pattern already sitting elsewhere in the repo). Rewrite the leakage tool's own claim to match what it actually measures (verbatim runs, not near-duplicates) rather than software the overclaim. Don't ship the specific auto-downsize threshold as proposed — surface the already-built benchmark as a disclosed, pre-selected choice instead.

## The one thing to do first

Fix `train.py`'s `estimate_loss()` to use a dedicated RNG generator instead of the global one — copy the pattern that already exists correctly in `exp_lr_width.py`. Red witness: eval-interval-dependent loss variance drops from 0.0044 to exactly 0.0000 once isolated.

## Advisor alignment map

| Seat | Position this round |
|---|---|
| **The PhD** (leads, + inherited audit duty) | Measured 0% clone-detection recall directly. Found the eval-RNG coupling unprompted. Refuted the Pragmatist's specific auto-downsize threshold using the project's own data. |
| Contrarian | Suspected `WINDOW=25` as another hand-picked risk — checked directly and cleared; his broader "0.20/0.05 thresholds are uncalibrated" call was confirmed and found worse than stated. |
| First Principles | Correctly diagnosed that self-authored mutation tests relocate rather than solve the oracle problem — this became the actual resolution path. |
| Expansionist | Proposed live time estimates as informed choice — confirmed technically sound and adopted as part of the final recommendation. |
| Outsider | Named the CPU/GPU experience gap as "two products under one name" — the recommendation addresses this by disclosure rather than by hiding it. |
| Pragmatist | Most concrete proposals across all three questions — several ideas adopted after correction; the auto-downsize threshold and the naive parameter-sweep method were both found unsound as specified. |

Full record: `council-transcript-2026-07-26_1935.md`.
