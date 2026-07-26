"""exp_lr_width.py — experiment 1: is a hardcoded lr=3e-4 wrong for this width?

Two preregistered profiles, and they are DIFFERENT EXPERIMENTS, not two speeds
of one:
  canonical  prereg_lr_width.json       2000 steps, 7-LR grid  (~2.5 min)
  fast       prereg_lr_width_fast.json   800 steps, 4-LR grid  (~1 min)
The effect size decays roughly 9x from 400 to 2000 steps, so the fast profile
reports a LARGER gap for the same phenomenon and licenses only the weaker claim
"reaches lower train loss faster". Each run writes its profile, step count, grid
size and claim into its own verdict string, so the two cannot be quietly
conflated later.

Each profile runs:
  stage 1  sweep LR at fixed width, single seed, to select the treatment arm
  stage 2  control (3e-4) vs treatment, 5 seeds each, train-loss endpoint

Endpoint is TRAIN loss on purpose: a positional train/val split can duplicate
training text into validation, so a val endpoint is not yet trustworthy here.
Eval batches come from a dedicated torch.Generator, never the global RNG, so
every arm sees identical batches and evaluation cannot perturb training.

    python exp_lr_width.py                     # canonical, ~2.5 min
    python exp_lr_width.py --profile fast      # separate experiment, ~1 min
    python exp_lr_width.py --quick             # 400-step sanity pass, not a result
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from model import GPT, GPTConfig          # noqa: E402
from data import CharTokenizer, Corpus    # noqa: E402
from train import cosine_lr, enable_fast_math, make_optimizer  # noqa: E402

EVAL_SEED = 12345
EVAL_BATCHES = 40
# Measured, and the measurement reversed itself, which is why the number is
# recorded here rather than reasoned about: running ONE arm at a time, fp32 beats
# bf16 autocast (6.00 vs 8.36 ms/step) because the casts cost more than the
# arithmetic they save on a 3M-parameter model. Running four arms concurrently,
# which is the shipped default, bf16 wins by a wide margin end to end (163s vs
# 215s). Benchmark the configuration you actually run.
USE_AMP = True


def fixed_eval_batches(corpus: Corpus, batch_size: int, block_size: int, n: int):
    """Identical batches for every arm, drawn from our own Generator rather than
    the global RNG, so evaluating can never disturb the training stream."""
    dev = corpus.train.device
    g = torch.Generator(device=dev.type).manual_seed(EVAL_SEED)
    return [corpus.get_batch("train", batch_size, block_size, generator=g)
            for _ in range(n)]


@torch.no_grad()
def eval_train_loss(model, batches):
    model.eval()
    tot = 0.0
    for x, y in batches:
        _, loss = model(x, y)
        tot += loss.item()
    model.train()
    return tot / len(batches)


_W = {}


def _init_worker(cfg_d, device, corpus_path):
    enable_fast_math()
    """Each worker builds the corpus once and reuses it for every arm it runs.

    Arms are independent training runs, and this rig is launch-bound rather than
    compute-bound: a 3M-parameter step leaves the GPU idle while Python queues
    the next one. Running several arms in separate processes fills that idle
    time. Results are unchanged, because nothing is shared between arms except
    the read-only corpus, and each arm seeds its own RNG.
    """
    text = Path(corpus_path).read_text(encoding="utf-8", errors="ignore")
    tok = CharTokenizer.from_text(text)
    corpus = Corpus(text, tok, device)
    _W.update(tok=tok, corpus=corpus, device=device, cfg=cfg_d,
              batches=fixed_eval_batches(corpus, cfg_d["batch_size"],
                                         cfg_d["block_size"], EVAL_BATCHES))


def _run_arm(job):
    label, lr, seed = job
    loss, secs, _ = run_one(_W["corpus"], _W["tok"], lr, seed, _W["cfg"],
                            _W["device"], _W["batches"])
    return label, lr, seed, loss, secs


def _run_jobs(jobs, cfg_d, device, workers, corpus_path):
    """Run arms across processes, or in-process when workers == 1."""
    if workers <= 1:
        _init_worker(cfg_d, device, corpus_path)
        return [_run_arm(j) for j in jobs]
    ctx = mp.get_context("spawn")          # required on Windows, and CUDA-safe
    with ctx.Pool(processes=workers, initializer=_init_worker,
                  initargs=(cfg_d, device, corpus_path)) as pool:
        return pool.map(_run_arm, jobs)


def run_one(corpus, tok, lr, seed, cfg_d, device, eval_batches=None):
    """One training run. The corpus and tokenizer are built ONCE by the caller
    and reused: re-tokenising half a million characters per arm cost more than
    some of the arms did."""
    torch.manual_seed(seed)
    if eval_batches is None:
        eval_batches = fixed_eval_batches(corpus, cfg_d["batch_size"],
                                          cfg_d["block_size"], EVAL_BATCHES)

    cfg = GPTConfig(vocab_size=tok.vocab_size, block_size=cfg_d["block_size"],
                    n_layer=cfg_d["n_layer"], n_head=cfg_d["n_head"],
                    n_embd=cfg_d["n_embd"], dropout=0.0)
    model = GPT(cfg).to(device)
    opt = make_optimizer(model, lr)
    use_bf16 = USE_AMP and device == "cuda" and torch.cuda.is_bf16_supported()

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
    ap.add_argument("--profile", choices=["canonical", "fast"], default="canonical",
                    help="canonical = prereg_lr_width.json (2000 steps, 7 LRs). "
                         "fast = prereg_lr_width_fast.json (800 steps, 4 LRs), a "
                         "SEPARATE experiment licensing a different claim, not a "
                         "cheaper version of the canonical one.")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=4,
                    help="arms to run concurrently (1 = serial). The GPU is "
                         "launch-bound at this model size, so concurrency is "
                         "close to free.")
    args = ap.parse_args()

    pf = "prereg_lr_width_fast.json" if args.profile == "fast" else "prereg_lr_width.json"
    prereg = json.loads((HERE / pf).read_text(encoding="utf-8"))
    C = dict(prereg["fixed_config"])
    C = {k: C[k] for k in ("n_layer", "n_head", "n_embd", "block_size",
                           "batch_size", "steps")}
    if args.quick:
        C["steps"] = 400

    device = "cuda" if torch.cuda.is_available() else "cpu"
    corpus_path = HERE / "corpus.txt"
    text = corpus_path.read_text(encoding="utf-8", errors="ignore")
    print(f"device {device} | corpus {len(text):,} chars | workers {args.workers} "
          f"| config {C}")
    print(f"prereg bar: gap >= {prereg['success_bar']['primary']}\n")

    t_all = time.time()

    # ---------------- stage 1: sweep
    sweep_lrs = prereg["stage_1_sweep"]["lrs"]
    sweep_seed = prereg["stage_1_sweep"]["seed"]
    print("=== STAGE 1: LR sweep (seed %d, selects treatment arm) ===" % sweep_seed)
    t_stage = time.time()
    res = _run_jobs([("sweep", lr, sweep_seed) for lr in sweep_lrs],
                    C, device, args.workers, str(corpus_path))
    sweep = {lr: loss for _, lr, _, loss, _ in res}
    for _, lr, _, loss, secs in sorted(res, key=lambda r: r[1]):
        print(f"  lr {lr:<8.1e}  train loss {loss:.4f}   ({secs:.0f}s)")
    print(f"  stage 1 wall clock: {time.time() - t_stage:.0f}s")
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
    t_stage = time.time()
    jobs = ([("control", control_lr, sd) for sd in seeds]
            + [("treatment", treatment_lr, sd) for sd in seeds])
    res = _run_jobs(jobs, C, device, args.workers, str(corpus_path))
    arms = {"control": [], "treatment": []}
    for label, lr, sd, loss, secs in sorted(res, key=lambda r: (r[0], r[2])):
        arms[label].append(loss)
        print(f"  {label:<10} seed {sd}  train loss {loss:.4f}   ({secs:.0f}s)")
    print(f"  stage 2 wall clock: {time.time() - t_stage:.0f}s")

    c, t = arms["control"], arms["treatment"]
    mc, mt = sum(c) / len(c), sum(t) / len(t)
    gap = mc - mt
    overlap = not (max(t) < min(c) or max(c) < min(t))

    print("\n" + "=" * 62)
    print(f"control   lr {control_lr:.1e}  mean {mc:.4f}  range [{min(c):.4f}, {max(c):.4f}]")
    print(f"treatment lr {treatment_lr:.1e}  mean {mt:.4f}  range [{min(t):.4f}, {max(t):.4f}]")
    print(f"gap (control - treatment) = {gap:+.4f}   bar = 0.020")
    print(f"ranges overlap = {overlap}   (bar requires NO overlap)")
    passed = (gap >= 0.020) and (not overlap)
    # The verdict carries its own provenance. A label kept only in a filename or
    # a person's memory gets conflated with the canonical result eventually; one
    # written into the string itself travels with the number wherever it is
    # pasted.
    verdict = (f"{'PASS' if passed else 'FAIL / NULL'} "
               f"[{'QUICK SANITY RUN, not a result. ' if args.quick else ''}"
               f"{args.profile} profile: {C['steps']} steps, "
               f"{len(sweep_lrs)}-LR grid, {len(seeds)} seeds]")
    if args.profile == "fast":
        verdict += (" - claim: reaches lower train loss FASTER; "
                    "NOT the canonical effect size")
    print(f"\nPREREGISTERED VERDICT: {verdict}")
    if gap < 0 and abs(gap) >= 0.020:
        print("NOTE: control WON — the hypothesis is falsified on this rig.")
    print("=" * 62)

    # A sanity run must never overwrite a preregistered result file.
    if args.quick:
        out = HERE / "exp_lr_width_result_quick.json"
    elif args.profile == "fast":
        out = HERE / "exp_lr_width_result_fast.json"
    else:
        out = HERE / "exp_lr_width_result.json"
    out.write_text(json.dumps({
        "profile": args.profile, "prereg_file": pf, "verdict_string": verdict,
        "claim": prereg.get("claim_this_licenses", ""),
        "config": C, "device": device, "quick": args.quick,
        "sweep": {str(k): v for k, v in sweep.items()},
        "control_lr": control_lr, "treatment_lr": treatment_lr,
        "seeds": seeds, "control_losses": c, "treatment_losses": t,
        "mean_control": mc, "mean_treatment": mt, "gap": gap,
        "ranges_overlap": overlap, "passed": passed,
    }, indent=2), encoding="utf-8")
    print(f"wrote {out.name}   total wall clock {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()
