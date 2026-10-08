# locallm

**A transformer trainer that builds language models from random weights on your own hardware.** No pretrained
weights, no API, no account; the data and the model stay on the machine. It covers the whole path: tokenizer,
training on one GPU or four, checkpoints that resume exactly, cached and quantized inference, a desktop studio for
people who have never trained a model, and a research record in which every experiment was registered before it ran.

locallm is the model layer of [dawnr](https://github.com/trestoncuzzort/dawnr). Its outputs were graded by
[t-proof-engine](https://github.com/trestoncuzzort/t-proof-engine), which checks a program in seven independent
provers. It was built by one person between July and October 2026 and was split out of dawnr with its history.

## What is in it

| Area | Files | What it does |
|---|---|---|
| Model | [`model.py`](model.py) | GPT baseline (learned positions, LayerNorm, GELU) and a modern core (rotary positions, RMSNorm, SwiGLU, activation checkpointing) at about 30M, 91M and 312M parameters ([`CORE-2026-09-19.md`](CORE-2026-09-19.md)) |
| Data | [`data.py`](data.py), [`token_shards.py`](token_shards.py), [`make_corpus.py`](make_corpus.py) | character vocabulary or a byte-level BPE tokenizer learned from the training text; token shards so a multi-billion-token corpus streams instead of loading |
| Training | [`train.py`](train.py), [`train_distributed.py`](train_distributed.py), [`cloud_train.py`](cloud_train.py) | single-GPU training; four-GPU BF16 training with gradient accumulation; the same command on a rented GPU. Resume restores optimizer state and every RNG and refuses a changed schedule, tokenizer or dataset ([`DISTRIBUTED-2026-09-19.md`](DISTRIBUTED-2026-09-19.md)) |
| Inference | [`generate.py`](generate.py), [`plain_generate.py`](plain_generate.py), [`quant_int8.py`](quant_int8.py) | KV-cache decoding; a generator that runs on the Python standard library alone (no torch, no numpy); per-row symmetric int8 weight quantization (Krishnamoorthi 2018, arXiv:1806.08342) |
| Studio | [`studio.py`](studio.py), [`start_studio.py`](start_studio.py), [`check_my_computer.py`](check_my_computer.py) | a Tk desktop app: pick your files, pick a size, train, try the model; a hardware check that times the machine before it promises minutes ([`GUIDE.md`](GUIDE.md)) |
| Experiments | `exp_*.py`, `run_*_study.py`, `summarize_*.py`, `measure_capacity.py` | the scripts behind every number below; each writes a machine-readable result file next to it |

## Measured results

Every row is a number a script in this repository recorded; the record links to the file.

| Measurement | Result | Record |
|---|---|---|
| Pretraining from random weights | a 92.9M-parameter model on 3.70 billion English tokens: 56,457 steps on one rented H100, resumed once from its own checkpoint; final validation loss 2.180 | [`dawnr-r12-core-results-2026-09-30.json`](dawnr-r12-core-results-2026-09-30.json) |
| Continued pretraining on code | 15,000 steps on a 16 GB desktop GPU with activation checkpointing; validation loss from 1.758 (step 1,000) to 1.137 (best, step 13,500) | same file |
| Modern core against the GPT baseline | held-out loss 24.6%, 26.6% and 28.7% lower across three matched seeds, at about 18% more time per training segment | [`FINDINGS-source-pretraining-2026-09-19.md`](FINDINGS-source-pretraining-2026-09-19.md) |
| KV-cache decoding | 100 of 100 replies byte-identical to uncached decoding; a 1,200-token round in 304.6 s against 2,144.5 s (7x) | [`FINDINGS-kv-cache-2026-09-19.md`](FINDINGS-kv-cache-2026-09-19.md) |
| int8 weights | 4x smaller (43.5 MB to 11.0 MB) and 205 of 205 generated tokens identical to float32; 33% slower per token on the pure-Python path | [`bench-int8-results-2026-09-27.json`](bench-int8-results-2026-09-27.json) |
| How long to train | longer helps until about 80,000 steps and is flat after (32 runs, 500 to 160,000 steps) | [`FINDINGS-how-long-to-train.md`](FINDINGS-how-long-to-train.md) |

## What did not work, and how it was caught

The record keeps its failures beside its results, because each one changed what was measured next.

- **A withdrawn headline.** This project once claimed that a 92M locallm model tied Microsoft's Phi-4-mini on 232
  held-out program-synthesis problems, each answer proved by seven provers. A decontamination audit on 2026-09-21
  found that 32 of the held-out problems had a same-task source in the training data, and 22 of locallm's 23 clean
  answers were on them. On the other 200 it produced no correct, proved answer, so the claim was withdrawn
  ([`ACHIEVEMENTS.md`](ACHIEVEMENTS.md) section 2). After a 400-step fine-tune, the 92.9M core above writes 45
  well-formed answers to 100 fresh dev problems and passes the tests on none.
- **A transfer that did not happen.** A pre-registered factorial (12 arms, 3 seeds) showed the model learned the
  extra latent/execution supervision but did not carry it to held-out tasks
  ([`FINDINGS-factorial-2026-09-19.md`](FINDINGS-factorial-2026-09-19.md)).
- **A wrong prediction about caching.** The cache was predicted to be 1.5x faster at 128 new tokens and was not. It
  pays only on long outputs, which a later measurement at the real output length showed (the 7x row above).

## How the work was run

Each experiment has a registration written before it ran (`PREREG-*.md`, `PREDICT-*.md`), naming the number that
would falsify it. The outcome is in `FINDINGS-*.md`, including the predictions that failed. Result files carry the
settings, seeds and hashes needed to rerun them.

## Quick start

```sh
pip install -r requirements-training.txt          # torch + tokenizers
python train.py --data corpus.txt --out out/small --preset core-small \
  --tokenizer bpe --vocab-size 8192 --batch-size 1 --steps 2000 --lr 0.0003
python generate.py --out out/small --prompt "The " --tokens 200
python plain_generate.py --out out/small --prompt "The "   # the same model with nothing installed
python start_studio.py                                     # the desktop studio
```

Tests: `python -m pytest test_model_core.py test_kv_cache.py test_bpe.py` (the full list CI runs is in
[`.github/workflows/tests.yml`](.github/workflows/tests.yml)).

## Where it connects to dawnr

`continue_from_checkpoint.py`, `heldout_gate.py` and `chat_data.py` pass training data through dawnr's held-out
filter (`t/loop_filter.py`) before a model sees it, the gate that caught the contamination above; `t_tool.py` and
`app.py` call dawnr's `t/` pipeline. They run from a [dawnr](https://github.com/trestoncuzzort/dawnr) checkout,
where their tests pass. Links of the form `github.com/trestoncuzzort/dawnr/...` in the documents point at the
pipeline files they cite.

## License

Research Use License; see [`LICENSE`](LICENSE).
