#!/usr/bin/env python3
"""verify_dataset.py — the data-integrity GATE.

Before any training, re-run every preference pair through the verifier in BOTH
directions: `chosen` must still PASS its hidden tests and `rejected` must still
FAIL them. A rejected that passes is preference noise (nobody checked the rejected
side at generation time). Pure local execution — no model, no training env.

COVERS THE FILE TRAINING ACTUALLY LOADS. dpo_pairs_capped.jsonl is what
train_native.py reads; verifying only dpo_pairs.jsonl left that coverage merely
transitive (capped is built as a subset, so it *ought* to inherit the result).
"Ought to" is not a gate, so the capped file is now verified by name. Pairs are
deduplicated by content first, so the subset costs almost no extra subprocesses.

On success this writes a RECEIPT (schema in dataset_gate.py) recording the sha256
of every file it verified. train_native.py refuses to start without one that
matches its inputs — that is what makes "verified before training" a mechanism
rather than a habit.

Also reconciles the known_hard.json vs ledger contradiction (multiply_strings).

Writes data/dataset_verification.json. Exit code 1 if any violation is found.
"""
from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dataset_gate
import forge

DATA = forge.OUT_DIR
# dpo_pairs_capped.jsonl is the run-1 training input (build_training_set.py).
FILES = {"dpo_pairs.jsonl": "forge",
         "dpo_pairs_capped.jsonl": "train",
         "repair_pairs.jsonl": "repair"}
TASKS = {t.tid: t for t in forge.SEED_TASKS}


def signature(d: dict) -> str:
    """Content identity of a pair. Verification depends on which task's tests
    run, so the tid is part of the identity, not just the three text fields."""
    tid = (d.get("meta") or {}).get("tid") or ""
    return hashlib.sha1(
        (d.get("prompt", "") + d.get("chosen", "") +
         d.get("rejected", "") + tid).encode("utf-8")).hexdigest()


def load_pairs():
    """Returns (unique_pairs, rows_by_file). A pair present in several files is
    verified once; every file that contains it inherits that one verdict."""
    unique: dict[str, dict] = {}
    rows_by_file: dict[str, list[str]] = {}
    for fname, src in FILES.items():
        p = DATA / fname
        if not p.exists():
            continue
        sigs: list[str] = []
        for i, line in enumerate(p.open(encoding="utf-8")):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            sig = signature(d)
            sigs.append(sig)
            if sig not in unique:
                d["_src"], d["_row"], d["_file"] = src, i, fname
                unique[sig] = d
        rows_by_file[fname] = sigs
    return unique, rows_by_file


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
    unique, rows_by_file = load_pairs()
    sigs = list(unique)
    total_rows = sum(len(v) for v in rows_by_file.values())
    print(f"re-verifying {len(sigs)} unique pairs bidirectionally "
          f"(chosen passes / rejected fails) "
          f"covering {total_rows} rows across {len(rows_by_file)} files...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(check, (unique[s] for s in sigs)))
    by_sig = dict(zip(sigs, results))

    violations = [r for r in results if not r["ok"]]
    by_tid = {}
    for r in results:
        by_tid.setdefault(r["tid"], {"n": 0, "bad": 0})
        by_tid[r["tid"]]["n"] += 1
        if not r["ok"]:
            by_tid[r["tid"]]["bad"] += 1

    # Per-file rollup: a file is clean only if every row in it is clean.
    per_file = {
        fname: {
            "pairs": len(sl),
            "violations": sum(1 for s in sl if not by_sig[s]["ok"]),
        }
        for fname, sl in rows_by_file.items()
    }

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
        # schema/files are the RECEIPT train_native.py checks; the rest is the
        # human report. One artifact, one truth about the same verification run.
        "schema": dataset_gate.SCHEMA,
        "total_pairs": len(sigs),              # unique pairs actually verified
        "total_rows_across_files": total_rows,  # rows, counting shared pairs once per file
        "violations": len(violations),
        "violation_detail": violations[:50],
        "per_tid": by_tid,
        "files": dataset_gate.build_file_entries(DATA, per_file),
        "known_hard": kh,
        "reconcile_contradictions": contradictions,
    }
    dataset_gate.receipt_path(DATA).write_text(json.dumps(report, indent=2))

    for fname, e in report["files"].items():
        print(f"  {fname:<24} {e['pairs']:>5} rows  "
              f"{e['violations']} violations  sha256 {e['sha256'][:12]}…")
    print(f"\n{'PASS' if not violations else 'FAIL'}: "
          f"{len(sigs) - len(violations)}/{len(sigs)} pairs valid")
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
    print(f"\nwrote {dataset_gate.receipt_path(DATA)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
