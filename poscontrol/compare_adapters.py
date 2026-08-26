"""compare_adapters.py — is the training step reproducible on different hardware?

Compares two LoRA adapters produced from the same code, the same gated 918-pair
corpus, and the same seed (42, HuggingFace's TrainingArguments default, confirmed
present in the author's training_args.bin), differing only in the GPU that ran
them.

WHAT IS COMPARED, AND WHY NOT THE RAW FACTORS. A LoRA layer's effect on the model
is the product B@A scaled by alpha/r; the factors themselves are not identifiable
-- B@A is invariant under B->BM, A->M^-1 A for any invertible M, so two runs can
carry very different A and B while producing the identical update. Comparing A or
B directly would therefore manufacture disagreement that has no effect on the
model. Everything below is computed on the effective update dW = (B@A)*(alpha/r).

METRICS, per layer:
  cos      cosine similarity of the two flattened dW. Direction agreement.
           1.0 = same update direction; 0.0 = orthogonal; <0 = opposed.
  ratio    ||dW_b||_F / ||dW_a||_F. Magnitude agreement, 1.0 = same size.
  rel      ||dW_b - dW_a||_F / ||dW_a||_F. Total relative discrepancy, the
           strictest of the three: it is small only if direction AND magnitude
           both agree.

INTERPRETATION, stated before the numbers exist so it cannot be fitted to them:
bitwise identity is NOT expected across different GPU architectures -- bf16
accumulation order, cuDNN/cuBLAS kernel selection, and the 8-bit optimiser's
quantised state all differ by device. High cosine with ratio near 1 means the
training step reproduces in substance. Low cosine would mean the same code, data,
and seed do not determine the adapter, which bears directly on the paper's
admission that a single checkpoint carries zero training-seed variance.

NOT CLAIMED: agreement here says nothing about whether either adapter helps on
the benchmark. It is a reproducibility measurement, not an efficacy one.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path

from safetensors import safe_open

MODS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def load_deltas(adapter_dir: Path) -> dict[str, "object"]:
    cfg = json.loads((adapter_dir / "adapter_config.json").read_text())
    scale = cfg["lora_alpha"] / cfg["r"]
    pairs: dict = collections.defaultdict(dict)
    with safe_open(str(adapter_dir / "adapter_model.safetensors"), framework="pt") as f:
        for k in f.keys():
            if "lora_A" in k:
                pairs[k.replace("lora_A", "*")]["A"] = f.get_tensor(k)
            elif "lora_B" in k:
                pairs[k.replace("lora_B", "*")]["B"] = f.get_tensor(k)
    # float64 throughout. In float32 the dot products below accumulate enough
    # error on 4096-wide layers to return cosine > 1.0, which is impossible and
    # was observed (1.0049, min 1.0002) on the 50,000x amplified control before
    # this cast. A metric that can report an out-of-range value is not one to
    # trust near its boundary, which is exactly where the interesting answer is.
    out = {}
    for k, v in pairs.items():
        if "A" in v and "B" in v:
            out[k] = (v["B"].double() @ v["A"].double()) * scale
    return out


def module_of(key: str) -> str:
    for m in MODS:
        if m in key:
            return m
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="reference adapter dir (author's)")
    ap.add_argument("--b", required=True, help="replication adapter dir (ours)")
    args = ap.parse_args()

    A = load_deltas(Path(args.a))
    B = load_deltas(Path(args.b))

    only_a = sorted(set(A) - set(B))
    only_b = sorted(set(B) - set(A))
    shared = sorted(set(A) & set(B))
    print(f"layers: A={len(A)}  B={len(B)}  shared={len(shared)}")
    if only_a or only_b:
        print(f"  !! A-only: {len(only_a)}   B-only: {len(only_b)}")
        for k in (only_a + only_b)[:6]:
            print("     ", k)
    if not shared:
        print("no shared layers — adapters are not comparable")
        return 1

    per_mod: dict = collections.defaultdict(list)
    for k in shared:
        da, db = A[k], B[k]
        if da.shape != db.shape:
            print(f"  !! shape mismatch {k}: {tuple(da.shape)} vs {tuple(db.shape)}")
            continue
        na = da.norm().item()
        nb = db.norm().item()
        fa, fb = da.flatten(), db.flatten()
        denom = (fa.norm() * fb.norm()).item()
        cos = (fa @ fb).item() / denom if denom > 0 else float("nan")
        ratio = nb / na if na > 0 else float("nan")
        rel = (db - da).norm().item() / na if na > 0 else float("nan")
        per_mod[module_of(k)].append((cos, ratio, rel))

    print()
    print("%-12s%8s%10s%10s%10s%10s" % ("module", "layers", "cos", "ratio", "rel", "min cos"))
    allc, allr, alld = [], [], []
    for m in MODS:
        if m not in per_mod:
            continue
        v = per_mod[m]
        cs = [x[0] for x in v]
        rs = [x[1] for x in v]
        ds = [x[2] for x in v]
        allc += cs
        allr += rs
        alld += ds
        print("%-12s%8d%10.4f%10.4f%10.4f%10.4f"
              % (m, len(v), sum(cs) / len(cs), sum(rs) / len(rs),
                 sum(ds) / len(ds), min(cs)))

    n = len(allc)
    mc = sum(allc) / n
    sc = math.sqrt(sum((c - mc) ** 2 for c in allc) / (n - 1)) if n > 1 else 0.0
    print()
    print(f"ALL {n} layers:  mean cos={mc:.6f} (sd {sc:.6f}, min {min(allc):.6f})"
          f"  mean ratio={sum(allr)/n:.6f}  mean rel={sum(alld)/n:.6f}")
    print()
    print("READING: cos near 1.0 with ratio near 1.0 = the training step reproduces")
    print("in substance on different hardware. Bitwise identity is not expected and")
    print("is not the bar. A low cos would mean code+data+seed do not determine the")
    print("adapter -- report that plainly if it is what the numbers say.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
