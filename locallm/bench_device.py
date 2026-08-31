"""bench_device.py — measure what YOUR machine can actually train, then say so.

    python bench_device.py

Times the real training step on every device available here, at several model
sizes, and reports how long a full 2000-step run would take on each. No advice
that is not backed by a number measured on this machine.

Why this exists: "it runs fine on CPU, just slower" is the kind of claim that
gets repeated until someone tries it on a laptop and waits an hour. Whether a
CPU-only install is reasonable is a question with a measurable answer, and the
answer differs per machine, so the machine should answer it.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from model import GPT, GPTConfig          # noqa: E402
from data import CharTokenizer, Corpus    # noqa: E402
import runlog                            # noqa: E402
from train import auto_lr, enable_fast_math, make_optimizer, sync, wants_bf16  # noqa: E402

# Sizes worth knowing about: something a weak machine can hold, the shipped
# default, and something that needs real hardware.
SIZES = [
    ("small",   dict(n_layer=2, n_head=4, n_embd=128, block_size=128, batch_size=32)),
    ("default", dict(n_layer=4, n_head=4, n_embd=256, block_size=128, batch_size=32)),
    ("large",   dict(n_layer=6, n_head=8, n_embd=512, block_size=256, batch_size=32)),
]
FULL_RUN_STEPS = 2000


def time_steps(corpus, tok, device, cfg_d, steps, warmup):
    cfg = GPTConfig(vocab_size=tok.vocab_size, block_size=cfg_d["block_size"],
                    n_layer=cfg_d["n_layer"], n_head=cfg_d["n_head"],
                    n_embd=cfg_d["n_embd"], dropout=0.0)
    model = GPT(cfg).to(device)
    opt = make_optimizer(model, auto_lr(cfg_d["n_embd"]))
    B, T = cfg_d["batch_size"], cfg_d["block_size"]
    use_bf16 = wants_bf16(device)

    def one():
        x, y = corpus.get_batch("train", B, T)
        if use_bf16:
            with torch.autocast(device, dtype=torch.bfloat16):
                _, loss = model(x, y)
        else:
            _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    for _ in range(warmup):
        one()
    sync(device)
    t0 = time.time()
    for _ in range(steps):
        one()
    sync(device)
    elapsed = time.time() - t0
    return model.num_params(), elapsed / steps * 1000, B * T * steps / elapsed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "corpus.txt"))
    ap.add_argument("--gpu-steps", type=int, default=200)
    ap.add_argument("--cpu-steps", type=int, default=25,
                    help="fewer, because CPU steps are slow and we are measuring "
                         "a rate, not running a job")
    args = ap.parse_args()

    enable_fast_math()
    text = Path(args.data).read_text(encoding="utf-8", errors="ignore")
    tok = CharTokenizer.from_text(text)

    devices = ["cpu"]
    gpu_name = None
    if torch.cuda.is_available():
        devices.append("cuda")
        p = torch.cuda.get_device_properties(0)
        gpu_name = p.name
        gpu_desc = f"{p.name}, {p.total_memory / 1e9:.1f} GB"
    elif torch.backends.mps.is_available():
        # Apple gives the GPU no queryable name; the shared-memory budget is
        # what actually bounds model size here, so report that instead.
        devices.append("mps")
        gpu_name = "Apple silicon (MPS)"
        gpu_desc = (f"Apple silicon via MPS, "
                    f"{torch.mps.recommended_max_memory() / 1e9:.1f} GB usable")
    print(f"machine: {platform.processor() or platform.machine()}")
    print(f"gpu    : {gpu_desc}" if gpu_name else "gpu    : none detected")
    print(f"corpus : {len(text):,} chars, vocab {tok.vocab_size}\n")

    rows, results = [], {}
    for device in devices:
        corpus = Corpus(text, tok, device)
        steps = args.cpu_steps if device == "cpu" else args.gpu_steps
        for name, cfg_d in SIZES:
            params, ms, tok_s = time_steps(corpus, tok, device, cfg_d, steps,
                                           warmup=5 if device == "cpu" else 20)
            full = ms * FULL_RUN_STEPS / 1000
            rows.append((device, name, params, ms, tok_s, full, steps))
            results[f"{device}/{name}"] = {
                "params": params, "ms_per_step": round(ms, 2),
                "tokens_per_s": round(tok_s), "full_2000_step_s": round(full, 1),
                "measured_over_steps": steps}

    print(f"{'device':7} {'size':8} {'params':>9}  {'ms/step':>8} {'tok/s':>9}"
          f"  {'2000 steps':>12}")
    print("-" * 62)
    for device, name, params, ms, tok_s, full, _ in rows:
        full_s = f"{full:.0f}s" if full < 120 else f"{full / 60:.1f} min"
        print(f"{device:7} {name:8} {params / 1e6:8.2f}M  {ms:7.2f}  {tok_s:9,.0f}"
              f"  {full_s:>12}")

    gpu_dev = next((d for d in devices if d != "cpu"), None)
    if gpu_dev:
        print()
        for name, _ in SIZES:
            c = results[f"cpu/{name}"]["ms_per_step"]
            g = results[f"{gpu_dev}/{name}"]["ms_per_step"]
            print(f"  {name:8} GPU is {c / g:5.1f}x faster than CPU here")

    verdict = []
    for name, _ in SIZES:
        cpu_full = results[f"cpu/{name}"]["full_2000_step_s"]
        if cpu_full <= 300:
            verdict.append(f"  {name:8} CPU-only is fine ({cpu_full / 60:.1f} min for a full run)")
        elif cpu_full <= 1800:
            verdict.append(f"  {name:8} CPU-only is usable but slow ({cpu_full / 60:.0f} min)")
        else:
            verdict.append(f"  {name:8} CPU-only is impractical ({cpu_full / 3600:.1f} hours)")
    print("\nwhat this machine says about a CPU-only install:")
    print("\n".join(verdict))

    out = HERE / "bench_device_result.json"
    out.write_text(json.dumps({
        "machine": platform.processor() or platform.machine(),
        "gpu": gpu_name,
        "torch": torch.__version__, "full_run_steps": FULL_RUN_STEPS,
        "results": results}, indent=2), encoding="utf-8")
    print(f"\nwrote {out.name}")


if __name__ == "__main__":
    main()
