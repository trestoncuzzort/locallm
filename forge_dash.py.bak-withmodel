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
                            f"belongs to you. Under the agreement with Ryan that card is yours; "
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
# Local model commentary (ollama on 127.0.0.1:11434, pinned to GPU 0).
# ---------------------------------------------------------------------------

OLLAMA = "http://127.0.0.1:11434"
FALLBACK_MODEL = "llama3:8b-instruct-q4_K_M"

SCOPES = {
    "findings": "what the data actually shows, in prose",
    "overview": "the overall state of the project",
    "arms": "the per-arm replicate results",
    "runs": "the training run history",
    "evals": "the held-out and held-in evaluations",
    "rounds": "the pair-mining rounds",
}


LAUNCHER = Path.home() / "ollama-gpu0.sh"
STATUS = "\x1f"  # delimits status messages inside the streamed body


def ollama_alive(timeout: float = 2.0) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/version", timeout=timeout):
            return True
    except Exception:
        return False


def models_on_disk() -> list[str]:
    """Model names without asking the server, so the picker works while it is off."""
    root = Path.home() / ".ollama" / "models" / "manifests"
    out = []
    if not root.is_dir():
        return out
    for tag in root.rglob("*"):
        if not tag.is_file():
            continue
        rel = tag.relative_to(root).parts
        if len(rel) < 2:
            continue
        name = "/".join(rel[1:-1]) if len(rel) > 2 else rel[-2]
        # drop the registry/namespace prefix for library models, matching ollama's own naming
        name = name.split("/")[-1] if name.startswith("library/") or len(rel) == 3 else name
        out.append(f"{name}:{rel[-1]}")
    return sorted(set(out))


def ollama_models() -> list[str]:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=6) as r:
            d = json.loads(r.read().decode())
        return [m["name"] for m in d.get("models", [])]
    except Exception:
        return models_on_disk()


