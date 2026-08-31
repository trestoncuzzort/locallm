# srlm-forge

**One research program in measurement-integrity engineering for machine learning —
a local learning model, and the instruments that keep its numbers honest.**

This repository is one project at two scales. It used to look like two projects;
that was an accident of history, and the history is all here.

## The two scales

**The forge** (repository root) is the field site. A language model writes code; the
code is executed against hidden unit tests; whichever candidate actually passes becomes
`chosen`, a worse one becomes `rejected`, and the pair becomes preference-training data.
The model never grades itself — a program that runs decides. The interesting output of
running that loop honestly was not a better model. It was a catalogue of the ways the
measuring instruments kept emitting well-formed numbers after they stopped measuring,
and the gates built in response: a hash-receipt dataset gate, a pinned verifier, a
frozen benchmark, preregistration before every run, red witnesses before every fix.

**The trainer** ([`locallm/`](locallm/)) is the laboratory, and the product. A local
learning model: a small, readable, from-scratch GPT that learns whatever text-shaped
data your machine produces — notes, code, logs, query dumps — trained on your own
hardware with nothing leaving your computer. It carries the same discipline at a scale
anyone can verify: a machine-checked README, leakage gates on every val loss,
preregistered experiments with PASS/FAIL verdicts, an append-only run ledger. A full
training run costs under a minute on an ordinary laptop (CUDA, Apple silicon, or CPU).
Start there: [`locallm/README.md`](locallm/README.md).

## The paper

The first report from the field site is **"Automated Oracles Are Not Enough: An
Empirical Decomposition of an Execution-Verified Benchmark Gain."** In one paragraph:
a preregistered DPO evaluation on an 8B model produced a null result that replicated
across hardware; retraining produced large, consistent gains — and decomposing those
gains against the verifier attributed roughly half of them to an idiosyncrasy of the
measuring instrument, not the model. The verdict of an execution-based reward is
objective; that does not make it trustworthy. The manuscript chain (v10–v15) is at
[`docs/revision-2026-08-25/`](docs/revision-2026-08-25/), and the measurement-integrity
failures it reports are documented alongside the code that repaired them.

## What is in here

| Where | What |
|---|---|
| `forge.py`, `dataset_gate.py`, `verify_dataset.py` | The execution verifier and the hash-receipt gate that decides whether training data may be trusted. `dataset_gate.require_verified` checks; `verify_dataset.py` re-verifies and *writes* the receipt. |
| `eval.py`, `screen_tasks.py`, `build_ruler.py`, `ruler_noise.py` | The frozen 31-task benchmark, its screening, and its measured noise floor. |
| `harness_smells.py`, `traces.py`, `test_gate_coverage.py`, `tests/` | Defenses built after each documented failure: verdict-channel smells, provenance traces, coverage that fails if anything bypasses the gate. |
| `data/` | The verified corpus, receipts, preregistrations, and every banked evaluation row. Append-only where it matters; `data/*.jsonl` merge by union. |
| `dafny_*.py` | The next instrument: verified-pair generation from Dafny, a language whose compiler proves code correct — the stronger fix the paper points at. |
| `docs/` | Manuscripts, review dossiers, port witnesses, machine bootstrap notes. |
| `results/`, `council/` | The run record and the working record, kept because a result file the next run overwrites cannot show you a trend. |
| [`locallm/`](locallm/) | The local learning model. MIT-licensed, self-contained, beginner-runnable. |

## Honest status

Read the paper for the precise claims; nothing here rounds up. The trained adapter did
not beat its null baseline on the frozen benchmark. Retrains beat theirs, and about
half of that gain was the instrument. The mechanism behind the original null — 8-bit
blockwise Adam state colliding with a massive-activation channel — is measured link by
link, not inferred. Everything quantitative sits behind a gate or a receipt, and the
things that are not yet shown are named as limitations rather than implied.

## License

[`locallm/`](locallm/) is MIT — use it, change it, ship it, sell it. The repository
root is the working research record; third-party datasets referenced here keep their
own licenses (KodCode is CC BY-NC and is never redistributed from this repository;
AceCode is MIT with attribution).

Copyright (c) 2026 Treston Malachi Cuzzort.
