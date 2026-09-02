"""exp_steps_vs_quality.py — does training longer actually help, or is it luck?

Runs the arms declared in prereg_steps_vs_quality.json and answers against the
success bar written there BEFORE any run happened. Read that file first; this
one only executes it.

WHY IT LOADS THE CORPUS ONCE. Shelling out to train.py twenty times would re-read
and re-tokenise 20MB and rebuild the same trigram table twenty times, which is
about six minutes of pure repetition on a run that is otherwise ~12. It would
also make the split a per-process accident rather than one fixed object. One
Corpus, one baseline, twenty models.

WHY THE BASELINE IS COMPUTED ONCE. Every arm is scored on the identical holdout,
so the lookup table's score is a property of the text, not of the run. Computing
it per-run would produce twenty identical numbers and invite someone to average
them as if they were measurements.
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
from train import (auto_lr, cosine_lr, enable_fast_math, estimate_loss,
                   make_optimizer, pick_device, wants_bf16)

HERE = Path(__file__).resolve().parent
PREREG = json.loads((HERE / "prereg_steps_vs_quality.json").read_text(encoding="utf-8"))
OUT = HERE / "exp_steps_vs_quality_result.json"

STEPS_ARMS = PREREG["arms"]["steps"]
SEEDS = PREREG["arms"]["seeds"]
ARCH = dict(n_layer=4, n_head=4, n_embd=256, block_size=128)
BATCH, DROPOUT = 32, 0.1


def train_one(corpus, tok, device, steps: int, seed: int) -> float:
    """One run. Returns final validation loss on the fixed holdout.

    This loop mirrors train.py's exactly — same warmup rule, same cosine
    schedule and min_lr, same grad clip, same bf16 autocast when the card
    supports it. An experiment that trains a LOOKALIKE of the product measures
    the lookalike; every line here that differs from train.py:164-181 would be a
    silent confound in the result.
    """
    torch.manual_seed(seed)
    cfg = GPTConfig(vocab_size=tok.vocab_size, dropout=DROPOUT, **ARCH)
    model = GPT(cfg).to(device)
    lr = auto_lr(ARCH["n_embd"])
    opt = make_optimizer(model, lr)

    use_bf16 = wants_bf16(device)
    amp = (lambda: torch.autocast(device, dtype=torch.bfloat16)) if use_bf16 \
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
    elif device == "mps":
        torch.mps.empty_cache()
    return float(final["val"])


def main() -> None:
    enable_fast_math()
    device = pick_device()
    text = (HERE / "corpus.txt").read_text(encoding="utf-8")
    tok = CharTokenizer.from_text(text)
    corpus = Corpus(text, tok, device)
    print(f"corpus {len(text):,} chars | vocab {tok.vocab_size} | device {device}", flush=True)

    print("scoring the lookup table once (same holdout for every arm)...", flush=True)
    t0 = time.time()
    base = baselines.compare(corpus.train_text or "", corpus.val_text or "",
                             tok.vocab_size)
    ngram_choices = base[f"ngram_{baselines.NGRAM_ORDER}"]["choices"]
    print(f"  trigram: {base[f'ngram_{baselines.NGRAM_ORDER}']['bits_per_char']:.3f} "
          f"bits/char, {ngram_choices:.2f} choices  ({time.time()-t0:.1f}s)\n", flush=True)

    # A baseline is only worth reporting on a holdout that is worth reporting.
    # baselines.py has said so in prose since it was written and studio.py has
    # enforced it since; this file published closed_fraction for any corpus at
    # all, including ones with no holdout to speak of.
    ineligible = baselines.holdout_eligibility(text, corpus.train_text,
                                               corpus.val_text,
                                               corpus.val_frac, corpus.seed)
    if ineligible:
        print(f"  NOT ELIGIBLE for a baseline comparison: {ineligible}\n"
              f"  closed_fraction will be recorded as null for every arm; the "
              f"val losses below stand on their own.\n", flush=True)

    results: dict[str, list[float]] = {}
    wall0 = time.time()
    for steps in STEPS_ARMS:
        row = []
        for seed in SEEDS:
            t = time.time()
            val = train_one(corpus, tok, device, steps, seed)
            row.append(val)
            print(f"  steps={steps:<6} seed={seed}  val={val:.4f}  "
                  f"({time.time()-t:.1f}s)", flush=True)
        results[str(steps)] = row
        lo, hi = min(row), max(row)
        print(f"  -> steps={steps}: mean {sum(row)/len(row):.4f}  "
              f"spread {hi-lo:.4f}\n", flush=True)

    # ---- analysis, against the bar declared before any of this ran -----------
    summary = {}
    for steps, row in results.items():
        mean = sum(row) / len(row)
        closed, why = baselines.closed_fraction(ngram_choices, math.exp(mean),
                                                ineligible)
        summary[steps] = {
            "seeds": row, "mean": mean, "min": min(row), "max": max(row),
            "spread": max(row) - min(row),
            "choices": math.exp(mean),
            "closed_fraction": closed, "closed_fraction_reason": why,
        }

    comparisons = []
    arms = [str(s) for s in STEPS_ARMS]
    for a, b in zip(arms, arms[1:]):
        gap = summary[a]["mean"] - summary[b]["mean"]          # positive = b better
        noise = max(summary[a]["spread"], summary[b]["spread"])
        comparisons.append({
            "from_steps": int(a), "to_steps": int(b),
            "gap_in_val_loss": gap, "wider_seed_spread": noise,
            "beats_noise": bool(gap > noise),
        })

    verdict = ("longer training measurably helps"
               if all(c["beats_noise"] for c in comparisons)
               else "some step increases are NOT distinguishable from seed luck")

    payload = {
        "prereg": PREREG["experiment"],
        "success_bar": PREREG["success_bar"]["primary"],
        "device": device,
        "wall_s": time.time() - wall0,
        "baseline": base,
        "holdout_eligible": ineligible is None,
        "ineligible_reason": ineligible,
        "arms": summary,
        "comparisons": comparisons,
        "verdict": verdict,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    runlog.record("experiment", kind_detail="steps_vs_quality", device=device,
                  corpus=runlog.corpus_fingerprint(text),
                  metrics={"verdict": verdict, "wall_s": payload["wall_s"]})

    print("=" * 70)
    print(f"{'steps':>7} {'mean val':>10} {'spread':>8} {'choices':>9} {'vs table':>9}")
    for steps in arms:
        s = summary[steps]
        vs = (f"{s['closed_fraction']*100:>8.0f}%"
              if s["closed_fraction"] is not None else f"{'n/a':>9}")
        print(f"{steps:>7} {s['mean']:>10.4f} {s['spread']:>8.4f} "
              f"{s['choices']:>9.2f} {vs}")
    if ineligible:
        print(f"  vs table: n/a -- {ineligible}")
    print()
    for c in comparisons:
        mark = "REAL" if c["beats_noise"] else "inside noise"
        print(f"  {c['from_steps']:>5} -> {c['to_steps']:<6} improved {c['gap_in_val_loss']:.4f}"
              f"   seed luck moves it {c['wider_seed_spread']:.4f}   {mark}")
    print(f"\nVERDICT: {verdict}")
    print(f"written to {OUT.name}")


if __name__ == "__main__":
    main()
