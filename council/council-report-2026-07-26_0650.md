# srlm-forge Council — Report

**Activation #7** · 2026-07-26 ~06:50 · triggered by DIRECTIVE watcher (task `bkk3n3jtj`)
**Scope:** `instructions.txt` + code at commit `ccbee91` (`localllm/{studio,model,train,data}.py`), extended on the council's own initiative to `train_native.py`, `config.py`, `data/dpo_pairs.jsonl`, `localllm/make_corpus.py`, and the installed TRL/PEFT source.

## The question

The project has two tracks competing for one GPU: **Track A** (llama3:8b QLoRA DPO+NLL, council-approved in §14, zero gradient steps ever taken) and **Track B** (a from-scratch char-GPT + GUI, commit `ccbee91`, built for AI-engineering learning). The DIRECTIVE asked the council to rank them (Q1: is Track A parked?), give a citation-backed first experiment for Track B (Q2, assigned to The PhD), and specify the minimum honest instrument before trusting any Track-B number (Q3).

## Key numbers

- Track A recipe compliance: **1 of 9** approved parameters correctly implemented in code (target_modules); **7 wrong or missing**, including the mandated `rpo_alpha=1.0` (absent entirely — vanilla DPO, not DPO+NLL).
- Track B validation set: **68.3%** of held-out solutions are byte-identical duplicates of training data; **98.2%** of held-out lines appear verbatim in train.
- Track B's biggest lever: current LR is tuned for a model ~100x wider. Measured **~5x compute-equivalent penalty** from the mis-set LR — larger than any architecture change on the table.
- Noise floors, independently measured on both tracks, nearly identical: Track A ruler std **0.009**; Track B run-to-run std **0.0093** (true seed effect ~0.0051 after removing eval noise).

## The chairman's verdict

**Where the council agrees:** Track A is parked (unanimous once the Contrarian/Pragmatist split was resolved against the code). Track B needs instrumentation before any number counts — confirmed by every seat, but the *what* differed sharply until The Asshole found the contamination bug.

**Corrections that changed the round:** The Asshole's own first-pass MFU figure (8.5%) used the wrong "GUI default" config — The PhD re-measured the real default at ~24.6% MFU. The PhD's own citation notes had one misattributed figure (Fig. 1 → Fig. 3) and one real formula (Kaplan et al. Appendix D.6) wrongly written off as unconfirmable — both caught on citation spot-check.

**Blind spots the council caught:** No style advisor opened `make_corpus.py`; that's where the 68.3% val-set contamination was hiding. The Pragmatist's proposed "one-line fix" (`torch.manual_seed` inside eval) is an active bug — The Asshole ran it and it collapses training to 3 repeating batches.

**The recommendation:** Track A gets a same-day fix (8 keyword-argument edits + the N=918 capped file + a better merge strategy borrowed from llama.cpp/Ollama's adapter path), then resumes §14's frozen sequence. Track B runs The PhD's muP-informed learning-rate experiment first (safe today — train-loss-only, immune to the contamination bug), then fixes the corpus split before anything relying on val loss is trusted.

## The one thing to do first

Run The PhD's preregistered LR experiment on Track B: 5 seeds each, `lr=3e-4` (control) vs the width-appropriate rate (`~2e-2` at width 128), train-loss endpoint, success bar ≥0.020 gap with zero range overlap. ~90 seconds wall-clock, and it's the only Track B result that's trustworthy before the corpus fix lands.

## Advisor alignment map

| Seat | Position this round |
|---|---|
| **The PhD** (leads) | Q2: LR-vs-width mismatch is the real lever (~5x), not architecture; muP-cited, reproduced on this GPU. Corrected the round's MFU figure and Q1's DPOP-urgency framing. |
| **The Asshole** | Q1: PARKED — code implements a different, pre-ruling experiment. Found the 68.3% val contamination (finding of the round). Resolved Contrarian/Pragmatist split. |
| Contrarian | Track A parked (right verdict, incomplete reason). Track B's fixed split + no eval seed = can't trust signal (right instinct, magnitude later corrected). |
| First Principles | Reframed Q1 as sequencing not ranking — graded a dodge on the unfalsifiable psychology, but the shared-instrument sequencing survives narrowly. |
| Expansionist | Track B as control-plane for Track A — good in principle, arithmetic off 9-15x, two proposals mechanically impossible (zero shared code between tracks). |
| Outsider | Friction-avoidance reading — partly confirmed (zero Track A artifacts exist), partly wrong (no actual GPU contention between tracks). |
| Pragmatist | Concrete Monday-morning checklist — but the proposed "one-line" eval-seed fix is an active bug, confirmed by execution. |

Full record, all raw responses, and the citation table: `council-transcript-2026-07-26_0650.md`.
