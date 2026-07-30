# OPEN ITEMS

One line per parked thing: **why** it is parked and **where** the details live.
Parked is not done. Prune entries when they close.

## Track A (DPO pipeline)

- ~~**Zero gradient steps.**~~ CLOSED 2026-07-28 — the path was exercised end to end on
  `Qwen/Qwen2.5-0.5B-Instruct` (10 steps, real adapter + `run_meta.json` written,
  DPO+NLL confirmed live).

- **No run on the real base; no efficacy result.** Nothing has run on the real 8B
  base, no held-out evaluation has been scored, and no prereg is signed. A smoke
  test is not a result.
  *Where:* `data/smoke_rpo_alpha_result.json`, README "Track A" status paragraph.

- ~~**The ruler is saturated, and its noise floor was understated.**~~ REPLACED
  2026-07-29 (§69–§72). The old 10-task bank is spent (§64: pass@20 == pass@3 ==
  0.9000, 7 at ceiling / 1 at floor). A 31-task replacement was screened from
  AceCode `oss`, confirmed at n=60, and FROZEN — `data/ruler_frozen.json`, set
  sha256 `74560a4c…`, with a disjoint 43-tid training pool declared in the same act.
  Its noise floor is now MEASURED, not assumed: run-level pass@1 sd **0.0283** over
  10 null replicates under the pinned verifier.
  *Where:* `data/ruler_frozen.json`, `screen_tasks.NOISE_FLOOR`, §71/§72.

- **Only the NULL arm's noise was measured.** At 40 replicates the run-level sd is
  **0.0381**, CI [0.0312, 0.0489] — i.e. **1.01×** the 0.0376 independence
  prediction, so independence holds and §70's sizing table is correct as published
  (3pp = k=25 = 3,875 gens/arm). §72's 0.0283 / 0.75× / "k=20 suffices" was an n=10
  artifact and is WITHDRAWN (§73); its residual covariance sign flipped too
  (−0.0072 → +0.0102). What remains open is the arm assumption: `se_diff =
  sqrt(2)*run_sd` assumes BOTH arms share a run-level sd and only the null arm has
  one. A trained arm could be noisier and nothing bounds it, so **the first efficacy
  run must report its own arm sd rather than borrowing this one.** This is now the
  largest unmeasured quantity in the sizing.
  *Where:* `council/ruler_noise_analysis_n40.txt`, `screen_tasks.NOISE_FLOOR`, §73.

- **`data/ruler_frozen.json` records n=10 eval-instrument rates, superseded by
  n=40.** The frozen tid set and set-sha are unaffected (composition unchanged), but
  the per-task `eval_instrument_rate` and the `eval_instrument_out_of_band` list
  (3 tasks at n=10, 4 at n=40 — `ace_oss_2454` joins) came from the smaller sample.
  Re-issuing needs `freeze --force`, deliberately, because freezing twice silently
  is what that guard exists to prevent. *Where:* §73 open item 3.

- **Four frozen ruler tasks sit outside [0.2, 0.8] under the eval instrument.** At
  n=40: `ace_oss_16070` (0.880), `ace_oss_19459` (0.855), `ace_oss_2454` (0.180),
  `ace_oss_24748` (0.145). Frozen and flagged rather than dropped, because dropping
  them selects on the very measurement being reported and each drop-and-remeasure
  round biases the next. So the ruler is **27 clearly-live channels plus 4 weak
  ones**, and 0 dead channels across 40 runs. All four are pushed out by the greedy
  anchor (each has greedy pinned at 1.00 or 0.00).
  *Where:* `data/ruler_frozen.json` → `eval_instrument_out_of_band`, §73.

- **The greedy anchor is 20% of every eval score and it is a deterministic
  constant.** `eval.py` samples 1 draw at temp 0.0 + 4 at 0.8, and the resulting
  rate is exactly `0.2*greedy + 0.8*temp0.8` (verified to 0.000000 over 31 tasks).
  Greedy was constant on 31/31 tasks across **40** runs, so it buys a 0.894×
  variance reduction while POLARIZING the rate distribution. It is now the **sole**
  mechanism putting tasks outside the band on this ruler — all four out-of-band
  tasks have greedy pinned at 1.00 or 0.00. Whether the ruler should sample all 5 at
  temp 0.8 is a real design question; changing it re-baselines every
  `eval_history.jsonl` row, so it is named, not done.
  *Where:* §73 open item 4, `ruler_noise.py` CAUSE 1.

