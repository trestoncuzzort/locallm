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
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPT_NAME = "dataset_verification.json"
SCHEMA = 5          # bump when the `files` or `verifier` entry shape changes
                    # 3 -> 4: `verifier` gained the INTERPRETER, not just the
                    # file hashes (section 71).
                    # 4 -> 5: `verifier` gained the TASK SOURCE (section 91).

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

# ...AND THE VERIFIER IS NOT ONLY forge.py EITHER. "0 violations" is a statement
# about verify() run against A SET OF TASKS, so whatever supplies those tasks is
# part of what "verified" means. Until section 91 the task set was SEED_TASKS,
# a literal inside forge.py, and the forge.py hash therefore covered it for free.
# It no longer does: verify_dataset.load_tasks() now also builds tasks from the
# SCREENED payloads, so the definitions live in a data file and the harness that
# binds their entry point lives in screen_tasks.py. Change either and the tests a
# pair is judged against change while every hash in the old fingerprint still
# matches — the exact silent-weakening failure the block above exists to stop.
#
# Whole files again, for the reason given above: hashing "just the payloads we
# used" would mean hand-picking which bytes are semantic, and that is the
# invented-scope mistake this project keeps paying for. The price is the same one
# already accepted — screening a new task invalidates the receipt and forces a
# re-verify. That is the correct direction to be wrong in.
TASK_SOURCE_FILES = ("screen_tasks.py", "data/screen_results.jsonl")

# ---------------------------------------------------------------------------
# ...AND THE VERIFIER IS NOT ONLY ITS SOURCE. It is source PLUS the interpreter
# that executes the candidate. The block above says the failure mode exactly:
# "every data hash still matches while the *meaning* of 'verified' silently
# changes". A different Python is precisely that, and section 71 caught it live.
# forge.verify() launched [sys.executable, ...], so ground truth was inherited
# from whichever script called it: screen_tasks.py/build_ruler.py re-exec under
# .venv-train (3.11) via venv_guard, while eval.py/forge.py run under system
# 3.14. Red witness: 310 completions replayed through verify() under both, same
# bytes -- 3.14 scored 172/310, 3.11 scored 154/310, all 18 disagreements one
# way, cause PEP 649 deferred annotations (`def f(x: List[int])` with no import
# is a NameError on 3.11 and harmless on 3.14).
#
# The pin LIVES HERE, in the one module both interpreters already import, so
# there is a single definition rather than one per caller -- the mistake
# venv_guard.py exists to prevent. forge.py imports it; it is not re-derived.
# Stdlib only, as the docstring requires.
# ---------------------------------------------------------------------------
_VENV_PY = HERE / ".venv-train" / "Scripts" / "python.exe"
_INTERP_CACHE: dict[str, str] | None = None


def verify_py() -> str:
    """The interpreter that decides 'correct'. SRLM_VERIFY_PY overrides.

    IT FAILS LOUDLY RATHER THAN FALLING BACK, and that is the whole point. The
    first version of this function ended `return sys.executable`, which meant
    that on any machine without .venv-train the verifier silently became the
    launching interpreter again -- i.e. the exact section 71 defect, restored,
    with every artifact still recording a fingerprint as if a pin were in force.
    An independent review pass caught it. Red witness, with _VENV_PY patched to
    a nonexistent path in-memory:
        verify_py() -> C:\\Python314\\python.exe   == sys.executable   DEFECT BACK
    A fallback that reintroduces the bug is worse than no fallback, because it is
    quiet. Anyone genuinely wanting the launcher must now say so with
    SRLM_VERIFY_PY and it will be recorded as a deliberate pin.
    """
    env = os.environ.get("SRLM_VERIFY_PY")
    if env:
        return env
    if _VENV_PY.exists():
        return str(_VENV_PY)
    raise SystemExit(
        "VERIFIER NOT PINNED. Ground truth would fall back to the launching\n"
        f"  interpreter ({sys.executable}), which is the defect section 71 fixed:\n"
        "  guarded and unguarded callers then score against different Pythons.\n"
        f"  expected: {_VENV_PY}\n"
        "  fix: create .venv-train, or pin deliberately with\n"
        "       SRLM_VERIFY_PY=<path-to-python>  (it is recorded in the receipt)")


def interpreter_fingerprint() -> dict[str, str]:
    """Identity of the verifying interpreter, ASKED of it rather than assumed.

    Keyed under a name that cannot collide with a filename in VERIFIER_FILES, so
    it slots into the same `verifier` dict the gate already compares.
    """
    global _INTERP_CACHE
    if _INTERP_CACHE is None:
        exe, ver = verify_py(), "unknown"
        try:
            p = subprocess.run([exe, "-I", "-c",
                                "import sys; print(sys.version.split()[0])"],
                               capture_output=True, text=True, timeout=30)
            if p.returncode == 0:
                ver = p.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        _INTERP_CACHE = {"interpreter": f"python {ver}"}
    return _INTERP_CACHE


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
    """Everything that defines what 'verified' means: the sha256 of every
    verifier file, PLUS the task source those tasks are built from, PLUS the
    interpreter that executes candidates."""
    fp = {name: sha256_file(HERE / name)
          for name in VERIFIER_FILES + TASK_SOURCE_FILES}
    fp.update(interpreter_fingerprint())
    return fp


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


def load_verified(paths: list[str | Path], data_dir: str | Path) -> list[str]:
    """Verify, THEN hand back the paths. Use this instead of calling
    require_verified and then separately naming the files.

    "Parse, don't validate" (Alexis King, 2019): make the checked thing the only
    way to obtain what you need, so the check cannot be skipped by forgetting a
    line. A trainer that gets its file list from here cannot train on data that
    did not pass.

    HONEST LIMIT: this narrows the hole, it does not close it. A future trainer
    could still build a path string itself and never call this. What actually
    bounds that is the coverage test (test_gate_coverage.py), which fails if any
    module outside this file and verify_dataset.py opens data/*.jsonl directly.
    """
    require_verified(paths, data_dir)
    return [str(p) for p in paths]


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
