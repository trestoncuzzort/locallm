#!/usr/bin/env python3
"""optstate_trace.py - the per-step causal trace of bitsandbytes 8-bit Adam state.

WHY THIS RUN EXISTS. F2 established that 8-bit optimizer state produces 176 over-bound
coordinates in one 256-element block, and that the block's absmax-setting column (2427,
a massive activation measured at BOS) is itself the LEAST displaced column while its
block-mates inflate 14.9x against the 32-bit arm. That EXHIBITS the effect. It does not
show the causal chain.

The literature review named this the single highest-value extension available for F2:
implement Dettmers et al. (2022) Eq. 4 against the installed bitsandbytes maps and ask,
per step:
  1. does column 2427 hold its block's absmax at EVERY step, or only sometimes?
  2. how large is the per-step dequantization error on its 255 block-mates?
  3. does that error carry a CONSISTENT SIGN?

(3) is the crux. Adam's step is m_hat / (sqrt(v_hat) + eps). If the stored second moment
is systematically UNDER-estimated for the block-mates, their denominator is too small and
their steps are too large - which is the inflation, with a direction rather than just a
magnitude. A symmetric, zero-mean error would refute the mechanism and leave the
displacement unexplained.

WHAT IS READ. bitsandbytes Optimizer2State.init_state stores, per parameter:
    state1 / state2  uint8 quantization codes (first / second moment)
    qmap1            "dynamic"  (SIGNED)    - first moment
    qmap2            "udynamic" (UNSIGNED)  - second moment
    absmax1/absmax2  fp32, one per 256-element block of the FLATTENED tensor
Dequantization is Dettmers Eq. 4: value = qmap[code] * absmax[block].

Blocks are flat over the row-major (16, 14336) tensor, so the block holding column 2427
differs per row: block(r) = (r*14336 + 2427) // 256. Row 0 lands in block 9, which is the
block the manuscript names.

A shadow fp32 Adam is maintained from the same gradients as an ideal reference. It is NOT
a claim about what bitsandbytes should compute - it is the unquantized recurrence, so the
difference isolates quantization from everything else.

Usage:
    export SRLM_VERIFY_PY=$PWD/.venv-train/bin/python
    ~/gpuguard.sh -- .venv-train/bin/python poscontrol/optstate_trace.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

TENSOR = "layers.1.mlp.down_proj.lora_A."
FOCUS_CH = 2427
CONTROL_CH = 198
BLOCK = 256
NCOL = 14336

_TRACE: list[dict] = []
_STATE: dict = {}


def _capture(p, opt, step, torch):
    """One step's worth of quantized-vs-ideal comparison."""
    st = opt.state.get(p, {})
    if "state2" not in st or "absmax2" not in st:
        return {"step": step, "note": "no 8-bit state on this parameter"}
    g = p.grad.detach().float().flatten()
    n = g.numel()

    # ---- ideal fp32 Adam recurrence from the same gradients ----
    b1, b2 = 0.9, 0.999
    m = _STATE.setdefault("m", torch.zeros_like(g))
    v = _STATE.setdefault("v", torch.zeros_like(g))
    m.mul_(b1).add_(g, alpha=1 - b1)
    v.mul_(b2).addcmul_(g, g, value=1 - b2)

    # ---- what bitsandbytes actually holds, dequantized (Dettmers Eq. 4) ----
    code2 = st["state2"].detach().flatten().long()
    qmap2 = st["qmap2"].detach().float()
    amax2 = st["absmax2"].detach().float()
    nblk = amax2.numel()
    blk_of = (torch.arange(n, device=g.device) // BLOCK).clamp(max=nblk - 1)
    v_bnb = qmap2[code2] * amax2[blk_of]

    rows = n // NCOL
    out = {"step": step, "n": int(n), "blocks": int(nblk)}
    per_row = []
    for r in range(rows):
        flat = r * NCOL + FOCUS_CH
        b = flat // BLOCK
        lo, hi = b * BLOCK, min(b * BLOCK + BLOCK, n)
        idx = torch.arange(lo, hi, device=g.device)
        mates = idx[idx != flat]

        v_true_blk = v[idx]
        holds = int(v_true_blk.argmax()) == int(flat - lo)      # does 2427 set the absmax?
        # relative error of the stored second moment, block-mates only
        vt, vb = v[mates], v_bnb[mates]
        nz = vt > 0
        rel = ((vb[nz] - vt[nz]) / vt[nz]) if nz.any() else torch.zeros(1, device=g.device)
        per_row.append({
            "row": r, "block": int(b),
            "focus_holds_absmax": holds,
            "focus_v_true": float(v[flat]),
            "mates_v_true_median": float(vt.median()),
            "mates_rel_err_median": float(rel.median()),
            "mates_rel_err_mean": float(rel.mean()),
            "mates_frac_underestimated": float((rel < 0).float().mean()),
            "mates_frac_exactly_zero": float((vb[nz] == 0).float().mean()),
        })
    out["per_row"] = per_row
    out["focus_holds_absmax_rows"] = sum(1 for x in per_row if x["focus_holds_absmax"])
    out["mates_frac_underestimated"] = sum(x["mates_frac_underestimated"] for x in per_row) / rows
    out["mates_rel_err_median"] = sorted(x["mates_rel_err_median"] for x in per_row)[rows // 2]
    out["mates_frac_exactly_zero"] = sum(x["mates_frac_exactly_zero"] for x in per_row) / rows

    # control block, same treatment, for the channel the manuscript names as the weak case
    cflat = CONTROL_CH
    cb = cflat // BLOCK
    clo, chi = cb * BLOCK, min(cb * BLOCK + BLOCK, n)
    cidx = torch.arange(clo, chi, device=g.device)
    cm = cidx[cidx != cflat]
    cvt, cvb = v[cm], v_bnb[cm]
    cnz = cvt > 0
    crel = ((cvb[cnz] - cvt[cnz]) / cvt[cnz]) if cnz.any() else torch.zeros(1, device=g.device)
    out["control"] = {
        "block": int(cb),
        "holds_absmax": int(v[cidx].argmax()) == int(cflat - clo),
        "mates_rel_err_median": float(crel.median()),
        "mates_frac_underestimated": float((crel < 0).float().mean()),
    }
    return out


def _make_callback(ref):
    from transformers import TrainerCallback
    import torch

    class Trace(TrainerCallback):
        def on_optimizer_step(self, args, state, control, **kw):
            tr = ref[0]
            for name, p in tr.model.named_parameters():
                if TENSOR in name and name.endswith("weight") and p.grad is not None:
                    try:
                        _TRACE.append(_capture(p, tr.optimizer, int(state.global_step), torch))
                    except Exception as e:                       # never kill the run
                        _TRACE.append({"step": int(state.global_step), "error": repr(e)})
                    break
            return control

    return Trace()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="/tmp/optstate/adapter")
    ap.add_argument("--json", default=None)
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--optim", default="adamw_bnb_8bit")
    a = ap.parse_args()

    if not os.environ.get("SRLM_VERIFY_PY"):
        sys.exit("SRLM_VERIFY_PY must be exported or dataset_gate SystemExits at import.")

    os.chdir(REPO)
    sys.path.insert(0, str(REPO))
    import trl
    import train_native

    orig = trl.DPOTrainer
    ref: list = [None]

    class TraceTrainer(orig):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            ref[0] = self
            self.add_callback(_make_callback(ref))

    trl.DPOTrainer = TraceTrainer
    try:
        sys.argv = ["train_native.py", "--out", a.out, "--max-steps", str(a.max_steps),
                    "--lr", str(a.lr), "--seed", str(a.seed), "--optim", a.optim]
        train_native.main()
    finally:
        trl.DPOTrainer = orig

    live = [t for t in _TRACE if "per_row" in t]
    print("\n" + "=" * 78)
    print("OPTIMIZER-STATE TRACE - second moment, 8-bit blockwise")
    print("=" * 78)
    if not live:
        print("no usable steps captured:", _TRACE[:2])
        sys.exit(1)

    rows = len(live[0]["per_row"])
    print(f"steps captured: {len(live)}   rows per step: {rows}\n")
    hdr = (f"{'step':>4}  {'2427 sets absmax':>17}  {'mates under-est':>16}  "
           f"{'median rel err':>15}  {'mates quantized to 0':>21}")
    print(hdr); print("-" * len(hdr))
    for t in live:
        print(f"{t['step']:>4}  {t['focus_holds_absmax_rows']:>13}/{rows}  "
              f"{100*t['mates_frac_underestimated']:>15.1f}%  "
              f"{t['mates_rel_err_median']:>15.4f}  {100*t['mates_frac_exactly_zero']:>20.1f}%")

    und = [t["mates_frac_underestimated"] for t in live]
    holds = [t["focus_holds_absmax_rows"] for t in live]
    zero = [t["mates_frac_exactly_zero"] for t in live]
    ctl = [t["control"]["mates_frac_underestimated"] for t in live]
    print("\nSUMMARY")
    print(f"  column {FOCUS_CH} set its block's absmax in "
          f"{sum(holds)}/{len(live)*rows} (step, row) cells")
    print(f"  block-mates with an UNDER-estimated second moment: "
          f"median {100*sorted(und)[len(und)//2]:.1f}% of coordinates")
    print(f"  block-mates quantized to exactly zero: median {100*sorted(zero)[len(zero)//2]:.1f}%")
    print(f"  control block {CONTROL_CH//BLOCK}: under-estimated "
          f"median {100*sorted(ctl)[len(ctl)//2]:.1f}%")
    print("\n  A consistently NEGATIVE error means sqrt(v_hat) is too small, so the step")
    print("  m_hat/(sqrt(v_hat)+eps) is too LARGE - the inflation, with a direction.")
    print("  A symmetric zero-mean error would leave the displacement unexplained.")
    print("  Reported as measured.")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({"config": vars(a), "trace": _TRACE}, indent=2))
        print(f"\n[trace] wrote {a.json}")


if __name__ == "__main__":
    main()
