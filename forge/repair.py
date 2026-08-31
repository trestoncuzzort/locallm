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
        # THE CLASS NAME ONLY, NEVER str(e). The exception was raised while the
        # HIDDEN tests were driving the candidate, so its message can carry the
        # test's own inputs verbatim: `raise ValueError(x)` on a hidden call
        # solve("SECRET42") printed `raised ValueError: SECRET42` straight back
        # into the repair prompt. That is test internals reaching the model,
        # which is the one thing this function exists to prevent -- and it is
        # also the anti-hardcode defense, because a model shown the hidden
        # inputs can special-case them instead of solving the task.
        "except Exception as e:\n"
        "    print('__FB__|raised ' + type(e).__name__)\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(harness)
        path = fh.name
    try:
        # forge.VERIFY_PY, not sys.executable: the failure DESCRIBED to the model
        # must come from the same interpreter that decides `ok`. Launching the
        # feedback harness under whatever ran repair.py reintroduces the
        # section-71 split (forge.py:87-123) inside one function -- verify()
        # judged the candidate under the pin while this told the model what went
        # wrong under the launcher, and PEP 649 annotation behaviour alone makes
        # those two disagree. Read through forge at call time so the pin has one
        # definition, not a copy per module.
        p = subprocess.run([forge.VERIFY_PY, "-I", path], capture_output=True,
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
    # The RESULT is kept, not just the code: the verdict carries `timed_out`,
    # and dropping it here is what let a timeout be treated as a wrong answer.
    fails: list[forge.Result] = []
    for i in range(forge.NUM_CANDIDATES):
        temp = 0.0 if i == 0 else forge.GEN_TEMP
        try:
            code = forge.extract_code(
                actor.generate(task.prompt, forge.ACTOR_SYSTEM, temp))
        except Exception:  # noqa: BLE001
            continue
        res = forge.verify(code, task)
        if res.ok:
            log["status"] = "already_solved"
            return log, None
        fails.append(res)
    if not fails:
        log["status"] = "no_output"
        return log, None

    # A TIMEOUT IS NOT A WRONG ANSWER. Same rule as forge.run_task (forge.py:654):
    # `rejected` must be demonstrably WRONG, not merely slow or unmeasured. A
    # candidate that ran out of budget has an UNKNOWN verdict -- it may well be
    # correct and slow -- so training the model to prefer anything over it
    # teaches speed under the guise of correctness. This used to keep fails[0]
    # whatever it was, which on an all-fail task is frequently the greedy
    # candidate at temp 0.0, i.e. the timeout when the model loops.
    verified_fails = [r for r in fails if not r.timed_out and r.code.strip()]
    if not verified_fails:
        log["status"] = "no_verified_failure"   # every base candidate timed out
        return log, None
    rejected = verified_fails[0].code

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

    # Invariant: chosen truly passes, rejected truly FAILS (ground-truth recheck).
    # `not ok` alone does not say that: a timeout is also not-ok, so the old form
    # of this check would have certified a pair the selection above had already
    # let through. Re-checked here rather than trusted from the base probe
    # because verification is the thing this file is not allowed to assume.
    rej = forge.verify(rejected, task)
    if not (forge.verify(chosen, task).ok and not rej.ok and not rej.timed_out):
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
