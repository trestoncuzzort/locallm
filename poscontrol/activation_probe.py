#!/usr/bin/env python3
"""activation_probe.py - is channel 2427 a massive activation or an outlier feature?

WHY THIS RUN EXISTS. The literature audit found that manuscript-v9.md:311 cites Sun et al.
(2024) for channel 2427, but Sun et al. §2 states: "our study of activations is on the
hidden state h_l, i.e., the output of residual summations, NOT any intermediate states
inside F_l." Channel 2427 is a down_proj INPUT - an MLP intermediate, exactly what they
disclaim. Their taxonomy also separates the two phenomena:

  massive activation  - a SCALAR, at particular (token, feature) positions, input-agnostic
  outlier feature     - a VECTOR, large at ALL tokens in a feature dimension
                        (Dettmers et al. 2022, LLM.int8(), arXiv:2208.07339)
  and they report the two "do not overlap"

The manuscript's own measurement (386 vs 46 next-largest, median ~1e-2) is a per-channel
ranking with no token dimension reported, so it cannot currently tell these apart. This
run adds the token dimension and settles it.

It also tests the unevidenced claim at line 313 - "because the super activation is
prompt-invariant, the LoRA on that layer acts largely as a learned constant offset" -
which rests on invariance that one forward pass on one code prompt cannot establish.

And it applies Yu et al.'s (arXiv:2411.07191) data-free detection method, which the
manuscript currently lacks a citation for: the spike in down_proj's OUTPUT gives the row,
the spike in its INPUT gives the column.

DISCRIMINATOR, decided before the run:
  large at a LARGE FRACTION of token positions -> outlier feature (cite Dettmers 2022)
  large at ONLY 1-2 positions (BOS/delimiters)  -> massive activation (cite Sun et al.)
Sun et al.'s numeric criterion is also checked: magnitude > 100 AND >= ~1000x the median
magnitude of its hidden state.

Forward passes only. No training, no adapter, nothing written to the repo.

Usage:
    export SRLM_VERIFY_PY=$PWD/.venv-train/bin/python
    ~/gpuguard.sh -- .venv-train/bin/python poscontrol/activation_probe.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

LAYER = 1
FOCUS_CH = 2427
CONTROL_CH = 198
BLOCK = 256

# Deliberately varied: code and prose, long and short, different first real tokens.
PROMPTS = [
    ("code_twosum",  "Write a Python function two_sum(nums, target) that returns indices."),
    ("code_roman",   "def int_to_roman(n):\n    # convert an integer to a roman numeral\n"),
    ("prose_short",  "The weather today is"),
    ("prose_long",   "In 1957 the International Geophysical Year brought together scientists "
                     "from sixty-seven nations to study the upper atmosphere, the oceans and "
                     "the polar regions, and it produced among other things the first "
                     "measurements of atmospheric carbon dioxide at Mauna Loa."),
    ("digits",       "1 2 3 4 5 6 7 8 9 10"),
    ("single_word",  "Hello"),
    ("punct",        ". . . . ."),
    ("nonlatin",     "こんにちは世界"),
]


def _scan_all(model, tok, torch, a):
    """Every layer's down_proj input, one prompt, looking for >100-magnitude channels."""
    text = "Write a Python function two_sum(nums, target) that returns indices."
    ids = tok(text, return_tensors="pt").to(model.device)
    grabbed = {}

    def mk(i):
        def h(mod, inp, out):
            grabbed[i] = inp[0].detach().float()[0].abs()
        return h

    hs = [model.model.layers[i].mlp.down_proj.register_forward_hook(mk(i))
          for i in range(len(model.model.layers))]
    with torch.no_grad():
        model(**ids)
    for h in hs:
        h.remove()

    print(f"\n{'layer':>5} {'top channel':>12} {'magnitude':>12} {'median':>11} "
          f"{'ratio':>10} {'256-block':>10}  token")
    print("-" * 78)
    toks = tok.convert_ids_to_tokens(ids["input_ids"][0])
    hits = []
    for i, A in sorted(grabbed.items()):
        colmax = A.max(dim=0).values
        ch = int(colmax.argmax())
        mag = float(colmax[ch])
        med = float(A.median())
        tokpos = int(A[:, ch].argmax())
        ratio = mag / med if med > 0 else float("inf")
        blk = ch // BLOCK
        flag = "  <-- massive" if (mag > 100 and ratio > 1000) else ""
        print(f"{i:>5} {ch:>12} {mag:>12.1f} {med:>11.4f} {ratio:>10.0f} {blk:>10} "
              f" {toks[tokpos]}{flag}")
        if mag > 100 and ratio > 1000:
            hits.append({"layer": i, "channel": ch, "magnitude": mag, "block": blk,
                         "token": toks[tokpos], "ratio": ratio})
    print(f"\nchannels meeting Sun et al.'s criterion (>100 AND >1000x median): {len(hits)}")
    for h in hits:
        print(f"  layer {h['layer']:>2}  channel {h['channel']:>6}  "
              f"magnitude {h['magnitude']:>8.1f}  256-block {h['block']:>4}  at token {h['token']!r}")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({"scan": "all_layers", "hits": hits}, indent=2))
        print(f"\n[probe] wrote {a.json}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=None)
    ap.add_argument("--layer", type=int, default=LAYER)
    ap.add_argument("--top", type=int, default=5, help="top-k channels to report per prompt")
    ap.add_argument("--scan-all-layers", action="store_true",
                    help="sweep every layer's down_proj input for massive-activation channels")
    a = ap.parse_args()

    if not os.environ.get("SRLM_VERIFY_PY"):
        sys.exit("SRLM_VERIFY_PY must be exported or dataset_gate SystemExits at import.")

    os.chdir(REPO)
    sys.path.insert(0, str(REPO))

    import torch
    import config
    from transformers import AutoModelForCausalLM, AutoTokenizer

    M = config.MODEL
    print(f"[probe] base={M.hf_base} layer={a.layer} focus_ch={FOCUS_CH} control_ch={CONTROL_CH}")
    tok = AutoTokenizer.from_pretrained(M.hf_base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        M.hf_base, device_map={"": 0}, torch_dtype=torch.bfloat16)
    model.eval()

    if a.scan_all_layers:
        _scan_all(model, tok, torch, a)
        return

    dp = model.model.layers[a.layer].mlp.down_proj
    grab: dict = {}

    def hook(mod, inp, out):
        grab["in"] = inp[0].detach().float()[0]    # (tokens, 14336) - the intermediate
        grab["out"] = out.detach().float()[0]      # (tokens, 4096)  - the residual write

    h = dp.register_forward_hook(hook)

    results = []
    for name, text in PROMPTS:
        ids = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            model(**ids)
        A = grab["in"].abs()                        # (T, 14336)
        O = grab["out"].abs()                       # (T, 4096)
        T = A.shape[0]
        toks = tok.convert_ids_to_tokens(ids["input_ids"][0])

        per_tok_focus = A[:, FOCUS_CH]
        per_tok_ctrl = A[:, CONTROL_CH]
        argmax_ch = A.argmax(dim=1)                 # which channel dominates each token
        med_per_tok = A.median(dim=1).values

        # Sun et al.: >100 in magnitude AND ~1000x the median of its hidden state.
        crit_mag = (per_tok_focus > 100)
        crit_rel = (per_tok_focus > 1000 * med_per_tok)

        rec = {
            "prompt": name, "n_tokens": int(T),
            "focus_max": float(per_tok_focus.max()),
            "focus_median_over_tokens": float(per_tok_focus.median()),
            "focus_min": float(per_tok_focus.min()),
            "focus_is_argmax_frac": float((argmax_ch == FOCUS_CH).float().mean()),
            "control_max": float(per_tok_ctrl.max()),
            "control_is_argmax_frac": float((argmax_ch == CONTROL_CH).float().mean()),
            "median_channel_mag": float(med_per_tok.median()),
            "sun_crit_mag_frac": float(crit_mag.float().mean()),
            "sun_crit_rel_frac": float(crit_rel.float().mean()),
            # Yu et al. detection, this prompt
            "yu_row_from_output": int(O.max(dim=0).values.argmax()),
            "yu_col_from_input": int(A.max(dim=0).values.argmax()),
            "top_channels": [[int(c), float(A.max(dim=0).values[c])]
                             for c in A.max(dim=0).values.topk(a.top).indices.tolist()],
            "focus_per_token": [[toks[i], float(per_tok_focus[i])] for i in range(min(T, 12))],
        }
        results.append(rec)
        print(f"\n== {name}  ({T} tokens) ==")
        print(f"   ch{FOCUS_CH}: max {rec['focus_max']:.1f}  median-over-tokens "
              f"{rec['focus_median_over_tokens']:.1f}  min {rec['focus_min']:.1f}")
        print(f"   ch{FOCUS_CH} is the argmax channel at {100*rec['focus_is_argmax_frac']:.0f}% of tokens"
              f"   |  ch{CONTROL_CH} at {100*rec['control_is_argmax_frac']:.0f}%")
        print(f"   Sun et al. criterion met at: magnitude>100 {100*rec['sun_crit_mag_frac']:.0f}% of tokens, "
              f">1000x median {100*rec['sun_crit_rel_frac']:.0f}%")
        print(f"   Yu et al. detection -> row {rec['yu_row_from_output']} (output), "
              f"col {rec['yu_col_from_input']} (input)")
        print(f"   top channels: " + ", ".join(f"c{c}={v:.1f}" for c, v in rec['top_channels']))

    h.remove()

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    fracs = [r["focus_is_argmax_frac"] for r in results]
    maxes = [r["focus_max"] for r in results]
    meds = [r["focus_median_over_tokens"] for r in results]
    cols = [r["yu_col_from_input"] for r in results]
    print(f"  ch{FOCUS_CH} is the dominant channel at a median {100*statistics.median(fracs):.0f}% "
          f"of token positions (range {100*min(fracs):.0f}-{100*max(fracs):.0f}%)")
    print(f"  its max magnitude across prompts: {min(maxes):.1f} .. {max(maxes):.1f}")
    print(f"  its median-over-tokens across prompts: {min(meds):.1f} .. {max(meds):.1f}")
    print(f"  Yu et al. input-spike column, per prompt: {cols}")
    print(f"    -> {'STABLE, same column every prompt' if len(set(cols))==1 else 'VARIES BY PROMPT'}")
    print()
    magfracs = [r["sun_crit_mag_frac"] for r in results]
    ntok = [r["n_tokens"] for r in results]
    over = [f * n for f, n in zip(magfracs, ntok)]
    print(f"  tokens exceeding Sun et al.'s magnitude bar (>100): {[round(x) for x in over]}"
          f" of {ntok} tokens")
    print("  NOTE: the argmax fraction above is NOT the discriminator - at most positions every")
    print("  channel is near zero, so ch2427 can be 'largest' while measuring 0.1. Magnitude is.")
    print()
    if max(over) > 2:
        print("  READING: large at many token positions -> this is an OUTLIER FEATURE")
        print("  in Sun et al.'s taxonomy (a vector, all tokens), i.e. the Dettmers et al. 2022")
        print("  LLM.int8() phenomenon, NOT a massive activation. Cite accordingly.")
        print("  This STRENGTHENS the gradient argument: dL/dA[:,j] scales with the j-th input")
        print("  activation, and an all-token outlier accumulates across the sequence.")
    else:
        print("  READING: large at only a minority of token positions -> consistent with a")
        print("  MASSIVE ACTIVATION (Sun et al.), pending the input-agnosticism check above.")
    spread = (max(meds) / min(meds)) if min(meds) > 0 else float("inf")
    print(f"\n  prompt-invariance: median-over-tokens varies by {spread:.2f}x across "
          f"{len(results)} prompts")
    print("    (line 313's 'learned constant offset' needs this near 1; report it as measured)")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(
            {"layer": a.layer, "focus_ch": FOCUS_CH, "control_ch": CONTROL_CH,
             "results": results}, indent=2))
        print(f"\n[probe] wrote {a.json}")


if __name__ == "__main__":
    main()
