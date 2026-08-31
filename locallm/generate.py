"""generate.py — sample from a model YOU trained. Loads only your local files.

    python generate.py --out mymodel --prompt "def solve(" --tokens 400
"""
from __future__ import annotations

import argparse

import checkpoint


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out", help="model dir (from train.py)")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=40)
    args = ap.parse_args()

    # One implementation, imported: checkpoint.py owns loading and sampling so
    # studio.py cannot drift away from what this CLI does (and vice versa).
    model, tok, _ = checkpoint.load_checkpoint(args.out)
    print(checkpoint.sample(model, tok, args.prompt, args.tokens,
                            temperature=args.temperature, top_k=args.top_k))


if __name__ == "__main__":
    main()
