#!/usr/bin/env python3
"""make_random_adapter.py - F6's norm-matched random adapter.

manuscript-v9.md:925 specifies it: "an adapter whose B is random with per-layer Frobenius
norms matched to a healthy adapter's", built "on that healthy adapter's own A_0, with a
0.5x-scaled variant".

WHY A_0 AND NOT A_healthy. At the paper recipe lora_A barely moves - across the seeded
series max|A - A_0| is order 1e-3 against |A| of order 1e-2 - so the healthy adapter's A
is very nearly its initialisation. Using A_0 makes the random arm differ from the healthy
arm in exactly one factor, B, which is the contrast F6 wants. Both norms are reported so
the approximation is visible rather than assumed.

HOW A_0 IS OBTAINED. A --max-steps 1 run on this pipeline takes its single optimizer step
at lr exactly 0 (transformers computes warmup as ceil(steps * warmup_ratio) = ceil(0.1) = 1),
so the saved adapter IS the initialisation. Re-running train_native.py at the healthy
adapter's seed with --max-steps 1 therefore recovers its A_0 exactly, at no modelling cost.

WHAT IS MATCHED, AND WHAT IS NOT. Per-layer ||B||_F is matched exactly. That is what F6
asks for, and it is deliberately weaker than matching the spectrum: a Gaussian B has
generic singular values, so the random arm is not a spectral twin of the healthy one. The
intruder-dimension counts reported alongside are what test whether the two are separable
by spectral signature before any behaviour is measured.

Usage:
    make_random_adapter.py --healthy DIR --a0 DIR --out DIR [--scale 1.0] [--seed N]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--healthy", required=True, help="the healthy adapter to match")
    ap.add_argument("--a0", required=True,
                    help="its initialisation (a --max-steps 1 run at the same seed)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=1.0,
                    help="1.0 for the matched arm, 0.5 for the scaled variant")
    ap.add_argument("--seed", type=int, default=20260826)
    a = ap.parse_args()

    import torch
    from safetensors.torch import load_file, save_file

    H = Path(a.healthy)
    A0 = Path(a.a0)
    out = Path(a.out)
    sd_h = load_file(H / "adapter_model.safetensors")
    sd_0 = load_file(A0 / "adapter_model.safetensors")

    missing = [k for k in sd_h if k not in sd_0]
    if missing:
        sys.exit(f"A0 is missing {len(missing)} tensors present in the healthy adapter, "
                 f"e.g. {missing[:2]} - are they the same seed and config?")

    g = torch.Generator().manual_seed(a.seed)
    new = {}
    rows = []
    for k, v in sd_h.items():
        if "lora_A" in k:
            new[k] = sd_0[k].clone()                       # A stays at initialisation
        elif "lora_B" in k:
            target = v.float().norm().item()               # ||B_healthy||_F for this layer
            r = torch.randn(v.shape, generator=g, dtype=torch.float32)
            cur = r.norm().item()
            r = r * (target / cur if cur > 0 else 0.0)
            new[k] = r.to(v.dtype)
            rows.append((k, target, r.float().norm().item()))
        else:
            new[k] = v.clone()

    # scaled variant, applied to B only
    if a.scale != 1.0:
        for k in list(new):
            if "lora_B" in k:
                new[k] = (new[k].float() * a.scale).to(sd_h[k].dtype)

    out.mkdir(parents=True, exist_ok=True)
    save_file(new, str(out / "adapter_model.safetensors"))
    for f in ("adapter_config.json", "special_tokens_map.json",
              "tokenizer_config.json", "tokenizer.json", "README.md"):
        if (H / f).exists():
            shutil.copy2(H / f, out / f)

    # what actually got built, in numbers
    def dw_norm(sd):
        tot = 0.0
        for k in sd:
            if "lora_A" not in k:
                continue
            b = sd.get(k.replace("lora_A", "lora_B"))
            if b is None:
                continue
            tot += (b.float() @ sd[k].float()).pow(2).sum().item()
        return tot ** 0.5

    nh, nr = dw_norm(sd_h), dw_norm(new)
    maxerr = max(abs(t - g_) / t for _, t, g_ in rows) if rows else 0.0
    print(f"[random] layers matched      : {len(rows)}")
    print(f"[random] max per-layer ||B||_F relative error : {maxerr:.3e}")
    print(f"[random] ||dW||_F healthy    : {nh:.6f}")
    print(f"[random] ||dW||_F random     : {nr:.6f}   ratio {nr/nh if nh else float('nan'):.4f}")
    print(f"[random] scale applied to B  : {a.scale}")
    print(f"[random] wrote {out}")
    (out / "random_arm_meta.json").write_text(json.dumps({
        "healthy": str(H), "a0": str(A0), "scale": a.scale, "seed": a.seed,
        "layers_matched": len(rows), "max_rel_norm_err": maxerr,
        "dW_norm_healthy": nh, "dW_norm_random": nr,
    }, indent=2))


if __name__ == "__main__":
    main()
