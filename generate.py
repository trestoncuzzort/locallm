"""generate.py — sample from a model YOU trained. Loads only your local files.

    python generate.py --out mymodel --prompt "def solve(" --tokens 400
"""
from __future__ import annotations

import argparse

import torch

from model import GPT, GPTConfig
from data import CharTokenizer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out", help="model dir (from train.py)")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=40)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # weights_only=True: forward-compatible with torch>=2.6, where it becomes the
    # default. Our checkpoint is a plain dict of tensors + config primitives.
    ck = torch.load(f"{args.out}/ckpt.pt", map_location=device, weights_only=True)
    model = GPT(GPTConfig(**ck["config"])).to(device)
    model.load_state_dict(ck["model"])
    model.eval()
    tok = CharTokenizer.load(f"{args.out}/tokenizer.json")

    ids = tok.encode(args.prompt) or [0]
    idx = torch.tensor([ids], dtype=torch.long, device=device)
    out = model.generate(idx, args.tokens, temperature=args.temperature, top_k=args.top_k)
    print(tok.decode(out[0].tolist()))


if __name__ == "__main__":
    main()
