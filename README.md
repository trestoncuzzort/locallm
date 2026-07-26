# locallm

**Build and train your own language model from scratch, on your own machine, from your own text.**

No pretrained weights. No API. No account. No downloads. Nothing leaves your computer.

The model starts as random numbers. The vocabulary is built from exactly the characters
in the text you give it. You watch it learn.

```
python studio.py
```

---

## What this actually is

A small, readable, from-scratch GPT — and a GUI so you don't need a terminal to use it.

| File | What it is |
|---|---|
| `model.py` | The transformer. Decoder-only GPT, written out in full — attention, MLP, blocks, weight tying, GPT-2 scaled init. ~145 lines. |
| `data.py` | A character-level tokenizer built from *your* corpus, plus batching. No external tokenizer, nothing downloaded. |
| `train.py` | The training loop. Random init → your weights. Cosine schedule, warmup, gradient clipping, bf16 autocast when your GPU supports it. |
| `generate.py` | Sample from a model you trained. |
| `make_corpus.py` | Point it at a folder; it builds `corpus.txt` from your files. |
| `studio.py` | The GUI. Build the architecture, train it, watch the loss curve, sample from it. |
| `exp_lr_width.py` | A preregistered experiment harness (see below). |

Dependencies: **PyTorch and Tk.** That's it. Tk ships with Python.

## Quick start

```bash
pip install torch                       # CUDA build if you have an NVIDIA GPU
python make_corpus.py --src ./my_notes  # or --src . --ext .py to train on code
python studio.py                        # or: python train.py --data corpus.txt
```

Then in the GUI: **Scan** your corpus → set the architecture → **Train from scratch** → **Sample**.

Checkpoints are plain `ckpt.pt` + `tokenizer.json` in your output folder. They're yours.
`generate.py --out <folder>` reads them back.

## What makes it different

Most small-model repos show you a loss curve going down and let you feel good about it.
This one is built to stop you fooling yourself:

- **The learning rate follows your architecture.** A fixed `3e-4` is a GPT-2-scale constant
  (width 768–1600) and is badly wrong at the widths this trains. `auto_lr(n_embd)` scales
  with width, and the GUI retargets it when you change the model — but never overwrites a
  value you typed yourself.
- **Experiments are preregistered.** `prereg_lr_width.json` fixes the success bar, the arm
  selection rule, and the interpretation of a null result *before* the run. `exp_lr_width.py`
  then reports PASS or FAIL against it. Writing the bar first is the whole point.
- **Evaluation can't disturb training.** Eval batches come from a dedicated
  `torch.Generator`, never the global RNG, so every arm sees byte-identical batches.
- **Multiple seeds, and ranges reported.** One run is an anecdote.

### A worked result

The first experiment run through this harness, on an RTX 4080 — 4 layers, 4 heads, width 256,
block 128, batch 32, 2000 steps:

```
control   lr 3.0e-04   mean 0.2601   range [0.2561, 0.2647]
treatment lr 3.0e-03   mean 0.1545   range [0.1538, 0.1553]
gap +0.1056   bar 0.020   ranges overlap: no
PREREGISTERED VERDICT: PASS
```

Five seeds per arm, bar written down first. The hardcoded default was leaving **0.11 train
loss** on the table — more than any architecture change on the table was worth. That is why
the learning rate scales with width now.

Reproduce it: `python exp_lr_width.py` (about 4 minutes on a 4080).

## Honest limits

Read this part before you expect too much.

- **A small model trained on one person's text produces mediocre text.** This is not ChatGPT
  and it is not close. That is compute and data scale, not a bug to engineer around.
- **Character-level tokenizer.** Simple and dependency-free, but less efficient per token
  than BPE.
- **`make_corpus.py` + `data.py` use a positional 90/10 train/val split.** If your corpus
  contains duplicated or near-duplicated documents, validation text can also appear in
  training, and val loss will look better than it deserves. **A group-aware split and a
  leakage scan are the next thing being built.** Until then, prefer train loss when
  comparing configurations — which is exactly why the experiment above uses it.
- No resume-from-checkpoint yet, no gradient accumulation, no multi-GPU.
- Large architectures will run out of VRAM rather than warning you first.

## Why from scratch

Because "download someone's weights and run them locally" is a solved problem with good
tools already. This is the other thing: a model that has read **only** what you gave it,
that started as random numbers on your machine, and whose every line you can read.

It is small. It is yours. It is honest about what it is.
