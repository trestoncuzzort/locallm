"""exp_lr_width.py — experiment 1: is a hardcoded lr=3e-4 wrong for this width?

Runs the preregistered experiment in prereg_lr_width.json:
  stage 1  sweep LR at fixed width, single seed, to select the treatment arm
  stage 2  control (3e-4) vs treatment, 5 seeds each, train-loss endpoint

Endpoint is TRAIN loss on purpose: a positional train/val split can duplicate
training text into validation, so a val endpoint is not yet trustworthy here.
Eval batches come from a dedicated torch.Generator, never the global RNG, so
every arm sees identical batches and evaluation cannot perturb training.

    python exp_lr_width.py            # full experiment
    python exp_lr_width.py --quick    # 400 steps, for a fast sanity pass
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from model import GPT, GPTConfig          # noqa: E402
from data import CharTokenizer, Corpus    # noqa: E402
from train import cosine_lr               # noqa: E402

EVAL_SEED = 12345
EVAL_BATCHES = 40


def fixed_eval_batches(corpus: Corpus, batch_size: int, block_size: int, n: int):
    """Identical batches for every arm — drawn from our own Generator, not the
    global RNG, so evaluating can never disturb the training stream."""
    g = torch.Generator().manual_seed(EVAL_SEED)
    d = corpus.train
    out = []
    for _ in range(n):
        ix = torch.randint(len(d) - block_size, (batch_size,), generator=g)
        x = torch.stack([d[i:i + block_size] for i in ix]).to(corpus.device)
        y = torch.stack([d[i + 1:i + 1 + block_size] for i in ix]).to(corpus.device)
        out.append((x, y))
    return out


@torch.no_grad()
def eval_train_loss(model, batches):
    model.eval()
    tot = 0.0
    for x, y in batches:
        _, loss = model(x, y)
        tot += loss.item()
    model.train()
    return tot / len(batches)


def run_one(text, lr, seed, cfg_d, device, eval_batches=None):
    torch.manual_seed(seed)
    tok = CharTokenizer.from_text(text)
    corpus = Corpus(text, tok, device)
    if eval_batches is None:
        eval_batches = fixed_eval_batches(corpus, cfg_d["batch_size"],
                                          cfg_d["block_size"], EVAL_BATCHES)

    cfg = GPTConfig(vocab_size=tok.vocab_size, block_size=cfg_d["block_size"],
                    n_layer=cfg_d["n_layer"], n_head=cfg_d["n_head"],
                    n_embd=cfg_d["n_embd"], dropout=0.0)
    model = GPT(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95),
                            weight_decay=0.1)
    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()

    steps = cfg_d["steps"]
    warmup = max(10, steps // 20)
    t0 = time.time()
    for step in range(steps):
        for g in opt.param_groups:
            g["lr"] = cosine_lr(step, warmup, steps, lr, lr / 10)
        x, y = corpus.get_batch("train", cfg_d["batch_size"], cfg_d["block_size"])
        if use_bf16:
            with torch.autocast("cuda", dtype=torch.bfloat16):
                _, loss = model(x, y)
        else:
            _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if not torch.isfinite(loss):
            return float("nan"), time.time() - t0, eval_batches

    return eval_train_loss(model, eval_batches), time.time() - t0, eval_batches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    prereg = json.loads((HERE / "prereg_lr_width.json").read_text(encoding="utf-8"))
    C = dict(prereg["fixed_config"])
    C = {k: C[k] for k in ("n_layer", "n_head", "n_embd", "block_size",
                           "batch_size", "steps")}
    if args.quick:
        C["steps"] = 400

    device = "cuda" if torch.cuda.is_available() else "cpu"
    text = (HERE / "corpus.txt").read_text(encoding="utf-8", errors="ignore")
    print(f"device {device} | corpus {len(text):,} chars | config {C}")
    print(f"prereg bar: gap >= {prereg['success_bar']['primary']}\n")

    # ---------------- stage 1: sweep
    sweep_lrs = prereg["stage_1_sweep"]["lrs"]
    sweep_seed = prereg["stage_1_sweep"]["seed"]
    print("=== STAGE 1: LR sweep (seed %d, selects treatment arm) ===" % sweep_seed)
    sweep, batches = {}, None
    for lr in sweep_lrs:
        loss, secs, batches = run_one(text, lr, sweep_seed, C, device, batches)
        sweep[lr] = loss
        print(f"  lr {lr:<8.1e}  train loss {loss:.4f}   ({secs:.0f}s)")
    finite = {k: v for k, v in sweep.items() if v == v}
    if not finite:
        print("\nAll sweep arms diverged (NaN). Stopping — nothing to confirm.")
        return
    treatment_lr = min(finite, key=finite.get)
    control_lr = prereg["stage_2_confirm"]["control_lr"]
    print(f"\n  -> treatment selected by rule (lowest loss): lr = {treatment_lr:.1e}")
    if treatment_lr == control_lr:
        print("  -> treatment == control; the shipped default already wins this sweep.")

    # ---------------- stage 2: confirm
    seeds = prereg["stage_2_confirm"]["seeds"]
    print(f"\n=== STAGE 2: control {control_lr:.1e} vs treatment {treatment_lr:.1e}, "
          f"seeds {seeds} ===")
    arms = {"control": (control_lr, []), "treatment": (treatment_lr, [])}
    for name, (lr, acc) in arms.items():
        for s in seeds:
            loss, secs, batches = run_one(text, lr, s, C, device, batches)
            acc.append(loss)
            print(f"  {name:<10} seed {s}  train loss {loss:.4f}   ({secs:.0f}s)")

    c, t = arms["control"][1], arms["treatment"][1]
    mc, mt = sum(c) / len(c), sum(t) / len(t)
    gap = mc - mt
    overlap = not (max(t) < min(c) or max(c) < min(t))

    print("\n" + "=" * 62)
    print(f"control   lr {control_lr:.1e}  mean {mc:.4f}  range [{min(c):.4f}, {max(c):.4f}]")
    print(f"treatment lr {treatment_lr:.1e}  mean {mt:.4f}  range [{min(t):.4f}, {max(t):.4f}]")
    print(f"gap (control - treatment) = {gap:+.4f}   bar = 0.020")
    print(f"ranges overlap = {overlap}   (bar requires NO overlap)")
    passed = (gap >= 0.020) and (not overlap)
    print(f"\nPREREGISTERED VERDICT: {'PASS' if passed else 'FAIL / NULL'}")
    if gap < 0 and abs(gap) >= 0.020:
        print("NOTE: control WON — the hypothesis is falsified on this rig.")
    print("=" * 62)

    out = HERE / "exp_lr_width_result.json"
    out.write_text(json.dumps({
        "config": C, "device": device, "quick": args.quick,
        "sweep": {str(k): v for k, v in sweep.items()},
        "control_lr": control_lr, "treatment_lr": treatment_lr,
        "seeds": seeds, "control_losses": c, "treatment_losses": t,
        "mean_control": mc, "mean_treatment": mt, "gap": gap,
        "ranges_overlap": overlap, "passed": passed,
    }, indent=2), encoding="utf-8")
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