- ~~**`export_adapter.py` does not exist.**~~ CLOSED 2026-07-28. Built and verified
  end to end on the smoke adapter: conversion exit 0 with tensor count 336 = 336,
  both the adapted model and the null baseline created, coherent spot check, and
  the adapter-is-live control passed (lora_B × 50,000 → output similarity 0.0238
  vs null, i.e. the ADAPTER directive is genuinely applied, not silently ignored).
  Requires llama.cpp's converter — set `SRLM_LLAMA_CPP` if it is not at
  `C:\Users\t\llama.cpp`. *Where:* `export_adapter.py`, `data/export_acceptance_result.json`.
  STILL OPEN: only exercised against a 0.5B stand-in; the real 8B base is untested
  on this path.

- **No Track A prereg.** The only prereg files are `localllm/prereg_lr_width{,_fast}.json`,
  both Track B. §14/§18 specify N + sha256 + recipe must be recorded before run 1.
  *Where:* `build_training_set.py` closing print; `instructions.txt` §14.

## Data

- **`data/dpo_pairs_capped.jsonl` is CRLF on disk; the builder now writes LF.**
  Deliberately NOT regenerated: the 918 pairs are byte-identical in content, only line
  endings differ, and the file is pinned by council §12/§14 rulings. Consequence —
  rebuilding it changes its sha256, which invalidates the receipt and makes training
  refuse until `verify_dataset.py` is re-run. That is the gate working, not a fault.
  *Where:* `build_training_set.py` (the `newline=""` comment), `dataset_gate.py`.

- **3 pairs appear in both `dpo_pairs.jsonl` and `repair_pairs.jsonl`**
  (`dpo_pairs:13 / repair:2`, `dpo_pairs:435 / repair:35`, `dpo_pairs:1016 / repair:21`).
  They are verified once, but would be seen twice per epoch under `--include-repair`.
  Not deduplicated because that changes a council-pinned dataset. Default run-1 config
  (capped only) is unaffected.
  *Where:* `verify_dataset.py` (`signature()` dedup), README Track A section.

## Guard scope

- **Cross-version verifier divergence beyond the annotation case is unenumerated.**
  §71 found `forge.verify()` launching `[sys.executable, …]`, so ground truth was
  inherited from the caller: guarded scripts (`screen_tasks.py`, `build_ruler.py`)
  re-exec under `.venv-train`/3.11, unguarded ones (`eval.py`, `forge.py`) ran under
  3.14. Red witness: 310 identical completions scored **172/310 on 3.14 vs 154/310
  on 3.11**, all 18 disagreements one way, cause PEP 649 deferred annotations. Now
  pinned in one place (`dataset_gate.verify_py`) and recorded in the receipt
  (schema 4). `tests/test_verifier_pin.py` is a fixed probe for that one mechanism
  plus a structural check that the interpreter is no longer inherited — **a
  flashlight, not a fence.** Other 3.11↔3.14 semantic differences are not swept, and
  the fingerprint covers the interpreter version but not its installed packages, the
  OS, or CPU-dependent behaviour.
  *Where:* `forge.py` pin block, `dataset_gate.py` VERIFIER_FILES block, §71.

- **The dataset receipt is unsigned.** It defends against drift and accident, not
  against someone editing the receipt itself. Stated deliberately rather than implied.
  *Where:* `dataset_gate.py` module docstring, "WHO MAY ISSUE A RECEIPT".

## Third-party datasets (imported 2026-07-28, for building the second instrument)

- **KodCode-V1 is CC BY-NC 4.0 and must never be redistributed from this repo.**
  487,432 triplets, pytest-style tests. Downloaded for LOCAL screening only -
  downloading is not redistributing, but publishing its rows from an MIT repo
  would make this repo's own licence untrue. If a task derived from it ever needs
  to ship, it must be re-derived independently or the licence renegotiated.
  *Where:* `.gitignore` third-party block, verified on the HF dataset card.

- **AceCode-89K is MIT and may be redistributed with attribution.** 87,149 rows,
  bare `assert` test cases (~16 per question) - structurally the same shape
  `forge.py` already runs, which is why it is the import candidate rather than
  KodCode. Attribution must accompany any published subset.
  *Where:* `.gitignore` third-party block; TIGER-Lab/AceCode-89K on HuggingFace.

- **The second instrument is costed but not built.** To detect a +3% effect at 80%
  power needs ~30 movable tasks at k=5 seeds per side (~50 at k=3, ~150 at k=1);
  +5% needs ~11 at k=5. A paired before/after design does NOT help here - measured
  1.0x, because the aggregate is already a per-task average and the residual noise
  is per-task binomial sampling, which pairing cannot cancel. The current ruler has
  4 movable tasks; the other 6 are pinned at 1.000 and carry no signal.
  *Where:* `data/eval_history.jsonl` (57 runs), README Track A status paragraph.
