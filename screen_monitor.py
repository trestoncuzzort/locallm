#!/usr/bin/env python3
"""screen_monitor.py — live window showing the task-screening run.

Reads data/screen_results.jsonl and nothing else. It never talks to the screening
process, so opening, closing or crashing this window cannot disturb the run - which
matters because that run holds the GPU for hours.

    python screen_monitor.py                 # defaults match the launched run
    python screen_monitor.py --candidates 400 --target 30

Shows: how many candidates are screened, how many admitted against the target that
actually matters (~30 supports detecting +3% at k=5 seeds), elapsed time, a rate and
an ETA computed from observed throughput, why candidates are being rejected, and
whether the run is still alive.

The ETA is honest about which of two finishes comes first: the run stops either when
the candidate pool is exhausted OR when the admitted target is reached, so both are
projected and the sooner one is highlighted.
"""
from __future__ import annotations

import argparse
import json
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "data" / "screen_results.jsonl"

BG, FG, DIM = "#14161a", "#e8e8e8", "#8b93a1"
OK, WARN, BAD = "#2d7d46", "#b8860b", "#c0392b"


def hms(s: float) -> str:
    s = max(0, int(s))
    return f"{s // 3600:d}h {(s % 3600) // 60:02d}m {s % 60:02d}s"


class Monitor(tk.Tk):
    def __init__(self, candidates: int, target: int):
        super().__init__()
        self.n_cand, self.target = candidates, target
        self.title("srlm-forge - task screening")
        self.configure(bg=BG)
        self.geometry("760x560")
        self.minsize(640, 480)
        self._last_size = -1
        self._last_change = time.time()

        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("H.Horizontal.TProgressbar", troughcolor="#1e2128",
                     background="#4a9eff", bordercolor=BG, lightcolor="#4a9eff",
                     darkcolor="#4a9eff")
        st.configure("A.Horizontal.TProgressbar", troughcolor="#1e2128",
                     background=OK, bordercolor=BG, lightcolor=OK, darkcolor=OK)

        def lab(txt, size=11, colour=FG, bold=False, pady=0):
            # pady goes to pack(), not to the widget: tk.Label's own pady takes a
            # single screen distance and rejects the (top, bottom) tuple form.
            w = tk.Label(self, text=txt, bg=BG, fg=colour,
                         font=("Segoe UI", size, "bold" if bold else "normal"))
            w.pack(anchor="w", padx=18, pady=pady)
            return w

        lab("TASK SCREENING", 16, FG, True, (14, 0))
        self.sub = lab("admitting tasks whose base pass rate lands in [0.2, 0.8]",
                       9, DIM, False, (0, 10))

        self.l_screened = lab("screened 0 / 0", 12, FG, True)
        self.p_screened = ttk.Progressbar(self, style="H.Horizontal.TProgressbar",
                                          length=700, maximum=candidates)
        self.p_screened.pack(anchor="w", padx=18, pady=(2, 12))

        self.l_admit = lab("admitted 0 / 0", 12, FG, True)
        self.p_admit = ttk.Progressbar(self, style="A.Horizontal.TProgressbar",
                                       length=700, maximum=target)
        self.p_admit.pack(anchor="w", padx=18, pady=(2, 14))

        self.l_time = lab("elapsed --", 11)
        self.l_rate = lab("rate --", 11, DIM)
        self.l_eta = lab("eta --", 11, DIM)
        self.l_alive = lab("", 11, DIM, False, (6, 8))

        lab("WHY CANDIDATES ARE REJECTED", 9, DIM, True, (8, 2))
        self.l_reasons = tk.Label(self, text="", bg=BG, fg=FG, justify="left",
                                  font=("Consolas", 10))
        self.l_reasons.pack(anchor="w", padx=18)

        lab("RECENT", 9, DIM, True, (10, 2))
        self.txt = tk.Text(self, height=9, bg="#1a1d23", fg=FG, bd=0,
                           font=("Consolas", 9), wrap="none")
        self.txt.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        self.refresh()

    def read(self):
        if not RESULTS.exists():
            return [], 0.0
        rows = []
        for line in RESULTS.open(encoding="utf-8"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        try:
            started = RESULTS.stat().st_ctime
        except OSError:
            started = time.time()
        return rows, started

    def refresh(self):
        rows, started = self.read()
        n = len(rows)
        admitted = sum(1 for r in rows if r.get("admitted"))
        elapsed = time.time() - started

        self.p_screened["value"] = min(n, self.n_cand)
        self.p_admit["value"] = min(admitted, self.target)
        self.l_screened.config(text=f"screened   {n} / {self.n_cand}"
                                    f"   ({n / max(self.n_cand,1):.0%})")
        self.l_admit.config(text=f"admitted   {admitted} / {self.target}"
                                 f"   ({admitted / max(self.target,1):.0%})")
        self.l_time.config(text=f"elapsed    {hms(elapsed)}")

        if n >= 2 and elapsed > 0:
            per = elapsed / n
            self.l_rate.config(
                text=f"rate       {per:.1f}s per candidate"
                     f"   |   {admitted / n:.1%} admit rate")
            # Two ways this run ends; report whichever arrives first.
            eta_pool = (self.n_cand - n) * per
            if admitted:
                eta_target = (self.target - admitted) * (elapsed / admitted)
            else:
                eta_target = float("inf")
            if eta_target < eta_pool:
                self.l_eta.config(text=f"eta        {hms(eta_target)} to "
                                       f"{self.target} admitted (target first)",
                                  fg=OK)
            else:
                short = admitted + (self.n_cand - n) * (admitted / n)
                note = ("" if short >= self.target
                        else f"  - projecting ~{short:.0f} admitted, SHORT of {self.target}")
                self.l_eta.config(text=f"eta        {hms(eta_pool)} to pool exhausted"
                                       f"{note}",
                                  fg=WARN if note else DIM)

        size = RESULTS.stat().st_size if RESULTS.exists() else 0
        if size != self._last_size:
            self._last_size, self._last_change = size, time.time()
        quiet = time.time() - self._last_change
        if quiet < 240:
            self.l_alive.config(text=f"* running   (last result {int(quiet)}s ago)", fg=OK)
        else:
            self.l_alive.config(
                text=f"! no new result for {hms(quiet)} - finished, stopped, or stalled",
                fg=WARN)

        reasons = {}
        for r in rows:
            w = r.get("why", "?")
            key = ("admitted" if r.get("admitted") else
                   "floor (0/n)" if "floor" in w else
                   "ceiling (n/n)" if "ceiling" in w else
                   "outside band" if "outside band" in w else
                   "no samples" if "no samples" in w else w)
            reasons[key] = reasons.get(key, 0) + 1
        self.l_reasons.config(text="\n".join(
            f"  {k:<18} {v:>4}   {v / max(n,1):>5.1%}"
            for k, v in sorted(reasons.items(), key=lambda t: -t[1])) or "  (none yet)")

        self.txt.delete("1.0", "end")
        for r in rows[-9:]:
            mark = "ADMIT" if r.get("admitted") else "  -  "
            rate = f"{r['rate']:.2f}" if "rate" in r else "   "
            self.txt.insert("end", f"{mark} {r.get('tid','?')[:34]:<34} "
                                   f"{rate:>5}  {r.get('why','')[:34]}\n")
        self.txt.see("end")
        self.after(2000, self.refresh)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=int, default=400)
    ap.add_argument("--target", type=int, default=30)
    a = ap.parse_args()
    Monitor(a.candidates, a.target).mainloop()
