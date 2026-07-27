"""runlog.py — an append-only record of every run, so evidence accumulates.

    python runlog.py              # summary of everything recorded
    python runlog.py --kind train # just training runs
    python runlog.py --last 20    # the most recent 20
    python runlog.py --review     # the digest to hand a reviewer

Every training run, experiment, benchmark and leakage scan appends one line to
runs.jsonl. Nothing is ever overwritten or deleted by this module.

Why: result files that get overwritten by the next run cannot show a trend, and
a number quoted from memory is not evidence. Twenty runs recorded with their
configuration, their machine and their timing are reviewable; the same twenty
runs printed to a terminal that has since been closed are not.

What a record deliberately includes:
  - a fingerprint of the CORPUS, so runs on different text are never compared
  - the DEVICE and model configuration, so a slower number is attributable
  - wall clock and ms/step, so a change in speed is visible
  - the leakage verdict where one applies, so a val loss is never read without
    knowing whether it means anything
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "runs.jsonl"


def corpus_fingerprint(text: str) -> dict:
    return {"chars": len(text), "vocab": len(set(text)),
            "sha1": hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:12]}


def record(kind: str, **fields) -> None:
    """Append one run. Never raises into the caller: a logging failure must not
    take down a training run that otherwise succeeded."""
    try:
        row = {"ts": datetime.now().isoformat(timespec="seconds"), "kind": kind}
        row.update(fields)
        row.setdefault("host", platform.node())
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
    except Exception as e:                      # noqa: BLE001
        print(f"[runlog] could not record this run: {e}", file=sys.stderr)


def load() -> list[dict]:
    if not LOG.is_file():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue                            # a torn line must not lose the rest
    return out


def _g(row: dict, *path, default=""):
    cur = row
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def summary(rows: list[dict]) -> None:
    if not rows:
        print("No runs recorded yet. Train something, or run bench_device.py.")
        return

    kinds = {}
    for r in rows:
        kinds.setdefault(r.get("kind", "?"), []).append(r)
    print(f"{len(rows)} runs recorded in {LOG.name}")
    print("  " + "  ".join(f"{k}: {len(v)}" for k, v in sorted(kinds.items())))
    corpora = {_g(r, "corpus", "sha1") for r in rows if _g(r, "corpus", "sha1")}
    if len(corpora) > 1:
        print(f"  NOTE: {len(corpora)} different corpora appear here. Runs on "
              f"different text are not comparable.")
    print()

    train = kinds.get("train", [])
    if train:
        print("TRAINING RUNS")
        print(f"  {'when':16} {'device':6} {'model':>16} {'steps':>6} "
              f"{'train':>7} {'val':>7} {'leak':>6} {'wall':>7}")
        print("  " + "-" * 78)
        for r in train[-40:]:
            cfg = r.get("config", {})
            model = f"{cfg.get('n_layer','?')}L{cfg.get('n_head','?')}H{cfg.get('n_embd','?')}D"
            val = _g(r, "metrics", "val_loss", default=None)
            print(f"  {r.get('ts','')[5:16]:16} {r.get('device','?'):6} {model:>16} "
                  f"{str(cfg.get('steps','?')):>6} "
                  f"{_g(r,'metrics','train_loss',default=float('nan')):7.4f} "
                  f"{(f'{val:.4f}' if isinstance(val,(int,float)) else '   -  '):>7} "
                  f"{str(_g(r,'leakage','verdict',default='-'))[:6]:>6} "
                  f"{_g(r,'metrics','wall_s',default=0):6.0f}s")
        print()

    for kind, label in (("experiment", "EXPERIMENTS"), ("benchmark", "BENCHMARKS"),
                        ("leakage", "LEAKAGE SCANS")):
        group = kinds.get(kind, [])
        if not group:
            continue
        print(label)
        for r in group[-15:]:
            if kind == "experiment":
                print(f"  {r.get('ts','')[5:16]}  {r.get('name','?'):22} "
                      f"{_g(r,'metrics','verdict', default='')}")
            elif kind == "benchmark":
                res = r.get("results", {})
                best = ", ".join(f"{k.split('/')[-1]} {v.get('ms_per_step','?')}ms"
                                 for k, v in list(res.items())[:3])
                print(f"  {r.get('ts','')[5:16]}  {r.get('device','?'):6} {best}")
            else:
                print(f"  {r.get('ts','')[5:16]}  {_g(r,'leakage','verdict'):13} "
                      f"content {_g(r,'leakage','content_frac',default=0):.2%}  "
                      f"{_g(r,'corpus','chars',default=0):,} chars")
        print()


def review(rows: list[dict]) -> None:
    """The digest meant for someone who did not watch any of it happen."""
    print("=" * 70)
    print("RUN LOG REVIEW DIGEST")
    print("=" * 70)
    if not rows:
        print("Nothing recorded.")
        return
    print(f"records      {len(rows)}")
    print(f"first        {rows[0].get('ts','?')}")
    print(f"last         {rows[-1].get('ts','?')}")
    devices = sorted({r.get("device", "?") for r in rows} - {"?"})
    print(f"devices      {', '.join(devices) or 'not recorded'}")
    corpora = {_g(r, "corpus", "sha1"): _g(r, "corpus", "chars")
               for r in rows if _g(r, "corpus", "sha1")}
    print(f"corpora      {len(corpora)}  " +
          ", ".join(f"{k} ({v:,} chars)" for k, v in list(corpora.items())[:4]))

    train = [r for r in rows if r.get("kind") == "train"]
    if train:
        losses = [(_g(r, "metrics", "train_loss", default=None), r) for r in train]
        losses = [(l, r) for l, r in losses if isinstance(l, (int, float))]
        if losses:
            best_l, best_r = min(losses, key=lambda t: t[0])
            cfg = best_r.get("config", {})
            print(f"\nbest train loss  {best_l:.4f}  "
                  f"({cfg.get('n_layer')}L{cfg.get('n_head')}H{cfg.get('n_embd')}D, "
                  f"{cfg.get('steps')} steps, {best_r.get('device')}, "
                  f"{best_r.get('ts','')[:16]})")
        untrusted = [r for r in train
                     if _g(r, "leakage", "verdict", default="") not in ("CLEAN", "")]
        print(f"runs whose val loss is NOT trustworthy: {len(untrusted)} of {len(train)}")

    print("\nWhat this digest does NOT establish: that any two runs above are")
    print("comparable. Check the corpus fingerprint and the config before")
    print("reading a difference between two lines as a result.")
    print("=" * 70)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", help="filter: train, experiment, benchmark, leakage")
    ap.add_argument("--last", type=int, default=0)
    ap.add_argument("--review", action="store_true", help="digest for a reviewer")
    ap.add_argument("--json", action="store_true", help="dump raw records")
    args = ap.parse_args()

    rows = load()
    if args.kind:
        rows = [r for r in rows if r.get("kind") == args.kind]
    if args.last:
        rows = rows[-args.last:]

    if args.json:
        print(json.dumps(rows, indent=2))
    elif args.review:
        review(rows)
    else:
        summary(rows)


if __name__ == "__main__":
    main()
