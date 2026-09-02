#!/usr/bin/env python3
"""run_par.py — cell-parallel driver for the t suite; run_all.py is the
reference instrument. Cells (task, backend) are independent — distinct
out/ filenames — so this computes the identical (real, twin, agreed) tuple
per cell over a ProcessPoolExecutor instead of a for-loop, writing the
identical t/AGREEMENT.md format so the two tables diff cleanly modulo the
timestamp line.

Cross-check against run_all.py: DONE 2026-08-31, ubuntu-box — the two
tables are byte-identical modulo the timestamp line (65/66 cells
verified/refuted, the same count_matches x rocq timeout finding, exit 1
from both), serial 27 min vs parallel 9 min, the parallel time being the
slowest single cell (that rocq timeout, 3 x 180 s wall). Standing rule:
divergence between the two tables is a finding about the suite, not a
driver bug to paper over — parallel is a second measurement, never a
faster stand-in trusted by default.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                      # noqa: E402
from verifiers import Outcome, flake_check, sha256_file, mp_context   # noqa: E402

BACKENDS = [
    ("dafny", "lower_dafny", "dfy"),
    ("verus", "lower_verus", "rs"),
    ("spark", "lower_spark", "ads"),
    ("framac", "lower_framac", "c"),
    ("lean", "lower_lean", "lean"),
    ("rocq", "lower_rocq", "v"),
    ("fstar", "lower_fstar", "fst"),
]


def _live_conflict() -> str | None:
    # /proc scan, not pgrep: no external-binary dependency. Two live
    # run_all.py/run_par.py both write the same out/*.{suffix} names.
    me = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == me:
            continue
        try:
            raw = entry.joinpath("cmdline").read_bytes()
        except OSError:
            continue
        argv = [a for a in raw.decode(errors="replace").split("\0") if a]
        # Basename equality, not substring: the first Dell run refused
        # against its own launching shell, whose single -c argument merely
        # CONTAINED "run_par.py" inside a longer command string (measured
        # 2026-08-31, exit 2, zero cells run). boot_witness.sh paid for the
        # same self-match lesson with pgrep; a real invocation has the
        # script as its own argv element, and that is what this matches.
        if any(os.path.basename(a) in ("run_all.py", "run_par.py")
               for a in argv):
            return f"pid {entry.name}: {' '.join(argv)}"
    return None


def _run_cell(bname: str, task_name: str, suffix: str, op: str):
    # Re-imported per call: correct under spawn (fresh interpreter, no
    # inherited module object); a sys.modules hit under fork, used below.
    backend = importlib.import_module(f"verifiers.{bname}")
    real = harness.OUT / f"{task_name}.{suffix}"
    twin = harness.OUT / f"{task_name}_twin.{suffix}"
    r_real, a1 = flake_check(backend.verify, real)
    r_twin, a2 = flake_check(backend.verify, twin)
    return task_name, bname, op, (r_real.outcome, r_twin.outcome, a1 and a2)


def main() -> int:
    # /proc is Linux furniture; elsewhere the lock in __main__ is the
    # only guard, and iterating a missing /proc would crash before it.
    conflict = _live_conflict() if Path("/proc").is_dir() else None
    if conflict:
        print(f"REFUSED: another t run is live ({conflict}). Two concurrent "
              f"runs write the same out/ filenames; let it finish first.")
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=None)
    jobs_arg = ap.parse_args().jobs
    tasks = sorted((HERE / "tasks").glob("*.json"))
    cols, rows, all_ok = [], {t.stem: {} for t in tasks}, True
    present = []                        # (bname, lower_fn, suffix), probed backends only

    for bname, lmod, suffix in BACKENDS:
        try:
            backend = importlib.import_module(f"verifiers.{bname}")
            ver = backend.version()     # binary probe: exactly once, only here, in the parent
        except (Exception, SystemExit) as e:               # noqa: BLE001
            cols.append((bname, f"ABSENT — {e}"))
            continue
        cols.append((bname, ver))
        present.append((bname, importlib.import_module(lmod).lower, suffix))
    # Lowering + writes: sequential, entirely before any dispatch below, so
    # out/*.{suffix} has a single writer for the whole time it is produced.
    pending, wits = [], {}
    for bname, lower, suffix in present:
        for tpath in tasks:
            task = harness.load(tpath)
            name = task["name"]
            # The whole task, not just the body: the twin is chosen by a
            # measured witness (harness.twin_for), and the witness needs
            # params/requires/ensures to have anything to run on. Cached, so
            # the ladder search happens once per task, not once per backend.
            twin_body, op, w = harness.twin_cached(task)
            if twin_body is None:
                rows[name][bname] = ("no-twin", "no-twin", True)
                all_ok = False
                print(f"  {name} x {bname}: no twin — "
                      f"{harness.REFUSALS[op]}  <-- FINDING")
                continue
            try:
                real_src = lower(task, task["body"])
                twin_src = lower(task, twin_body)
            except NotImplementedError as e:
                rows[name][bname] = ("abstain", "abstain", True)
                all_ok = False
                print(f"  {name} x {bname}: ABSTAIN — {e}")
                continue
            except Exception as e:                          # noqa: BLE001
                rows[name][bname] = ("lower-error", "lower-error", True)
                all_ok = False
                print(f"  {name} x {bname}: LOWER-ERROR — {type(e).__name__}: {e}")
                continue
            (harness.OUT / f"{name}.{suffix}").write_text(real_src, encoding="utf-8")
            (harness.OUT / f"{name}_twin.{suffix}").write_text(twin_src, encoding="utf-8")
            pending.append((bname, name, suffix, op))
            wits[name] = w
    n_cells = len(tasks) * len(BACKENDS)          # matrix size, independent of what lowered
    jobs = jobs_arg or max(1, min(n_cells, os.cpu_count() or 1))
    # Platform-selected: fork where it exists, spawn on Windows. The spawn
    # contract (module-level worker, picklable args, __main__ guard) lives
    # in verifiers.mp_context's docstring; the spawn branch is exercised on
    # Linux via T_MP_START=spawn against the full matrix.
    ctx = mp_context()
    with ProcessPoolExecutor(max_workers=jobs, mp_context=ctx) as ex:
        futs = {ex.submit(_run_cell, b, n, s, o): (b, n, o) for b, n, s, o in pending}
        for fut in as_completed(futs):
            name, bname, op, cell = fut.result()
            rows[name][bname] = cell
            good = cell == (Outcome.VERIFIED, Outcome.REFUTED, True)
            all_ok &= good
            print(f"  {name} x {bname} [{op}]: real={cell[0]} twin={cell[1]}"
                  + ("" if good else "  <-- FINDING")
                  + f"   (twin witness: {harness.witness(wits.get(name))})")
    present_names = [b for b, v in cols if not v.startswith("ABSENT")]
    MIN_KERNELS = int(os.environ.get("T_MIN_KERNELS", "2"))

    lines = [f"# t cross-kernel agreement — "
             f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')}",
             "",
             "Cell = real outcome / twin outcome. Agreement means "
             "`verified / refuted` in every present column.",
             ""]
    header = "| task | " + " | ".join(b for b, _ in cols) + " |"
    lines += [header, "|" + "---|" * (len(cols) + 1)]
    for tname, cells in rows.items():
        row = [tname]
        for bname, _ in cols:
            c = cells.get(bname)
            row.append("—" if c is None else
                       f"{c[0]} / {c[1]}" + ("" if c[2] else " (FLAKED)"))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"Kernels present: {len(present_names)} of {len(cols)} "
              f"({', '.join(present_names) if present_names else 'NONE'})"]
    lines += ["", "Backends:"] + [f"- {b}: {v}" for b, v in cols]
    lines += ["", f"Verdict basis: every source file hashed; e.g. "
              f"`abs.dfy` {sha256_file(harness.OUT / 'abs.dfy')[:16]}…, "
              f"`abs.rs` {sha256_file(harness.OUT / 'abs.rs')[:16]}…"]
    (HERE / "AGREEMENT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if len(present_names) < MIN_KERNELS:
        print(f"\nREFUSED: {len(present_names)} kernel(s) available, "
              f"{MIN_KERNELS} required. Agreement across fewer than two "
              f"kernels is not agreement — it is one opinion, or none.")
        for b, v in cols:
            if v.startswith("ABSENT"):
                print(f"  {b}: {v}")
        return 2
    if not tasks:
        print("\nREFUSED: no tasks in t/tasks/ — nothing was verified.")
        return 2
    print(f"\n{len(present_names)} kernels, {len(tasks)} tasks: "
          f"{'FULL AGREEMENT' if all_ok else 'DISAGREEMENT — a finding, see t/AGREEMENT.md'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    from verifiers import acquire_run_lock
    _lock = acquire_run_lock(HERE / "out")
    if not callable(_lock):
        print(f"REFUSED: {_lock}")
        raise SystemExit(2)
    try:
        _code = main()
    finally:
        _lock()
    raise SystemExit(_code)
