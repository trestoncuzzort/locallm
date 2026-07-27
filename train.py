"""train.py — train a GPT from scratch on YOUR text. 100% local. No API, no account.

    python train.py --data your_corpus.txt --steps 2000 --out mymodel

Random init -> your weights. Everything (model, tokenizer, checkpoint) is written to
--out and belongs to you.
"""
from __future__ import annotations

import argparse
import contextlib
import math
import time
from pathlib import Path

import torch

import runlog
from model import GPT, GPTConfig
from data import CharTokenizer, Corpus


def enable_fast_math() -> None:
    """Two settings that are free at this scale and off by default in PyTorch.

    TF32 matmuls cost ~10 bits of mantissa and nothing in training quality.
    Measured on this rig they are worth only ~5%, because a 3M-parameter model
    is bound by per-kernel overhead rather than arithmetic, but they are free.
    """
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True


def make_optimizer(model, lr: float):
    """AdamW, fused when CUDA allows it.

    A small model has many small parameter tensors, so the optimizer step is
    dominated by launch overhead rather than arithmetic. Fusing it into one
    kernel measured 5.37 -> 4.93 ms/step here.
    """
    kw = dict(lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
    try:
        return torch.optim.AdamW(model.parameters(), fused=torch.cuda.is_available(), **kw)
    except (RuntimeError, TypeError):
        return torch.optim.AdamW(model.parameters(), **kw)


def _leak_of(text: str) -> dict:
    """Leakage verdict for the split this run actually trained on, so a val loss
    is never recorded without the context that says whether it means anything."""
    try:
        from leakage import scan
        from data import group_split
        tr, va = group_split(text)
        rep = scan(tr, va)
        return {"verdict": rep.verdict, "content_frac": rep.shingle_frac}
    except Exception:                            # noqa: BLE001
        return {}


def auto_lr(n_embd: int) -> float:
    """Width-appropriate learning rate.

    The old hardcoded 3e-4 is a GPT-2-scale constant (width 768-1600) and is far
    too low for the widths this rig runs. Measured on this box (exp_lr_width.py,
    prereg_lr_width.json): at width 256 / 4 layers on corpus.txt, lr=3e-3 beats
    3e-4 by 0.1056 train loss, 5 seeds/arm, zero range overlap.

    The 1/width scaling is muP's (Yang et al. 2022, arXiv:2203.03466). ANCHORED AT
    ONE MEASURED POINT ONLY (width 256). Other widths are extrapolation, not
    measurement — re-run exp_lr_width.py at a new width before trusting it there.
    """
    return 3e-3 * (256.0 / max(n_embd, 1))


def cosine_lr(step: int, warmup: int, total: int, lr: float, min_lr: float) -> float:
    if step < warmup:
        return lr * (step + 1) / warmup
    if step >= total:
        return min_lr
    ratio = (step - warmup) / max(1, total - warmup)
    return min_lr + 0.5 * (1 + math.cos(math.pi * ratio)) * (lr - min_lr)


EVAL_SEED = 12345          # eval draws are reproducible and never touch training


@torch.no_grad()
def estimate_loss(model, corpus, batch_size, block_size, iters=20):
    """Loss on fixed, independently-drawn batches.

    The batches come from a dedicated Generator seeded the same way every call,
    NOT from the global RNG. That matters more than it sounds: drawing eval
    batches from the training stream means the number of times you look at the
    model changes what the model learns, because every eval consumes random
    numbers the next training batch would otherwise have used.

    Measured on this repo before the fix, same seed and same data, varying only
    eval_interval over 248/249/250/251/252/500: final train loss spread 0.031166.
    After: 0.000000, identical regardless of how often you evaluate. It also
    makes successive evals comparable to each other, since they score the same
    batches rather than a fresh random sample each time.
    """
    dev = corpus.train.device
    g = torch.Generator(device=dev.type).manual_seed(EVAL_SEED)
    model.eval()
    out = {}
    for split in ("train", "val"):
        losses = torch.zeros(iters)
        for i in range(iters):
            x, y = corpus.get_batch(split, batch_size, block_size, generator=g)
            _, loss = model(x, y)
            losses[i] = loss.item()
        out[split] = losses.mean().item()
    model.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path to a .txt corpus (yours)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--block-size", type=int, default=128)
    ap.add_argument("--n-layer", type=int, default=4)
    ap.add_argument("--n-head", type=int, default=4)
    ap.add_argument("--n-embd", type=int, default=256)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--lr", type=float, default=None,
                    help="learning rate; default = auto_lr(n_embd), width-scaled")
    ap.add_argument("--eval-interval", type=int, default=250)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed)

    if args.lr is None:
        args.lr = auto_lr(args.n_embd)
        print(f"lr: {args.lr:.2e} (auto, width-scaled from n_embd={args.n_embd}; "
              f"pass --lr to override)")

    text = Path(args.data).read_text(encoding="utf-8", errors="ignore")
    tok = CharTokenizer.from_text(text)
    corpus = Corpus(text, tok, device)
    print(f"corpus: {len(text):,} chars | vocab {tok.vocab_size} | device {device}")

    cfg = GPTConfig(vocab_size=tok.vocab_size, block_size=args.block_size,
                    n_layer=args.n_layer, n_head=args.n_head, n_embd=args.n_embd,
                    dropout=args.dropout)
    model = GPT(cfg).to(device)
    print(f"model: {model.num_params() / 1e6:.2f}M params | "
          f"{args.n_layer}L {args.n_head}H {args.n_embd}D")

    enable_fast_math()
    opt = make_optimizer(model, args.lr)
    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()
    amp = (lambda: torch.autocast("cuda", dtype=torch.bfloat16)) if use_bf16 \
        else (lambda: contextlib.nullcontext())

    Path(args.out).mkdir(parents=True, exist_ok=True)
    warmup = max(10, args.steps // 20)
    t0 = time.time()
    for step in range(args.steps):
        lr = cosine_lr(step, warmup, args.steps, args.lr, args.lr / 10)
        for g in opt.param_groups:
            g["lr"] = lr
        if step % args.eval_interval == 0 or step == args.steps - 1:
            L = estimate_loss(model, corpus, args.batch_size, args.block_size)
            print(f"step {step:5d} | train {L['train']:.4f} | val {L['val']:.4f} | "
                  f"lr {lr:.2e} | {time.time() - t0:.0f}s")
        x, y = corpus.get_batch("train", args.batch_size, args.block_size)
        with amp():
            _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    torch.save({"model": model.state_dict(), "config": cfg.__dict__}, Path(args.out) / "ckpt.pt")
    tok.save(Path(args.out) / "tokenizer.json")
    print(f"\nsaved model + tokenizer to {args.out}/")

    # Append this run to the shared log. A checkpoint folder tells you nothing
    # about what produced it a week later; the log does.
    wall = time.time() - t0
    final = estimate_loss(model, corpus, args.batch_size, args.block_size)
    runlog.record("train", device=device, out=args.out, source="cli",
                  corpus=runlog.corpus_fingerprint(text),
                  config={"n_layer": args.n_layer, "n_head": args.n_head,
                          "n_embd": args.n_embd, "block_size": args.block_size,
                          "batch_size": args.batch_size, "steps": args.steps,
                          "lr": args.lr, "dropout": args.dropout,
                          "seed": args.seed},
                  metrics={"train_loss": final["train"], "val_loss": final["val"],
                           "wall_s": wall,
                           "ms_per_step": wall / max(args.steps, 1) * 1000,
                           "params": model.num_params()},
                  leakage=_leak_of(text))
    print(f"recorded to {runlog.LOG.name}  (python runlog.py to review)")

    ctx = torch.zeros((1, 1), dtype=torch.long, device=device)
    sample = tok.decode(model.generate(ctx, 400, temperature=0.8, top_k=40)[0].tolist())
    print("\n--- sample from your model ---\n" + sample)


if __name__ == "__main__":
    main()
