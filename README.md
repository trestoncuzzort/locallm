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
| `bench_device.py` | Times a real training step on your hardware and tells you what it can handle. |
| `test_detectors.py` | Tests for the leakage detector. `python test_detectors.py`, no framework. |
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
- **The detector is itself tested, against a copy of its own old bug.**
  `test_detectors.py` keeps the previous, broken fingerprinter in the file on purpose and
  runs every test against both: the current one must pass and the broken one must fail. A
  test that both pass is not testing anything. Test inputs are drawn randomly rather than
  hand picked, because the original bug was a stride of 10 and every offset a person
  reaches for by hand (0, 100, 500, 1000) is a multiple of 10 and passes on the broken
  code.

### A worked result

The first experiment run through this harness, on an RTX 4080 (4 layers, 4 heads, width 256,
block 128, batch 32, 2000 steps):

```
control   lr 3.0e-04   mean 0.1495   range [0.1471, 0.1507]
treatment lr 3.0e-03   mean 0.1056   range [0.1016, 0.1099]
gap +0.0439   bar 0.020   ranges overlap: no
PREREGISTERED VERDICT: PASS
```

Five seeds per arm, bar written down first. The hardcoded default was leaving **0.04 train
loss** on the table, more than any architecture change was worth. That is why the learning
rate scales with width now.

Reproduce it: `python exp_lr_width.py` (about 2.5 minutes on a 4080, running 4 arms
concurrently; pass `--workers 1` to run them one at a time).

There is also a one minute profile, `python exp_lr_width.py --profile fast` (measured 59s),
at 800 steps with a 4 point sweep. It is deliberately **a separate experiment, not a cheaper
version of this one**, because the effect size changes with step count: measured across
400/800/1200/2000 steps the gap decays about 9x, so a shorter run reports a *larger* number
for the same underlying phenomenon. The fast profile licenses the claim "reaches lower train
loss faster" and nothing more. To stop the two being confused later, the profile, step count,
grid size and claim are written into the result file's own verdict string rather than kept in
a filename or someone's memory:

```
PASS [fast profile: 800 steps, 4-LR grid, 5 seeds] - claim: reaches lower train loss
FASTER; NOT the canonical effect size
```

These numbers moved once since first publication, and the reason is worth stating: the
document splitter's `seed` argument was silently unused, so fixing it changed which
documents land in training. The verdict did not change, the margin did.

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
capable default with the GPU build as an opt in, and the Python runtime bundled so the
user never sees it.

That plan rests on CPU training being tolerable, which is a measurable claim, so it was
measured rather than assumed. Run `python bench_device.py` to get the same table for your
own machine. On an RTX 4080 with a Ryzen 7000 series CPU, for a full 2000 step run:

| size | params | CPU | GPU | GPU speedup |
|---|---|---|---|---|
| small (2L, 128 wide) | 0.41M | 63s | 8s | 7.5x |
| default (4L, 256 wide) | 3.18M | 5.4 min | 14s | 23.8x |
| large (6L, 512 wide) | 18.96M | 56.9 min | 40s | 84.9x |

So a CPU only install is genuinely fine at the small size, usable at the default, and
impractical above it. That is the shape the installer should follow: detect the hardware,
pick a size the machine can actually finish, and say which it chose.

**2. Leakage scan and group aware splitting. DONE.**
Shipped in `leakage.py`, and wired into the GUI and the training loop. Measured on this
project's own corpus: the old positional split put 82.6% of validation content inside
training. Splitting by document drops that to 1.5%. The effect on the numbers is the
point: under the contaminated split, val loss came out *lower* than train loss, which is
backwards. With a clean split there is an honest gap.

Those two figures were first published as 70.1% and 0.0%, measured with a detector that
was itself broken. It sampled fingerprints at a fixed stride, so it only compared two
copies of a passage when both happened to start on the same stride phase: a document
copied verbatim into training was caught at 1 byte offset out of 10. Fingerprints are now
selected by content (winnowing), which is phase invariant, catches that case at 10 offsets
out of 10, and is cheaper than the sampler it replaced.

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

## Why a program like this is useful

### Immunity to "Enshittification" and API Decay

Every hosted AI service follows the same arc. It launches good and cheap, because it is
buying users. Then the free tier shrinks. Then the model behind the endpoint is quietly
swapped for a smaller one, and the thing you built and tuned against changes underneath
you without a version bump. Then the API you depend on is deprecated, rate limited,
moved behind a higher tier, or switched off. Your work was never yours. It was rented,
and the landlord kept the keys.

A model you trained yourself cannot be degraded by someone else's quarterly targets.
The weights are a file on your disk. The tokenizer is a file on your disk. The training
code is a few hundred readable lines you can open right now. Nothing phones home,
nothing needs an account, nothing expires, and no terms of service update can reach
backwards and take it away. Run it in ten years on a disconnected laptop and it behaves
exactly as it does today, because every part of it is already in your hands.

That is the whole point. Not that a small model trained on your own text will beat a
frontier model. It will not, and this README says so plainly further down. The point is
that it is *yours*, permanently, and that you can see and change every part of how it
works.

### The goal

Make training your own language model something an ordinary person can actually do.

Not "download someone else's weights and run them locally", which is already a solved
problem with good tools. This is the other thing: start from random numbers, learn from
text you chose, on hardware you own, and watch it happen. Understanding how the thing
works should not require a research group, a cloud account, or a credit card.

The direction of travel is a single installer, no terminal, no Python, no configuration
files. Point it at a folder of your own writing and press train. See the
[Roadmap](#roadmap) for where that stands.

### Free for everyone

This is free. Not free-tier, not free-for-now, not free-until-we-raise-a-round. There is
no account, no telemetry, no usage limit, no paid version holding the good features, and
nothing about it that stops working if this project goes quiet. It runs on hardware
people already have, including without a GPU.

## Why from scratch

Because "download someone's weights and run them locally" is a solved problem with good
tools already. This is the other thing: a model that has read **only** what you gave it,
that started as random numbers on your machine, and whose every line you can read.

It is small. It is yours. It is honest about what it is.
