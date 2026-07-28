#!/usr/bin/env python3
"""repair.py — turn all-fail tasks into training signal (failure-derived pairs).

forge.py only builds pairs from tasks the model already solves, so all-fail tasks
emit ZERO gradient. This closes that gap
WITHOUT a stronger external model, using two purely-local moves on an all-fail task:

  1. best-of-N search    : sample far more candidates; the verifier keeps any pass.
  2. feedback self-repair : show the model its OWN failure -- SANITIZED, never the
     expected values, only the exception class or "wrong on a hidden test" -- and
     let it iterate. A repaired pass becomes `chosen`; the original failure is
     `rejected`. This trains the no-feedback base model to one-shot what currently
     needs iteration.

Honesty guard: feedback carries NO test internals or
expected outputs, so nothing leaks into the pair. That keeps the reward grounded
and doubles as an anti-hardcode defense -- the model can't memorize an answer it
was never shown. `chosen` is always re-checked by forge.verify (the same ground
truth the trainer trusts); best-of-N and repair only *find* candidates, the
verifier still decides.

Output: data/repair_pairs.jsonl (source-tagged, provenance=failure_derived) and
data/repair_log.jsonl. Local Ollama only; reuses forge's Task/Actor/verify.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import forge

SEARCH_N    = 12    # best-of-N budget for an all-fail task
MAX_STEPS   = 3     # feedback-repair iterations
SEARCH_TEMP = 0.9
REPAIR_TEMP = 0.5
OUT_DIR     = forge.OUT_DIR


def sanitized_feedback(code: str, task: forge.Task) -> str:
    """Run `code` against the task's tests and return a SAFE failure description:
    the exception class, or a generic 'wrong output' -- never expected values or
    test source. This is the only failure signal shown to the model."""
    if not code or forge.BANNED.search(code):
        return "used a disallowed operation, or produced no code"
    harness = (
        f"{code}\n\n{task.tests}\n"
        "try:\n"
        f"    run_tests({task.entry})\n"
        "    print('__OK__')\n"
        "except AssertionError:\n"
        "    print('__FB__|returned incorrect output on a hidden test case')\n"
        "except Exception as e:\n"
        "    print('__FB__|raised ' + type(e).__name__ + ': ' + str(e)[:100])\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(harness)
        path = fh.name
    try:
        p = subprocess.run([sys.executable, "-I", path], capture_output=True,
                           text=True, timeout=forge.CAND_TIMEOUT)
        out = p.stdout
    except subprocess.TimeoutExpired:
        out = "__FB__|did not terminate (likely an infinite loop)"
    finally:
        Path(path).unlink(missing_ok=True)
    for line in out.splitlines():
        if line.startswith("__OK__"):
            return "OK"
        if line.startswith("__FB__|"):
            return line.split("|", 1)[1]
    return "failed to run"


def best_of_n(actor: forge.Actor, task: forge.Task, n: int = SEARCH_N) -> str | None:
    """Sample n candidates; return the first the verifier passes, else None.
    Pure search over the model's own outputs -- ground truth still decides."""
    for _ in range(n):
        try:
            code = forge.extract_code(
                actor.generate(task.prompt, forge.ACTOR_SYSTEM, SEARCH_TEMP))
        except Exception:  # noqa: BLE001
            continue
        if forge.verify(code, task).ok:
            return code
    return None


def feedback_repair(actor: forge.Actor, task: forge.Task, initial_bad: str,
                    max_steps: int = MAX_STEPS) -> tuple[str | None, int]:
    """Iterate: show the model its SANITIZED failure, let it correct. Returns
    (passing_code|None, steps_used). Feedback never contains expected values."""
    attempt = initial_bad
    for step in range(1, max_steps + 1):
        fb = sanitized_feedback(attempt, task)
        prompt = (
            "Your previous solution to this task is incorrect.\n\n"
            f"Task: {task.prompt}\n\n"
            f"Your solution:\n```python\n{attempt}\n```\n\n"
            f"Result: {fb}\n\n"
            "Provide a corrected, complete solution in one ```python block. "
            "Define exactly the requested function."
        )
        try:
            cand = forge.extract_code(
                actor.generate(prompt, forge.ACTOR_SYSTEM, REPAIR_TEMP))
        except Exception:  # noqa: BLE001
            continue
        if forge.verify(cand, task).ok:
            return cand, step
        attempt = cand
    return None, max_steps


