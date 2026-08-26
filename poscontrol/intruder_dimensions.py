#!/usr/bin/env python3
"""intruder_dimensions.py - F6's spectral-signature check.

manuscript-v9.md:925 requires that the random arm's "intruder-dimension count
(Shuttleworth et al., 2024) is reported beside the healthy adapter's, so that the two are
not separable by spectral signature before any function is measured."

METRIC, from Shuttleworth et al., "LoRA vs Full Fine-tuning: An Illusion of Equivalence"
(arXiv:2410.21228), Definition 3.1: a singular vector y_j of W_tuned is an INTRUDER
DIMENSION iff max_i cos(y_j, x_i) < eps, where x_i are the singular vectors of W_0.

Reimplemented here rather than vendored, for two reasons the reference implementation
cannot cover: it carries no target-module list for any Llama model, and it assumes an
fp16 base, whereas ours is bitsandbytes NF4. Three details are taken from the reference
code rather than from the prose, because the prose alone would mislead:

  1. W_tuned is the MERGED matrix W_0 + (alpha/r) * B @ A. Never B @ A on its own.
  2. The comparison uses the ABSOLUTE cosine. Singular vectors are sign-arbitrary, so a
     raw cosine would count sign flips as intruders. The paper's Fig. 2c caption says
     "near-zero absolute cosine similarity"; Definition 3.1's prose omits the bars.
  3. The top-k singular vectors of W_tuned are compared against ALL singular vectors of
     W_0, not against W_0's top-k.

  Left singular vectors (columns of U) only, never V.

QUANTIZATION. The base is NF4, so W_0 must be dequantized first, via
peft.utils.integrations.dequantize_bnb_weight (which calls bitsandbytes'
dequantize_4bit with the tensor's own quant_state). NF4's block size is 64 - unrelated
to the 256-element optimizer-state block discussed elsewhere in this project. Dequantizing
is lossy relative to an fp16 original: W_0 here is the base as actually served, which is
the right reference for this comparison but should be stated.

Usage:
    intruder_dimensions.py --adapter DIR [--adapter DIR ...] --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
DEFAULT_K = 10
DEFAULT_EPS = 0.5
SWEEP = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", action="append", required=True,
                    help="adapter dir (repeatable; counts are reported side by side)")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--eps", type=float, default=DEFAULT_EPS)
    ap.add_argument("--layers", default=None,
                    help="comma-separated layer indices; default all")
    ap.add_argument("--json", default=None)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()

    if not os.environ.get("SRLM_VERIFY_PY"):
        sys.exit("SRLM_VERIFY_PY must be exported or dataset_gate SystemExits at import.")

    os.chdir(REPO)
    sys.path.insert(0, str(REPO))

    import torch
    import config
    from transformers import AutoModelForCausalLM
    from safetensors.torch import load_file
    from peft.utils.integrations import dequantize_bnb_weight

    M = config.MODEL
    print(f"[intruder] base={M.hf_base}  k={a.k}  eps={a.eps}  device={a.device}")
    print(f"[intruder] metric: Shuttleworth et al. arXiv:2410.21228 Definition 3.1, "
          f"absolute cosine, left singular vectors, W_tuned = W0 + (alpha/r) B A")

    base = AutoModelForCausalLM.from_pretrained(
        M.hf_base, device_map={"": 0}, torch_dtype=torch.bfloat16)
    base.eval()

    adapters = {}
    for d in a.adapter:
        p = Path(d)
        sd = load_file(p / "adapter_model.safetensors")
        cfg = json.loads((p / "adapter_config.json").read_text())
        scale = cfg.get("lora_alpha", 32) / cfg.get("r", 16)
        adapters[p.name] = {"sd": sd, "scale": scale, "cfg": cfg}
        print(f"[intruder] {p.name}: alpha/r = {cfg.get('lora_alpha')}/{cfg.get('r')} "
              f"= {scale:g}")

    layers = (range(len(base.model.layers)) if not a.layers
              else [int(x) for x in a.layers.split(",")])

    counts = {name: {e: 0 for e in SWEEP} for name in adapters}
    allcos: dict = {}
    per_matrix = {name: [] for name in adapters}
    n_mat = 0

    for li in layers:
        layer = base.model.layers[li]
        for t in TARGETS:
            mod = getattr(layer.self_attn, t, None) or getattr(layer.mlp, t, None)
            if mod is None:
                continue
            key_a = (f"base_model.model.model.layers.{li}."
                     f"{'self_attn' if hasattr(layer.self_attn, t) else 'mlp'}.{t}.lora_A.weight")
            key_b = key_a.replace("lora_A", "lora_B")
            if not all(key_a in v["sd"] and key_b in v["sd"] for v in adapters.values()):
                continue

            W0 = dequantize_bnb_weight(mod.weight, state=mod.weight.quant_state).float()
            # all singular vectors of the pretrained matrix
            U0 = torch.linalg.svd(W0, full_matrices=False).U
            n_mat += 1

            for name, v in adapters.items():
                A = v["sd"][key_a].to(W0.device).float()
                B = v["sd"][key_b].to(W0.device).float()
                Wt = W0 + v["scale"] * (B @ A)
                Ut = torch.linalg.svd(Wt, full_matrices=False).U[:, :a.k]
                # |cos| against EVERY pretrained singular vector; columns are unit norm
                cos = (Ut.T @ U0).abs()
                mx = cos.max(dim=1).values                      # best match per tuned vector
                for e in SWEEP:
                    counts[name][e] += int((mx < e).sum())
                per_matrix[name].append({"layer": li, "module": t,
                                         "max_cos": [round(float(x), 4) for x in mx]})
                allcos.setdefault(name, []).extend(float(x) for x in mx)
                del A, B, Wt, Ut, cos, mx
            del W0, U0
            if a.device == "cuda":
                torch.cuda.empty_cache()
        print(f"  layer {li} done ({n_mat} matrices)", flush=True)

    print("\n" + "=" * 74)
    print(f"INTRUDER DIMENSIONS over {n_mat} matrices, top-{a.k} each "
          f"({n_mat * a.k} candidate vectors)")
    print("=" * 74)
    hdr = f"{'eps':>6}" + "".join(f"{n:>22}" for n in adapters)
    print(hdr); print("-" * len(hdr))
    for e in SWEEP:
        row = f"{e:>6.2f}"
        for name in adapters:
            c = counts[name][e]
            row += f"{c:>15} ({100*c/(n_mat*a.k):>4.1f}%)"
        print(row)
    # A count of zero at every threshold is what a BROKEN metric also returns, so the
    # distribution of the statistic itself is reported. If these sit at ~1.0 the tuned
    # matrix simply has not moved off the pretrained basis; if they are spread, the
    # metric is discriminating and the zero is real.
    print(f"\nmax|cos| to the pretrained basis, per tuned singular vector:")
    for name, xs in allcos.items():
        xs = sorted(xs)
        n = len(xs)
        print(f"  {name:<24} min {xs[0]:.6f}  p05 {xs[n//20]:.6f}  median {xs[n//2]:.6f}  max {xs[-1]:.6f}")
    print(f"\nheadline at eps={a.eps} (reference implementation's CLI default):")
    for name in adapters:
        c = counts[name][a.eps]
        print(f"  {name:<24} {c:>6} of {n_mat*a.k}  ({100*c/(n_mat*a.k):.1f}%)")
    print("\nF6 asks whether the arms are separable by spectral signature BEFORE any")
    print("behaviour is measured. Similar counts mean they are not; a large gap means")
    print("the behavioural comparison is confounded by an already-visible difference.")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(
            {"k": a.k, "eps": a.eps, "sweep": SWEEP, "n_matrices": n_mat,
             "counts": {n: {str(e): c for e, c in d.items()} for n, d in counts.items()},
             "per_matrix": per_matrix}, indent=2))
        print(f"\n[intruder] wrote {a.json}")


if __name__ == "__main__":
    main()
