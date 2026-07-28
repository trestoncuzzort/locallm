#!/usr/bin/env python3
"""
eval.py : the RULER. A frozen held-out benchmark that scores any Ollama model
so successive forge->train->re-inject rounds can be measured against a fixed
baseline. Without this, "the loop closed" says nothing about better vs. worse.

Design
------
- HELD_OUT tasks are DISJOINT from forge.SEED_TASKS and are never used to
  generate training pairs. They are the yardstick, nothing else touches them.
- Scoring reuses forge.verify (same subprocess ground truth as the loop).
- Reports unbiased pass@k (Chen et al. 2021): sample n >= k completions per
  task, count c correct, estimate the probability that a random k-subset
  contains at least one correct sample. This is stable under sampling noise,
  unlike a single greedy pass.

Caveat (documented, not hidden): these task shapes may overlap the base
model's pretraining, so ABSOLUTE pass@k partly reflects recall. That is fine
for a RULER -- we compare iteration-N to iteration-0 on the SAME frozen set,
where a relative rise/fall is still a real signal. Swap in provably-novel
tasks later to harden the absolute number.

Run:  python eval.py                       # scores forge.MODEL_NAME
      python eval.py llama3-forged         # scores a trained/re-injected model
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import forge  # reuse Task, Actor, verify, extract_code, ACTOR_SYSTEM

N_SAMPLES = 5          # completions per task; must be >= max k reported
TEMP = 0.8             # sampling temperature for the non-greedy draws
KS = (1, 3)            # report pass@1 and pass@3
OUT = Path(__file__).with_name("data")


# ---------------------------------------------------------------------------
# Held-out task bank (frozen; never fed to the training loop)
# ---------------------------------------------------------------------------
HELD_OUT: list[forge.Task] = [
    forge.Task("gcd",
        "Write `gcd(a, b)` returning the greatest common divisor of two "
        "positive integers.",
        "gcd",
        """
def run_tests(gcd):
    assert gcd(12, 8) == 4
    assert gcd(17, 5) == 1
    assert gcd(100, 10) == 10
    assert gcd(7, 7) == 7
    assert gcd(1, 1) == 1
"""),
    forge.Task("is_prime",
        "Write `is_prime(n)` returning True iff the integer n is prime.",
        "is_prime",
        """
def run_tests(is_prime):
    assert is_prime(2) is True
    assert is_prime(1) is False
    assert is_prime(0) is False
    assert is_prime(17) is True
    assert is_prime(18) is False
    assert is_prime(97) is True
"""),
    forge.Task("reverse_words",
        "Write `reverse_words(s)` returning the words of s in reverse order, "
        "separated by single spaces, with leading/trailing/duplicate spaces removed.",
        "reverse_words",
        """
def run_tests(reverse_words):
    assert reverse_words("hello world") == "world hello"
    assert reverse_words("  the sky  is blue ") == "blue is sky the"
    assert reverse_words("single") == "single"
    assert reverse_words("a b c") == "c b a"
"""),
    forge.Task("rle",
        "Write `rle(s)` run-length-encoding a string as char+count per run, "
        "e.g. 'aaabbc' -> 'a3b2c1'. Empty string -> ''.",
        "rle",
        """
def run_tests(rle):
    assert rle("aaabbc") == "a3b2c1"
    assert rle("") == ""
    assert rle("x") == "x1"
    assert rle("aabbaa") == "a2b2a2"
"""),
    forge.Task("flatten",
        "Write `flatten(x)` flattening an arbitrarily nested list of integers "
        "into a single flat list, left to right.",
        "flatten",
        """
def run_tests(flatten):
    assert flatten([1, [2, [3, 4], 5]]) == [1, 2, 3, 4, 5]
    assert flatten([]) == []
    assert flatten([1, 2, 3]) == [1, 2, 3]
    assert flatten([[[[1]]], 2]) == [1, 2]
"""),
    forge.Task("nth_fib",
        "Write `nth_fib(n)` returning the nth Fibonacci number, 0-indexed, "
        "with nth_fib(0)=0 and nth_fib(1)=1.",
        "nth_fib",
        """
def run_tests(nth_fib):
    assert nth_fib(0) == 0
    assert nth_fib(1) == 1
    assert nth_fib(2) == 1
    assert nth_fib(7) == 13
    assert nth_fib(10) == 55
"""),
    forge.Task("count_vowels",
        "Write `count_vowels(s)` counting the vowels (a,e,i,o,u) in s, "
        "case-insensitive.",
        "count_vowels",
        """
def run_tests(count_vowels):
    assert count_vowels("hello") == 2
    assert count_vowels("XYZ") == 0
    assert count_vowels("AEIOU") == 5
    assert count_vowels("") == 0
    assert count_vowels("Programming") == 3
