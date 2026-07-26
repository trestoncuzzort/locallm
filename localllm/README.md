# localllm — build and train your own LLM, 100% locally

No API. No subscription. No account. No dependence on someone else's harness. Just
Python + PyTorch on your machine. You define the model, you bring the text, you own
the weights.

## What's here
- `model.py`    — the Transformer (a from-scratch GPT; set any size)
- `data.py`     — a dependency-free char tokenizer built from *your* corpus
- `train.py`    — train from random init on your text
- `generate.py` — sample from the model you trained

The only dependency is `torch`. Nothing here calls out to any external service.

## Quickstart
```
# any Python env with torch (the project's .venv-train already has it)
python train.py --data your_corpus.txt --steps 2000 --out mymodel
python generate.py --out mymodel --prompt "Once upon a time"
```
`train.py` writes `mymodel/ckpt.pt` (weights) and `mymodel/tokenizer.json` — both
yours, portable, offline.

## Bring your own data
Point `--data` at any `.txt` file. Bigger + cleaner corpus = better model. Scale the
model with `--n-layer --n-head --n-embd --block-size` and train longer with `--steps`.

## Scale, honestly
On a single 16 GB GPU you can train small models — a few million up to a few hundred
million parameters — from scratch. That's enough to learn the structure and style of
your corpus and generate coherent text in its domain. It will **not** rival GPT-4;
those take thousands of GPUs and internet-scale data. This is *your* model: small,
local, fully owned, and a real from-scratch LLM you built end to end.

## Where it fits
This is the "build your own model" foundation. The rest of srlm-forge (the verifier,
the self-rewarding data loop) can later generate training corpora *for* a model you
own here — so the whole stack, model included, is yours with no external base.
