#!/usr/bin/env python3
"""dashboard.py — a simple live viewer for the test runs in data/ruler_noise.jsonl.

Groups replicate rows by (model/arm, task_set, verifier version) — the same
partition ruler_noise.py itself refuses to pool across — and shows each
group's count and mean pass@1, with a per-replicate detail view. Auto-refreshes
as new replicates are appended, so it can watch a `measure` run land live.

Deliberately does NOT compute arm-vs-arm comparisons (that needs the
same-session-control / interleaving discipline poscontrol/*.py already
implements — this just shows what's in the file). Use the "Run analysis"
button to invoke poscontrol/final_summary.py for a real comparison.

Run: python dashboard.py
Dependencies: stdlib only (tkinter, json, subprocess).
"""
from __future__ import annotations

import json
import queue
import statistics
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "ruler_noise.jsonl"
FINAL_SUMMARY = HERE / "poscontrol" / "final_summary.py"

# Human labels for known arms, from poscontrol/final_summary.py's own convention.
# Anything not listed here just shows its raw model tag.
ARM_LABELS = {
    "llama3-forged": "trained (original, Jul 28)",
    "llama3-forged-null": "null (original, Jul 28)",
    "llama3-forged-null-rep": "null (Aug 4)",
    "ctl-null": "null (Aug 5 a)",
    "ctl-null3": "null (Aug 5 b)",
    "llama3-forged-rep": "HIS adapter (Aug 4)",
    "ctl-his": "HIS adapter (Aug 5)",
    "llama3-forged-rep1": "retrain 1 (Aug 5)",
    "llama3-forged-rep2": "retrain 2 (Aug 5)",
    "llama3-forged-rep3": "retrain 3 (Aug 5)",
}


