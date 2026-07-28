#!/usr/bin/env python3
"""clean_dataset.py — resolve the two gate findings, reproducibly.

1. Drop any pair whose `rejected` actually passes (legacy conciseness pairs — a
   different, weaker preference type already gated off in forge.py). The raw file
   is preserved as dpo_pairs.raw.jsonl; nothing is destroyed.
2. Recompute known_hard.json: a task is only 'known-hard' if it has ZERO verified
   pairs. multiply_strings has 41 verified solves -> the quarantine label was stale.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import forge

DATA = forge.OUT_DIR
TASKS = {t.tid: t for t in forge.SEED_TASKS}


def valid(pair) -> bool:
    task = TASKS.get(pair.get("meta", {}).get("tid"))
    if task is None:
        return False
    return forge.verify(pair["chosen"], task).ok and not forge.verify(pair["rejected"], task).ok


def main() -> None:
    src = DATA / "dpo_pairs.jsonl"
    raw = DATA / "dpo_pairs.raw.jsonl"
    pairs = [json.loads(l) for l in src.open(encoding="utf-8")]

    with ThreadPoolExecutor(max_workers=8) as ex:
        keep_flags = list(ex.map(valid, pairs))
    kept = [p for p, k in zip(pairs, keep_flags) if k]
    dropped = [p for p, k in zip(pairs, keep_flags) if not k]

    if not raw.exists():
        raw.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs),
                       encoding="utf-8")
    src.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in kept),
                   encoding="utf-8")

    from collections import Counter
    drop_reasons = Counter(p.get("meta", {}).get("reason", "?") for p in dropped)
    print(f"kept {len(kept)}/{len(pairs)} pairs; dropped {len(dropped)} "
          f"(reasons: {dict(drop_reasons)})")
    print(f"raw preserved at {raw.name}")

    # Recompute known_hard from the cleaned dataset.
    solved = {p.get("meta", {}).get("tid") for p in kept}
    khp = DATA / "known_hard.json"
    old_kh = json.loads(khp.read_text()) if khp.exists() else []
    new_kh = [t for t in old_kh if t not in solved]
    khp.write_text(json.dumps(sorted(new_kh)))
    removed = sorted(set(old_kh) - set(new_kh))
    print(f"known_hard: {old_kh} -> {new_kh}  (removed as stale: {removed})")


if __name__ == "__main__":
    main()
