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
import platform
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


def _run_cell(bname: str, name: str, suffix: str, op: str):
    # Re-imported per call: correct under spawn (fresh interpreter, no
    # inherited module object); a sys.modules hit under fork, used below.
    # `name` is the TASK name, which is what named the two sources the
    # lowering pass wrote and what keys the row this cell belongs to.
    backend = importlib.import_module(f"verifiers.{bname}")
    real = harness.OUT / f"{name}.{suffix}"
    twin = harness.OUT / f"{name}_twin.{suffix}"
    r_real, a1 = flake_check(backend.verify, real)
    r_twin, a2 = flake_check(backend.verify, twin)
    return name, bname, op, (r_real.outcome, r_twin.outcome, a1 and a2)


def main() -> int:
    # Mutual exclusion is the lock file taken in __main__ (verifiers.
    # acquire_run_lock), on every platform. A /proc scan used to sit here
    # as an extra Linux-only check, matching any process whose argv held
    # "run_par.py"; it refused against its own launcher — `timeout 600
    # python3 run_par.py`, nohup, sh -c — because the wrapper's argv
    # carries the script name too (measured 2026-09-02 inside a tup guest,
    # exit 2, zero cells run). The lock already answers the question the
    # scan was asking, so the scan is gone.
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=None)
    jobs_arg = ap.parse_args().jobs
    tasks = sorted((HERE / "tasks").glob("*.json"))
    # `rows` is filled at LOAD time below, not here: a task that loaded is
    # keyed by its `name`, and a file the door refused by its stem, which is
    # all such a file has. Building it here from stems made the STEM the
    # identity of the whole run.
    cols, rows, all_ok = [], {}, True
    present = []                        # (bname, lower_fn, suffix), probed backends only

    # INVENTORY FIRST, THEN THE REFUSALS, THEN LOWERING. See run_all.py for
    # the measurement: probing is complete before any task is lowered, so the
    # refusals below can return without a byte having been written under
    # out/.
    for bname, lmod, suffix in BACKENDS:
        try:
            backend = importlib.import_module(f"verifiers.{bname}")
            ver = backend.version()     # binary probe: exactly once, only here, in the parent
        except (Exception, SystemExit) as e:               # noqa: BLE001
            cols.append((bname, f"ABSENT — {e}"))
            continue
        cols.append((bname, ver))
        present.append((bname, importlib.import_module(lmod).lower, suffix))
    present_names = [b for b, v in cols if not v.startswith("ABSENT")]
    MIN_KERNELS = int(os.environ.get("T_MIN_KERNELS", "2"))
    # Refuse BEFORE writing anything — out/ as well as the table; see
    # run_all.py for both measurements behind it.
    if len(present_names) < MIN_KERNELS:
        print(f"\nREFUSED: {len(present_names)} kernel(s) available, "
              f"{MIN_KERNELS} required. Agreement across fewer than two "
              f"kernels is not agreement — it is one opinion, or none. "
              f"Nothing was written: not AGREEMENT.md, not out/.")
        for b, v in cols:
            if v.startswith("ABSENT"):
                print(f"  {b}: {v}")
        return 2
    if not tasks:
        print("\nREFUSED: no tasks in t/tasks/ — nothing was verified. "
              "Nothing was written: not AGREEMENT.md, not out/.")
        return 2

    # LOAD EVERY TASK ONCE, HERE, BEFORE ANY LOWERING. harness.load refuses a
    # task SPEC.md does not admit (harness.SpecError). That call used to sit
    # inside the per-backend loop with nothing catching it, so one
    # nonconforming file in tasks/ ended the whole run in a traceback: every
    # other task's measurement lost, nothing written, and the load repeated
    # once per backend. The rule is the lower-error rule below — one cell's
    # absence must not silence every other measurement in the run — so a
    # nonconforming task is a row of spec-error cells, loud on the console,
    # and the run continues and exits nonzero. Since 2026-09-05 harness.load
    # also refuses a file that is not JSON at all, and one whose top-level
    # value is not an object (`[]`): both used to walk straight past this
    # except and end the run in a traceback.
    # THE ROW KEY IS THE TASK NAME, AND `rows` IS BUILT HERE BECAUSE OF IT.
    # A task's identity is `name`: SPEC.md makes it an Id, and every lowering
    # embeds it as the module, crate or unit name of what it emits. A FILE
    # name is not an Id — `abs.v1.json`, or a name with a space, is a legal
    # file — so keying the run on the stem handed one to the kernels as a
    # filename: measured 2026-09-05, abs.json copied to zzW2_abs.v1.json
    # emitted out/zzW2_abs.v1.fst carrying `module Abs`, and F* refuses that
    # file by name (Error 141, "Expected module zzW2_abs.v1", exit 1, while
    # the same bytes named Abs.fst verify), and verifiers/verus.py hands the
    # path to verus with no --crate-name, so rustc derives THAT name from the
    # filename too. Building `rows` from t.stem up front was the
    # other half of that, and the KeyError it was meant to avoid — a file
    # whose task name is not its stem — is closed by keying the row with the
    # name the task actually loaded with. A file the DOOR refused has no
    # trustworthy name, so its row is keyed by its stem: the only thing such
    # a file has.
    loaded = []
    for tpath in tasks:
        try:
            task = harness.load(tpath)
        except harness.SpecError as e:
            rows[tpath.stem] = {b: ("spec-error", "spec-error", True, "")
                                for b in present_names}
            all_ok = False
            print(f"  {tpath.stem}: REFUSED — {e}  <-- FINDING")
            continue
        loaded.append((tpath.name, task))
        rows.setdefault(task["name"], {})

    # Lowering + writes: sequential, entirely before any dispatch below, so
    # out/*.{suffix} has a single writer for the whole time it is produced.
    # ONE ARTIFACT, ONE WRITER. Identity is the task NAME, so two task files
    # holding the same `name` — or names `x` and `x_twin`, both Ids — claim
    # one out/<name>.<sfx> and one out/<name>_twin.<sfx>.
    # This driver lowers every task before it dispatches any verification, so
    # without this map the second writer's REAL source landed on the first
    # task's twin path before a kernel read either: measured 2026-09-05 with
    # two task files claiming one twin path, the first row came back
    # `verified / verified` on dafny, lean and F*, its two artifacts hashing
    # the same 9fe1e7e8….
    # A collision is a defect in the task SET, and the author who named the
    # tasks is the one who can fix it, so it is refused and named here rather
    # than worked around with per-task directories or a rename.
    written: dict[Path, str] = {}     # artifact path -> the task FILE that wrote it
    pending, wits, emitted = [], {}, []
    for bname, lower, suffix in present:
        for fname, task in loaded:
            name = task["name"]
            # ONE IDENTITY, THE TASK NAME — the key `rows` was built with
            # at load time, and the name every lowering embeds in what it
            # emits. The file's stem was tried here and is not an identity:
            # a stem can be any legal filename, and the kernels read the
            # emitted file BY NAME (measured 2026-09-05 — see the load loop
            # above, and harness.run_task).
            # The whole task, not just the body: the twin is chosen by a
            # measured witness (harness.twin_for), and the witness needs
            # params/requires/ensures to have anything to run on. Cached, so
            # the ladder search happens once per task, not once per backend.
            twin_body, op, w = harness.twin_cached(task)
            if twin_body is None:
                rows[name][bname] = ("no-twin", "no-twin", True, "")
                all_ok = False
                # The count the search ACTUALLY enumerated, not the cap:
                # harness.refusal re-walks the domain for a coverage refusal
                # (86 points on the probe measured 2026-09-05), and the
                # static string can only quote interp.MAX_POINTS.
                print(f"  {name} x {bname}: no twin — "
                      f"{harness.refusal(op, task)}  <-- FINDING")
                continue
            try:
                real_src = lower(task, task["body"])
                twin_src = lower(task, twin_body, witness=w)
            except NotImplementedError as e:
                rows[name][bname] = ("abstain", "abstain", True, "")
                all_ok = False
                print(f"  {name} x {bname}: ABSTAIN — {e}")
                continue
            except Exception as e:                          # noqa: BLE001
                rows[name][bname] = ("lower-error", "lower-error", True, "")
                all_ok = False
                print(f"  {name} x {bname}: LOWER-ERROR — {type(e).__name__}: {e}")
                continue
            # newline="\n": the lowering's bytes are the verdict basis, hashed
            # into AGREEMENT.md. Path.write_text defaults to os.linesep, so a
            # Windows host produced CRLF sources whose hashes differed from
            # every other platform's for the same text (measured 2026-09-02:
            # abs.dfy 9147e4af… on Windows vs 9fe1e7e8… everywhere else,
            # equal after CRLF->LF). One newline choice, every host.
            real = harness.OUT / f"{name}.{suffix}"
            twin = harness.OUT / f"{name}_twin.{suffix}"
            clash = next((p for p in (real, twin) if p in written), None)
            if clash is not None:
                # NEITHER file is written. What is already on disk is what an
                # earlier task's verdict will be measured on, and this task
                # has no artifact of its own to be measured on.
                rows[name][bname] = ("path-collision", "path-collision",
                                     True, "")
                all_ok = False
                print(f"  {name} ({fname}) x {bname}: PATH-COLLISION — "
                      f"out/{clash.name} is also written by "
                      f"{written[clash]}  <-- FINDING")
                continue
            real.write_text(real_src, encoding="utf-8", newline="\n")
            twin.write_text(twin_src, encoding="utf-8", newline="\n")
            written[real] = written[twin] = fname
            emitted += [real, twin]     # only what THIS run wrote; see below
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
            name, bname, op, cell3 = fut.result()
            # A +nonrefuting TWIN IS NOT COUNTABLE. When no rung of the ladder
            # falsifies `ensures`, harness.twin_for falls back to a twin that
            # merely computes something different and records the weakness in
            # the operator tag. A kernel may still REFUTE such a twin, for a
            # reason its witness does not name; counting that as the flip
            # credits the instrument with a measurement it did not make. The
            # tag rides in the cell so the table says so too, not just the
            # console line that scrolls past. The rule is one function,
            # harness.counts_as_flip, asked here and in harness.run_task.
            note = "" if harness.counts_as_flip(op) else "+nonrefuting"
            cell = cell3 + (note,)
            if rows[name].get(bname, ("",))[0] == "path-collision":
                # Two task files hold this NAME, so they share this row;
                # the verdict is the first writer's and the cell is the
                # second's refusal. run_all.py measures each task as it
                # lowers and ends the row on the collision because it came
                # second; here the pool hands verdicts back later. Same
                # row in both: a name claimed twice has no verdict of its
                # own. Measured 2026-09-05 with abs.json copied under a
                # second file name: the row read `verified / refuted`
                # under three PATH-COLLISION lines.
                print(f"  {name} x {bname} [{op}]: real={cell[0]} "
                      f"twin={cell[1]} — not recorded, the row is a "
                      f"path-collision")
                continue
            rows[name][bname] = cell
            flip = cell[:3] == (Outcome.VERIFIED, Outcome.REFUTED, True)
            good = flip and not note
            all_ok &= good
            mark = "" if good else "  <-- FINDING"
            if flip and note:
                mark += (" — refuted, but the twin's witness does not falsify "
                         "`ensures`, so this is not the flip and is not "
                         "counted")
            print(f"  {name} x {bname} [{op}]: real={cell[0]} twin={cell[1]}"
                  + mark
                  + f"   (twin witness: {harness.witness(wits.get(name))})")

    tagged = any(c[3] for cells in rows.values() for c in cells.values())
    lines = [f"# t cross-kernel agreement — "
             f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')}",
             "",
             # WHICH KIND OF MACHINE PRODUCED THIS. The committed table read
             # "Kernels present: 7 of 7" with the tool versions and no host
             # on it; the same command on a three-kernel box regenerates
             # "3 of 7", and a reader had no way to tell a different platform
             # from a regression. OS and release only — no user, no path, and
             # since 2026-09-05 no node name either: a workstation nickname
             # is a machine's, not a measurement's, and nothing downstream
             # reads it.
             f"Produced on: {platform.system()} {platform.release()}",
             "",
             "Cell = real outcome / twin outcome. Agreement means "
             "`verified / refuted` in every present column."]
    if tagged:
        lines.append("A cell tagged `(+nonrefuting)` is NOT counted: that "
                     "twin differs from the real body but does not falsify "
                     "`ensures`, so a REFUTED verdict on it is not the flip.")
    lines.append("")
    header = "| task | " + " | ".join(b for b, _ in cols) + " |"
    lines += [header, "|" + "---|" * (len(cols) + 1)]
    for tname, cells in rows.items():
        row = [tname]
        for bname, _ in cols:
            c = cells.get(bname)
            row.append("—" if c is None else
                       f"{c[0]} / {c[1]}"
                       + (f" ({c[3]})" if c[3] else "")
                       + ("" if c[2] else " (FLAKED)"))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"Kernels present: {len(present_names)} of {len(cols)} "
              f"({', '.join(present_names) if present_names else 'NONE'})"]
    lines += ["", "Backends:"] + [f"- {b}: {v}" for b, v in cols]
    # HASH WHAT THIS RUN WROTE. The basis line named `abs.rs` unconditionally
    # — verus's lowering. On a box without verus nothing writes that file, so
    # the line either crashed on a clean out/ (FileNotFoundError, measured
    # 2026-09-05) or hashed a committed leftover from another machine and
    # presented it as this run's basis. `emitted` holds only the files this
    # run produced, in write order, so the example is always one of them.
    if emitted:
        lines += ["", "Verdict basis: every source file hashed; e.g. "
                  + ", ".join(f"`{p.name}` {sha256_file(p)[:16]}…"
                              for p in emitted[:2])]
    else:
        lines += ["", "Verdict basis: none — no lowering was emitted, so "
                  "there is no source file to hash."]
    (HERE / "AGREEMENT.md").write_text("\n".join(lines) + "\n",
                                       encoding="utf-8", newline="\n")
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
