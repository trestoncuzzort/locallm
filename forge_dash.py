#!/usr/bin/env python3
"""forge_dash.py — a live viewer for everything srlm-forge has gathered.

Serves an auto-refreshing dashboard on 127.0.0.1 (localhost only — this is a
shared workstation, so nothing is exposed to the lab). Open it from the box's
own browser; the launcher in ~/.local/share/applications does that for you.

Panels:
  GPUs      nvidia-smi, with GPU 0 flagged as yours and a gpuguard-style
            warning when others take GPU 0 or hold >= 3 cards.
  Runs      srlm-forge-runs/manifest.jsonl — per-seed status, duration, git head.
  Arms      data/ruler_noise.jsonl grouped by (model, task_set, verifier version),
            the same partition ruler_noise.py refuses to pool across.
  Evals     data/eval_history.jsonl and data/heldin_history.jsonl.
  Rounds    data/round_stats.jsonl — tasks/solved/pairs per round.
  Log       tail of the newest srlm-forge-runs/logs/*.log.

Like dashboard.py, this deliberately does NOT compute arm-vs-arm comparisons.
That needs the same-session-control discipline in poscontrol/*.py; this only
shows what is in the files.

Dependencies: stdlib only. No sudo, no pip, no tkinter.
Run: python3 forge_dash.py [--port 8777] [--no-browser]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import threading
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RUNS = Path.home() / "srlm-forge-runs"
LOGS = RUNS / "logs"

# Human labels for known arms, from poscontrol/final_summary.py's convention.
# Anything not listed just shows its raw model tag.
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

_cache: dict[str, tuple[float, int, list]] = {}


def read_jsonl(path: Path) -> list[dict]:
    """Parse a JSONL file, re-parsing only when it has changed on disk.

    Bad lines are skipped rather than fatal: an append interrupted mid-write
    leaves a partial last row, and the viewer must not die on it.
    """
    try:
        st = path.stat()
    except OSError:
        return []
    key = str(path)
    hit = _cache.get(key)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    rows = []
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    _cache[key] = (st.st_mtime, st.st_size, rows)
    return rows


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def verifier_tag(row: dict) -> str:
    """Short stable id for a row's verifier fileset, so arms don't pool across it."""
    v = row.get("verifier")
    if not isinstance(v, dict) or not v:
        return "none"
    blob = json.dumps(v, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:8]


_UUID_MAP = None


def _uuid_index_map() -> dict:
    """GPU uuid -> nvidia-smi index. Fixed for the life of the box, so cache it."""
    global _UUID_MAP
    if _UUID_MAP is None:
        _UUID_MAP = {}
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=10)
            for line in r.stdout.strip().splitlines():
                parts = [c.strip() for c in line.split(",")]
                if len(parts) == 2:
                    _UUID_MAP[parts[1]] = int(parts[0])
        except Exception:
            pass
    return _UUID_MAP


_UID_NAMES: dict = {}


def _owner(pid: int) -> str:
    """Username owning a pid, read from /proc rather than by spawning ps.

    This runs for every compute process on every 5s poll; on a shared box that
    was a handful of subprocesses a second for information already in /proc.
    """
    try:
        uid = Path(f"/proc/{pid}").stat().st_uid
    except OSError:
        return "?"
    if uid not in _UID_NAMES:
        try:
            import pwd
            _UID_NAMES[uid] = pwd.getpwuid(uid).pw_name
        except Exception:
            _UID_NAMES[uid] = str(uid)
    return _UID_NAMES[uid]


def _is_ollama(pid: int) -> bool:
    """Label a GPU process as ollama's runner rather than a research job.

    ollama spawns a runner named llama-server, so matching the process name alone
    misses it; check the executable's location instead. Kept after the commentary
    feature was removed because knowing which process holds a card is useful anyway.
    """
    try:
        exe = os.path.realpath(f"/proc/{pid}/exe")
    except OSError:
        return False
    return "/ollama/" in exe or os.path.basename(exe) in (
        "ollama", "llama-server", "ollama_llama_server")


def gpus() -> dict:
    fields = "index,name,memory.used,memory.total,utilization.gpu,temperature.gpu"
    out = {"cards": [], "procs": [], "error": None}
    try:
        r = subprocess.run(
            ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            out["error"] = (r.stderr or "nvidia-smi failed").strip()[:200]
            return out
        for line in r.stdout.strip().splitlines():
            p = [c.strip() for c in line.split(",")]
            if len(p) < 6:
                continue
            out["cards"].append({
                "index": int(p[0]), "name": p[1],
                "used": int(p[2]), "total": int(p[3]),
                "util": int(p[4]), "temp": int(p[5]),
            })
    except Exception as e:
        out["error"] = str(e)[:200]
        return out
    # Attribute each compute process to a card, the way nvtop does: which GPU,
    # which user, which binary. "5.7 GB on GPU 1" is only actionable once you can
    # see it is ollama's runner and not a colleague's training job.
    uuid2idx = _uuid_index_map()
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        me = os.getuid()
        for line in r.stdout.strip().splitlines():
            parts = [c.strip() for c in line.split(",")]
            if len(parts) < 3:
                continue
            pid = int(parts[1])
            try:
                mine = Path(f"/proc/{pid}").stat().st_uid == me
            except OSError:
                mine = False
            user = _owner(pid)
            out["procs"].append({
                "pid": pid, "mem": int(parts[2]), "mine": mine,
                "gpu": uuid2idx.get(parts[0]),
                "name": _proc_name(pid) or "?",
                "user": user or "?",
                "ollama": _is_ollama(pid),
            })
    except Exception:
        pass
    return out


# A short in-memory trace per card, so each GPU gets a live graph the way nvtop
# draws one. Sampled on each poll; never written to disk.
_HIST = {}
_HIST_MAX = 90


def push_history(cards):
    for c in cards:
        h = _HIST.setdefault(str(c["index"]), [])
        h.append([c["util"], round(c["used"] / max(c["total"], 1) * 100, 1)])
        if len(h) > _HIST_MAX:
            del h[: len(h) - _HIST_MAX]
    return _HIST


def arms() -> list[dict]:
    """Group replicates by the partition ruler_noise.py refuses to pool across."""
    groups: dict[tuple, dict] = {}
    for row in read_jsonl(DATA / "ruler_noise.jsonl"):
        agg = row.get("aggregate") or {}
        p1 = agg.get("pass@1")
        if p1 is None:
            continue
        key = (row.get("model", "?"), row.get("task_set", "?"), verifier_tag(row))
        g = groups.setdefault(key, {
            "model": key[0], "task_set": key[1], "verifier": key[2],
            "label": ARM_LABELS.get(key[0], key[0]),
            "p1": [], "p3": [], "p1_typing": [], "typing_fails": 0,
            "n_tasks": row.get("n_tasks"), "last_ts": row.get("ts", ""),
        })
        g["p1"].append(p1)
        if agg.get("pass@3") is not None:
            g["p3"].append(agg["pass@3"])
        alt = (row.get("aggregate_if_typing_imported") or {}).get("pass@1")
        if alt is not None:
            g["p1_typing"].append(alt)
        g["typing_fails"] += row.get("typing_nameerror_fails_total") or 0
        if (row.get("ts") or "") > g["last_ts"]:
            g["last_ts"] = row.get("ts", "")

    out = []
    for g in groups.values():
        n = len(g["p1"])
        out.append({
            "model": g["model"], "task_set": g["task_set"], "verifier": g["verifier"],
            "label": g["label"], "n": n, "n_tasks": g["n_tasks"], "last_ts": g["last_ts"],
            "family": family_of(g["model"]),
            "mean_p1": round(statistics.fmean(g["p1"]), 4),
            "sd_p1": round(statistics.stdev(g["p1"]), 4) if n > 1 else None,
            "mean_p3": round(statistics.fmean(g["p3"]), 4) if g["p3"] else None,
            "mean_p1_typing": round(statistics.fmean(g["p1_typing"]), 4) if g["p1_typing"] else None,
            "typing_fails": g["typing_fails"],
        })
    out.sort(key=lambda r: r["mean_p1"], reverse=True)
    return out


def evals() -> dict:
    def pack(path: Path, limit: int) -> list[dict]:
        rows = read_jsonl(path)
        out = []
        for r in rows[-limit:]:
            agg = r.get("aggregate") or {}
            cov = (r.get("coverage") or {}).get("pass@1") or {}
            out.append({
                "ts": r.get("ts", ""), "model": r.get("model", "?"),
                "task_set": r.get("task_set", "?"), "arm": r.get("arm"),
                "engine": r.get("engine"),
                "p1": agg.get("pass@1"), "p3": agg.get("pass@3"),
                "n_tasks": r.get("n_tasks"), "n_samples": r.get("n_samples"),
                "scored": cov.get("tasks_scored"), "total": cov.get("tasks_total"),
                "gen_errors": r.get("gen_errors_total"),
                "not_served": r.get("not_the_served_artifact"),
            })
        out.reverse()
        return out
    held = read_jsonl(DATA / "eval_history.jsonl")
    heldin = read_jsonl(DATA / "heldin_history.jsonl")
    return {
        "held_out": pack(DATA / "eval_history.jsonl", 25),
        "held_in": pack(DATA / "heldin_history.jsonl", 25),
        "n_held_out": len(held), "n_held_in": len(heldin),
    }


def rounds() -> dict:
    rows = read_jsonl(DATA / "round_stats.jsonl")
    recent = []
    for r in rows[-40:]:
        recent.append({
            "ts": r.get("ts", ""), "model": r.get("model", "?"),
            "source": r.get("task_source", "?"),
            "tasks": r.get("tasks", 0), "solved": r.get("solved", 0),
            "pairs": r.get("pairs", 0),
            "reasons": r.get("pairs_by_reason") or {},
        })
    recent.reverse()
    return {
        "n": len(rows),
        "tasks": sum(r.get("tasks") or 0 for r in rows),
        "solved": sum(r.get("solved") or 0 for r in rows),
        "pairs": sum(r.get("pairs") or 0 for r in rows),
        "spark": [r.get("pairs") or 0 for r in rows[-60:]],
        "recent": recent,
    }


def manifest() -> dict:
    rows = read_jsonl(RUNS / "manifest.jsonl")
    recent = [{
        "ts": r.get("ts", ""), "item": r.get("item", "?"), "status": r.get("status", "?"),
        "seconds": r.get("seconds"), "gpu": r.get("gpu"), "rc": r.get("rc"),
        "git_head": (r.get("git_head") or "")[:8], "dirty": r.get("tree_dirty"),
    } for r in rows[-30:]]
    recent.reverse()
    ok = sum(1 for r in rows if r.get("status") == "ok")
    bad = sum(1 for r in rows if r.get("status") not in ("ok", "done", None))
    return {"n": len(rows), "ok": ok, "bad": bad, "recent": recent}


def datasets() -> list[dict]:
    """Sizes and freshness of the gathered corpora, so a stale file is visible."""
    names = [
        "dpo_pairs.jsonl", "dpo_pairs_capped.jsonl", "failures.jsonl",
        "repair_pairs.jsonl", "screen_results.jsonl", "ruler_noise.jsonl",
        "round_stats.jsonl", "eval_history.jsonl", "heldin_history.jsonl",
        "sql_screen_history.jsonl",
    ]
    out = []
    for n in names:
        p = DATA / n
        try:
            st = p.stat()
        except OSError:
            out.append({"name": n, "missing": True})
            continue
        out.append({
            "name": n, "missing": False, "bytes": st.st_size,
            "rows": len(read_jsonl(p)),
            "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "age_s": int(time.time() - st.st_mtime),
        })
    return out


def gate() -> dict:
    """Surface the dataset gate + verification receipts without re-running them."""
    out = {}
    v = read_json(DATA / "dataset_verification.json")
    if isinstance(v, dict):
        out["verification"] = {k: v[k] for k in list(v)[:14]}
    b = read_json(DATA / "bank_concentration.json")
    if isinstance(b, dict):
        out["bank"] = b
    out["python_running"] = sys.version.split()[0]
    return out


def newest_log() -> dict:
    try:
        cands = sorted(LOGS.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        cands = []
    if not cands:
        return {"name": None, "text": "", "age_s": None}
    p = cands[0]
    try:
        data = p.read_bytes()[-16000:]
        text = data.decode("utf-8", errors="replace")
    except OSError:
        text = ""
    return {
        "name": p.name,
        "text": text,
        "age_s": int(time.time() - p.stat().st_mtime),
    }


def uptime() -> str:
    try:
        return subprocess.run(["uptime"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def state() -> dict:
    return {
        "host": os.uname().nodename,
        "now": datetime.now().isoformat(timespec="seconds"),
        "uptime": uptime(),
        "gpus": gpus(),
        "arms": arms(),
        "evals": evals(),
        "rounds": rounds(),
        "manifest": manifest(),
        "datasets": datasets(),
        "gate": gate(),
        "log": newest_log(),
    }


# ---------------------------------------------------------------------------
# Plain-language narration.
#
# These are computed in Python, deterministically, from the same rows the
# tables show. They are NOT model output: a reader must be able to trust the
# headline strip even with ollama stopped. The local model only ever writes
# into the commentary panel, which is labelled as commentary.
# ---------------------------------------------------------------------------

def _fmt_age(seconds) -> str:
    if seconds is None:
        return "unknown"
    s = int(seconds)
    if s < 90:
        return f"{s} seconds ago"
    if s < 5400:
        return f"{s // 60} minutes ago"
    if s < 172800:
        return f"{s // 3600} hours ago"
    return f"{s // 86400} days ago"


def _pts(x) -> str:
    return f"{x * 100:.1f}"


def headlines(st: dict) -> list[dict]:
    """The dashboard in sentences: what a reader should notice, ranked."""
    out: list[dict] = []

    # --- is anything happening right now? ---
    cards = st["gpus"]["cards"]
    g0 = next((c for c in cards if c["index"] == 0), None)
    foreign = [p for p in st["gpus"]["procs"] if not p["mine"]]
    mine = [p for p in st["gpus"]["procs"] if p["mine"]]
    if g0 and g0["used"] > 500 and mine:
        out.append({"kind": "ok", "title": "A job of yours is on GPU 0",
                    "text": f"GPU 0 is holding {g0['used']/1024:.1f} GB at {g0['util']}% "
                            f"utilisation, {g0['temp']}°C. That is your card."})
    elif g0 and g0["used"] > 500 and foreign:
        out.append({"kind": "bad", "title": "Someone else is on GPU 0",
                    "text": f"GPU 0 is holding {g0['used']/1024:.1f} GB but no process there "
                            f"belongs to you. Under the lab agreement that card is yours; "
                            f"gpuguard.sh would yield right now."})
    else:
        busy = sum(1 for c in cards if c["used"] > 500)
        out.append({"kind": "ok" if busy < 3 else "warn",
                    "title": "Nothing of yours is training",
                    "text": f"GPU 0 is idle and free to take. "
                            f"{busy} of {len(cards)} cards in the box are in use."})

    # --- freshness: the most common question is "did last night land?" ---
    fresh = [f for f in st["datasets"] if not f["missing"]]
    if fresh:
        newest = min(fresh, key=lambda f: f["age_s"])
        kind = "ok" if newest["age_s"] < 7200 else "warn" if newest["age_s"] < 172800 else "info"
        out.append({"kind": kind, "title": "Last time data was written",
                    "text": f"The most recently touched file is {newest['name']}, "
                            f"changed {_fmt_age(newest['age_s'])}. "
                            f"Nothing in data/ has changed since."})

    # --- runs: failures are the thing worth surfacing ---
    m = st["manifest"]
    if m["bad"]:
        failed = [r["item"] for r in m["recent"] if r["status"] not in ("ok", "done")]
        shown = ", ".join(failed[:6]) + ("…" if len(failed) > 6 else "")
        out.append({"kind": "bad", "title": f"{m['bad']} of {m['n']} run entries did not succeed",
                    "text": f"Non-ok entries include: {shown}. "
                            f"{m['ok']} entries completed cleanly."})
    elif m["n"]:
        out.append({"kind": "ok", "title": f"All {m['n']} run entries are clean",
                    "text": "No failures recorded in srlm-forge-runs/manifest.jsonl."})

    # --- arms: state the best one in words, and the honest caveat ---
    arms_ = st["arms"]
    if arms_:
        best = arms_[0]
        sd = f" give or take {_pts(best['sd_p1'])} points" if best["sd_p1"] else ""
        out.append({"kind": "info", "title": "Strongest arm on record",
                    "text": f"{best['label']} averages {_pts(best['mean_p1'])}% pass@1 "
                            f"— about {round(best['mean_p1'] * 100)} solved out of every 100 "
                            f"attempts{sd} — over {best['n']} replicates on {best['task_set']}. "
                            f"This is a within-group average only; it is not a comparison "
                            f"against any other arm."})
        # the typing artefact is a real, quantified confound worth spelling out
        infl = [a for a in arms_ if a["mean_p1_typing"] and a["mean_p1_typing"] > a["mean_p1"]]
        if infl:
            worst = max(infl, key=lambda a: a["mean_p1_typing"] - a["mean_p1"])
            gap = (worst["mean_p1_typing"] - worst["mean_p1"]) * 100
            out.append({"kind": "warn", "title": "A `typing` import artefact is suppressing scores",
                        "text": f"On {worst['label']}, {worst['typing_fails']} generations failed "
                                f"with a NameError that a `typing` import would have prevented. "
                                f"Scored as-is it reaches {_pts(worst['mean_p1'])}%; had those "
                                f"imports been present it would reach "
                                f"{_pts(worst['mean_p1_typing'])}% — a gap of {gap:.1f} points. "
                                f"{len(infl)} arms are affected."})

    # --- evals: the served-artifact flag is a correctness trap ---
    ev = st["evals"]
    not_served = [r for r in ev["held_in"] if r.get("not_served")]
    if not_served:
        out.append({"kind": "warn", "title": "Some held-in evals did not test the served artifact",
                    "text": f"{len(not_served)} of the last {len(ev['held_in'])} held-in rows carry "
                            f"not_the_served_artifact. Those numbers describe a different "
                            f"artifact than the one being served."})
    errs = [r for r in (ev["held_out"] + ev["held_in"]) if r.get("gen_errors")]
    if errs:
        tot = sum(r["gen_errors"] for r in errs)
        out.append({"kind": "warn", "title": "Generation errors during evaluation",
                    "text": f"{tot} generation errors across {len(errs)} eval rows. "
                            f"An errored generation is not a wrong answer — check whether "
                            f"coverage still reached every task."})

    # --- rounds: yield rate in plain terms ---
    rd = st["rounds"]
    if rd["n"] and rd["tasks"]:
        solve = rd["solved"] / rd["tasks"] * 100
        per = rd["pairs"] / rd["n"]
        out.append({"kind": "info", "title": "Mining yield across all rounds",
                    "text": f"{rd['n']} rounds attempted {rd['tasks']} tasks and solved "
                            f"{rd['solved']} ({solve:.0f}%), producing {rd['pairs']} preference "
                            f"pairs — about {per:.1f} pairs per round."})
    return out


# ---------------------------------------------------------------------------
# Documents. The project's real thinking lives in markdown - handoffs, open
# items, council reports, the manuscript - and none of it was visible here.
# pandoc renders it properly (tables, code, footnotes) instead of the half-broken
# output a hand-rolled regex converter would give.
# ---------------------------------------------------------------------------
DOC_ROOTS = [HERE, RUNS]


def doc_list():
    seen, out = set(), []
    for base, pat in [(HERE, "*.md"), (HERE / "docs", "**/*.md"),
                      (HERE / "council", "*.md"), (RUNS, "*.md")]:
        if not base.is_dir():
            continue
        for f in sorted(base.glob(pat)):
            if not f.is_file() or f in seen:
                continue
            seen.add(f)
            try:
                st = f.stat()
            except OSError:
                continue
            out.append({"path": str(f), "name": f.name,
                        "group": "root" if f.parent == HERE else f.parent.name,
                        "kb": round(st.st_size / 1024, 1),
                        "age_s": int(time.time() - st.st_mtime)})
    out.sort(key=lambda d: d["age_s"])
    return out[:150]


def render_doc(path: str) -> str:
    """pandoc markdown -> HTML fragment, confined to the project directories."""
    try:
        f = Path(path).resolve()
    except OSError:
        return "<p>bad path</p>"
    if f.suffix.lower() not in (".md", ".markdown", ".txt"):
        return "<p>only markdown and text files are viewable here</p>"
    if not any(str(f).startswith(str(r.resolve()) + os.sep) for r in DOC_ROOTS):
        return "<p>that file is outside the project directories</p>"
    if not f.is_file():
        return "<p>file not found</p>"
    try:
        r = subprocess.run(
            ["pandoc", str(f), "-f", "markdown+pipe_tables+backtick_code_blocks",
             "-t", "html", "--no-highlight"],
            capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else f"<p>pandoc failed: {r.stderr[:300]}</p>"
    except FileNotFoundError:
        return "<p>pandoc is not installed</p>"
    except Exception as e:
        return f"<p>could not render: {e}</p>"


# ---------------------------------------------------------------------------
# Disk. Adapters run ~177 MB each and accumulate; du is far too slow for a 5s
# poll, so a background thread refreshes and the page serves the last value.
# ---------------------------------------------------------------------------
_DISK = {"rows": [], "biggest": [], "free": None, "ts": 0}


def _du(path):
    try:
        r = subprocess.run(["du", "-sb", str(path)], capture_output=True, text=True, timeout=180)
        return int(r.stdout.split()[0]) if r.returncode == 0 else None
    except Exception:
        return None


def refresh_disk():
    rows = []
    for label, path in [("srlm-forge", HERE), ("srlm-forge-runs", RUNS),
                        ("adapters", RUNS / "adapters"), ("data", DATA)]:
        if path.is_dir():
            b = _du(path)
            if b is not None:
                rows.append({"label": label, "bytes": b})
    biggest = []
    ad = RUNS / "adapters"
    if ad.is_dir():
        for d in sorted(x for x in ad.iterdir() if x.is_dir()):
            b = _du(d)
            if b is not None:
                biggest.append({"label": d.name, "bytes": b})
        biggest.sort(key=lambda r: -r["bytes"])
    free = None
    try:
        st = os.statvfs(str(Path.home()))
        free = st.f_bavail * st.f_frsize
    except Exception:
        pass
    _DISK.update({"rows": rows, "biggest": biggest[:8], "free": free, "ts": time.time()})


def disk_worker():
    while True:
        try:
            refresh_disk()
        except Exception:
            pass
        time.sleep(300)



# ---------------------------------------------------------------------------
# What is happening RIGHT NOW. The logs already carry step progress; without
# this the dashboard can tell you a card is hot but not what is running on it.
# ---------------------------------------------------------------------------
_RUN_PATTERNS = ("train_native", "ruler_noise", "poscontrol", "measure",
                 "eval_heldin", "eval.py", "forge.py")


def running() -> list[dict]:
    """Active project processes, with progress parsed from the log they write."""
    out = []
    try:
        r = subprocess.run(["ps", "-eo", "pid,etimes,user:32,args"],
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return out
    me = os.environ.get("USER", "")
    for line in r.stdout.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, etimes, user, args = parts
        if user != me or "/python" not in args:
            continue
        if not any(k in args for k in _RUN_PATTERNS):
            continue
        # the interesting half of the command line, minus the interpreter path
        cmd = args.split(None, 1)[1] if " " in args else args
        model = ""
        m = re.search(r"--model\s+(\S+)", args)
        if m:
            model = m.group(1)
        out.append({"pid": int(pid), "elapsed": int(etimes),
                    "cmd": cmd[:160], "model": model,
                    "kind": next((k for k in _RUN_PATTERNS if k in args), "?")})
    out.sort(key=lambda d: -d["elapsed"])
    return out[:6]


_STEP_RE = re.compile(r"(\d+)/(\d+)\s*\[")
_LOSS_RE = re.compile(r"'loss':\s*([0-9.]+)")
_EPOCH_RE = re.compile(r"'epoch':\s*([0-9.]+)")


def log_progress() -> dict:
    """Step/loss/epoch scraped from the tail of the newest run log."""
    prog = {"file": None, "step": None, "total": None, "loss": None,
            "epoch": None, "age_s": None}
    try:
        cands = sorted(LOGS.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return prog
    if not cands:
        return prog
    f = cands[0]
    prog["file"] = f.name
    try:
        prog["age_s"] = int(time.time() - f.stat().st_mtime)
        tail = f.read_bytes()[-20000:].decode("utf-8", errors="replace")
    except OSError:
        return prog
    steps = _STEP_RE.findall(tail)
    if steps:
        prog["step"], prog["total"] = int(steps[-1][0]), int(steps[-1][1])
    losses = _LOSS_RE.findall(tail)
    if losses:
        prog["loss"] = float(losses[-1])
    eps = _EPOCH_RE.findall(tail)
    if eps:
        prog["epoch"] = float(eps[-1])
    return prog


def family_of(model: str) -> str:
    """Experiment family. 51 flat arm groups is a list; grouped it is a study."""
    m = re.match(r"^(f\d+|hc|concur|ctl)", model or "")
    if m:
        return m.group(1)
    if (model or "").startswith("llama3"):
        return "llama3"
    return "other"


def per_task_matrix(top: int = 8) -> dict:
    """Per-task pass rate for the strongest arms - which tasks carry the gain.

    The per_task payload is already on every replicate row; nothing here is new
    measurement, it is aggregation the page never surfaced.
    """
    from collections import defaultdict
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # model -> tid -> [correct, n]
    labels = {}
    for row in read_jsonl(DATA / "ruler_noise.jsonl"):
        model = row.get("model")
        pt = row.get("per_task")
        if not model or not isinstance(pt, list):
            continue
        labels[model] = ARM_LABELS.get(model, model)
        for t in pt:
            tid = t.get("tid")
            if not tid:
                continue
            cell = agg[model][tid]
            cell[0] += t.get("correct") or 0
            cell[1] += t.get("n") or 0
    scored = []
    for model, tids in agg.items():
        tot_c = sum(c for c, n in tids.values())
        tot_n = sum(n for c, n in tids.values())
        if tot_n:
            scored.append((tot_c / tot_n, model))
    scored.sort(reverse=True)
    keep = [m for _, m in scored[:top]]
    tids = sorted({t for m in keep for t in agg[m]})
    return {
        "tasks": tids,
        "rows": [{"model": m, "label": labels.get(m, m),
                  "cells": [round(agg[m][t][0] / agg[m][t][1], 3) if agg[m].get(t) and agg[m][t][1] else None
                            for t in tids]} for m in keep],
    }


def full_state() -> dict:
    st = state()
    st["headlines"] = headlines(st)
    st["history"] = push_history(st["gpus"]["cards"])
    st["docs"] = doc_list()
    st["disk"] = dict(_DISK)
    st["running"] = running()
    st["progress"] = log_progress()
    st["pertask"] = per_task_matrix()
    return st


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>srlm-forge</title>
<style>
  /* ---- palette: dataviz reference instance, validated for the dark surface ---- */
  :root{
    --page:#0d0d0d; --surface:#1a1a19; --surface-2:#232322;
    --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#898781;
    --grid:#2c2c2a; --axis:#383835;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
    --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --crit:#d03b3b;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Ubuntu,Cantarell,sans-serif;
    --r:10px;
  }
  *{box-sizing:border-box}
  html{-webkit-font-smoothing:antialiased}
  body{margin:0;background:var(--page);color:var(--ink);font:15px/1.55 var(--sans)}
  .wrap{max-width:1560px;margin:0 auto;padding:0 28px 72px}

  /* ---- header ---- */
  header{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;
    padding:14px 28px;background:rgba(13,13,13,.9);backdrop-filter:blur(10px);
    border-bottom:1px solid var(--grid);margin-bottom:26px}
  .brand{font-weight:650;font-size:15px;letter-spacing:-.01em}
  .brand .dot{display:inline-block;width:7px;height:7px;border-radius:50%;
    background:var(--good);margin-right:9px;vertical-align:1px}
  .brand .dot.off{background:var(--ink-3)}
  .meta{font:12px var(--mono);color:var(--ink-3)}
  .sp{flex:1}
  button{background:var(--surface-2);color:var(--ink-2);border:1px solid var(--grid);
    border-radius:7px;padding:6px 13px;font:13px var(--sans);cursor:pointer}
  button:hover{border-color:var(--ink-3);color:var(--ink)}
  button:focus-visible{outline:2px solid var(--s1);outline-offset:2px}

  /* ---- hero stat row ---- */
  .hero{display:grid;gap:1px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
    background:var(--grid);border:1px solid var(--grid);border-radius:var(--r);
    overflow:hidden;margin-bottom:22px}
  .tile{background:var(--surface);padding:18px 20px 16px}
  .tile .k{font:11px var(--mono);letter-spacing:.09em;text-transform:uppercase;
    color:var(--ink-3);margin-bottom:9px}
  .tile .v{font:600 30px/1.05 var(--sans);letter-spacing:-.025em;
    font-variant-numeric:tabular-nums}
  .tile .v small{font-size:15px;font-weight:500;color:var(--ink-2);letter-spacing:0}
  .tile .sub{font:12px var(--mono);color:var(--ink-3);margin-top:7px}
  .tile .v.good{color:var(--good)} .tile .v.warn{color:var(--warn)}
  .tile .v.crit{color:var(--crit)}

  /* ---- attention strip: only what needs action ---- */
  .attn{display:flex;flex-direction:column;gap:8px;margin-bottom:22px}
  .att{display:flex;gap:12px;align-items:flex-start;padding:12px 16px;border-radius:var(--r);
    background:var(--surface);border:1px solid var(--grid);border-left:3px solid var(--ink-3)}
  .att.crit{border-left-color:var(--crit)} .att.warn{border-left-color:var(--warn)}
  .att.good{border-left-color:var(--good)}
  .att .ic{font:13px var(--mono);width:16px;flex:none;text-align:center;padding-top:1px}
  .att.crit .ic{color:var(--crit)} .att.warn .ic{color:var(--warn)} .att.good .ic{color:var(--good)}
  .att .tx{font-size:13.5px;color:var(--ink-2)}
  .att .tx b{color:var(--ink);font-weight:600}

  /* ---- panels ---- */
  .grid{display:grid;gap:18px;grid-template-columns:repeat(12,1fr)}
  .col12{grid-column:span 12} .col8{grid-column:span 8} .col6{grid-column:span 6}
  .col4{grid-column:span 4}
  @media(max-width:1100px){.col8,.col6,.col4{grid-column:span 12}}
  .panel{background:var(--surface);border:1px solid var(--grid);border-radius:var(--r);
    overflow:hidden;display:flex;flex-direction:column}
  .panel > h2{margin:0;padding:15px 20px 0;font:600 14px var(--sans);letter-spacing:-.01em;
    display:flex;align-items:baseline;gap:10px}
  .panel > h2 .tag{margin-left:auto;font:11px var(--mono);color:var(--ink-3);font-weight:400}
  .lede{padding:6px 20px 0;font-size:12.5px;color:var(--ink-3);line-height:1.5}
  .body{padding:16px 20px 18px}
  .scroll{overflow:auto;max-height:340px}

  /* ---- bar chart ---- */
  .bars{display:flex;flex-direction:column;gap:6px}
  .bar{display:grid;grid-template-columns:170px 1fr 62px 44px;align-items:center;gap:12px}
  .bar .lb{font:12px var(--mono);color:var(--ink-2);white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis}
  .bar .tr{position:relative;height:16px}
  .bar .tr i{position:absolute;left:0;top:0;bottom:0;background:var(--s1);
    border-radius:0 4px 4px 0;transition:width .35s ease}
  .bar.top .tr i{background:var(--s3)}
  .bar .tr .wk{position:absolute;top:7px;height:2px;background:var(--ink-3);opacity:.85}
  .bar .tr .wk::before,.bar .tr .wk::after{content:"";position:absolute;top:-3px;
    width:1px;height:8px;background:var(--ink-3)}
  .bar .tr .wk::before{left:0} .bar .tr .wk::after{right:0}
  .bar .vl{font:13px var(--mono);text-align:right;font-variant-numeric:tabular-nums}
  .bar .n{font:11px var(--mono);color:var(--ink-3);text-align:right}
  .axis{display:flex;justify-content:space-between;margin-top:10px;padding-left:182px;
    padding-right:106px;font:10.5px var(--mono);color:var(--ink-3);
    border-top:1px solid var(--axis);padding-top:6px}

  /* ---- gpu strip ---- */
  .gpus{display:grid;gap:1px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
    background:var(--grid);border:1px solid var(--grid);border-radius:var(--r);overflow:hidden}
  .g{background:var(--surface);padding:14px 16px;position:relative}
  .g .top{display:flex;align-items:baseline;gap:8px;margin-bottom:3px}
  .g .id{font:600 13px var(--mono)}
  .g .mine{font:10px var(--mono);color:var(--s1);border:1px solid var(--s1);
    border-radius:99px;padding:0 6px;opacity:.9}
  .g .sub{font:11px var(--mono);color:var(--ink-3)}
  .g .meter{height:4px;background:var(--surface-2);border-radius:99px;margin:10px 0 7px;overflow:hidden}
  .g .meter i{display:block;height:100%;background:var(--s1);border-radius:99px}
  .g.busy .meter i{background:var(--s4)} .g.foreign .meter i{background:var(--crit)}
  .g .row{display:flex;justify-content:space-between;font:11px var(--mono);color:var(--ink-2)}
  .g .procs{margin-top:9px;display:flex;flex-direction:column;gap:3px}
  .g .p{display:flex;gap:6px;font:10.5px var(--mono);color:var(--ink-3)}
  .g .p .nm{color:var(--ink-2)} .g .p .mm{margin-left:auto}
  .g .p.them .nm{color:var(--crit)}

  /* ---- tables ---- */
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{position:sticky;top:0;background:var(--surface);text-align:left;font:11px var(--mono);
    letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);font-weight:400;
    padding:9px 20px;border-bottom:1px solid var(--axis);white-space:nowrap}
  td{padding:9px 20px;border-bottom:1px solid var(--grid);color:var(--ink-2)}
  tr:last-child td{border-bottom:0}
  tbody tr:hover td{background:var(--surface-2)}
  .num{font:12.5px var(--mono);text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
  .mono{font:11.5px var(--mono);color:var(--ink-3)}
  .pill{font:10.5px var(--mono);padding:2px 8px;border-radius:99px;white-space:nowrap}
  .pill.ok{color:var(--good);background:rgba(12,163,12,.13)}
  .pill.bad{color:var(--crit);background:rgba(208,59,59,.15)}
  .pill.warn{color:var(--warn);background:rgba(250,178,25,.13)}

  /* ---- misc ---- */
  .empty{padding:26px 20px;text-align:center;color:var(--ink-3);font-size:13px}
  pre.log{margin:0;padding:14px 20px;font:11.5px/1.6 var(--mono);color:var(--ink-2);
    max-height:320px;overflow:auto;white-space:pre-wrap;word-break:break-word}
  select{background:var(--surface-2);color:var(--ink-2);border:1px solid var(--grid);
    border-radius:7px;padding:6px 9px;font:12px var(--mono);max-width:420px}
  .doc{padding:4px 22px 20px;max-height:560px;overflow:auto;font-size:14px;line-height:1.68}
  .doc h1,.doc h2,.doc h3{line-height:1.3;margin:1.4em 0 .5em;color:var(--ink)}
  .doc h1{font-size:20px;border-bottom:1px solid var(--grid);padding-bottom:.3em}
  .doc h2{font-size:16.5px} .doc h3{font-size:14.5px;color:var(--ink-2)}
  .doc p,.doc li{color:var(--ink-2)}
  .doc code{font:12px var(--mono);background:var(--surface-2);padding:1px 5px;border-radius:4px}
  .doc pre{background:var(--surface-2);border:1px solid var(--grid);border-radius:8px;
    padding:12px 14px;overflow-x:auto}
  .doc table{margin:.8em 0;font-size:12.5px} .doc th,.doc td{padding:6px 10px}
  .doc blockquote{margin:.8em 0;padding:.1em 1em;border-left:2px solid var(--axis);color:var(--ink-3)}
  .bars.disk .bar{grid-template-columns:150px 1fr 80px}
  svg .gl{stroke:var(--grid);stroke-width:1}
  svg text{fill:var(--ink-3);font:10px var(--mono)}
</style>
</head><body>
<header>
  <span class="brand"><span class="dot" id="dot"></span>srlm-forge</span>
  <span class="meta" id="host">connecting…</span>
  <span class="sp"></span>
  <span class="meta" id="stamp"></span>
  <button id="pause">Pause</button>
  <button onclick="pull(true)">Refresh</button>
</header>

<div class="wrap">

  <div class="hero" id="hero"></div>
  <div class="attn" id="attn"></div>

  <div class="grid">

    <section class="panel col8">
      <h2>Arms <span class="tag" id="armtag"></span></h2>
      <p class="lede">Mean pass@1 per arm, averaged over replicates. Whiskers span one standard
        deviation. Grouped by (model, task_set, verifier) — the partition
        <code>ruler_noise.py</code> refuses to pool across, so these are within-group means and
        not a comparison between arms.</p>
      <div class="body" id="armchart"></div>
    </section>

    <section class="panel col4">
      <h2>GPUs <span class="tag" id="gputag"></span></h2>
      <div class="body" style="padding:16px 16px 18px"><div class="gpus" id="gpus"></div></div>
    </section>

    <section class="panel col6">
      <h2>Evaluations over time <span class="tag" id="evtag"></span></h2>
      <p class="lede">pass@1 per evaluation, oldest to newest. Held-in shares tasks with training
        and reads higher; the gap between the lines is the quantity of interest.</p>
      <div class="body" id="evchart"></div>
    </section>

    <section class="panel col6">
      <h2>Mining rounds <span class="tag" id="rdtag"></span></h2>
      <p class="lede">Preference pairs produced per round. A round that solves everything mines
        nothing — pairs come from disagreement.</p>
      <div class="body" id="rdchart"></div>
    </section>

    <section class="panel col6">
      <h2>Runs <span class="tag" id="runtag"></span></h2>
      <div class="scroll"><table id="runs"></table></div>
    </section>

    <section class="panel col6">
      <h2>Data files <span class="tag" id="dstag"></span></h2>
      <div class="scroll"><table id="datasets"></table></div>
    </section>

    <section class="panel col4">
      <h2>Disk <span class="tag" id="disktag"></span></h2>
      <div class="body"><div class="bars disk" id="diskbars"></div></div>
    </section>

    <section class="panel col8">
      <h2>Documents <span class="tag" id="doctag"></span></h2>
      <div class="body" style="display:flex;gap:10px;align-items:center;padding-bottom:0">
        <select id="doclist"></select>
        <button id="docopen">Open</button>
        <span class="mono" id="docmeta"></span>
      </div>
      <div class="doc" id="docview"><div class="empty">Pick a document and press Open.
        Rendered with pandoc.</div></div>
    </section>

    <section class="panel col12">
      <h2>Newest log <span class="tag" id="logtag"></span></h2>
      <pre class="log" id="log"></pre>
    </section>

  </div>
</div>

<script>
const $ = id => document.getElementById(id);
let paused = false;

$("pause").onclick = () => {
  paused = !paused;
  $("pause").textContent = paused ? "Resume" : "Pause";
  $("dot").classList.toggle("off", paused);
  if (!paused) pull(true);
};

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pct = v => v == null ? "—" : (v * 100).toFixed(1) + "%";
const bytes = b => b == null ? "—" : b > 1073741824 ? (b/1073741824).toFixed(1)+" GB"
                 : b > 1048576 ? (b/1048576).toFixed(0)+" MB"
                 : b > 1024 ? (b/1024).toFixed(0)+" KB" : b+" B";
const ago = s => s == null ? "—" : s < 60 ? s+"s" : s < 3600 ? Math.round(s/60)+"m"
              : s < 86400 ? Math.round(s/3600)+"h" : Math.round(s/86400)+"d";
const dur = s => s == null ? "—" : s < 60 ? Math.round(s)+"s"
             : Math.floor(s/60)+"m"+String(Math.round(s%60)).padStart(2,"0");
const ts = t => esc(String(t||"").replace("T"," ").replace("Z","").slice(5,16));

function table(el, cols, rows, cell, emptyMsg){
  if(!rows.length){ el.innerHTML = '<tr><td><div class="empty">'+esc(emptyMsg||"nothing yet")+'</div></td></tr>'; return; }
  el.innerHTML = "<thead><tr>"+cols.map(c=>"<th>"+esc(c)+"</th>").join("")+"</tr></thead>"
               + "<tbody>"+rows.map(r=>"<tr>"+cell(r)+"</tr>").join("")+"</tbody>";
}

/* ---------- line chart: 2px strokes, recessive grid, hover crosshair ---------- */
function lineChart(el, series, fmt, unit){
  const all = series.flatMap(s=>s.pts);
  if(all.length < 2){ el.innerHTML = '<div class="empty">not enough points to plot</div>'; return; }
  const W=560, H=190, L=44, B=26, R=10, T=12;
  const lo=Math.min(...all.map(p=>p.y)), hi=Math.max(...all.map(p=>p.y));
  const span=(hi-lo)||1, y0=lo-span*.15, y1=hi+span*.15;
  const X=(i,n)=> L + (n<2?0:i/(n-1))*(W-L-R);
  const Y=v=> H-B - (v-y0)/(y1-y0)*(H-B-T);
  let s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="200" role="img">';
  for(let g=0; g<=3; g++){
    const v=y0+(y1-y0)*g/3, y=Y(v);
    s+='<line class="gl" x1="'+L+'" x2="'+(W-R)+'" y1="'+y.toFixed(1)+'" y2="'+y.toFixed(1)+'"/>';
    s+='<text x="'+(L-8)+'" y="'+(y+3.5).toFixed(1)+'" text-anchor="end">'+fmt(v)+'</text>';
  }
  s+='<line stroke="#383835" x1="'+L+'" x2="'+(W-R)+'" y1="'+(H-B)+'" y2="'+(H-B)+'"/>';
  series.forEach(se=>{
    if(se.pts.length<2) return;
    const d=se.pts.map((p,i)=>(i?"L":"M")+X(i,se.pts.length).toFixed(1)+" "+Y(p.y).toFixed(1)).join(" ");
    s+='<path d="'+d+'" fill="none" stroke="'+se.c+'" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
    const last=se.pts[se.pts.length-1];
    s+='<circle cx="'+X(se.pts.length-1,se.pts.length).toFixed(1)+'" cy="'+Y(last.y).toFixed(1)
      +'" r="4" fill="'+se.c+'" stroke="#1a1a19" stroke-width="2"/>';
    se.pts.forEach((p,i)=>{ s+='<circle cx="'+X(i,se.pts.length).toFixed(1)+'" cy="'+Y(p.y).toFixed(1)
      +'" r="7" fill="transparent"><title>'+esc(p.label)+'</title></circle>'; });
  });
  s+='</svg>';
  const legend='<div style="display:flex;gap:18px;margin-top:8px;font:11.5px var(--mono);color:var(--ink-3)">'
    + series.filter(se=>se.pts.length).map(se=>'<span><span style="display:inline-block;width:9px;height:9px;'
    + 'border-radius:2px;background:'+se.c+';margin-right:6px"></span>'+esc(se.name)
    + ' <span style="color:var(--ink-2)">'+pct(se.pts[se.pts.length-1].y)+'</span></span>').join("")+'</div>';
  el.innerHTML = s + legend;
}

/* ---------- area sparkline for round yield ---------- */
function areaChart(el, vals, label){
  if(vals.length<2){ el.innerHTML='<div class="empty">not enough rounds</div>'; return; }
  const W=560,H=150,B=22,T=10,R=6,L=30;
  const hi=Math.max(...vals,1);
  const X=i=> L+(i/(vals.length-1))*(W-L-R);
  const Y=v=> H-B-(v/hi)*(H-B-T);
  const line=vals.map((v,i)=>(i?"L":"M")+X(i).toFixed(1)+" "+Y(v).toFixed(1)).join(" ");
  let s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="160" role="img">';
  for(let g=0;g<=2;g++){ const v=hi*g/2,y=Y(v);
    s+='<line class="gl" x1="'+L+'" x2="'+(W-R)+'" y1="'+y.toFixed(1)+'" y2="'+y.toFixed(1)+'"/>';
    s+='<text x="'+(L-8)+'" y="'+(y+3.5).toFixed(1)+'" text-anchor="end">'+Math.round(v)+'</text>'; }
  s+='<path d="'+line+' L'+X(vals.length-1).toFixed(1)+' '+(H-B)+' L'+L+' '+(H-B)+' Z" fill="#3987e5" opacity="0.16"/>';
  s+='<path d="'+line+'" fill="none" stroke="#3987e5" stroke-width="2" stroke-linejoin="round"/>';
  s+='<line stroke="#383835" x1="'+L+'" x2="'+(W-R)+'" y1="'+(H-B)+'" y2="'+(H-B)+'"/></svg>';
  el.innerHTML = s + '<div style="margin-top:6px;font:11.5px var(--mono);color:var(--ink-3)">'+esc(label)+'</div>';
}

/* ---------- render ---------- */
function render(d){
  $("host").textContent = d.host + " · " + (d.uptime||"").replace(/^\s*/,"");
  $("stamp").textContent = "updated " + d.now.slice(11);

  const arms = d.arms || [], best = arms[0];
  const m = d.manifest || {}, rd = d.rounds || {};
  const cards = (d.gpus && d.gpus.cards) || [], procs = (d.gpus && d.gpus.procs) || [];
  const mine = procs.filter(p => p.mine && !p.ollama);
  const g0 = cards.find(c => c.index === 0);
  const fresh = (d.datasets||[]).filter(f=>!f.missing);
  const newest = fresh.length ? Math.min(...fresh.map(f=>f.age_s)) : null;
  const okPct = m.n ? Math.round(m.ok/m.n*100) : 0;

  /* hero: the four questions actually worth answering at a glance */
  $("hero").innerHTML = [
    ['Strongest arm', best ? pct(best.mean_p1) : "—",
     best ? esc(best.label)+' · n='+best.n : "no replicates",
     ''],
    ['GPU 0', mine.length ? 'busy' : 'idle',
     g0 ? (g0.used/1024).toFixed(1)+' / '+(g0.total/1024).toFixed(0)+' GB · '+g0.util+'% · '+g0.temp+'°C' : '—',
     mine.length ? 'warn' : 'good'],
    ['Runs clean', m.n ? m.ok+'<small> / '+m.n+'</small>' : '—',
     m.bad ? m.bad+' did not succeed' : 'all clean',
     m.bad ? 'crit' : 'good'],
    ['Data last written', newest != null ? ago(newest) + '<small> ago</small>' : '—',
     fresh.length ? esc(fresh.reduce((a,b)=>a.age_s<b.age_s?a:b).name) : '—',
     newest != null && newest > 172800 ? 'warn' : ''],
  ].map(([k,v,sub,cls]) =>
    '<div class="tile"><div class="k">'+k+'</div><div class="v '+cls+'">'+v+'</div>'
    + '<div class="sub">'+sub+'</div></div>').join("");

  /* attention: only rows that need action, ranked */
  const att = (d.headlines||[]).filter(h => h.kind === 'bad' || h.kind === 'warn')
    .map(h => '<div class="att '+(h.kind==='bad'?'crit':'warn')+'">'
      + '<span class="ic">'+(h.kind==='bad'?'!':'▲')+'</span>'
      + '<span class="tx"><b>'+esc(h.title)+'</b> — '+esc(h.text)+'</span></div>').join("");
  $("attn").innerHTML = att || '<div class="att good"><span class="ic">✓</span>'
    + '<span class="tx">Nothing needs attention. '
    + (m.n ? m.ok+' of '+m.n+' runs clean' : 'no runs recorded') + '.</span></div>';

  /* arms */
  $("armtag").textContent = arms.length + " groups";
  const show = arms.slice(0, 12);
  const top = show.length ? Math.max(...show.map(a => a.mean_p1 + (a.sd_p1||0))) : 1;
  $("armchart").innerHTML = show.length
    ? '<div class="bars">' + show.map((a,i) => {
        const w = a.mean_p1/top*100;
        const lo = Math.max(0,(a.mean_p1-(a.sd_p1||0))/top*100);
        const hi = Math.min(100,(a.mean_p1+(a.sd_p1||0))/top*100);
        return '<div class="bar'+(i===0?' top':'')+'">'
          + '<span class="lb" title="'+esc(a.label)+'">'+esc(a.label)+'</span>'
          + '<span class="tr"><i style="width:'+w.toFixed(1)+'%"></i>'
          + (a.sd_p1 ? '<span class="wk" style="left:'+lo.toFixed(1)+'%;width:'+(hi-lo).toFixed(1)+'%"></span>' : '')
          + '</span>'
          + '<span class="vl">'+pct(a.mean_p1)+'</span>'
          + '<span class="n">n='+a.n+'</span></div>';
      }).join("") + '</div>'
      + '<div class="axis"><span>0%</span><span>'+pct(top/2)+'</span><span>'+pct(top)+'</span></div>'
    : '<div class="empty">no replicates in data/ruler_noise.jsonl</div>';

  /* gpus */
  $("gputag").textContent = cards.length + " cards";
  $("gpus").innerHTML = (d.gpus && d.gpus.error)
    ? '<div class="empty">nvidia-smi: '+esc(d.gpus.error)+'</div>'
    : cards.map(c => {
        const own = procs.filter(p => p.gpu === c.index);
        const foreign = own.some(p => !p.mine);
        const use = c.total ? c.used/c.total*100 : 0;
        return '<div class="g'+(foreign?' foreign':own.length?' busy':'')+'">'
          + '<div class="top"><span class="id">GPU '+c.index+'</span>'
          + (c.index===0?'<span class="mine">yours</span>':'')+'</div>'
          + '<div class="sub">'+esc(c.name.replace("NVIDIA ",""))+'</div>'
          + '<div class="meter"><i style="width:'+use.toFixed(1)+'%"></i></div>'
          + '<div class="row"><span>'+(c.used/1024).toFixed(1)+' / '+(c.total/1024).toFixed(0)+' GB</span>'
          + '<span>'+c.util+'% · '+c.temp+'°C</span></div>'
          + (own.length ? '<div class="procs">'+own.slice(0,3).map(p =>
              '<div class="p'+(p.mine?'':' them')+'"><span class="nm">'+esc(p.ollama?'ollama':p.name)+'</span>'
              + '<span>'+esc(p.user)+'</span><span class="mm">'+(p.mem/1024).toFixed(1)+'G</span></div>').join("")+'</div>' : '')
          + '</div>';
      }).join("");

  /* evals */
  const ev = d.evals || {held_out:[],held_in:[]};
  $("evtag").textContent = (ev.n_held_out||0)+" held-out · "+(ev.n_held_in||0)+" held-in";
  const mk = rows => (rows||[]).filter(r=>r.p1!=null).slice().reverse()
    .map(r=>({y:r.p1,label:r.ts+"  "+r.model+"  "+pct(r.p1)}));
  lineChart($("evchart"), [
    {name:"held-out", c:"#3987e5", pts: mk(ev.held_out)},
    {name:"held-in",  c:"#d95926", pts: mk(ev.held_in)},
  ], v => (v*100).toFixed(0)+"%");

  /* rounds */
  $("rdtag").textContent = (rd.n||0)+" rounds";
  areaChart($("rdchart"), rd.spark||[],
    (rd.tasks ? rd.solved+" of "+rd.tasks+" tasks solved ("+Math.round(rd.solved/rd.tasks*100)+"%), "
      +rd.pairs+" pairs total · " : "") + "last "+(rd.spark||[]).length+" rounds");

  /* runs */
  $("runtag").textContent = m.n ? okPct+"% clean" : "";
  table($("runs"), ["When","Item","Status","Time","GPU"], m.recent||[], r => {
    const good = r.status==="ok" || r.status==="done";
    return '<td class="mono">'+ts(r.ts)+'</td><td>'+esc(r.item)+'</td>'
      + '<td><span class="pill '+(good?"ok":"bad")+'">'+esc(r.status)+'</span></td>'
      + '<td class="num">'+dur(r.seconds)+'</td><td class="num">'+(r.gpu??"—")+'</td>';
  }, "no runs recorded");

  /* datasets */
  const stale = fresh.filter(f=>f.age_s>172800).length;
  $("dstag").textContent = stale ? stale+" stale" : fresh.length+" files";
  table($("datasets"), ["File","Rows","Size","Changed"], d.datasets||[], f =>
    f.missing
      ? '<td class="mono">'+esc(f.name)+'</td><td colspan="3"><span class="pill warn">missing</span></td>'
      : '<td class="mono">'+esc(f.name)+'</td><td class="num">'+f.rows+'</td>'
        + '<td class="num">'+bytes(f.bytes)+'</td><td class="num">'+ago(f.age_s)+'</td>',
    "no data/ directory");

  /* disk */
  const dk = d.disk||{};
  if((dk.rows||[]).length){
    const dtop = Math.max(...dk.rows.map(r=>r.bytes),1);
    $("disktag").textContent = dk.free!=null ? bytes(dk.free)+" free" : "";
    $("diskbars").innerHTML = dk.rows.concat((dk.biggest||[]).slice(0,5)).map((r,i)=>{
      const sub = i>=dk.rows.length;
      return '<div class="bar"><span class="lb">'+(sub?"&nbsp;&nbsp;":"")+esc(r.label)+'</span>'
        + '<span class="tr"><i style="width:'+(r.bytes/dtop*100).toFixed(1)+'%'
        + (sub?';background:var(--s4)':'')+'"></i></span>'
        + '<span class="vl">'+bytes(r.bytes)+'</span></div>';
    }).join("");
  } else $("diskbars").innerHTML = '<div class="empty">measuring…</div>';

  /* docs */
  const docs = d.docs||[], dsel = $("doclist");
  $("doctag").textContent = docs.length+" files";
  if(dsel.dataset.n !== String(docs.length)){
    dsel.innerHTML = docs.map(f=>'<option value="'+esc(f.path)+'">'
      + esc(f.group==="root"?f.name:f.group+"/"+f.name)+'  ·  '+f.kb+' KB</option>').join("");
    dsel.dataset.n = String(docs.length);
  }

  /* log */
  const lg = d.log||{}, pre = $("log");
  $("logtag").textContent = lg.name ? esc(lg.name)+" · "+ago(lg.age_s)+" ago" : "none";
  const stick = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 40;
  pre.textContent = lg.text || "no *.log files in srlm-forge-runs/logs";
  if(stick) pre.scrollTop = pre.scrollHeight;
}

$("docopen").onclick = async () => {
  const path = $("doclist").value; if(!path) return;
  const v = $("docview");
  v.innerHTML = '<div class="empty">rendering with pandoc…</div>';
  try{
    const r = await fetch("/api/doc?path="+encodeURIComponent(path));
    v.innerHTML = await r.text(); v.scrollTop = 0;
    $("docmeta").textContent = path.split("/").slice(-2).join("/");
  }catch(e){ v.innerHTML = '<div class="empty">could not render: '+esc(e.message)+'</div>'; }
};
$("doclist").ondblclick = () => $("docopen").click();

async function pull(force){
  if(paused && !force) return;
  try{
    const r = await fetch("/api/state", {cache:"no-store"});
    render(await r.json());
    $("dot").classList.toggle("off", paused);
  }catch(e){
    $("dot").classList.add("off");
    $("stamp").textContent = "server unreachable";
  }
}
if(window.__INIT__){ try{ render(window.__INIT__); }catch(e){ $("stamp").textContent = "first paint failed: "+e.message; } }
pull(true);
setInterval(pull, 5000);
</script>
</body></html>
'''



def _proc_name(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return ""






class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _chunk(self, text: str):
        data = text.encode("utf-8")
        self.wfile.write(b"%X\r\n" % len(data) + data + b"\r\n")
        self.wfile.flush()

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path in ("/", "/index.html"):
            # Inline the first state so the page paints with data immediately
            # instead of flashing an empty shell while the first fetch runs.
            page = PAGE
            try:
                st = full_state()
                boot = ("<script>window.__INIT__=" +
                        json.dumps(st).replace("</", "<\\/") + ";</script>")
                page = page.replace("<script>", boot + "<script>", 1)
            except Exception:
                pass
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            return

        if u.path == "/api/state":
            try:
                st = full_state()
                body = json.dumps(st).encode("utf-8")
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode("utf-8")
            self._send(200, body, "application/json")
            return

        if u.path == "/api/doc":
            html = render_doc((q.get("path") or [""])[0])
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return


        self._send(404, b"not found", "text/plain")

    def log_message(self, *a):
        pass  # keep the terminal clean

    def handle_error(self, *a):
        # A browser that navigates away mid-poll, or Stop during a stream, closes
        # the socket and raises BrokenPipe. That is normal, not an error worth a
        # traceback on the terminal.
        pass


def main():
    ap = argparse.ArgumentParser(description="Live viewer for srlm-forge data.")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--host", default="127.0.0.1",
                    help="default 127.0.0.1 — this is a shared box, do not bind 0.0.0.0")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    url = f"http://{args.host}:{args.port}/"
    try:
        srv = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as e:
        # Most likely a copy is already running (the launcher was clicked twice).
        # Surfacing the existing window beats an error dialog.
        print(f"cannot bind {args.host}:{args.port} — {e}", file=sys.stderr)
        print(f"a copy is probably already running; opening {url}", file=sys.stderr)
        if not args.no_browser:
            try:
                subprocess.Popen(["xdg-open", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        return 0

    threading.Thread(target=disk_worker, daemon=True).start()
    print(f"srlm-forge dashboard  ->  {url}")
    print("reading:", DATA, "and", RUNS)
    print("Ctrl-C to stop.")
    if not args.no_browser:
        try:
            subprocess.Popen(["xdg-open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
