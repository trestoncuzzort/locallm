"""Does the seed control INITIALISATION, TRAINING, or neither?

LoRA initialises A from a seeded RNG and B to exactly zero, so the update
B@A starts at zero and everything in the final adapter came from training.
That gives a clean split between two very different failures:

  A identical, B different  -> the seed DOES fix initialisation; the divergence
                               is inside the optimisation (non-deterministic CUDA
                               kernels, bf16 accumulation order, the 8-bit
                               optimiser state). Reproducibility would need
                               torch.use_deterministic_algorithms(True) and
                               CUBLAS_WORKSPACE_CONFIG, which train_native.py
                               does not set.

  A different               -> the seed is not even reaching initialisation, and
                               the run is unseeded in practice regardless of what
                               TrainingArguments records.

Compares two adapter directories factor-by-factor, in float64, and reports each
family separately. Prints the exact count of A pairs that are bitwise identical,
because "close" and "identical" are different claims here.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

import torch
from safetensors import safe_open


def load_factors(d: Path) -> dict[str, torch.Tensor]:
    out = {}
    with safe_open(str(d / "adapter_model.safetensors"), framework="pt") as f:
        for k in f.keys():
            out[k] = f.get_tensor(k).double()
    return out


def stats(name: str, keys: list[str], A: dict, B: dict) -> None:
    if not keys:
        print(f"{name}: none")
        return
    ident = 0
    cos_v, rel_v = [], []
    for k in keys:
        a, b = A[k], B[k]
        if a.shape != b.shape:
            print(f"  !! shape mismatch {k}")
            continue
        if torch.equal(a, b):
            ident += 1
        fa, fb = a.flatten(), b.flatten()
        na, nb = fa.norm().item(), fb.norm().item()
        if na > 0 and nb > 0:
            cos_v.append((fa @ fb).item() / (na * nb))
            rel_v.append((fb - fa).norm().item() / na)
        elif na == 0 and nb == 0:
            cos_v.append(float("nan"))
            rel_v.append(0.0)
    n = len(keys)
    fin = [c for c in cos_v if c == c]
    print(f"{name}: {n} tensors | BITWISE IDENTICAL: {ident}/{n}")
    if fin:
        print(f"    mean cos={sum(fin)/len(fin):.6f}  min={min(fin):.6f}  "
              f"max={max(fin):.6f}")
    if rel_v:
        print(f"    mean rel diff={sum(rel_v)/len(rel_v):.6f}  "
              f"max={max(rel_v):.6f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    args = ap.parse_args()
    A = load_factors(Path(args.a))
    B = load_factors(Path(args.b))
    shared = sorted(set(A) & set(B))
    ak = [k for k in shared if "lora_A" in k]
    bk = [k for k in shared if "lora_B" in k]
    other = [k for k in shared if k not in ak and k not in bk]
    print(f"tensors: A-dir={len(A)} B-dir={len(B)} shared={len(shared)}")
    print()
    stats("lora_A (seeded init, then trained)", ak, A, B)
    print()
    stats("lora_B (init ZERO, then trained)", bk, A, B)
    if other:
        print()
        stats("other", other, A, B)
    print()
    print("READING: lora_A bitwise-identical => the seed fixes initialisation and")
    print("the divergence is inside the optimisation. lora_A differing => the seed")
    print("is not reaching init and the run is effectively unseeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
