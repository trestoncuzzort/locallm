#!/usr/bin/env python
"""Adam trust-region scan over LoRA adapters (F2 and F9).

For each adapter tensor, count elements that lie outside the region a run could
legitimately have reached:

    lora_A:  |A| <= 1/sqrt(fan_in)  +  3.16 * SIGMA_LR
    lora_B:  |B| <= 0               +  3.16 * SIGMA_LR

1/sqrt(fan_in) is the peft LoRA init bound: kaiming_uniform_(a=sqrt(5)) gives
gain sqrt(1/3), std gain/sqrt(fan_in), and a uniform half-width sqrt(3)*std,
i.e. exactly 1/sqrt(fan_in). lora_B initialises to zero. 3.16*SIGMA_LR is the
Kingma & Ba Adam trust region: per step |dw| <~ lr, so |w - w0| <~ sum(lr).

SIGMA_LR is reconstructed from the run's own training_args.bin through the same
scheduler the run used, not assumed.

Weights are stored in bf16. A value at the init bound rounds to the nearest bf16,
which can land above it, so the comparison carries one ULP of tolerance at the
bound's magnitude. Without it every untrained adapter reports spurious violations.

Usage:
  adam_bound_scan.py --arm DIR [--arm DIR ...] [--a0 INIT_DIR] [--block 256]
"""
import argparse, json, math, os, sys, warnings
from collections import defaultdict

import torch
from safetensors.torch import load_file

warnings.filterwarnings("ignore")
TRUST = 3.16


