# locallm

**Build and train your own language model from scratch, on your own machine, from your own text.**

No pretrained weights. No API. No account. No downloads. Nothing leaves your computer.

The model starts as random numbers. The vocabulary is built from exactly the characters
in the text you give it. You watch it learn.

```
python studio.py
```

> ## 🚧 Work in progress
>
> **This is an early, actively developed project, not a finished product.** It trains real
> models today and the results below are real, but interfaces will change, features are
> missing, and the limits section further down is not modesty. It is accurate.
>
> **Where this is going: a single all in one `.exe` installer. Double click, point it at
> your text, train. No terminal, no Python install, no `pip`, no command line, ever.**
>
> The commands in Quick Start are the *current* state, not the destination. Right now you
> do need Python and a terminal to get started. Removing that requirement entirely is a
> primary goal, not a nice to have. See [Roadmap](#roadmap).

---

## What this actually is

A small, readable, from-scratch GPT and a GUI so you don't need a terminal to use it.

| File | What it is |
|---|---|
| `model.py` | The transformer. Decoder-only GPT, written out in full: attention, MLP, blocks, weight tying, GPT-2 scaled init. ~145 lines. |
| `data.py` | A character-level tokenizer built from *your* corpus, plus batching. No external tokenizer, nothing downloaded. |
| `train.py` | The training loop. Random init → your weights. Cosine schedule, warmup, gradient clipping, bf16 autocast when your GPU supports it. |
| `generate.py` | Sample from a model you trained. |
| `make_corpus.py` | Point it at a folder; it builds `corpus.txt` from your files. |
| `studio.py` | The GUI. Build the architecture, train it, watch the loss curve, sample from it. |
| `leakage.py` | Finds training text hiding in your validation set, and says so. |
| `exp_lr_width.py` | A preregistered experiment harness (see below). |

Dependencies: **PyTorch and Tk.** That's it. Tk ships with Python.

## Quick start

*Temporary. All of this disappears behind a double click once the installer lands.*

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

- **It refuses to hand you a fake number.** Before training, it checks whether your
  validation text also appears in your training text. If it does, val loss is measuring
  memorisation rather than generalisation, and the tool tells you so instead of letting
  you believe the number. Splitting is by whole document, after de-duplication, so
  repeated material cannot land on both sides.
- **The learning rate follows your architecture.** A fixed `3e-4` is a GPT-2-scale constant
  (width 768–1600) and is badly wrong at the widths this trains. `auto_lr(n_embd)` scales
  with width, and the GUI retargets it when you change the model but never overwrites a
  value you typed yourself.
- **Experiments are preregistered.** `prereg_lr_width.json` fixes the success bar, the arm
  selection rule, and the interpretation of a null result *before* the run. `exp_lr_width.py`
  then reports PASS or FAIL against it. Writing the bar first is the whole point.
- **Evaluation can't disturb training.** Eval batches come from a dedicated
  `torch.Generator`, never the global RNG, so every arm sees byte-identical batches.
- **Multiple seeds, and ranges reported.** One run is an anecdote.

### A worked result

The first experiment run through this harness, on an RTX 4080 (4 layers, 4 heads, width 256,
block 128, batch 32, 2000 steps):

```
control   lr 3.0e-04   mean 0.2601   range [0.2561, 0.2647]
treatment lr 3.0e-03   mean 0.1545   range [0.1538, 0.1553]
gap +0.1056   bar 0.020   ranges overlap: no
PREREGISTERED VERDICT: PASS
```

Five seeds per arm, bar written down first. The hardcoded default was leaving **0.11 train
loss** on the table, more than any architecture change was worth. That is why the learning
rate scales with width now.

Reproduce it: `python exp_lr_width.py` (about 4 minutes on a 4080).

## Honest limits

Read this part before you expect too much.

- **A small model trained on one person's text produces mediocre text.** This is not ChatGPT
  and it is not close. That is compute and data scale, not a bug to engineer around.
- **Character-level tokenizer.** Simple and dependency-free, but less efficient per token
  than BPE.
- **A tiny corpus, or one dominated by a single huge document, cannot be split cleanly.**
  Whole-document splitting cannot hit a 10% target when there are only three documents.
  The scanner reports the validation fraction it actually achieved and warns you when the
  document sizes, not your setting, are in charge.
- **The leakage scan is string matching, not semantics.** It catches verbatim and
  near-verbatim reuse, which is the common case. It will not catch a paraphrase.
- No resume-from-checkpoint yet, no gradient accumulation, no multi-GPU.
- Large architectures will run out of VRAM rather than warning you first.
- **You currently need Python and a terminal to install and start it.** The GUI itself
  needs neither once it is running, but getting there does. That is the single biggest
  barrier to "anyone can use this", and it is item 1 on the roadmap.

## Roadmap

In order. The training core gets sharpened before anything expands.

**1. One click installer, the headline goal.**
A single `.exe`: no Python, no `pip`, no virtualenv, no terminal, no command line. Double
click, choose your text, press train. The honest obstacle is that PyTorch with CUDA is
roughly 2.5 GB, which no amount of packaging polish makes friendly. The plan is a CPU
capable default (a small character model trains perfectly well on CPU, just slower), with
the GPU build as an opt in, and the Python runtime bundled so the user never sees it.

**2. Leakage scan and group aware splitting. DONE.**
Shipped in `leakage.py`, and wired into the GUI and the training loop. Measured on this
project's own corpus: the old positional split put 70.1% of validation text inside
training. Splitting by document drops that to 0.0%. The effect on the numbers is the
point: under the contaminated split, val loss came out *lower* than train loss, which is
backwards. With a clean split there is an honest gap.

**3. Noise floor by default.**
Multiple seeds on every comparison, mean plus or minus 3 sigma, with test retest variance
reported separately from between configuration variance, so the tool can say "that
improvement is inside noise, it isn't real" instead of letting you believe it.

**4. Training that resumes and keeps going.**
Resume from a checkpoint and train for as long as you want, rather than a fixed step count.

Further out: an assistant layer that can reason and act on your machine. That is a separate
track, built against whatever local model is strongest, because a small from-scratch model
cannot do that job and pretending otherwise would be dishonest. If a model trained here
ever becomes good enough, it earns its way in on measured results.

## Why from scratch

Because "download someone's weights and run them locally" is a solved problem with good
tools already. This is the other thing: a model that has read **only** what you gave it,
that started as random numbers on your machine, and whose every line you can read.

It is small. It is yours. It is honest about what it is.