def ollama_unload(model: str) -> None:
    """Ask the server to drop the model, releasing its VRAM without stopping it."""
    import urllib.request
    body = json.dumps({"model": model, "keep_alive": 0}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            pass
    except Exception:
        pass


def ollama_start(timeout: float = 60.0) -> bool:
    """Bring the server up via the pinned launcher. Returns True once it answers."""
    if ollama_alive():
        return True
    if not LAUNCHER.exists():
        return False
    try:
        subprocess.run([str(LAUNCHER)], capture_output=True, text=True, timeout=timeout)
    except Exception:
        pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ollama_alive():
            return True
        time.sleep(0.5)
    return False


def ollama_stop(model: str | None = None, timeout: float = 25.0) -> None:
    """Unload, then stop the server outright so the card is completely free."""
    if model:
        ollama_unload(model)
    for sig in ("-TERM", "-KILL"):
        if not ollama_alive(timeout=1.5):
            break
        subprocess.run(["pkill", sig, "-x", "ollama"], capture_output=True)
        subprocess.run(["pkill", sig, "-f", "ollama/llama-server"], capture_output=True)
        deadline = time.time() + (timeout if sig == "-TERM" else 5)
        while time.time() < deadline:
            if not ollama_alive(timeout=1.0):
                return
            time.sleep(0.5)


def digest(scope: str, st: dict) -> str:
    """A compact, factual rendering of the data for the model to read.

    Deliberately plain text and deliberately small — llama3:8b is the reader,
    and a bloated context makes it worse, not better.
    """
    if scope == "findings":
        scope = "overview"  # findings differs in how it is asked, not in what it reads
    L: list[str] = []
    A = L.append
    A(f"HOST: {st['host']}   TIME: {st['now']}")

    cards = st["gpus"]["cards"]
    if cards:
        A("GPUS: " + "; ".join(
            f"gpu{c['index']} {c['used']/1024:.1f}/{c['total']/1024:.0f}GB {c['util']}%"
            for c in cards))

    if scope in ("overview", "arms"):
        A("")
        A("ARMS (replicate pass@1, grouped by model/task_set/verifier; "
          "NOT comparable across groups):")
        for a in st["arms"][:14]:
            sd = f" sd={a['sd_p1']:.3f}" if a["sd_p1"] else ""
            ty = (f" (would be {a['mean_p1_typing']*100:.1f}% with typing imported, "
                  f"{a['typing_fails']} NameError fails)") if a["mean_p1_typing"] else ""
            A(f"  {a['label']} [{a['task_set']}] n={a['n']} replicates, "
              f"mean pass@1={a['mean_p1']*100:.1f}%{sd}{ty}")

    if scope in ("overview", "runs"):
        m = st["manifest"]
        A("")
        A(f"RUNS: {m['n']} manifest entries, {m['ok']} ok, {m['bad']} not ok.")
        for r in m["recent"][:12]:
            A(f"  {r['ts']} {r['item']} status={r['status']} "
              f"secs={r['seconds']} gpu={r['gpu']} rc={r['rc']} commit={r['git_head']}"
              + (" TREE-DIRTY" if r["dirty"] else ""))

    if scope in ("overview", "evals"):
        ev = st["evals"]
        A("")
        A(f"HELD-OUT EVALS ({ev['n_held_out']} rows, newest first):")
        for r in ev["held_out"][:8]:
            A(f"  {r['ts']} {r['model']} [{r['task_set']}] pass@1={r['p1']} pass@3={r['p3']} "
              f"coverage={r['scored']}/{r['total']} gen_errors={r['gen_errors']}")
        A(f"HELD-IN EVALS ({ev['n_held_in']} rows, newest first):")
        for r in ev["held_in"][:8]:
            flag = " NOT-THE-SERVED-ARTIFACT" if r.get("not_served") else ""
            A(f"  {r['ts']} {r['model']} [{r['task_set']}] pass@1={r['p1']} "
              f"engine={r['engine']}{flag}")

    if scope in ("overview", "rounds"):
        rd = st["rounds"]
        A("")
        A(f"ROUNDS: {rd['n']} rounds, {rd['tasks']} tasks attempted, {rd['solved']} solved, "
          f"{rd['pairs']} preference pairs mined.")
        for r in rd["recent"][:8]:
            A(f"  {r['ts']} source={r['source']} tasks={r['tasks']} solved={r['solved']} "
              f"pairs={r['pairs']} reasons={r['reasons']}")

    A("")
    A("DATA FILES:")
    for f in st["datasets"]:
        if f["missing"]:
            A(f"  {f['name']}: MISSING")
        else:
            A(f"  {f['name']}: {f['rows']} rows, changed {_fmt_age(f['age_s'])}")

    A("")
    A("FACTS ALREADY COMPUTED (do not contradict these):")
    for h in st["headlines"]:
        A(f"  - {h['title']}: {h['text']}")
    return "\n".join(L)


SYSTEM = (
    "You are reading a machine-learning research dashboard for a project called srlm-forge, "
    "which trains a small language model on self-generated preference pairs and measures it "
    "against a frozen task set.\n"
    "Your job is to turn the numbers into plain English for the researcher who owns this data.\n"
    "Rules you must follow:\n"
    "1. Only state things the data below actually shows. Never invent a number.\n"
    "2. Never claim one arm beats another. Arms are grouped by (model, task_set, verifier) "
    "precisely because they are not poolable, and a real comparison needs the same-session "
    "control procedure in poscontrol/. If asked to compare, say that instead.\n"
    "3. Prefer concrete sentences over hedging. 'About 62 of every 100 attempts succeed' beats "
    "'performance appears moderate'.\n"
    "4. Point out anything that looks like a measurement problem: missing coverage, generation "
    "errors, stale files, failed runs, dirty git trees, artifacts that were not the served one.\n"
    "5. Be brief. Use short paragraphs or bullets. No preamble, no restating the question, no "
    "closing summary."
)

PROMPTS = {
    "findings":
        "Tell me what I have found so far, in plain natural language, as if you were "
        "explaining it to a colleague who has not seen this data.\n\n"
        "Write flowing prose in short paragraphs. Do not produce a bulleted list of "
        "numbers, and do not walk through the data section by section — I can already "
        "read the tables. Instead tell me what the data means.\n\n"
        "Cover, in this order:\n"
        "1. What the results appear to show.\n"
        "2. How much of it I should believe, given the replicate spread, the coverage, "
        "and any measurement artefacts.\n"
        "3. What is unresolved or missing — the thing I should look at next.\n\n"
        "Where a number matters, say it in words a person would use ('about three in five "
        "attempts succeed'). Be candid: if the data does not support a conclusion, say so "
        "plainly rather than hedging it into something that sounds positive.",
    "overview": "Give the researcher a short readout of where this project currently stands, "
                "then list anything that needs their attention.",
    "arms": "Describe what the per-arm replicate results show, in plain English. Note the "
            "spread across replicates and any measurement artefacts affecting the scores.",
    "runs": "Describe the training run history. Focus on what failed and what that pattern "
            "suggests about where to look.",
    "evals": "Describe what the held-out and held-in evaluations show, and flag any row whose "
             "coverage, errors, or artifact provenance makes it untrustworthy.",
    "rounds": "Describe the pair-mining rounds: the yield, how it changed over time, and "
              "whether anything looks anomalous.",
}


def _status(msg: str) -> str:
    return f"{STATUS}{msg}{STATUS}"


def _generate(scope: str, model: str, st: dict):
    import urllib.request
    body = json.dumps({
        "model": model,
        "system": SYSTEM,
        "prompt": f"{PROMPTS[scope]}\n\nHere is the data:\n\n{digest(scope, st)}",
        "stream": True,
        # num_predict was 700, which truncated the findings readout mid-sentence.
        # The overview digest is ~2050 tokens and the system prompt ~250, so an 8192
        # context leaves ample room for a 1600-token answer.
        "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": 1600},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("response"):
                yield d["response"]
            if d.get("done"):
                break


def explain_chunks(scope: str, model: str, st: dict):
    """Yield commentary, bringing ollama up for the request and shutting it down after.

    The server is left off between clicks so the whole card is free for training.
    Crucially, if ollama was ALREADY running it is left completely alone: the eval
    harness talks to the same server on 11434, and tearing it down mid-measure would
    break a run. Only a server this request started is a server this request stops.
    """
    scope = scope if scope in SCOPES else "overview"
    we_started = False

    if not ollama_alive():
        yield _status("starting the local model on GPU 0")
        if not ollama_start():
            yield _status("")
            yield ("[could not start ollama. Run ~/ollama-gpu0.sh by hand to see why — "
                   "the dashboard will not guess.]")
            return
        we_started = True
        yield _status("loading weights")

    finished = False
    try:
        for piece in _generate(scope, model, st):
            yield piece
        finished = True
    finally:
        # runs on the Stop button and on client disconnect too, so the card is never
        # left holding weights because someone closed the tab
        if we_started:
            ollama_stop(model)

    if finished:
        yield _status("done — model offline, GPU 0 released" if we_started
                      else "done — left the running ollama alone")


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


def full_state() -> dict:
    st = state()
    st["headlines"] = headlines(st)
    st["models"] = ollama_models()
    st["ollama_alive"] = ollama_alive(timeout=1.0)
    st["history"] = push_history(st["gpus"]["cards"])
    st["docs"] = doc_list()
    st["disk"] = dict(_DISK)
    return st


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>srlm-forge</title>
<style>
  :root{
    --bg:#0e1116; --panel:#161b22; --panel2:#1c222b; --line:#2a323d;
    --fg:#e6edf3; --dim:#9198a1; --dimmer:#6e7681;
    --accent:#58a6ff; --ok:#3fb950; --warn:#d29922; --bad:#f85149; --mine:#a371f7;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
    font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Ubuntu,sans-serif}
  .bar{position:sticky;top:0;z-index:9;display:flex;align-items:center;gap:14px;
    padding:12px 20px;background:rgba(14,17,22,.93);backdrop-filter:blur(8px);
    border-bottom:1px solid var(--line)}
  .bar h1{margin:0;font-size:15px;font-weight:600;letter-spacing:.3px}
  .host{font:12px var(--mono);color:var(--dim)}
  .spacer{flex:1}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite}
  .dot.off{background:var(--dimmer);animation:none;box-shadow:none}
  @keyframes pulse{70%{box-shadow:0 0 0 7px rgba(63,185,80,0)}100%{box-shadow:0 0 0 0 rgba(63,185,80,0)}}
  button{background:var(--panel2);color:var(--fg);border:1px solid var(--line);
    border-radius:6px;padding:5px 11px;font-size:12px;cursor:pointer}
  button:hover:not(:disabled){border-color:var(--dim)}
  button:disabled{opacity:.45;cursor:default}
  button.go{background:rgba(88,166,255,.14);border-color:rgba(88,166,255,.45);color:#a9d1ff}
  button.findings{background:rgba(63,185,80,.16);border-color:rgba(63,185,80,.55);
    color:#56d364;font-weight:600;padding:7px 15px;font-size:12.5px}
  button.findings:hover:not(:disabled){background:rgba(63,185,80,.26);border-color:#3fb950}
  select{background:var(--panel2);color:var(--fg);border:1px solid var(--line);
    border-radius:6px;padding:5px 8px;font:12px var(--mono)}
  .wrap{padding:18px 20px 60px;max-width:1500px;margin:0 auto}
  .grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(430px,1fr))}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
  .card > h2{margin:0;padding:11px 15px;font-size:12px;font-weight:600;letter-spacing:.7px;
    text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--line);
    display:flex;align-items:center;gap:9px}
  .card > h2 .tag{margin-left:auto;font:11px var(--mono);color:var(--dimmer);
    text-transform:none;letter-spacing:0;font-weight:400}
  .card > h2 button{margin-left:8px;padding:3px 9px;font-size:11px}
  .pad{padding:13px 15px}
  .span2{grid-column:1/-1}
  /* headline strip — the readability layer */
  .heads{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));
    margin-bottom:16px}
  .head{background:var(--panel);border:1px solid var(--line);border-left-width:3px;
    border-radius:8px;padding:11px 14px}
  .head.ok{border-left-color:var(--ok)} .head.warn{border-left-color:var(--warn)}
  .head.bad{border-left-color:var(--bad)} .head.info{border-left-color:var(--accent)}
  .head .t{font-weight:600;font-size:13px;margin-bottom:3px}
  .head.ok .t{color:#56d364} .head.warn .t{color:#e3b341}
  .head.bad .t{color:#ff7b72} .head.info .t{color:#79c0ff}
  .head .d{font-size:13px;color:var(--dim)}
  /* explain */
  #explain{margin-bottom:16px}
  .exbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:11px 15px;
    border-bottom:1px solid var(--line)}
  .exbar .lab{font-size:12px;color:var(--dim);margin-right:2px}
  #excaveat{font-size:11.5px;color:var(--dimmer);padding:9px 15px;border-top:1px solid var(--line)}
  #exstatus{font:11.5px var(--mono);color:var(--accent)}
  #exstatus:not(:empty)::before{content:"⋯ "}
  #exout{margin:0;padding:14px 16px;font:13px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Ubuntu,sans-serif;
    white-space:pre-wrap;word-break:break-word;min-height:56px;max-height:460px;overflow:auto;color:#d5dde5}
  #exout .ph{color:var(--dimmer)}
  .cursor{display:inline-block;width:7px;height:14px;background:var(--accent);
    vertical-align:-2px;animation:blink 1s steps(1) infinite}
  @keyframes blink{50%{opacity:0}}
  /* gpus */
  .gpus{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-bottom:14px}
  .gpu{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
  .gpu.mine{border-color:var(--mine)}
  .gpu .top{display:flex;align-items:baseline;gap:8px}
  .gpu .id{font:600 13px var(--mono)}
  .gpu .badge{font-size:10px;padding:1px 6px;border-radius:99px;background:rgba(163,113,247,.15);
    color:var(--mine);border:1px solid rgba(163,113,247,.35)}
  .gpu .sub{font:11px var(--mono);color:var(--dimmer);margin-top:2px}
  .meter{height:5px;background:var(--panel2);border-radius:99px;overflow:hidden;margin-top:9px}
  .meter i{display:block;height:100%;background:var(--accent);border-radius:99px;transition:width .4s}
  .meter i.hot{background:var(--warn)} .meter i.max{background:var(--bad)}
  .gpu .row{display:flex;justify-content:space-between;font:11px var(--mono);color:var(--dim);margin-top:6px}
  /* tables */
  table{width:100%;border-collapse:collapse;font-size:12.5px}
  th{text-align:left;font-weight:500;color:var(--dimmer);font-size:11px;text-transform:uppercase;
    letter-spacing:.5px;padding:8px 15px;border-bottom:1px solid var(--line);white-space:nowrap}
  td{padding:7px 15px;border-bottom:1px solid rgba(42,50,61,.5)}
  tr:last-child td{border-bottom:0}
  tr:hover td{background:rgba(255,255,255,.022)}
  .num{font:12px var(--mono);text-align:right;white-space:nowrap}
  .mono{font:11.5px var(--mono);color:var(--dim)}
  .said{font-size:12.5px;color:var(--dim)}
  .pill{font:11px var(--mono);padding:1px 7px;border-radius:99px;border:1px solid}
  .pill.ok{color:var(--ok);border-color:rgba(63,185,80,.4);background:rgba(63,185,80,.1)}
  .pill.bad{color:var(--bad);border-color:rgba(248,81,73,.4);background:rgba(248,81,73,.1)}
  .pill.warn{color:var(--warn);border-color:rgba(210,153,34,.4);background:rgba(210,153,34,.1)}
  .pill.mute{color:var(--dimmer);border-color:var(--line)}
  .scroll{max-height:330px;overflow:auto}
  .stats{display:flex;gap:24px;flex-wrap:wrap}
  .stat .v{font:600 21px var(--mono)}
  .stat .k{font-size:11px;color:var(--dimmer);text-transform:uppercase;letter-spacing:.5px}
  pre.log{margin:0;padding:13px 15px;font:11.5px/1.55 var(--mono);color:#b9c4d0;
    max-height:340px;overflow:auto;white-space:pre-wrap;word-break:break-word}
  .empty{padding:26px 15px;text-align:center;color:var(--dimmer);font-size:13px}
  .note{font-size:11.5px;color:var(--dimmer);padding:9px 15px;border-top:1px solid var(--line)}
  /* GPU cards with a live trace behind the numbers */
  .gpu{position:relative;overflow:hidden}
  .gpu .trace{position:absolute;left:0;right:0;bottom:0;height:38px;opacity:.5;pointer-events:none}
  .gpu .body{position:relative;z-index:1}
  .gpu.busy{border-color:rgba(88,166,255,.5)}
  .gpu.foreign{border-color:rgba(248,81,73,.55)}
  .gpu .who{margin-top:8px;display:flex;flex-direction:column;gap:3px}
  .gpu .who .p{display:flex;gap:6px;align-items:baseline;font:10.5px var(--mono);
    padding:2px 6px;border-radius:4px;background:rgba(255,255,255,.045)}
  .gpu .who .p.me{background:rgba(163,113,247,.16)}
  .gpu .who .p.olla{background:rgba(88,166,255,.14)}
  .gpu .who .p.them{background:rgba(248,81,73,.15)}
  .gpu .who .p .nm{font-weight:600}
  .gpu .who .p .mem{margin-left:auto;color:var(--dim)}
  /* document reader */
  .docbar{display:flex;gap:8px;align-items:center;padding:10px 15px;border-bottom:1px solid var(--line);flex-wrap:wrap}
  #doclist{min-width:250px;max-width:420px}
  .doc{padding:6px 22px 22px;max-height:620px;overflow:auto;font-size:14px;line-height:1.68}
  .doc h1,.doc h2,.doc h3{line-height:1.3;margin:1.4em 0 .5em}
  .doc h1{font-size:21px;border-bottom:1px solid var(--line);padding-bottom:.3em}
  .doc h2{font-size:17px;color:#79c0ff} .doc h3{font-size:15px;color:var(--dim)}
  .doc p{margin:.7em 0} .doc ul,.doc ol{margin:.6em 0;padding-left:1.5em} .doc li{margin:.25em 0}
  .doc code{font:12px var(--mono);background:var(--panel2);padding:1px 5px;border-radius:4px}
  .doc pre{background:var(--panel2);border:1px solid var(--line);border-radius:8px;
    padding:11px 13px;overflow-x:auto} .doc pre code{background:none;padding:0}
  .doc table{margin:.8em 0;font-size:12.5px;border:1px solid var(--line);border-radius:6px}
  .doc th{background:var(--panel2)} .doc td,.doc th{padding:6px 11px}
  .doc blockquote{margin:.8em 0;padding:.1em 1em;border-left:3px solid var(--line);color:var(--dim)}
  .doc a{color:var(--accent)} .doc hr{border:0;border-top:1px solid var(--line);margin:1.4em 0}
  /* disk */
  .bars{display:flex;flex-direction:column;gap:7px}
  .brow{display:flex;align-items:center;gap:9px;font:11.5px var(--mono)}
  .brow .lb{width:120px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .brow .tr{position:relative;flex:1;height:13px;background:var(--panel2);border-radius:4px}
  .brow .tr i{display:block;height:100%;border-radius:4px;
    background:linear-gradient(90deg,#1f6feb,#58a6ff);transition:width .4s}
  .brow .tr .wk{position:absolute;top:5px;height:3px;border-radius:2px;
    background:rgba(230,237,243,.55)}
  .brow .lb{width:190px}
  .brow .vl{width:66px;text-align:right}
  svg .ax{stroke:var(--line);stroke-width:1}
  svg .gl{stroke:rgba(42,50,61,.55);stroke-width:1}
  svg text{fill:var(--dimmer);font:10px var(--mono)}
</style></head><body>
<div class="bar">
  <span class="dot" id="dot"></span>
  <h1>srlm-forge</h1>
  <span class="host" id="host">connecting…</span>
  <span class="spacer"></span>
  <span class="host" id="stamp"></span>
  <button id="pause">Pause</button>
  <button onclick="pull(true)">Refresh</button>
  <button class="findings" data-scope="findings">What did I find?</button>
</div>
<div class="wrap">
  <div class="heads" id="heads"></div>

  <div class="card" id="explain">
    <div class="exbar">
      <span class="lab">Local model</span><span id="exoff" class="pill ok">offline</span>
      <select id="exmodel"></select>
      <button class="go" data-scope="overview">Everything</button>
      <button data-scope="arms">Arms</button>
      <button data-scope="runs">Runs</button>
      <button data-scope="evals">Evals</button>
      <button data-scope="rounds">Rounds</button>
      <span id="exstatus"></span>
      <span id="exwarn"></span>
      <span class="spacer"></span>
      <button id="exstop" disabled>Stop</button>
    </div>
    <div id="exout"><span class="ph">Press <b>What did I find?</b> and the local model reads everything
      below and tells you what it shows, in plain language. Runs on this machine, on GPU 0,
      only when you ask it to.</span></div>
    <div id="excaveat">Commentary generated locally by ollama. It is a reading aid, not evidence —
      nothing here is written to <b>data/</b>, and no number above comes from the model.
      It runs on GPU 0, the same card as your training runs, so it asks before adding load —
      and it stays shut down between clicks, holding no VRAM. If ollama is already running
      when you click (an eval, say), it is used as-is and left running afterwards.</div>
  </div>

  <div class="gpus" id="gpus"></div>
  <div class="grid">
    <div class="card span2"><h2>Arms · replicate pass@1
      <span class="tag" id="armtag"></span>
      <button data-scope="arms">Explain</button></h2>
      <div class="pad said" id="armsaid"></div>
      <div class="pad" id="armchart" style="padding-top:0"></div>
      <div class="scroll"><table id="arms"></table></div>
      <div class="note">Grouped by (model, task_set, verifier fileset) — the partition
        <b>ruler_noise.py</b> refuses to pool across. No arm-vs-arm comparison is computed here;
        that needs the same-session-control discipline in <b>poscontrol/</b>.</div></div>

    <div class="card"><h2>Evaluations over time
      <span class="tag" id="evtag"></span>
      <button data-scope="evals">Explain</button></h2>
      <div class="pad said" id="evsaid"></div>
      <div class="pad" id="evchart" style="padding-top:0"></div>
      <div class="scroll"><table id="evtable"></table></div></div>

    <div class="card"><h2>Runs <span class="tag" id="runtag"></span>
      <button data-scope="runs">Explain</button></h2>
      <div class="pad said" id="runsaid"></div>
      <div class="scroll"><table id="runs"></table></div></div>

    <div class="card"><h2>Rounds <span class="tag" id="roundtag"></span>
      <button data-scope="rounds">Explain</button></h2>
      <div class="pad said" id="roundsaid"></div>
      <div class="pad" id="rdchart" style="padding-top:0"></div>
      <div class="scroll"><table id="rounds"></table></div></div>

    <div class="card"><h2>Data files</h2>
      <div class="pad said" id="dssaid"></div>
      <div class="scroll"><table id="datasets"></table></div></div>

    <div class="card span2"><h2>Documents
      <span class="tag" id="doctag"></span></h2>
      <div class="docbar">
        <select id="doclist"></select>
        <button id="docopen" class="go">Open</button>
        <span class="mono" id="docmeta"></span>
      </div>
      <div class="doc" id="docview"><div class="empty">Pick a document and press Open —
        rendered with pandoc, so tables, code blocks and footnotes come through properly.</div></div>
    </div>

    <div class="card"><h2>Disk <span class="tag" id="disktag"></span></h2>
      <div class="pad said" id="disksaid"></div>
      <div class="pad bars" id="diskbars" style="padding-top:0"></div></div>

    <div class="card span2"><h2>Newest log <span class="tag" id="logtag"></span></h2>
      <pre class="log" id="log"></pre></div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
let paused = false, last = null, ctrl = null;

$("pause").onclick = () => {
  paused = !paused;
  $("pause").textContent = paused ? "Resume" : "Pause";
  $("dot").classList.toggle("off", paused);
  if (!paused) pull(true);
};

const esc = s => String(s ?? "").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const pct = v => v == null ? "—" : (v * 100).toFixed(1) + "%";
const bytes = b => b == null ? "—" : b > 1048576 ? (b/1048576).toFixed(1)+" MB"
                  : b > 1024 ? (b/1024).toFixed(0)+" KB" : b+" B";
const ago = s => s == null ? "—" : s < 60 ? s+"s ago" : s < 3600 ? Math.floor(s/60)+"m ago"
              : s < 86400 ? Math.floor(s/3600)+"h ago" : Math.floor(s/86400)+"d ago";
const dur = s => s == null ? "—" : s < 60 ? s.toFixed(0)+"s"
             : Math.floor(s/60)+"m "+String(Math.round(s%60)).padStart(2,"0")+"s";
const shortTs = t => esc(String(t||"").replace("T"," ").replace("Z","").slice(5,16));

function table(el, cols, rows, cell, emptyMsg) {
  if (!rows.length) { el.innerHTML =
    '<tr><td><div class="empty">'+esc(emptyMsg||"no rows yet")+'</div></td></tr>'; return; }
  el.innerHTML = "<thead><tr>"+cols.map(c=>"<th>"+esc(c)+"</th>").join("")+
    "</tr></thead><tbody>"+rows.map(r=>"<tr>"+cell(r)+"</tr>").join("")+"</tbody>";
}

/* ---- charts: small, dependency-free SVG ---- */
function barChart(el, items) {
  if (!items.length) { el.innerHTML = ""; return; }
  const top = Math.max(...items.map(i => i.v + (i.sd || 0)), 0.0001);
  el.innerHTML = '<div class="bars">' + items.map(it => {
    const w   = it.v / top * 100;
    const lo  = Math.max(0, (it.v - (it.sd||0)) / top * 100);
    const hi  = Math.min(100, (it.v + (it.sd||0)) / top * 100);
    const whisk = it.sd
      ? '<span class="wk" style="left:'+lo.toFixed(1)+'%;width:'+(hi-lo).toFixed(1)+'%"></span>' : '';
    return '<div class="brow">'+
      '<span class="lb" title="'+esc(it.t)+'">'+esc(it.t)+'</span>'+
      '<span class="tr"><i style="width:'+w.toFixed(1)+'%;background:'+it.c+'"></i>'+whisk+'</span>'+
      '<span class="vl">'+(it.v*100).toFixed(1)+'%</span>'+
      '<span class="vl" style="width:52px;color:var(--dimmer)">n='+(it.n||"")+'</span>'+
      '</div>';
  }).join("") + '</div>';
}

function lineChart(el, series, fmt) {
  const all = series.flatMap(s => s.pts);
  if (all.length < 2) { el.innerHTML = '<div class="empty">not enough points to plot</div>'; return; }
  const W = 320, H = 120, L = 34, B = 16;
  const lo = Math.min(...all.map(p => p.y)), hi = Math.max(...all.map(p => p.y));
  const span = (hi - lo) || 1, y0 = lo - span*.12, y1 = hi + span*.12;
  const X = (i, n) => L + (n < 2 ? 0 : i/(n-1) * (W-L-6));
  const Y = v => H-B - (v-y0)/(y1-y0) * (H-B-8);
  let s = '<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="150">';
  for (let g = 0; g <= 3; g++) {
    const v = y0 + (y1-y0)*g/3, y = Y(v);
    s += '<line class="gl" x1="'+L+'" x2="'+(W-6)+'" y1="'+y.toFixed(1)+'" y2="'+y.toFixed(1)+'"/>';
    s += '<text x="2" y="'+(y+3).toFixed(1)+'">'+fmt(v)+'</text>';
  }
  series.forEach(se => {
    const d = se.pts.map((p,i) => (i?"L":"M")+X(i,se.pts.length).toFixed(1)+" "+Y(p.y).toFixed(1)).join(" ");
    s += '<path d="'+d+'" fill="none" stroke="'+se.c+'" stroke-width="1.6" stroke-linejoin="round"/>';
    se.pts.forEach((p,i) => { s += '<circle cx="'+X(i,se.pts.length).toFixed(1)+'" cy="'+Y(p.y).toFixed(1)+
      '" r="1.9" fill="'+se.c+'"><title>'+esc(p.label)+'</title></circle>'; });
  });
  s += '</svg><div class="mono" style="margin-top:4px">' + series.map(se =>
    '<span style="color:'+se.c+'">■</span> '+esc(se.name)).join("&nbsp;&nbsp;") + '</div>';
  el.innerHTML = s;
}

function sparkline(el, vals, label) {
  if (vals.length < 2) { el.innerHTML = ""; return; }
  const W = 320, H = 40, top = Math.max(...vals, 1);
  const d = vals.map((v,i) => (i?"L":"M")+(i/(vals.length-1)*W).toFixed(1)+" "+
    (H - v/top*(H-4)).toFixed(1)).join(" ");
  el.innerHTML = '<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="46" preserveAspectRatio="none">'+
    '<path d="'+d+'" fill="none" stroke="#58a6ff" stroke-width="1.4"/></svg>'+
    '<div class="mono">'+esc(label)+'</div>';
}

/* ---- render ---- */
function render(d) {
  last = d;
  $("host").textContent = d.host + " · " + (d.uptime || "");
  $("stamp").textContent = "updated " + d.now.slice(11);

  $("heads").innerHTML = d.headlines.map(h =>
    '<div class="head '+h.kind+'"><div class="t">'+esc(h.title)+'</div>'+
    '<div class="d">'+esc(h.text)+'</div></div>').join("");

  $("exoff").textContent = d.ollama_alive ? "running" : "offline";
  $("exoff").className = "pill " + (d.ollama_alive ? "warn" : "ok");
  $("exoff").title = d.ollama_alive
    ? "ollama is up and may be holding VRAM"
    : "ollama is not running — no VRAM held. It starts when you click, and stops after.";

  const ct = d.contention || {};
  $("exwarn").innerHTML = ct.risky
    ? '<span class="pill warn" title="'+esc(ct.detail)+'">GPU 0 busy — '+esc(ct.reason)+'</span>'
    : (ct.ollama_loaded && ct.ollama_loaded.length
        ? '<span class="pill mute">model already resident, no reload needed</span>' : '');

  const sel = $("exmodel");
  if (sel.dataset.filled !== String(d.models.length)) {
    sel.innerHTML = d.models.length
      ? d.models.map(m => '<option>'+esc(m)+'</option>').join("")
      : '<option value="">no local model found</option>';
    sel.dataset.filled = String(d.models.length);
  }

  const g = d.gpus, hist = d.history || {};
  $("gpus").innerHTML = g.error
    ? '<div class="head bad"><div class="t">nvidia-smi failed</div><div class="d">'+esc(g.error)+'</div></div>'
    : g.cards.map(c => {
        const use = c.total ? c.used/c.total*100 : 0;
        const cls = use > 85 ? "max" : use > 60 ? "hot" : "";
        const procs = (g.procs||[]).filter(pr => pr.gpu === c.index);
        const foreign = procs.some(pr => !pr.mine);
        const busy = procs.length > 0;
        // live utilisation trace behind the numbers, nvtop-style
        const h = hist[String(c.index)] || [];
        let trace = "";
        if (h.length > 1) {
          const W = 100, H = 38;
          const pts = h.map((v,i) => [(i/(h.length-1))*W, H - (v[0]/100)*H]);
          const line = pts.map((q,i) => (i?"L":"M")+q[0].toFixed(1)+" "+q[1].toFixed(1)).join(" ");
          const area = line + ` L${W} ${H} L0 ${H} Z`;
          trace = '<svg class="trace" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none">'+
            '<path d="'+area+'" fill="'+(foreign?"rgba(248,81,73,.30)":"rgba(88,166,255,.30)")+'"/>'+
            '<path d="'+line+'" fill="none" stroke="'+(foreign?"#f85149":"#58a6ff")+'" stroke-width="1"/></svg>';
        }
        const who = procs.length ? '<div class="who">' + procs.slice(0,4).map(pr => {
          const k = pr.ollama ? "olla" : pr.mine ? "me" : "them";
          const tag = pr.ollama ? "ollama" : esc(pr.name);
          return '<div class="p '+k+'"><span class="nm">'+tag+'</span>'+
                 '<span>'+esc(pr.user)+'·'+pr.pid+'</span>'+
                 '<span class="mem">'+(pr.mem/1024).toFixed(1)+'G</span></div>';
        }).join("") + '</div>' : '';
        return '<div class="gpu'+(c.index===0?' mine':'')+(foreign?' foreign':busy?' busy':'')+'">'+
          trace+'<div class="body">'+
          '<div class="top"><span class="id">GPU '+c.index+'</span>'+
          (c.index===0?'<span class="badge">yours</span>':'')+'</div>'+
          '<div class="sub">'+esc(c.name.replace("NVIDIA ",""))+'</div>'+
          '<div class="meter"><i class="'+cls+'" style="width:'+use.toFixed(1)+'%"></i></div>'+
          '<div class="row"><span>'+(c.used/1024).toFixed(1)+' / '+(c.total/1024).toFixed(0)+' GB</span>'+
          '<span>'+c.util+'% · '+c.temp+'°C</span></div>'+
          who+'</div></div>';
      }).join("");

  // ---- disk ----
  const dk = d.disk || {};
  if (dk.rows && dk.rows.length) {
    const top = Math.max(...dk.rows.map(r => r.bytes), 1);
    $("diskbars").innerHTML = dk.rows.concat(dk.biggest||[]).map((r,i) => {
      const isDir = i >= dk.rows.length;
      return '<div class="brow"><span class="lb">'+(isDir?"&nbsp;&nbsp;":"")+esc(r.label)+'</span>'+
        '<span class="tr"><i style="width:'+(r.bytes/top*100).toFixed(1)+'%"></i></span>'+
        '<span class="vl">'+bytes(r.bytes)+'</span></div>';
    }).join("");
    $("disktag").textContent = dk.free != null ? bytes(dk.free)+" free" : "";
    $("disksaid").textContent = "Adapter directories are the bulk of it — each full run leaves "
      + "one behind. Refreshed every 5 minutes in the background.";
  } else {
    $("diskbars").innerHTML = '<div class="empty">measuring…</div>';
  }

  // ---- documents ----
  const docs = d.docs || [], dsel = $("doclist");   // not `sel` — that is the model picker
  $("doctag").textContent = docs.length + " markdown files";
  if (dsel.dataset.n !== String(docs.length)) {
    dsel.innerHTML = docs.map(f =>
      '<option value="'+esc(f.path)+'">'+esc(f.group === "root" ? f.name : f.group+"/"+f.name)+
      '  ·  '+f.kb+' KB</option>').join("");
    dsel.dataset.n = String(docs.length);
  }

  // arms
  const arms = d.arms;
  $("armtag").textContent = arms.length + " groups";
  if (arms.length) {
    const b = arms[0];
    $("armsaid").textContent =
      'Each row is one arm, averaged over its replicates. The strongest on record is ' +
      b.label + ' at ' + pct(b.mean_p1) + ' — roughly ' + Math.round(b.mean_p1*100) +
      ' solved per 100 attempts across ' + b.n + ' replicates. Whiskers show one standard ' +
      'deviation across replicates, so a wide whisker means the run-to-run noise is large ' +
      'relative to the score itself.';
  }
  barChart($("armchart"), arms.slice(0,14).map(a => ({
    t: a.label, n: a.n, v: a.mean_p1, sd: a.sd_p1 || 0,
    c: a === arms[0] ? "linear-gradient(90deg,#7d4fd1,#a371f7)"
                     : "linear-gradient(90deg,#1f6feb,#58a6ff)"})));
  table($("arms"),
    ["Arm","Task set","Verifier","Replicates","mean pass@1","sd","pass@3","if typing imported"],
    arms, a =>
      '<td>'+esc(a.label)+(a.label!==a.model?'<div class="mono">'+esc(a.model)+'</div>':'')+'</td>'+
      '<td class="mono">'+esc(a.task_set)+'</td>'+
      '<td class="mono">'+esc(a.verifier)+'</td>'+
      '<td class="num">'+a.n+'</td>'+
      '<td class="num">'+pct(a.mean_p1)+'</td>'+
      '<td class="num">'+(a.sd_p1==null?"—":(a.sd_p1*100).toFixed(1)+" pts")+'</td>'+
      '<td class="num">'+pct(a.mean_p3)+'</td>'+
      '<td class="num">'+(a.mean_p1_typing==null?"—":pct(a.mean_p1_typing)+
        ' <span class="mono">('+a.typing_fails+' fails)</span>')+'</td>',
    "no replicates in data/ruler_noise.jsonl");

  // evals
  const ev = d.evals;
  $("evtag").textContent = ev.n_held_out+" held-out · "+ev.n_held_in+" held-in";
  const mk = rows => rows.filter(r => r.p1 != null).slice().reverse()
    .map(r => ({y: r.p1, label: r.ts+"  "+r.model+"  "+pct(r.p1)}));
  lineChart($("evchart"), [
    {name:"held-out", c:"#58a6ff", pts: mk(ev.held_out)},
    {name:"held-in",  c:"#a371f7", pts: mk(ev.held_in)},
  ], v => (v*100).toFixed(0)+"%");
  $("evsaid").textContent =
    'pass@1 for each evaluation, oldest to newest, left to right. Held-out is the honest ' +
    'measurement; held-in shares tasks with training and will read higher — the gap between ' +
    'the two lines is the thing to watch, not either line alone.';
  const evRows = ev.held_out.slice(0,14).map(r => ({...r, which:"held-out"}))
    .concat(ev.held_in.slice(0,14).map(r => ({...r, which:"held-in"})))
    .sort((a,b) => String(b.ts).localeCompare(String(a.ts))).slice(0,24);
  table($("evtable"), ["When","Which","Model","pass@1","Coverage"], evRows, r =>
    '<td class="mono">'+shortTs(r.ts)+'</td>'+
    '<td class="mono">'+esc(r.which)+'</td>'+
    '<td>'+esc(r.model)+(r.not_served?' <span class="pill warn">not served</span>':'')+'</td>'+
    '<td class="num">'+pct(r.p1)+'</td>'+
    '<td class="num">'+(r.scored==null?"—":r.scored+"/"+r.total)+
      (r.gen_errors?' <span class="pill bad">'+r.gen_errors+' err</span>':'')+'</td>',
    "no eval history yet");

  // runs
  const m = d.manifest;
  $("runtag").textContent = m.n+" entries";
  $("runsaid").textContent = m.n
    ? m.ok+' of '+m.n+' entries finished cleanly'+(m.bad?', '+m.bad+' did not':'')+
      '. "dirty" means the git tree had uncommitted changes when that run was recorded, so the ' +
      'commit alone does not reproduce it.'
    : '';
  table($("runs"), ["When","Item","Status","Time","GPU","Commit"], m.recent, r => {
    const good = r.status==="ok"||r.status==="done";
    return '<td class="mono">'+shortTs(r.ts)+'</td>'+
      '<td>'+esc(r.item)+'</td>'+
      '<td><span class="pill '+(good?"ok":"bad")+'">'+esc(r.status)+'</span></td>'+
      '<td class="num">'+dur(r.seconds)+'</td>'+
      '<td class="num">'+(r.gpu??"—")+'</td>'+
      '<td class="mono">'+esc(r.git_head)+(r.dirty?' <span class="pill warn">dirty</span>':'')+'</td>';
  }, "no runs in srlm-forge-runs/manifest.jsonl");

  // rounds
  const rd = d.rounds;
  $("roundtag").textContent = rd.n+" rounds";
  $("roundsaid").textContent = rd.tasks
    ? 'Across '+rd.n+' rounds, '+rd.tasks+' tasks were attempted and '+rd.solved+' solved ('+
      (rd.solved/rd.tasks*100).toFixed(0)+'%), yielding '+rd.pairs+' preference pairs — about '+
      (rd.pairs/rd.n).toFixed(1)+' per round. A round that solves everything mines nothing: ' +
      'pairs come from disagreement.'
    : '';
  sparkline($("rdchart"), rd.spark, "pairs mined per round, last "+rd.spark.length+" rounds");
  table($("rounds"), ["When","Source","Tasks","Solved","Pairs"], rd.recent, r =>
    '<td class="mono">'+shortTs(r.ts)+'</td>'+
    '<td class="mono">'+esc(r.source)+'</td>'+
    '<td class="num">'+r.tasks+'</td>'+
    '<td class="num">'+r.solved+'</td>'+
    '<td class="num">'+r.pairs+'</td>', "no rounds yet");

  // datasets
  const stale = d.datasets.filter(f => !f.missing && f.age_s > 172800).length;
  $("dssaid").textContent = stale
    ? stale+' of '+d.datasets.length+' files have not changed in over two days.'
    : 'All files present and recently written.';
  table($("datasets"), ["File","Rows","Size","Changed"], d.datasets, f =>
    f.missing
      ? '<td class="mono">'+esc(f.name)+'</td><td colspan="3"><span class="pill mute">missing</span></td>'
      : '<td class="mono">'+esc(f.name)+'</td>'+
        '<td class="num">'+f.rows+'</td>'+
        '<td class="num">'+bytes(f.bytes)+'</td>'+
        '<td class="num">'+ago(f.age_s)+'</td>', "no data/ directory");

  // log
  const lg = d.log, pre = $("log");
  $("logtag").textContent = lg.name ? lg.name+" · "+ago(lg.age_s) : "none";
  const stick = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 40;
  pre.textContent = lg.text || "no *.log files in srlm-forge-runs/logs";
  if (stick) pre.scrollTop = pre.scrollHeight;
}

/* ---- the button: stream commentary from the local model ---- */
const base = (scope, model, force) =>
  "/api/explain?scope="+encodeURIComponent(scope)+"&model="+encodeURIComponent(model)+
  (force ? "&force=1" : "");

async function explain(scope) {
  if (ctrl) ctrl.abort();
  const model = $("exmodel").value;
  const out = $("exout");
  if (!model) { out.textContent = "No local model is loaded. Start ollama and pull one."; return; }
  $("docopen").onclick = async () => {
  const path = $("doclist").value;
  if (!path) return;
  const view = $("docview");
  view.innerHTML = '<div class="empty">rendering with pandoc…</div>';
  $("docmeta").textContent = "";
  try {
    const r = await fetch("/api/doc?path="+encodeURIComponent(path));
    view.innerHTML = await r.text();
    view.scrollTop = 0;
    $("docmeta").textContent = path.replace(/^.*\/(?=[^/]*\/[^/]*$)/, "");
  } catch (e) {
    view.innerHTML = '<div class="empty">could not render: '+esc(e.message)+'</div>';
  }
};
$("doclist").ondblclick = () => $("docopen").click();

document.querySelectorAll("[data-scope]").forEach(b => b.disabled = true);
  $("exstop").disabled = false;
  out.textContent = "";
  $("exstatus").textContent = "";
  const cur = document.createElement("span");
  cur.className = "cursor"; out.appendChild(cur);
  ctrl = new AbortController();
  const t0 = performance.now();
  try {
    let r = await fetch(base(scope, model, false), {signal: ctrl.signal});
    if (r.status === 409) {
      const c = await r.json();
      cur.remove();
      if (!confirm(c.reason + "\n\n" + c.detail + "\n\nGenerate commentary anyway?")) {
        out.innerHTML = '<span class="ph">Skipped — GPU 0 left alone.</span>';
        return;
      }
      out.textContent = ""; out.appendChild(cur);
      r = await fetch(base(scope, model, true), {signal: ctrl.signal});
    }
    const rd = r.body.getReader(), dec = new TextDecoder();
    let inStatus = false;                       // toggled by the \x1f delimiter
    for (;;) {
      const {done, value} = await rd.read();
      if (done) break;
      const parts = dec.decode(value, {stream: true}).split("\x1f");
      for (let i = 0; i < parts.length; i++) {
        if (i > 0) inStatus = !inStatus;        // survives chunk boundaries
        if (!parts[i]) continue;
        if (inStatus) $("exstatus").textContent = parts[i];
        else cur.insertAdjacentText("beforebegin", parts[i]);
      }
      out.scrollTop = out.scrollHeight;
    }
    const secs = ((performance.now()-t0)/1000).toFixed(1);
    cur.remove();
    const f = document.createElement("div");
    f.className = "mono"; f.style.marginTop = "10px";
    f.textContent = "— "+model+", "+scope+", "+secs+"s";
    out.appendChild(f);
  } catch (e) {
    cur.remove();
    if (e.name !== "AbortError")
      out.appendChild(document.createTextNode("\n\n[failed: "+e.message+"]"));
  } finally {
    $("docopen").onclick = async () => {
  const path = $("doclist").value;
  if (!path) return;
  const view = $("docview");
  view.innerHTML = '<div class="empty">rendering with pandoc…</div>';
  $("docmeta").textContent = "";
  try {
    const r = await fetch("/api/doc?path="+encodeURIComponent(path));
    view.innerHTML = await r.text();
    view.scrollTop = 0;
    $("docmeta").textContent = path.replace(/^.*\/(?=[^/]*\/[^/]*$)/, "");
  } catch (e) {
    view.innerHTML = '<div class="empty">could not render: '+esc(e.message)+'</div>';
  }
};
$("doclist").ondblclick = () => $("docopen").click();

document.querySelectorAll("[data-scope]").forEach(b => b.disabled = false);
    $("exstop").disabled = true; ctrl = null;
  }
}
$("docopen").onclick = async () => {
  const path = $("doclist").value;
  if (!path) return;
  const view = $("docview");
  view.innerHTML = '<div class="empty">rendering with pandoc…</div>';
  $("docmeta").textContent = "";
  try {
    const r = await fetch("/api/doc?path="+encodeURIComponent(path));
    view.innerHTML = await r.text();
    view.scrollTop = 0;
    $("docmeta").textContent = path.replace(/^.*\/(?=[^/]*\/[^/]*$)/, "");
  } catch (e) {
    view.innerHTML = '<div class="empty">could not render: '+esc(e.message)+'</div>';
  }
};
$("doclist").ondblclick = () => $("docopen").click();

document.querySelectorAll("[data-scope]").forEach(b =>
  b.onclick = () => {
    // the button lives in the sticky top bar; the answer renders further down
    if (b.dataset.scope === "findings")
      $("explain").scrollIntoView({behavior: "smooth", block: "start"});
    explain(b.dataset.scope);
  });
$("exstop").onclick = () => { if (ctrl) ctrl.abort(); };

async function pull(force) {
  if (paused && !force) return;
  try {
    const r = await fetch("/api/state", {cache:"no-store"});
    render(await r.json());
    $("dot").classList.toggle("off", paused);
  } catch (e) {
    $("dot").classList.add("off");
    $("stamp").textContent = "server unreachable — is forge_dash.py still running?";
  }
}
if (window.__INIT__) {
  // Never swallow this silently: a first-paint failure is invisible otherwise,
  // and the page just sits on "connecting..." looking like a dead server.
  try { render(window.__INIT__); }
  catch (e) { $("stamp").textContent = "first paint failed: " + e.message; }
}
pull(true);
setInterval(pull, 5000);
</script></body></html>
'''


# ---------------------------------------------------------------------------
# Contention guard.
#
# ollama is pinned to CUDA_VISIBLE_DEVICES=0 — the same card the training and
# measure runs use, and the only card assigned to us. So commentary is NOT
# free: it shares VRAM and SMs with whatever research is running, and it queues
# on the same ollama server the eval harness talks to.
#
# gpuguard.sh skips our own PIDs, so this can never cause a self-inflicted
# yield. The risk is subtler: added latency on an in-flight eval, and any
# measurement that records wall-clock seconds becoming contaminated.
#
# Hence: detect, refuse by default, and let the operator override deliberately.
# ---------------------------------------------------------------------------

def _proc_name(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return ""


def _ppid(pid: int) -> int:
    """Parent pid from /proc/<pid>/stat, tolerating spaces in the comm field."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        return int(raw[raw.rindex(")") + 2:].split()[1])
    except (OSError, ValueError, IndexError):
        return 0


def _is_ollama(pid: int) -> bool:
    """Is this pid ollama's own inference, rather than a research job?

    ollama does not run the model in-process: it spawns a runner that is named
    llama-server, not ollama. Matching on the process name alone made the guard
    mistake ollama's own runner for a training job and block itself after the
    first click. So check the executable's location and walk the parent chain.
    """
    try:
        exe = os.path.realpath(f"/proc/{pid}/exe")
        if "/ollama/" in exe or os.path.basename(exe) in ("ollama", "llama-server",
                                                          "ollama_llama_server"):
            return True
    except OSError:
        pass
    seen, cur = 0, pid
    while cur > 1 and seen < 6:
        if _proc_name(cur).lower().startswith("ollama"):
            return True
        cur = _ppid(cur)
        seen += 1
    return False


def contention() -> dict:
    """Is it safe to spend GPU 0 on commentary right now?"""
    info = {"risky": False, "reason": "", "detail": "", "ollama_loaded": []}

    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=5) as r:
            info["ollama_loaded"] = [
                {"name": m.get("name"), "vram": m.get("size_vram", 0)}
                for m in json.loads(r.read().decode()).get("models", [])
            ]
    except Exception:
        pass

    g = gpus()
    cards = {c["index"]: c for c in g["cards"]}
    g0 = cards.get(0)

    # Our own non-ollama compute on GPU 0 is the thing worth refusing over:
    # that is a training or measure run in progress.
    ours = []
    for p in g["procs"]:
        if not p["mine"]:
            continue
        if _is_ollama(p["pid"]):
            continue  # our own commentary model, not research
        ours.append({"pid": p["pid"], "name": _proc_name(p["pid"]) or "?", "mem": p["mem"]})

    if ours:
        who = ", ".join(f"{p['name']} (pid {p['pid']}, {p['mem']/1024:.1f} GB)" for p in ours[:3])
        info.update({
            "risky": True,
            "reason": "A job of yours is using GPU 0 right now.",
            "detail": f"Running: {who}. Generating commentary would take VRAM and compute from "
                      f"it, and would queue behind or ahead of it on the same ollama server. "
                      f"If that job records wall-clock seconds, those numbers would be "
                      f"contaminated. Run it anyway only if you know the job can absorb it.",
        })
        return info

    if g0 and g0["util"] >= 40 and not info["ollama_loaded"]:
        info.update({
            "risky": True,
            "reason": f"GPU 0 is at {g0['util']}% utilisation.",
            "detail": "Something is working on your card, but no compute process is attributable "
                      "to you — it may be a job started from another shell. Check before adding "
                      "load.",
        })
    return info


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
                st["contention"] = contention()
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
                st["contention"] = contention()
                body = json.dumps(st).encode("utf-8")
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode("utf-8")
            self._send(200, body, "application/json")
            return

        if u.path == "/api/doc":
            html = render_doc((q.get("path") or [""])[0])
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return

        if u.path == "/api/explain":
            scope = (q.get("scope") or ["overview"])[0]
            model = (q.get("model") or [FALLBACK_MODEL])[0]
            force = (q.get("force") or ["0"])[0] == "1"

            if not force:
                c = contention()
                if c["risky"]:
                    self._send(409, json.dumps(c).encode(), "application/json")
                    return

            # Streamed as chunked so text appears as the model produces it.
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                st = full_state()
                for piece in explain_chunks(scope, model, st):
                    self._chunk(piece)
            except BrokenPipeError:
                return  # operator hit Stop
            except Exception as e:
                try:
                    self._chunk(f"\n\n[the local model failed: {e}]")
                except Exception:
                    return
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except Exception:
                pass
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
    print("commentary model:", ", ".join(ollama_models()) or "none (ollama not responding)")
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
