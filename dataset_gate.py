#!/usr/bin/env python3
"""dataset_gate.py — one source of truth for "this training file was verified".

`verify_dataset.py` WRITES the receipt; `train_native.py` REQUIRES it. The
hashing rule lives here once, so a receipt cannot come to mean two different
things in two places.

A receipt vouches for FILE CONTENT, never for a filename: each entry carries the
sha256 of the exact bytes that were verified. Rebuild a dataset and its hash
changes, the stale receipt stops covering it, and training refuses to start.
That is the whole point — "every pair is verified before training" is enforced
here by a mechanism instead of by remembering to run a script.

There is deliberately NO bypass flag. A switch that let training proceed on
unverified data would make the claim this module exists to guarantee false again.

WHO MAY ISSUE A RECEIPT, and what this does NOT protect against — stated here
rather than left implicit, because a guard that overstates its reach is worse
than no guard:

  - A receipt is NOT proof of success by its existence. verify_dataset.py writes
    one on every run, recording the violation count truthfully including when it
    fails. `require_verified` is the only thing that grants permission, and it
    demands violations == 0 AND a matching hash. A failed run therefore replaces
    a passing receipt with a failing one, which is the intended behaviour.
  - This is unsigned plain JSON. It defends against DRIFT and ACCIDENT — a
    regenerated dataset, a stale receipt, hand-edited rows, a file swapped after
    verification. It does NOT defend against someone who edits the receipt
    itself, and it is not intended to; that would need signing and a key this
    project has nowhere to keep.
  - It certifies bytes, not judgement. "Verified" here means exactly: every pair
    in this file was executed and `chosen` passed while `rejected` failed. It
    says nothing about whether the pairs are good training signal.

Stdlib only, on purpose: this is imported both by the system Python (verify side)
and by .venv-train's Python 3.11 (training side).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPT_NAME = "dataset_verification.json"
SCHEMA = 3          # bump when the `files` or `verifier` entry shape changes

# THE RECEIPT MUST PIN THE VERIFIER, NOT ONLY THE DATA.
# "0 violations" is a statement about forge.verify() run against forge.SEED_TASKS.
# Weaken one assert, loosen the BANNED regex, shorten CAND_TIMEOUT, or drop the
# return-type guard, and every data hash still matches while the *meaning* of
# "verified" silently changes — producing a PASSING receipt for a weaker claim.
# That is worse than a failing one.
#
# Whole file, deliberately. The tempting alternative is to hash only "the parts
# that matter" — SEED_TASKS, BANNED, CAND_TIMEOUT, the harness template. That
# requires hand-picking which parts of a verifier are semantic, which is exactly
# the invented-scope mistake this project keeps paying for: the guard passes while
# the thing it guards has moved. A whole-file hash has no scope to get wrong.
# The price is real and accepted: editing a comment in forge.py invalidates the
# receipt and forces a re-verify. That is the correct direction to be wrong in.
VERIFIER_FILES = ("forge.py",)


def sha256_file(path: str | Path) -> str:
    """Hash a file's exact bytes, streamed (these files run to megabytes)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def receipt_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / RECEIPT_NAME


def verifier_fingerprint() -> dict[str, str]:
    """sha256 of every file whose contents define what 'verified' means."""
    return {name: sha256_file(HERE / name) for name in VERIFIER_FILES}


def build_file_entries(data_dir: str | Path,
                       per_file: dict[str, dict]) -> dict[str, dict]:
    """per_file: {filename: {"pairs": int, "violations": int}} -> receipt entries."""
    out: dict[str, dict] = {}
    for name, counts in per_file.items():
        p = Path(data_dir) / name
        if not p.exists():
            continue
        out[name] = {
            "sha256": sha256_file(p),
            "pairs": counts["pairs"],
            "violations": counts["violations"],
        }
    return out


def require_verified(paths: list[str | Path], data_dir: str | Path) -> dict:
    """Refuse to proceed unless every path has a clean, hash-matching entry.

    Raises SystemExit with an actionable message. Returns the receipt on success.
    """
    rp = receipt_path(data_dir)
    if not rp.exists():
        raise SystemExit(
            f"GATE: no dataset receipt at {rp}.\n"
            f"  Every pair must be re-verified (chosen passes / rejected fails)\n"
            f"  before training. Run:  python verify_dataset.py")
    try:
        receipt = json.loads(rp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"GATE: receipt {rp} is unreadable ({e}). "
                         f"Re-run: python verify_dataset.py")

    if receipt.get("schema") != SCHEMA:
        raise SystemExit(
            f"GATE: receipt schema is {receipt.get('schema')!r}, this code needs "
            f"{SCHEMA}.\n  The receipt predates the current gate and cannot be "
            f"trusted to mean the same thing. Re-run: python verify_dataset.py")

    # The verifier that produced this receipt must be the verifier on disk now.
    recorded = receipt.get("verifier") or {}
    current = verifier_fingerprint()
    if recorded != current:
        changed = sorted(set(recorded) | set(current))
        detail = "".join(
            f"      {n}: receipt {recorded.get(n, '(absent)')[:16]}… "
            f"on-disk {current.get(n, '(absent)')[:16]}…\n"
            for n in changed if recorded.get(n) != current.get(n))
        raise SystemExit(
            "GATE: the VERIFIER changed since this data was verified.\n"
            + detail +
            "  '0 violations' was a statement about the old verifier. It says\n"
            "  nothing about the current one, so the receipt no longer applies.\n"
            "  Re-run:  python verify_dataset.py")

    entries = receipt.get("files") or {}
    problems: list[str] = []
    for path in paths:
        p = Path(path)
        entry = entries.get(p.name)
        if entry is None:
            problems.append(f"{p.name}: NOT COVERED by the receipt")
            continue
        if entry.get("violations", -1) != 0:
            problems.append(f"{p.name}: {entry['violations']} verification "
                            f"violation(s) recorded")
            continue
        actual = sha256_file(p)
        if actual != entry.get("sha256"):
            problems.append(
                f"{p.name}: CONTENT CHANGED since verification\n"
                f"      verified sha256 {entry.get('sha256')}\n"
                f"      on-disk  sha256 {actual}")

    if problems:
        raise SystemExit(
            "GATE: refusing to train on data that is not provably verified.\n"
            + "".join(f"  - {p}\n" for p in problems)
            + "  Fix by re-running:  python verify_dataset.py")

    covered = ", ".join(f"{Path(p).name} ({entries[Path(p).name]['pairs']} pairs)"
                        for p in paths)
    print(f"[gate] verified receipt OK — {covered}; 0 violations, hashes match")
    return receipt
