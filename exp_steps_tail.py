"""exp_steps_tail.py — go past 10,000 steps and look for the turn-up.

Executes prereg_steps_tail.json. Read that first; this file only runs it.

TRACKS THE GAP, NOT JUST THE LOSS. Past ~5k steps every additional step re-reads
text the model has already seen, so the failure worth catching is not "stops
improving" but "improves on memorised text while getting worse on unseen text".
That shows up as val minus train widening, and it shows up BEFORE val itself
turns up. Reporting only val would find the damage a doubling or two late.

WRITES AFTER EVERY ARM. The 160k arm alone is ~15 minutes per seed; a crash at
the end of a 90-minute run that lost the first 75 would be its own small
tragedy. Partial results are a real artifact, not a consolation prize.
"""
from __future__ import annotations

import contextlib
import json
import math
import time
from pathlib import Path

import torch

import baselines
import runlog
from data import CharTokenizer, Corpus
from model import GPT, GPTConfig
from train import auto_lr, cosine_lr, enable_fast_math, estimate_loss, make_optimizer

HERE = Path(__file__).resolve().parent
PREREG = json.loads((HERE / "prereg_steps_tail.json").read_text(encoding="utf-8"))
OUT = HERE / "exp_steps_tail_result.json"

STEPS_ARMS = PREREG["arms"]["steps"]
SEEDS = PREREG["arms"]["seeds"]
ARCH = dict(n_layer=4, n_head=4, n_embd=256, block_size=128)
BATCH, DROPOUT = 32, 0.1
CHARS_PER_STEP = BATCH * ARCH["block_size"]