def harvest_task(actor: forge.Actor, task: forge.Task,
                 known_hard: set[str]) -> tuple[dict, dict | None]:
    """Probe the task; if all-fail, escalate via best-of-N then feedback repair.
    Returns (log, pair|None). Tasks already in known_hard are skipped."""
    log = {"tid": task.tid, "ts": time.strftime("%H:%M:%S")}
    if task.tid in known_hard:
        log["status"] = "skipped_known_hard"
        return log, None

    # Base probe at forge's budget. A pass here means it isn't a failure now.
    fails: list[str] = []
    for i in range(forge.NUM_CANDIDATES):
        temp = 0.0 if i == 0 else forge.GEN_TEMP
        try:
            code = forge.extract_code(
                actor.generate(task.prompt, forge.ACTOR_SYSTEM, temp))
        except Exception:  # noqa: BLE001
            continue
        if forge.verify(code, task).ok:
            log["status"] = "already_solved"
            return log, None
        fails.append(code)
    if not fails:
        log["status"] = "no_output"
        return log, None
    rejected = fails[0]  # a verified failure (every base attempt failed)

    chosen = best_of_n(actor, task)
    source, steps = "best_of_n", 0
    if not chosen:
        chosen, steps = feedback_repair(actor, task, rejected)
        source = "feedback_repair"

    if not chosen:
        # Unsolvable even with help -> quarantine; this is the residual tail that
        # needs an EXTERNAL reference solution (out of local self-improvement scope).
        log["status"] = "still_frontier"
        known_hard.add(task.tid)
        return log, None

    # Invariant: chosen truly passes, rejected truly fails (ground-truth recheck).
    if not (forge.verify(chosen, task).ok and not forge.verify(rejected, task).ok):
        log["status"] = "invariant_failed"
        return log, None

    pair = {
        "prompt": task.prompt,
        "chosen": chosen,
        "rejected": rejected,
        "meta": {"tid": task.tid, "source": source, "repair_steps": steps,
                 "provenance": "failure_derived"},
    }
    log.update(status="solved", source=source, steps=steps)
    return log, pair


def main(tasks: list[forge.Task] | None = None) -> None:
    tasks = tasks or forge.SEED_TASKS
    OUT_DIR.mkdir(exist_ok=True)
    pair_path = OUT_DIR / "repair_pairs.jsonl"
    log_path = OUT_DIR / "repair_log.jsonl"
    hard_path = OUT_DIR / "known_hard.json"
    known_hard: set[str] = set(json.loads(hard_path.read_text())) if hard_path.exists() else set()

    actor = forge.Actor(forge.OLLAMA_URL, forge.MODEL_NAME)
    try:
        tags = actor.s.get(f"{forge.OLLAMA_URL}/api/tags", timeout=5).json()
        if forge.MODEL_NAME not in {m["name"] for m in tags.get("models", [])}:
            print(f"[!] Model '{forge.MODEL_NAME}' not pulled.")
            return
    except Exception as e:  # noqa: BLE001
        print(f"[!] Ollama not reachable ({e}).")
        return

    seen: set[str] = set()
    if pair_path.exists():
        for line in pair_path.open(encoding="utf-8"):
            try:
                p = json.loads(line)
                seen.add(hashlib.sha1(
                    (p["prompt"] + p["chosen"] + p["rejected"]).encode()).hexdigest())
            except (json.JSONDecodeError, KeyError):
                pass

    solved = 0
    with pair_path.open("a", encoding="utf-8") as pf, \
         log_path.open("a", encoding="utf-8") as lf:
        for task in tasks:
            log, pair = harvest_task(actor, task, known_hard)
            lf.write(json.dumps(log, ensure_ascii=False) + "\n")
            tag = log["status"]
            if pair:
                sig = hashlib.sha1(
                    (pair["prompt"] + pair["chosen"] + pair["rejected"]).encode()
                ).hexdigest()
                if sig in seen:
                    tag = "solved(dup)"
                else:
                    seen.add(sig)
                    pf.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    solved += 1
                    tag = f"solved via {log['source']} (steps={log['steps']})"
            print(f"[{task.tid:16}] {tag}")

    actor.release()
    hard_path.write_text(json.dumps(sorted(known_hard)))
    print(f"\nrepair done. new failure-derived pairs: {solved}")
    print(f"known-hard (need external reference): {sorted(known_hard) or 'none'}")
    print(f"pairs: {pair_path}\nlog:   {log_path}")


if __name__ == "__main__":
    main()
