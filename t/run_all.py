#!/usr/bin/env python3
"""run_all.py — every t task through every available kernel; agreement is the
instrument.

Writes t/AGREEMENT.md: one row per task, one column per backend, each cell the
(real, twin) outcome pair. Full agreement means every kernel VERIFIED the real
lowering and REFUTED the twin. A DISAGREEMENT is not an error in this script's
eyes — it is a finding, the cross-verifier analogue of the paper's
interpreter-pin discovery, and it is written into the table and exits nonzero
so it cannot pass silently.

Backends are probed, not assumed: a kernel that is not installed on this
machine is listed as absent, never faked.
"""
from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness                      # noqa: E402
from verifiers import Outcome, flake_check, sha256_file   # noqa: E402

BACKENDS = [
    ("dafny", "lower_dafny", "dfy"),
    ("verus", "lower_verus", "rs"),
    ("spark", "lower_spark", "ads"),
    ("framac", "lower_framac", "c"),
    ("lean", "lower_lean", "lean"),
    ("rocq", "lower_rocq", "v"),
    # agda: adapter exists (verifiers/agda.py, taxonomy measured 2026-08-31);
    # the LOWERING is parked — no lia/omega analogue in the stdlib means the
    # proof-synthesis template is a design problem, recorded in ROADMAP.md.
    # It joins this list when lower_agda.py exists and flips honestly.
]


def main() -> int:
    tasks = sorted((HERE / "tasks").glob("*.json"))
    cols, rows, all_ok = [], {t.stem: {} for t in tasks}, True

    for bname, lmod, suffix in BACKENDS:
        try:
            backend = importlib.import_module(f"verifiers.{bname}")
            ver = backend.version()
        except (Exception, SystemExit) as e:              # noqa: BLE001
            # SystemExit, not just Exception: an adapter whose binary is
            # missing raises SystemExit carrying the sentence that says where
            # it looked. Catching only Exception let that kill the whole run
            # instead of recording one absent kernel.
            cols.append((bname, f"ABSENT — {e}"))
            continue
        lower = importlib.import_module(lmod).lower
        cols.append((bname, ver))
        for tpath in tasks:
            task = harness.load(tpath)
            real = harness.OUT / f"{task['name']}.{suffix}"
            real.write_text(lower(task, task["body"]), encoding="utf-8")
            twin_body, ok_twin = harness.collapse_first_if(task["body"])
            twin = harness.OUT / f"{task['name']}.twin.{suffix}"
            twin.write_text(lower(task, twin_body), encoding="utf-8")
            r_real, a1 = flake_check(backend.verify, real)
            r_twin, a2 = flake_check(backend.verify, twin)
            cell = (r_real.outcome, r_twin.outcome,
                    a1 and a2 and ok_twin)
            rows[task["name"]][bname] = cell
            good = cell == (Outcome.VERIFIED, Outcome.REFUTED, True)
            all_ok &= good
            print(f"  {task['name']} x {bname}: real={cell[0]} twin={cell[1]}"
                  + ("" if good else "  <-- FINDING"))

    # VACUOUS AGREEMENT IS NOT AGREEMENT. With no kernel installed the loop
    # above never runs, all_ok stays True, and this printed FULL AGREEMENT —
    # measured on a fresh Ubuntu box with nothing installed. A tool that
    # reports success after measuring nothing is the exact failure this
    # project exists to refuse, so a run with too few kernels is now an
    # explicit refusal rather than a pass.
    present = [b for b, v in cols if not v.startswith("ABSENT")]
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
    lines += ["", f"Kernels present: {len(present)} of {len(cols)} "
              f"({', '.join(present) if present else 'NONE'})"]
    lines += ["", "Backends:"] + [f"- {b}: {v}" for b, v in cols]
    lines += ["", f"Verdict basis: every source file hashed; e.g. "
              f"`abs.dfy` {sha256_file(harness.OUT / 'abs.dfy')[:16]}…, "
              f"`abs.rs` {sha256_file(harness.OUT / 'abs.rs')[:16]}…"]
    (HERE / "AGREEMENT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if len(present) < MIN_KERNELS:
        print(f"\nREFUSED: {len(present)} kernel(s) available, {MIN_KERNELS} "
              f"required. Agreement across fewer than two kernels is not "
              f"agreement — it is one opinion, or none.")
        for b, v in cols:
            if v.startswith("ABSENT"):
                print(f"  {b}: {v}")
        return 2
    if not tasks:
        print("\nREFUSED: no tasks in t/tasks/ — nothing was verified.")
        return 2
    print(f"\n{len(present)} kernels, {len(tasks)} tasks: "
          f"{'FULL AGREEMENT' if all_ok else 'DISAGREEMENT — a finding, see t/AGREEMENT.md'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