def train_one(corpus, tok, device, steps: int, seed: int) -> dict:
    """One run, mirroring train.py's loop exactly. Returns train and val."""
    torch.manual_seed(seed)
    cfg = GPTConfig(vocab_size=tok.vocab_size, dropout=DROPOUT, **ARCH)
    model = GPT(cfg).to(device)
    lr = auto_lr(ARCH["n_embd"])
    opt = make_optimizer(model, lr)
    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()
    amp = (lambda: torch.autocast("cuda", dtype=torch.bfloat16)) if use_bf16 \
        else (lambda: contextlib.nullcontext())
    warmup = max(10, steps // 20)

    model.train()
    for step in range(steps):
        for g in opt.param_groups:
            g["lr"] = cosine_lr(step, warmup, steps, lr, lr / 10)
        xb, yb = corpus.get_batch("train", BATCH, ARCH["block_size"])
        with amp():
            _, loss = model(xb, yb)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    final = estimate_loss(model, corpus, BATCH, ARCH["block_size"])
    del model, opt
    if device == "cuda":
        torch.cuda.empty_cache()
    return {"train": float(final["train"]), "val": float(final["val"])}


def summarise(rows: list[dict], steps: int, corpus_chars: int,
              ngram_choices: float) -> dict:
    vals = [r["val"] for r in rows]
    trains = [r["train"] for r in rows]
    gaps = [r["val"] - r["train"] for r in rows]
    mean_val = sum(vals) / len(vals)
    return {
        "seeds_val": vals, "seeds_train": trains, "seeds_gap": gaps,
        "mean_val": mean_val, "spread_val": max(vals) - min(vals),
        "mean_train": sum(trains) / len(trains),
        "mean_gap": sum(gaps) / len(gaps), "spread_gap": max(gaps) - min(gaps),
        "choices": math.exp(mean_val),
        "closed_fraction": (ngram_choices - math.exp(mean_val)) / (ngram_choices - 1.0),
        "corpus_crossings": steps * CHARS_PER_STEP / corpus_chars,
    }


def main() -> None:
    enable_fast_math()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    text = (HERE / "corpus.txt").read_text(encoding="utf-8")
    tok = CharTokenizer.from_text(text)
    corpus = Corpus(text, tok, device)
    print(f"corpus {len(text):,} chars | vocab {tok.vocab_size} | device {device}",
          flush=True)
    print(f"one crossing of this corpus = {len(text)/CHARS_PER_STEP:,.0f} steps\n",
          flush=True)

    base = baselines.compare(corpus.train_text, corpus.val_text, tok.vocab_size)
    ngram_choices = base[f"ngram_{baselines.NGRAM_ORDER}"]["choices"]

    summary: dict[str, dict] = {}
    wall0 = time.time()
    for steps in STEPS_ARMS:
        rows = []
        for seed in SEEDS:
            t = time.time()
            r = train_one(corpus, tok, device, steps, seed)
            rows.append(r)
            print(f"  steps={steps:<7} seed={seed}  train={r['train']:.4f}  "
                  f"val={r['val']:.4f}  gap={r['val']-r['train']:+.4f}  "
                  f"({time.time()-t:.0f}s)", flush=True)
        s = summarise(rows, steps, len(text), ngram_choices)
        summary[str(steps)] = s
        print(f"  -> {steps}: val {s['mean_val']:.4f} (spread {s['spread_val']:.4f})  "
              f"gap {s['mean_gap']:+.4f}  crossings {s['corpus_crossings']:.1f}\n",
              flush=True)
        # Written after every arm, not at the end. See module docstring.
        OUT.write_text(json.dumps(
            {"prereg": PREREG["experiment"], "device": device, "baseline": base,
             "partial": True, "arms": summary,
             "wall_s": time.time() - wall0}, indent=2), encoding="utf-8")

    arms = [str(s) for s in STEPS_ARMS]
    comparisons = []
    for a, b in zip(arms, arms[1:]):
        gap = summary[a]["mean_val"] - summary[b]["mean_val"]   # +ve = b better
        noise = max(summary[a]["spread_val"], summary[b]["spread_val"])
        gap_growth = summary[b]["mean_gap"] - summary[a]["mean_gap"]
        gap_noise = max(summary[a]["spread_gap"], summary[b]["spread_gap"])
        comparisons.append({
            "from_steps": int(a), "to_steps": int(b),
            "val_change": gap, "val_noise": noise,
            "still_improving": bool(gap > noise),
            "turned_up": bool(-gap > noise),
            "gap_growth": gap_growth, "gap_noise": gap_noise,
            "memorising": bool(gap_growth > gap_noise),
        })

    if any(c["turned_up"] for c in comparisons):
        verdict = "TAIL FOUND — more training measurably made it worse on unseen text"
    elif any(c["memorising"] for c in comparisons):
        verdict = ("no turn-up yet, but the train/val gap is widening beyond noise — "
                   "memorising is detectable before it is costly")
    elif all(c["still_improving"] for c in comparisons):
        verdict = "still improving at every arm — no tail within the range tested"
    else:
        verdict = "flattened — gains fell inside seed noise, but nothing got worse"

    payload = {"prereg": PREREG["experiment"], "device": device, "partial": False,
               "baseline": base, "arms": summary, "comparisons": comparisons,
               "verdict": verdict, "wall_s": time.time() - wall0}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    runlog.record("experiment", kind_detail="steps_tail", device=device,
                  corpus=runlog.corpus_fingerprint(text),
                  metrics={"verdict": verdict, "wall_s": payload["wall_s"]})

    print("=" * 78)
    print(f"{'steps':>8} {'crossings':>10} {'train':>8} {'val':>8} {'gap':>8} "
          f"{'spread':>8} {'vs table':>9}")
    for k in arms:
        s = summary[k]
        print(f"{k:>8} {s['corpus_crossings']:>9.1f}x {s['mean_train']:>8.4f} "
              f"{s['mean_val']:>8.4f} {s['mean_gap']:>+8.4f} {s['spread_val']:>8.4f} "
              f"{s['closed_fraction']*100:>8.0f}%")
    print()
    for c in comparisons:
        if c["turned_up"]:
            mark = "WORSE — tail found"
        elif c["still_improving"]:
            mark = "still improving"
        else:
            mark = "inside noise"
        print(f"  {c['from_steps']:>6} -> {c['to_steps']:<7} val {c['val_change']:+.4f} "
              f"(noise {c['val_noise']:.4f})   gap {c['gap_growth']:+.4f} "
              f"(noise {c['gap_noise']:.4f})   {mark}"
              f"{'  MEMORISING' if c['memorising'] else ''}")
    print(f"\nVERDICT: {verdict}")
    print(f"wall {payload['wall_s']/60:.1f} min -> {OUT.name}")


if __name__ == "__main__":
    main()
