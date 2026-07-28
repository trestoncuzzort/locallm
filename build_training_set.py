#!/usr/bin/env python3
"""build_training_set.py — the N=918 stratified, capped run-1 training file.

A 120-pairs-per-task cap, giving N=918 (the one removed poisoned pair was
`balanced`, an under-cap task, so it subtracts straight through). The rationale: a
loss drop measured on the full 54%-skewed set cannot be told apart from overfit to
the three most common task templates.

The cap was specified long before it was enforced anywhere — train_native.py used to
load all 1,234 rows. This builds the file that run 1 trains from, and prints the
sha256 that goes into the preregistration.

NOTE: stratifying with `groupby('tid')` does not work directly — there is no
top-level `tid` column, the task id lives at meta.tid. Lifted here explicitly.

    python build_training_set.py            # writes data/dpo_pairs_capped.jsonl
    python build_training_set.py --check    # report only, write nothing
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

import dataset_gate

HERE = Path(__file__).resolve().parent
SRC = HERE / "data" / "dpo_pairs.jsonl"
OUT = HERE / "data" / "dpo_pairs_capped.jsonl"
CAP = 120
SEED = 1337


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    rows = [json.loads(l) for l in SRC.open(encoding="utf-8")]
    by_tid: dict[str, list] = collections.defaultdict(list)
    missing = 0
    for i, r in enumerate(rows):
        tid = (r.get("meta") or {}).get("tid")
        if not tid:
            missing += 1
            continue
        by_tid[tid].append((i, r))

    if missing:
        raise SystemExit(f"ABORT: {missing} rows have no meta.tid — cannot stratify "
                         f"a set whose group key is incomplete.")

    rng = random.Random(args.seed)
    kept: list[tuple[int, dict]] = []
    print(f"source: {SRC.name}  {len(rows):,} pairs, {len(by_tid)} tasks, cap {args.cap}\n")
    print(f"  {'task':<20} {'have':>5} {'kept':>5}")
    for tid in sorted(by_tid):                      # sorted => deterministic
        group = sorted(by_tid[tid], key=lambda t: t[0])
        take = group if len(group) <= args.cap else rng.sample(group, args.cap)
        kept.extend(take)
        print(f"  {tid:<20} {len(group):>5} {len(take):>5}"
              f"{'   (capped)' if len(group) > args.cap else ''}")

    kept.sort(key=lambda t: t[0])                   # original file order
    total = len(kept)
    skew_before = max(len(v) for v in by_tid.values()) / len(rows)
    skew_after = max(sum(1 for i, r in kept
                         if r["meta"]["tid"] == tid) for tid in by_tid) / total
    print(f"\n  N = {total}   (top-task share {skew_before:.1%} -> {skew_after:.1%})")

    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for _, r in kept)
    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    print(f"  sha256 = {sha}")

    if args.check:
        print("\n--check: nothing written.")
        return
    # newline="" is load-bearing. write_text() defaults to translating "\n" to
    # os.linesep, so on Windows this wrote CRLF while `sha` above was computed
    # over the LF text — the number printed for the prereg did not match the
    # bytes on disk (measured: printed 0bb9a659…, file was 85fc0bdc…). Writing
    # LF verbatim makes the prereg hash checkable and the file platform-stable.
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(body)
    on_disk = dataset_gate.sha256_file(OUT)
    if on_disk != sha:
        raise SystemExit(f"ABORT: wrote bytes hashing {on_disk} but reported "
                         f"{sha}. The prereg number must match the file.")
    print(f"\nwrote {OUT.relative_to(HERE)}  ({total} pairs)")
    print("Put N and this sha256 in the prereg; train run 1 from THIS file only.")
    print("Re-run verify_dataset.py — this new file is not covered by the old "
          "receipt, and training will refuse until it is.")


if __name__ == "__main__":
    main()