def load_rows() -> list[dict]:
    if not DATA.exists():
        return []
    rows = []
    with DATA.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def group_rows(rows: list[dict]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        ver = (r.get("verifier") or {}).get("version", "unrecorded")
        key = (r.get("model", "?"), r.get("task_set", "?"), ver)
        groups.setdefault(key, []).append(r)
    return groups


def arm_label(model: str) -> str:
    return ARM_LABELS.get(model, model)


class ReplicatePlot(tk.Canvas):
    """pass@1 per replicate, oldest to newest. Fixed 0..1 axis on purpose --
    this is a stability check, not a curve to zoom in on."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg="#14161a", highlightthickness=0, **kw)
        self.values: list[float] = []
        self.bind("<Configure>", lambda e: self.redraw())

    def set_values(self, values: list[float]):
        self.values = values
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 30 or not self.values:
            return
        pad_l, pad_r, pad_t, pad_b = 36, 10, 10, 18
        x0, y0, x1, y1 = pad_l, pad_t, w - pad_r, h - pad_b

        for i in range(5):
            y = y0 + (y1 - y0) * i / 4
            self.create_line(x0, y, x1, y, fill="#2a2f38")
            self.create_text(x0 - 6, y, anchor="e", fill="#8a91a0",
                              font=("Segoe UI", 8), text=f"{1 - i / 4:.2f}")

        n = len(self.values)
        mean = statistics.fmean(self.values)

        def to_xy(i, v):
            fx = x0 + (x1 - x0) * (i / max(n - 1, 1))
            fy = y1 - (y1 - y0) * v
            return fx, fy

        my = to_xy(0, mean)[1]
        self.create_line(x0, my, x1, my, fill="#8a6100", dash=(4, 3))
        self.create_text(x1 - 4, my - 9, anchor="e", fill="#8a6100",
                          font=("Segoe UI", 8), text=f"mean {mean:.3f}")

        if n >= 2:
            flat = []
            for i, v in enumerate(self.values):
                flat.extend(to_xy(i, v))
            self.create_line(*flat, fill="#4da3ff", width=2)
        for i, v in enumerate(self.values):
            x, y = to_xy(i, v)
            self.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#4da3ff", outline="")


class Dashboard(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=8)
        self.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(3, weight=2)

        self.rows: list[dict] = []
        self.groups: dict[tuple, list[dict]] = {}
        self._last_mtime = None
        self.q: queue.Queue = queue.Queue()
        self.proc: subprocess.Popen | None = None

        self._build_top()
        self._build_table()
        self._build_detail()
        self._build_runner()
        self.refresh(force=True)
        self.after(2000, self._poll_file)
        self.after(100, self._drain)

    # ------------------------------------------------------------- layout
    def _build_top(self):
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Test runs", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w")
        self.status = ttk.Label(top, text="", foreground="#666a70")
        self.status.grid(row=0, column=1, sticky="e")

    def _build_table(self):
        cols = ("arm", "task_set", "verifier", "n", "mean", "sd", "mean3", "last")
        heads = {"arm": "Arm", "task_set": "Task set", "verifier": "Verifier",
                  "n": "N", "mean": "Mean pass@1", "sd": "SD",
                  "mean3": "Mean pass@3", "last": "Last run"}
        self.table = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c in cols:
            self.table.heading(c, text=heads[c])
            self.table.column(c, width=110 if c not in ("arm",) else 190,
                               anchor="w")
        self.table.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.table.yview)
        self.table["yscrollcommand"] = sb.set
        sb.grid(row=1, column=0, sticky="nse")
        self.table.bind("<<TreeviewSelect>>", lambda e: self._show_detail())

    def _build_detail(self):
        box = ttk.LabelFrame(self, text=" Replicates for the selected arm ")
        box.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        box.columnconfigure(0, weight=1)
        box.columnconfigure(1, weight=1)
        box.rowconfigure(0, weight=1)

        cols = ("rep", "ts", "pass1", "pass3", "errs")
        self.detail = ttk.Treeview(box, columns=cols, show="headings", height=8)
        for c, t, w in (("rep", "#", 40), ("ts", "Timestamp", 150),
                        ("pass1", "pass@1", 70), ("pass3", "pass@3", 70),
                        ("errs", "Gen errors", 80)):
            self.detail.heading(c, text=t)
            self.detail.column(c, width=w, anchor="w")
        self.detail.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.plot = ReplicatePlot(box, width=260, height=160)
        self.plot.grid(row=0, column=1, sticky="nsew")

    def _build_runner(self):
        box = ttk.LabelFrame(self, text=" Add more replicates ")
        box.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        for i in range(6):
            box.columnconfigure(i, weight=0)
        box.columnconfigure(5, weight=1)

        ttk.Label(box, text="Model/arm:").grid(row=0, column=0, padx=(8, 4), pady=6)
        self.v_model = tk.StringVar()
        self.cb_model = ttk.Combobox(box, textvariable=self.v_model, width=26)
        self.cb_model.grid(row=0, column=1, padx=(0, 12))

        ttk.Label(box, text="How many more:").grid(row=0, column=2, padx=(0, 4))
        self.v_count = tk.IntVar(value=5)
        ttk.Spinbox(box, from_=1, to=100, textvariable=self.v_count, width=5).grid(
            row=0, column=3, padx=(0, 12))

        self.b_start = ttk.Button(box, text="▶ Start", command=self._start_run)
        self.b_start.grid(row=0, column=4, padx=(0, 4))
        self.b_stop = ttk.Button(box, text="■ Stop", command=self._stop_run,
                                  state="disabled")
        self.b_stop.grid(row=0, column=5, padx=(0, 4), sticky="w")
        ttk.Button(box, text="Run analysis (final_summary.py)",
                   command=self._run_analysis).grid(row=0, column=6, padx=(0, 8))

        self.log = tk.Text(box, height=6, bg="#14161a", fg="#c8d0dc",
                            font=("Consolas", 9), wrap="word")
        self.log.grid(row=1, column=0, columnspan=7, sticky="nsew",
                       padx=8, pady=(0, 8))
        box.rowconfigure(1, weight=1)

    # ------------------------------------------------------------- data
    def refresh(self, force: bool = False):
        if not DATA.exists():
            self.status.config(text=f"no data yet at {DATA}")
            return
        mtime = DATA.stat().st_mtime
        if not force and mtime == self._last_mtime:
            return
        self._last_mtime = mtime
        self.rows = load_rows()
        self.groups = group_rows(self.rows)
        self._populate_table()
        models = sorted({r.get("model", "") for r in self.rows if r.get("model")})
        self.cb_model["values"] = models
        self.status.config(
            text=f"{len(self.rows)} rows · {len(self.groups)} arm/verifier "
                 f"groups · {DATA.name}")

    def _populate_table(self):
        selected = self.table.selection()
        selected_key = selected[0] if selected else None
        self.table.delete(*self.table.get_children())
        for (model, task_set, ver), rs in sorted(
                self.groups.items(),
                key=lambda kv: (arm_label(kv[0][0]), kv[0][1], kv[0][2])):
            vals = [r["aggregate"]["pass@1"] for r in rs
                    if "aggregate" in r and "pass@1" in r["aggregate"]]
            vals3 = [r["aggregate"]["pass@3"] for r in rs
                     if "aggregate" in r and "pass@3" in r["aggregate"]]
            n = len(rs)
            mean = statistics.fmean(vals) if vals else float("nan")
            sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
            mean3 = statistics.fmean(vals3) if vals3 else float("nan")
            last = max((r.get("ts", "") for r in rs), default="")
            iid = f"{model}\x1f{task_set}\x1f{ver}"
            self.table.insert("", "end", iid=iid, values=(
                arm_label(model), task_set, ver[:24], n,
                f"{mean:.4f}" if vals else "—",
                f"{sd:.4f}" if len(vals) > 1 else "—",
                f"{mean3:.4f}" if vals3 else "—", last))
        if selected_key and self.table.exists(selected_key):
            self.table.selection_set(selected_key)

    def _show_detail(self):
        sel = self.table.selection()
        self.detail.delete(*self.detail.get_children())
        if not sel:
            self.plot.set_values([])
            return
        model, task_set, ver = sel[0].split("\x1f")
        rs = self.groups.get((model, task_set, ver), [])
        rs = sorted(rs, key=lambda r: (r.get("replicate", 0), r.get("ts", "")))
        vals = []
        for r in rs:
            p1 = r.get("aggregate", {}).get("pass@1")
            p3 = r.get("aggregate", {}).get("pass@3")
            self.detail.insert("", "end", values=(
                r.get("replicate", "—"), r.get("ts", ""),
                f"{p1:.4f}" if p1 is not None else "—",
                f"{p3:.4f}" if p3 is not None else "—",
                r.get("gen_errors_total", 0)))
            if p1 is not None:
                vals.append(p1)
        self.plot.set_values(vals)

    def _poll_file(self):
        self.refresh()
        self.after(2000, self._poll_file)

    # ------------------------------------------------------------- runner
    def _start_run(self):
        if self.proc is not None:
            return
        model = self.v_model.get().strip()
        if not model:
            self._log("Pick or type a model/arm tag first.")
            return
        existing = sum(1 for r in self.rows if r.get("model") == model)
        want_total = existing + int(self.v_count.get())
        cmd = [sys.executable, str(HERE / "ruler_noise.py"), "measure",
               "--runs", str(want_total), "--model", model]
        self._log(f"$ {' '.join(cmd)}")
        self.b_start.config(state="disabled")
        self.b_stop.config(state="normal")
        try:
            self.proc = subprocess.Popen(
                cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
        except Exception as e:
            self._log(f"Could not start: {e}")
            self.b_start.config(state="normal")
            self.b_stop.config(state="disabled")
            self.proc = None
            return
        threading.Thread(target=self._pump_proc, args=(self.proc,),
                          daemon=True).start()

    def _pump_proc(self, proc: subprocess.Popen):
        for line in proc.stdout:
            self.q.put(("log", line.rstrip()))
        code = proc.wait()
        self.q.put(("run_done", code))

    def _stop_run(self):
        if self.proc is not None:
            self.proc.terminate()
            self._log("Stopping — the current replicate finishes or is killed; "
                       "already-banked ones are safe (measure resumes from there).")

    def _run_analysis(self):
        if not FINAL_SUMMARY.exists():
            self._log(f"{FINAL_SUMMARY} not found.")
            return
        cmd = [sys.executable, str(FINAL_SUMMARY)]
        self._log(f"$ {' '.join(cmd)}")

        def work():
            try:
                r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
                self.q.put(("log", r.stdout + r.stderr))
            except Exception as e:
                self.q.put(("log", f"Could not run analysis: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _log(self, msg: str):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "run_done":
                    self._log(f"[measure exited with code {payload}]")
                    self.proc = None
                    self.b_start.config(state="normal")
                    self.b_stop.config(state="disabled")
                    self.refresh(force=True)
        except queue.Empty:
            pass
        self.after(100, self._drain)


def main():
    root = tk.Tk()
    root.title("srlm-forge — test run dashboard")
    root.geometry("980x780")
    Dashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