def sigma_lr(arm_dir):
    """Sum of the learning rate over the run, via the run's own training_args.bin."""
    ta = os.path.join(arm_dir, "training_args.bin")
    if not os.path.exists(ta):
        return None, "no training_args.bin"
    args = torch.load(ta, weights_only=False)
    total = int(args.max_steps)
    derived = ""
    if total <= 0:
        # max_steps=-1: the run length came from the dataset. Recover it the way
        # the Trainer did -- floor(pairs / (per_device_bs * grad_accum * world)) * epochs.
        meta = os.path.join(arm_dir, "run_meta.json")
        if not os.path.exists(meta):
            return None, f"max_steps={total} and no run_meta.json: step count not recoverable"
        pairs = json.load(open(meta)).get("pairs")
        if not pairs:
            return None, f"max_steps={total} and run_meta has no pair count"
        eff = args.per_device_train_batch_size * args.gradient_accumulation_steps * max(1, args.world_size)
        total = int(pairs // eff * args.num_train_epochs)
        derived = f" [derived: {pairs} pairs / (bs {args.per_device_train_batch_size} * ga {args.gradient_accumulation_steps}) * {args.num_train_epochs} epochs]"
    warm = args.warmup_steps if args.warmup_steps > 0 else math.ceil(total * args.warmup_ratio)
    from transformers import get_scheduler
    p = torch.nn.Parameter(torch.zeros(1))
    opt = torch.optim.SGD([p], lr=args.learning_rate)
    sch = get_scheduler(args.lr_scheduler_type, opt, num_warmup_steps=warm, num_training_steps=total)
    lrs = []
    for _ in range(total):
        lrs.append(opt.param_groups[0]["lr"])
        sch.step()
    return sum(lrs), (f"{args.lr_scheduler_type} lr={args.learning_rate:g} "
                      f"steps={total} warmup={warm} sum_lr={sum(lrs):.6e}{derived}")


def ulp(x, dtype):
    """Width of one representable step at magnitude x, in the storage dtype."""
    if x == 0:
        return float(torch.finfo(dtype).tiny)
    t = torch.tensor([abs(x)], dtype=dtype)
    return float((torch.nextafter(t, torch.tensor([float("inf")], dtype=dtype)) - t).item())


def scan(arm_dir, a0=None, block=256):
    sd = load_file(os.path.join(arm_dir, "adapter_model.safetensors"))
    S, how = sigma_lr(arm_dir)
    if S is None:
        raise SystemExit(f"{arm_dir}: cannot reconstruct SIGMA_LR ({how})")
    slack = TRUST * S
    out = {"dir": arm_dir, "sigma_lr": S, "slack": slack, "schedule": how,
           "tensors": 0, "over": 0, "per_tensor": {}, "blocks": defaultdict(int),
           "colblocks": defaultdict(int),
           "max_excess": 0.0, "a0_delta": {}}
    for k, v in sorted(sd.items()):
        if "lora_A" not in k and "lora_B" not in k:
            continue
        out["tensors"] += 1
        isA = "lora_A" in k
        init_bound = 1.0 / math.sqrt(v.shape[1]) if isA else 0.0
        bound = init_bound + slack + ulp(init_bound + slack, v.dtype)
        a = v.detach().float().abs().flatten()
        mask = a > bound
        n = int(mask.sum())
        if n:
            out["over"] += n
            out["per_tensor"][k] = {"n": n, "bound": bound,
                                    "max_abs": float(a.max()), "numel": int(a.numel())}
            out["max_excess"] = max(out["max_excess"], float(a.max()) - bound)
            # Two binnings, because the manuscript specifies both and for a
            # (16, 14336) tensor they coincide only on row 0:
            #   flat  -- "binned by (layer, module, 256-aligned flat block)"
            #   col   -- "the observed violating columns ... are [2304, 2558]"
            # The decision rule's parenthetical is about columns, so `col` is
            # what the verdict uses; `flat` is reported alongside it.
            ncol = v.shape[1]
            for idx in mask.nonzero().flatten().tolist():
                out["blocks"][(k, idx // block)] += 1
                out["colblocks"][(k, (idx % ncol) // block)] += 1
        if a0 is not None and isA and k in a0:
            d = (v.detach().float() - a0[k].detach().float()).abs().max().item()
            out["a0_delta"][k] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="adapter dir (repeatable)")
    ap.add_argument("--a0", help="adapter dir holding the initialisation (an --max-steps 1 run)")
    ap.add_argument("--block", type=int, default=256)
    ap.add_argument("--focus", default="layers.1.mlp.down_proj.lora_A",
                    help="tensor named in the preregistered F2 rule")
    ap.add_argument("--focus-block", type=int, default=9)
    a = ap.parse_args()

    a0 = load_file(os.path.join(a.a0, "adapter_model.safetensors")) if a.a0 else None
    if a0 is not None:
        print(f"A0 reference: {a.a0}\n")

    results = {}
    for arm in a.arm:
        r = scan(arm, a0, a.block)
        results[arm] = r
        name = os.path.basename(arm.rstrip("/"))
        print(f"== {name} ==")
        print(f"   schedule        : {r['schedule']}")
        print(f"   3.16*SIGMA_LR   : {r['slack']:.6e}")
        print(f"   tensors scanned : {r['tensors']}")
        print(f"   over-bound elts : {r['over']}")
        if r["over"]:
            print(f"   max excess over bound : {r['max_excess']:.6e}")
            for k, d in sorted(r["per_tensor"].items(), key=lambda x: -x[1]["n"])[:8]:
                print(f"      {k.split('base_model.model.model.')[-1]:<52} {d['n']:>8} / {d['numel']}  max|w|={d['max_abs']:.4e} bound={d['bound']:.4e}")
        lo, hi = a.focus_block * a.block, (a.focus_block + 1) * a.block - 1
        hit_col = sum(n for (k, b), n in r["colblocks"].items() if a.focus in k and b == a.focus_block)
        hit_flat = sum(n for (k, b), n in r["blocks"].items() if a.focus in k and b == a.focus_block)
        print(f"   focus {a.focus} [{lo}, {hi}]:")
        print(f"      columns  [{lo},{hi}] across all rows : {hit_col:>5}   <- the decision rule")
        print(f"      flat block {a.focus_block} (row 0 only)          : {hit_flat:>5}")
        if r["a0_delta"]:
            mx = max(r["a0_delta"].values())
            within = sum(1 for d in r["a0_delta"].values() if d <= r["slack"])
            print(f"   max|A - A0|     : {mx:.6e}   (trust region {r['slack']:.6e}; "
                  f"{within}/{len(r['a0_delta'])} tensors inside)")
        print()

    print("=" * 74)
    print("PREREGISTERED DECISION RULE (manuscript-v9.md:917), quoted:")
    print('  "the mechanism is confirmed iff adamw_torch yields zero such elements')
    print('   across all 448 tensors while adamw_bnb_8bit yields at least 50 inside')
    print('   the block [2304, 2559] (block index 9, zero-based) of')
    print('   layers.1.mlp.down_proj.lora_A."')
    print("=" * 74)
    torch_arm = next((k for k in results if "adamw_torch" in k), None)
    bnb_arm = next((k for k in results if "f2-adamw_bnb_8bit" in k), None)
    if torch_arm and bnb_arm:
        t_over = results[torch_arm]["over"]
        b_hit = sum(n for (k, b), n in results[bnb_arm]["colblocks"].items()
                    if a.focus in k and b == a.focus_block)
        print(f"  adamw_torch      over-bound elements, all tensors : {t_over}   (rule needs 0)")
        print(f"  adamw_bnb_8bit   over-bound in focus columns       : {b_hit}   (rule needs >= 50)")
        verdict = "CONFIRMED" if (t_over == 0 and b_hit >= 50) else "NOT CONFIRMED"
        print(f"  VERDICT: {verdict}")
        if t_over > 0:
            print("  Note: adamw_torch producing over-bound elements is the manuscript's")
            print("  refutation branch - cause would be clipping, a kernel fault, or a")
            print("  driver event; the bound survives as a detector, the mechanism does not.")
    else:
        print("  (need both f2-adamw_torch and f2-adamw_bnb_8bit arms for the verdict)")


if __name__ == "__main__":
    main()
