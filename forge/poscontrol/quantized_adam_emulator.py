#!/usr/bin/env python3
"""quantized_adam_emulator.py - F2's numpy discriminator.

manuscript-v9.md:917 preregisters this:

    "A numpy emulator (quantized_adam_emulator.py) runs Adam with 256-block absmax-quantized
     second moments under the bitsandbytes dynamic map on gradient columns with one channel
     about 100x the others, and separates second-moment underflow from first-moment
     quantization, from the dynamic map's minimum representable value, and from interplay
     with gradient clipping."

    Prediction: "the emulator reproduces the over-bound displacement from second-moment
     underflow alone."

The arms isolate one cause at a time:
    fp32          - control. MUST produce zero over-bound coordinates, or the bound
                    accounting is wrong and every other arm's count is meaningless.
    v8            - second moment quantized, first moment exact   <- the preregistered cause
    m8            - first moment quantized, second moment exact
    both          - the deployed configuration
    v8_noclip     - v8 with gradient clipping disabled, to separate clipping interplay
    v8_flat       - v8 with the outlier channel REMOVED, to show the effect is caused by
                    the outlier rather than by 8-bit state per se

The quantization map is read from the installed bitsandbytes rather than reimplemented.
bitsandbytes Optimizer2State.init_state assigns qmap1 = name2qmap["dynamic"] (SIGNED,
first moment) and qmap2 = name2qmap["udynamic"] (UNSIGNED, second moment); the second
moment is non-negative so it uses the unsigned map. Dequantization is Dettmers et al.
(2022) Eq. 4: value = qmap[code] * absmax[block], blocks of 256 over the flattened tensor.

Usage:
    .venv-train/bin/python poscontrol/quantized_adam_emulator.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROWS, COLS = 16, 14336
BLOCK = 256
FOCUS_CH = 2427
B1, B2, EPS = 0.9, 0.999, 1e-8
TRUST = 3.16


def bnb_maps():
    """The actual maps bitsandbytes uses, not a reimplementation."""
    try:
        from bitsandbytes.functional import create_dynamic_map
    except Exception as e:
        sys.exit(f"bitsandbytes is required to read the real quantization map: {e!r}")
    signed = np.asarray(create_dynamic_map(signed=True).float().cpu().numpy(), dtype=np.float64)
    unsigned = np.asarray(create_dynamic_map(signed=False).float().cpu().numpy(), dtype=np.float64)
    return np.sort(signed), np.sort(unsigned)


def quantize_blockwise(x, qmap):
    """Dettmers Eq. 4, exactly: per-256-block absmax, nearest code, dequantize."""
    n = x.size
    pad = (-n) % BLOCK
    xp = np.concatenate([x, np.zeros(pad)]) if pad else x
    blocks = xp.reshape(-1, BLOCK)
    absmax = np.abs(blocks).max(axis=1, keepdims=True)
    safe = np.where(absmax == 0, 1.0, absmax)
    norm = blocks / safe
    # Nearest code by binary search on the sorted map. The broadcast form
    # (norm[...,None] - qmap) allocates blocks x 256 x 256 floats per call - hundreds of
    # MB and several cores on a shared machine - for the identical result.
    j = np.searchsorted(qmap, norm)
    j = np.clip(j, 1, qmap.size - 1)
    lo, hi = qmap[j - 1], qmap[j]
    codes = np.where(np.abs(norm - lo) <= np.abs(hi - norm), j - 1, j)
    deq = (qmap[codes] * safe).reshape(-1)
    return (deq[:n] if pad else deq), absmax.reshape(-1)


def lr_schedule(total, lr, ratio=0.1):
    warm = math.ceil(total * ratio)
    out = []
    for s in range(total):
        if s < warm:
            out.append(lr * s / max(warm, 1))
        else:
            prog = (s - warm) / max(total - warm, 1)
            out.append(lr * 0.5 * (1 + math.cos(math.pi * prog)))
    return out


def make_grads(steps, rng, outlier=True, scale=100.0):
    """Gradient columns with one channel about `scale` times the others."""
    gs = []
    for _ in range(steps):
        g = rng.normal(0, 1e-3, size=(ROWS, COLS))
        if outlier:
            g[:, FOCUS_CH] *= scale
        gs.append(g)
    return gs


def run(arm, grads, lrs, qs, qu, clip=1.0):
    n = ROWS * COLS
    A0 = np.zeros(n)                    # displacement is measured from init, so init at 0
    A = A0.copy()
    m = np.zeros(n)
    v = np.zeros(n)
    for t, (g2d, lr) in enumerate(zip(grads, lrs), start=1):
        g = g2d.reshape(-1).copy()
        if clip is not None:
            nrm = np.linalg.norm(g)
            if nrm > clip:
                g *= clip / nrm
        m = B1 * m + (1 - B1) * g
        v = B2 * v + (1 - B2) * g * g
        if arm in ("m8", "both"):
            m, _ = quantize_blockwise(m, qs)
        if arm in ("v8", "both", "v8_noclip", "v8_flat"):
            v, _ = quantize_blockwise(v, qu)
        mh = m / (1 - B1 ** t)
        vh = v / (1 - B2 ** t)
        A -= lr * mh / (np.sqrt(vh) + EPS)
    return A - A0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--scale", type=float, default=100.0, help="outlier channel multiplier")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    qs, qu = bnb_maps()
    pos_u = qu[qu > 0]
    print("=" * 78)
    print("QUANTIZED ADAM EMULATOR")
    print("=" * 78)
    print(f"  second-moment map: unsigned, {qu.size} levels, "
          f"min positive {pos_u.min():.6e} of block absmax")
    print(f"  first-moment map : signed,   {qs.size} levels, "
          f"min positive {qs[qs>0].min():.6e} of block absmax")
    print(f"  -> any second moment below {pos_u.min():.2e} x its block's absmax cannot be")
    print(f"     represented and quantizes toward zero. That is the underflow floor.")

    lrs = lr_schedule(a.steps, a.lr)
    sum_lr = sum(lrs)
    bound = TRUST * sum_lr
    print(f"\n  schedule: {a.steps} steps, cosine, warmup {math.ceil(a.steps*0.1)}, "
          f"sum_lr {sum_lr:.6e}")
    print(f"  trust region 3.16*sum_lr = {bound:.6e}")

    rng = np.random.default_rng(a.seed)
    grads = make_grads(a.steps, rng, outlier=True, scale=a.scale)
    flat_grads = make_grads(a.steps, np.random.default_rng(a.seed), outlier=False)

    focus_block = FOCUS_CH // BLOCK
    arms = [("fp32", grads, 1.0), ("v8", grads, 1.0), ("m8", grads, 1.0),
            ("both", grads, 1.0), ("v8_noclip", grads, None), ("v8_flat", flat_grads, 1.0)]

    results = {}
    print(f"\n{'arm':<12}{'over-bound':>12}{'in ch2427 block':>18}{'max|dA|':>14}   note")
    print("-" * 78)
    for name, gs, clip in arms:
        d = run(name, gs, lrs, qs, qu, clip=clip)
        over = np.abs(d) > bound
        cols = np.where(over)[0] % COLS
        inblk = int(((cols // BLOCK) == focus_block).sum())
        note = {"fp32": "control - must be 0",
                "v8": "second moment only",
                "m8": "first moment only",
                "both": "as deployed",
                "v8_noclip": "clipping off",
                "v8_flat": "no outlier channel"}[name]
        results[name] = {"over": int(over.sum()), "in_focus_block": inblk,
                         "max_abs": float(np.abs(d).max()), "bound": bound}
        print(f"{name:<12}{int(over.sum()):>12}{inblk:>18}{np.abs(d).max():>14.4e}   {note}")

    print("\nPREREGISTERED PREDICTION: 'the emulator reproduces the over-bound displacement")
    print("from second-moment underflow alone.'")
    ctl, v8 = results["fp32"]["over"], results["v8"]["over"]
    m8, flat = results["m8"]["over"], results["v8_flat"]["over"]
    ok_ctl = ctl == 0
    print(f"\n  fp32 control over-bound        : {ctl}   {'OK' if ok_ctl else 'PROBLEM - bound accounting is wrong'}")
    print(f"  v8 (second moment alone)       : {v8}")
    print(f"  m8 (first moment alone)        : {m8}")
    print(f"  v8 without the outlier channel : {flat}")
    if not ok_ctl:
        print("\n  VERDICT: cannot be read. The unquantized control violates its own bound,")
        print("  so no arm's count means anything. Fix the accounting before interpreting.")
    elif v8 > 0 and m8 == 0:
        print("\n  VERDICT: PREDICTION HELD. Second-moment quantization alone reproduces")
        print("  over-bound displacement; first-moment quantization alone does not.")
        if flat == 0:
            print("  And it vanishes without the outlier channel, so the cause is the")
            print("  outlier-dominated block scale, not 8-bit state per se.")
    elif v8 == 0:
        print("\n  VERDICT: PREDICTION DID NOT HOLD. Second-moment quantization alone did not")
        print("  reproduce the displacement. Report this - do not tune the emulator until")
        print("  it agrees. The real run's mechanism is then not captured by this model.")
    else:
        print("\n  VERDICT: MIXED - both moments contribute. Second-moment underflow is not")
        print("  sufficient on its own as preregistered. Report as measured.")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(
            {"config": vars(a), "sum_lr": sum_lr, "bound": bound,
             "map_min_unsigned": float(pos_u.min()), "results": results}, indent=2))
        print(f"\n[emulator] wrote {a.json}")


if __name__ == "__main__":
    main()
