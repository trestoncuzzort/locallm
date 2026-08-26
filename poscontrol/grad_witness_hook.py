#!/usr/bin/env python3
"""grad_witness_hook.py - F2's gradient discriminator for the layer-1 block artifact.

manuscript-v9.md:917 preregisters this:

    "A one-step gradient witness (grad_witness_hook.py, about 5 min of GPU) hooks
     layers.1.mlp.down_proj.lora_A.grad and records channel 2427's squared gradient
     against the median of its 255 block-mates, and the same for channel 198's block
     [0, 255], whose within-block dynamic range is about 70x smaller and should
     therefore show a weaker effect or none."

WHY IT IS NOT ONE STEP HERE. F9 states the reason itself: "dL/dA = 0 while B = 0".
LoRA computes dW = B @ A with B initialised to zero, so dL/dA = B^T @ (...) is
IDENTICALLY ZERO until B has been moved by an optimizer step. And on this pipeline a
--max-steps 1 run takes its single step at lr = 0, because transformers computes warmup
as ceil(num_training_steps * warmup_ratio) = ceil(1 * 0.1) = 1, so B never leaves zero.
A literal one-step witness therefore records an all-zero gradient and discriminates
nothing. The two preregistered entries contradict each other on this point.

So this runs the F2 arm configuration unchanged (--max-steps 20, lr 2e-4, seed 1234,
adamw_bnb_8bit) and captures the gradient at EVERY optimizer step, reporting which
steps carry a nonzero dL/dA. The comparison the entry asks for is then read off the
first step where the gradient exists at all.

CLIPPING. transformers clips at trainer.py:2511-2516, BEFORE it fires
on_pre_optimizer_step at :2532, so the captured gradient is post-clipping. Clipping is
a single global rescale, so every ratio reported here - which is what the decision rests
on - is unchanged by it. The raw grad_norm is recorded alongside so the scale is visible.

Usage:
    export SRLM_VERIFY_PY=$PWD/.venv-train/bin/python
    ~/gpuguard.sh -- .venv-train/bin/python poscontrol/grad_witness_hook.py \\
        --out /tmp/grad_witness --json /tmp/grad_witness/witness.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# peft names the LIVE parameter with the adapter name inserted -
# "...lora_A.default.weight" - while the SAVED safetensors key is "...lora_A.weight".
# Matching the saved form against named_parameters() silently finds nothing.
TENSOR = "layers.1.mlp.down_proj.lora_A."
BLOCK = 256
FOCUS_CH = 2427          # the massive-activation channel
FOCUS_BLK = 9            # columns [2304, 2559]
CONTROL_CH = 198         # the preregistered control channel
CONTROL_BLK = 0          # columns [0, 255]

_CAPTURED: list[dict] = []
_FIRED = {"hook": 0, "matched": 0, "grad_none": 0}
_SEEN_NAMES: list[str] = []


def _stats(g, torch):
    """Per-column squared gradient of a (rank, in_features) lora_A gradient."""
    import math
    col_sq = (g.float() ** 2).sum(dim=0)          # sum over the 16 LoRA rows
    n = col_sq.numel()
    out = {"n_cols": int(n), "total_sq": float(col_sq.sum()),
           "nonzero_cols": int((col_sq > 0).sum())}

    def block_report(ch, blk):
        lo, hi = blk * BLOCK, (blk + 1) * BLOCK - 1
        band = col_sq[lo:hi + 1]
        j = ch - lo
        mates = torch.cat([band[:j], band[j + 1:]])
        med = float(mates.median())
        val = float(band[j])
        rank = int((band > band[j]).sum()) + 1
        return {
            "channel": ch, "block": blk, "cols": [lo, hi],
            "channel_sq": val,
            "blockmates_median_sq": med,
            "blockmates_max_sq": float(mates.max()),
            "ratio_channel_over_median": (val / med) if med > 0 else float("inf") if val > 0 else 0.0,
            "rank_in_block": rank,
            "block_absmax_sq": float(band.max()),
            "block_dynamic_range": (float(band.max()) / med) if med > 0 else float("inf"),
        }

    out["focus"] = block_report(FOCUS_CH, FOCUS_BLK)
    out["control"] = block_report(CONTROL_CH, CONTROL_BLK)
    # Which 256-column block holds the largest single column, and by how much.
    nblk = n // BLOCK
    blk_max = col_sq[: nblk * BLOCK].reshape(nblk, BLOCK).max(dim=1).values
    top = int(blk_max.argmax())
    out["argmax_block"] = {"block": top, "cols": [top * BLOCK, top * BLOCK + BLOCK - 1],
                           "max_sq": float(blk_max[top])}
    out["argmax_col"] = int(col_sq.argmax())
    return out


def _make_callback(trainer_ref):
    from transformers import TrainerCallback
    import torch

    class GradWitness(TrainerCallback):
        """Fires at trainer.py:2532, after clipping, before optimizer.step()."""

        def on_pre_optimizer_step(self, args, state, control, **kw):
            _FIRED["hook"] += 1
            model = trainer_ref[0].model
            for name, p in model.named_parameters():
                if TENSOR in name and name.endswith("weight"):
                    _FIRED["matched"] += 1
                    if not _SEEN_NAMES:
                        _SEEN_NAMES.append(name)
                    if p.grad is None:
                        _FIRED["grad_none"] += 1
                        break
                    rec = _stats(p.grad.detach(), torch)
                    rec["step"] = int(state.global_step)
                    rec["tensor"] = name
                    rec["shape"] = list(p.shape)
                    _CAPTURED.append(rec)
                    break
            return control

    return GradWitness()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="/tmp/grad_witness",
                    help="adapter output dir for the underlying run (throwaway)")
    ap.add_argument("--json", default=None, help="write the full per-step record here")
    ap.add_argument("--max-steps", type=int, default=20,
                    help="F2's arm configuration. Fewer than 3 cannot work: see module docstring.")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--optim", default="adamw_bnb_8bit")
    a = ap.parse_args()

    if not os.environ.get("SRLM_VERIFY_PY"):
        sys.exit("SRLM_VERIFY_PY must be exported or dataset_gate SystemExits at import.")
    if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("0", None, ""):
        print(f"[witness] CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')}")

    os.chdir(REPO)
    sys.path.insert(0, str(REPO))

    import trl
    import train_native

    orig = trl.DPOTrainer
    ref: list = [None]

    class WitnessTrainer(orig):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            ref[0] = self
            self.add_callback(_make_callback(ref))

    trl.DPOTrainer = WitnessTrainer
    try:
        sys.argv = ["train_native.py", "--out", a.out, "--max-steps", str(a.max_steps),
                    "--lr", str(a.lr), "--seed", str(a.seed), "--optim", a.optim]
        train_native.main()
    finally:
        trl.DPOTrainer = orig

    print(f"\n[witness] hook fired {_FIRED['hook']}x, matched the tensor {_FIRED['matched']}x, "
          f"grad was None {_FIRED['grad_none']}x")
    if _SEEN_NAMES:
        print(f"[witness] live parameter name: {_SEEN_NAMES[0]}")
    if not _CAPTURED:
        if _FIRED["hook"] == 0:
            sys.exit("[witness] on_pre_optimizer_step never fired - the DPOTrainer patch did not take.")
        if _FIRED["matched"] == 0:
            sys.exit(f"[witness] hook fired but no parameter matched {TENSOR!r} - naming mismatch.")
        sys.exit("[witness] tensor matched but .grad was None at every step.")

    live = [r for r in _CAPTURED if r["total_sq"] > 0]
    print("\n" + "=" * 78)
    print(f"GRADIENT WITNESS - {TENSOR}")
    print(f"steps captured: {len(_CAPTURED)}   with nonzero dL/dA: {len(live)}")
    if len(live) < len(_CAPTURED):
        z = [r['step'] for r in _CAPTURED if r['total_sq'] == 0]
        print(f"steps with dL/dA identically zero: {z}")
        print("  (expected while B = 0: dL/dA = B^T @ (...) = 0. See module docstring.)")
    print("=" * 78)

    if not live:
        print("\nNO STEP CARRIED A NONZERO dL/dA. The witness discriminates nothing at this")
        print("step count, which is itself the reportable result - see the module docstring.")
    else:
        hdr = (f"{'step':>4}  {'focus ch2427 sq':>17}  {'blk9 median':>13}  {'ratio':>9}  "
               f"{'rank':>7}  {'ctrl ch198 sq':>14}  {'blk0 median':>13}  {'ratio':>9}  {'rank':>7}")
        print("\n" + hdr)
        print("-" * len(hdr))
        for r in live:
            f, c = r["focus"], r["control"]
            print(f"{r['step']:>4}  {f['channel_sq']:>17.6e}  {f['blockmates_median_sq']:>13.6e}  "
                  f"{f['ratio_channel_over_median']:>9.2f}  {f['rank_in_block']:>4}/256  "
                  f"{c['channel_sq']:>14.6e}  {c['blockmates_median_sq']:>13.6e}  "
                  f"{c['ratio_channel_over_median']:>9.2f}  {c['rank_in_block']:>4}/256")

        first = live[0]
        print("\nPREREGISTERED PREDICTION (manuscript-v9.md:917):")
        print("  \"channel 2427's squared gradient exceeds its block-mates' median by orders")
        print("   of magnitude while channel 198's block shows little or nothing\"")
        f, c = first["focus"], first["control"]
        print(f"\n  at first live step (step {first['step']}):")
        print(f"    ch2427 / block-9 median : {f['ratio_channel_over_median']:.2f}x   "
              f"(rank {f['rank_in_block']} of 256)")
        print(f"    ch198  / block-0 median : {c['ratio_channel_over_median']:.2f}x   "
              f"(rank {c['rank_in_block']} of 256)")
        print(f"    block-9 dynamic range   : {f['block_dynamic_range']:.2f}x")
        print(f"    block-0 dynamic range   : {c['block_dynamic_range']:.2f}x")
        print(f"    largest column overall  : col {first['argmax_col']} "
              f"(block {first['argmax_block']['block']}, cols {first['argmax_block']['cols']})")
        oom = f["ratio_channel_over_median"]
        print(f"\n  'orders of magnitude' means >= 100x. ch2427 is {oom:.2f}x -> "
              f"{'MET' if oom >= 100 else 'NOT MET as stated'}")
        print("  Reported as measured. Do not restate the threshold to fit the number.")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(
            {"tensor": TENSOR, "config": vars(a), "steps": _CAPTURED}, indent=2))
        print(f"\n[witness] full per-step record -> {a.json}")


if __name__ == "__main__":
    main()