"""),
    forge.Task("kadane",
        "Write `max_subarray(nums)` returning the maximum sum of any "
        "contiguous non-empty subarray.",
        "max_subarray",
        """
def run_tests(max_subarray):
    assert max_subarray([-2,1,-3,4,-1,2,1,-5,4]) == 6
    assert max_subarray([1]) == 1
    assert max_subarray([-1,-2,-3]) == -1
    assert max_subarray([5,4,-1,7,8]) == 23
"""),
    forge.Task("rotate",
        "Write `rotate(lst, k)` returning lst rotated to the right by k "
        "positions (k may exceed len). Do not mutate the input.",
        "rotate",
        """
def run_tests(rotate):
    assert rotate([1,2,3,4,5], 2) == [4,5,1,2,3]
    assert rotate([1,2,3], 0) == [1,2,3]
    assert rotate([1,2,3], 3) == [1,2,3]
    assert rotate([1,2], 3) == [2,1]
    assert rotate([], 2) == []
"""),
    forge.Task("dedup",
        "Write `dedup(lst)` removing duplicates while preserving first-seen order.",
        "dedup",
        """
def run_tests(dedup):
    assert dedup([1,1,2,3,3,3,4]) == [1,2,3,4]
    assert dedup([]) == []
    assert dedup([5,4,5,4]) == [5,4]
    assert dedup([1,2,3]) == [1,2,3]
"""),
]


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator: 1 - C(n-c, k)/C(n, k)."""
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def evaluate(model_tag: str) -> dict | None:
    actor = forge.Actor(forge.OLLAMA_URL, model_tag)
    try:
        tags = actor.s.get(f"{forge.OLLAMA_URL}/api/tags", timeout=5).json()
        if model_tag not in {m["name"] for m in tags.get("models", [])}:
            print(f"[!] Model '{model_tag}' not pulled.")
            return None
    except Exception as e:  # noqa: BLE001 - fail fast with a clear message
        print(f"[!] Ollama not reachable at {forge.OLLAMA_URL} ({e}).")
        return None

    # A GENERATION ERROR IS NOT A WRONG ANSWER. This loop used to `continue` on a
    # transport failure while still dividing by N_SAMPLES, so an Ollama hiccup was
    # scored as the model getting the task wrong -- depressing the score and
    # inflating the run-to-run spread that this file is the ruler for. Attempted
    # and scored are now counted separately; the score is over what was actually
    # measured, and a task nothing could be sampled for is EXCLUDED rather than
    # silently counted as zero.
    per_task = []
    for t in HELD_OUT:
        c = scored = errors = 0
        for i in range(N_SAMPLES):
            temp = 0.0 if i == 0 else TEMP  # one greedy anchor + diverse rest
            try:
                raw = actor.generate(t.prompt, forge.ACTOR_SYSTEM, temp)
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"  [{t.tid}] gen error: {e}")
                continue
            scored += 1
            if forge.verify(forge.extract_code(raw), t).ok:
                c += 1
        per_task.append({"tid": t.tid, "correct": c, "n": scored,
                         "requested": N_SAMPLES, "gen_errors": errors})
        marks = "".join("#" if j < c else "." for j in range(scored))
        flag = f"  [{errors} gen error(s), not scored]" if errors else ""
        print(f"  {t.tid:14} {marks} {c}/{scored}{flag}")
    actor.release()

    # pass@k is undefined when fewer than k samples were actually scored, so those
    # tasks drop out of that k rather than being counted as failures.
    agg, coverage = {}, {}
    for k in KS:
        usable = [p for p in per_task if p["n"] >= k]
        agg[f"pass@{k}"] = round(
            sum(pass_at_k(p["n"], p["correct"], k) for p in usable) / len(usable), 4
        ) if usable else None
        coverage[f"pass@{k}"] = {"tasks_scored": len(usable), "tasks_total": len(per_task)}

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_tag,
        "n_samples": N_SAMPLES,
        "temp": TEMP,
        "n_tasks": len(HELD_OUT),
        "aggregate": agg,
        "coverage": coverage,
        "gen_errors_total": sum(p["gen_errors"] for p in per_task),
        "per_task": per_task,
    }


def main() -> None:
    model_tag = sys.argv[1] if len(sys.argv) > 1 else forge.MODEL_NAME
    OUT.mkdir(exist_ok=True)
    print(f"Scoring '{model_tag}' on {len(HELD_OUT)} held-out tasks "
          f"({N_SAMPLES} samples each)...\n")
    result = evaluate(model_tag)
    if not result:
        return
    path = OUT / "eval_history.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"\naggregate: {result['aggregate']}")
    print(f"appended to {path}")
    print("This is the yardstick. Compare every future round's numbers to it.")


if __name__ == "__main__":
    main()
