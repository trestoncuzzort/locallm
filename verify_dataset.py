#!/usr/bin/env python3
"""verify_dataset.py — the data-integrity GATE (council §12 item 1a).

Before any training, re-run every preference pair through the verifier in BOTH
directions: `chosen` must still PASS its hidden tests and `rejected` must still
FAIL them. A rejected that passes is preference noise (nobody checked the rejected
side at generation time). Pure local execution — no model, no training env.

Also reconciles the known_hard.json vs ledger contradiction (multiply_strings).

Writes data/dataset_verification.json. Exit code 1 if any violation is found.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import forge

DATA = forge.OUT_DIR
FILES = {"dpo_pairs.jsonl": "forge", "repair_pairs.jsonl": "repair"}
TASKS = {t.tid: t for t in forge.SEED_TASKS}


def load_pairs():
    pairs = []
    for fname, src in FILES.items():
        p = DATA / fname
        if not p.exists():
            continue
        for i, line in enumerate(p.open(encoding="utf-8")):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            d["_src"], d["_row"] = src, i
            pairs.append(d)
    return pairs


def check(pair) -> dict:
    tid = pair.get("meta", {}).get("tid")
    task = TASKS.get(tid)
    if task is None:
        return {"tid": tid, "src": pair["_src"], "row": pair["_row"],
                "ok": False, "why": "no_matching_task"}
    chosen_ok = forge.verify(pair["chosen"], task).ok
    rejected_ok = forge.verify(pair["rejected"], task).ok
    problems = []
    if not chosen_ok:
        problems.append("chosen_does_not_pass")
    if rejected_ok:
        problems.append("rejected_incorrectly_passes")
    return {"tid": tid, "src": pair["_src"], "row": pair["_row"],
            "ok": not problems, "why": ",".join(problems) or "ok"}


def main() -> int:
    pairs = load_pairs()
    print(f"re-verifying {len(pairs)} pairs bidirectionally (chosen passes / rejected fails)...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(check, pairs))

    violations = [r for r in results if not r["ok"]]
    by_tid = {}
    for r in results:
        by_tid.setdefault(r["tid"], {"n": 0, "bad": 0})
        by_tid[r["tid"]]["n"] += 1
        if not r["ok"]:
            by_tid[r["tid"]]["bad"] += 1

    # Reconcile known_hard vs ledger.
    kh = []
    khp = DATA / "known_hard.json"
    if khp.exists():
        kh = json.loads(khp.read_text())
    reconcile = {tid: {"pairs_in_dataset": by_tid.get(tid, {}).get("n", 0),
                       "labeled_known_hard": tid in kh} for tid in set(list(by_tid) + kh)}
    contradictions = {t: v for t, v in reconcile.items()
                      if v["labeled_known_hard"] and v["pairs_in_dataset"] > 0}

    report = {
        "total_pairs": len(pairs),
        "violations": len(violations),
        "violation_detail": violations[:50],
        "per_tid": by_tid,
        "known_hard": kh,
        "reconcile_contradictions": contradictions,
    }
    (DATA / "dataset_verification.json").write_text(json.dumps(report, indent=2))

    print(f"\n{'PASS' if not violations else 'FAIL'}: "
          f"{len(pairs) - len(violations)}/{len(pairs)} pairs valid")
    if violations:
        from collections import Counter
        print("  violation types:", dict(Counter(v["why"] for v in violations)))
        for v in violations[:10]:
            print(f"    {v['src']}[{v['row']}] tid={v['tid']}: {v['why']}")
    if contradictions:
        print("\nRECONCILE: tasks labeled known_hard BUT present as training pairs "
              "(label is stale — they were solved):")
        for t, v in contradictions.items():
            print(f"    {t}: {v['pairs_in_dataset']} pairs in dataset, known_hard={v['labeled_known_hard']}")
    print(f"\nwrote {DATA / 'dataset_verification.json'}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
