# OPEN ITEMS

One line per parked thing: **why** it is parked and **where** the details live.
Parked is not done. Prune entries when they close.

## Track A (DPO pipeline)

- **Zero gradient steps.** No training run has ever executed: no adapter directory,
  no `run_meta.json`. Every hyperparameter in `train_native.py` is configured but
  unexercised. Parked pending the items below plus a signed prereg.
  *Where:* `train_native.py`, README "Track A" status paragraph, `instructions.txt` §18 finding 3.

- **`export_adapter.py` does not exist.** `train_native.py:140` points readers at it
  for the "convert_lora_to_gguf.py → Ollama ADAPTER directive" export path. A training
  run would produce an adapter with no documented way to apply it.
  *Where:* `train_native.py` closing comment; `instructions.txt` §18 (adopt-don't-build).

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

- **The dataset receipt is unsigned.** It defends against drift and accident, not
  against someone editing the receipt itself. Stated deliberately rather than implied.
  *Where:* `dataset_gate.py` module docstring, "WHO MAY ISSUE A RECEIPT".
