#!/usr/bin/env python3
"""
srlm-forge : failure-driven self-rewarding DPO data generator.

Architecture
------------
For each coding task (a prompt + hidden unit tests):

  1. ACTOR   - sample K candidate solutions from a local Ollama model.
  2. VERIFY  - run each candidate against the unit tests in an isolated
               subprocess. This is the GROUND TRUTH reward. The model does
               not get to score itself; the tests do.
  3. PAIR    - chosen  = best verified candidate (most tests passed, then
                         fastest, then shortest).
               rejected = a strictly-worse candidate.
               A pair is only emitted when chosen is strictly better than
               rejected, so every row carries real preference signal.
  4. CRITIC  - the model writes a short rationale explaining WHY chosen beat
               rejected, grounded in the test outcome. Stored as metadata;
               it explains the verdict, it never overrides it.
  5. CURRICULUM - tasks where every candidate fails go to failures.jsonl.
               Those are "current failures" - the curriculum for the next
               round and the seed for training from scratch.

Output
------
  dpo_pairs.jsonl : {"prompt","chosen","rejected","meta"}  <- Unsloth DPO ready
  failures.jsonl  : tasks no candidate could solve         <- next-round curriculum

Runtime deps: requests + a running Ollama with a 4-bit GGUF model.
VRAM: only the actor model is resident (~5-6 GB for an 8B q4). keep_alive
      is set so the model stays warm between tasks but is released on exit.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

import config
import dataset_gate

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Model is resolved by config.py from $SRLM_MODEL (defaults to llama3:8b). This
# makes the whole pipeline model-agnostic; eval/repair/measure read these two.
OLLAMA_URL   = config.OLLAMA_URL
MODEL_NAME   = config.MODEL_NAME
NUM_CANDIDATES = 4          # samples per task; more = better pairs, more time
GEN_TEMP     = 0.8          # diversity matters for preference pairs
KEEP_ALIVE   = "5m"         # keep model warm between tasks; released on exit
CAND_TIMEOUT = 8            # seconds per candidate execution

EMIT_CONCISENESS = False    # length-preference is a reward-hack;
                            # off until a robustness signal (mutation tests) exists
OUT_DIR      = Path(__file__).with_name("data")

ACTOR_SYSTEM = (
    "You are a precise Python engineer. Given a task, respond with a single "
    "self-contained Python solution inside one ```python fenced code block. "
    "Define exactly the requested function. No prose, no tests, no prints."
)

# Cheap defense-in-depth for executing model output. NOT a real sandbox.
# For untrusted / scaled runs, execute inside a container or throwaway VM.
BANNED = re.compile(
    r"\b(import\s+(os|sys|subprocess|socket|shutil|ctypes|requests|urllib|http)"
    r"|__import__|open\s*\(|eval\s*\(|exec\s*\()",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# THE VERIFIER'S INTERPRETER IS PINNED, NOT INHERITED.
#
# verify() used to launch [sys.executable, "-I", path], so ground truth -- the
# one objective signal this whole project rests on -- depended on which script
# happened to call it. That is not hypothetical: screen_tasks.py and
# build_ruler.py go through venv_guard, and system Python has no pyarrow, so
# they ALWAYS re-exec under .venv-train (3.11). eval.py, ruler_noise.py and
# forge.py have no guard and run under system Python (3.14). The screen that
# admitted the ruler and the eval that scores it were verifying against
# different Pythons.
#
# RED WITNESS (section 71): 310 completions banked once, then replayed through
# verify() under both interpreters -- identical code bytes, identical tasks.
#   3.14: 172/310 = 0.5548     3.11: 154/310 = 0.4968
# 18 disagreements, ALL ONE WAY (3.14 passes, 3.11 fails), on 6 of 31 tasks.
# Cause is PEP 649/749 deferred annotation evaluation: `def f(x: List[int])`
# with no `from typing import List` raises NameError at def time on 3.11 and is
# harmless on 3.14. Minimal probe:
#     def f(x: List[int]) -> Tuple[int, int]: return (1, 2)
#   3.11 -> NameError: name 'List' is not defined      3.14 -> DEFINED_OK
# Consequence measured: 5 ruler tasks that sit at 0.60-0.80 under 3.11 become
# DEAD CHANNELS at 1.000 under 3.14, and tasks outside the [0.2,0.8] band go
# from 2/31 to 7/31. The permissive reading destroys the instrument.
#
# WHY .venv-train IS THE DEFAULT rather than system Python. Not because it
# preserves the ruler -- that would be reasoning that conveniently saves work.
# Because (a) unimported typing annotations genuinely do not run on any Python
# before 3.14, so accepting them rewards code that is broken nearly everywhere,
# and (b) .venv-train is the interpreter the training stack itself runs on, so
# it is what the model is being trained to write for. It is version-pinned and
# lives in the repo, which is what makes it a pin rather than a coincidence.
#
# THIS RE-DEFINES GROUND TRUTH for artifacts verified under 3.14 -- data/
# dpo_pairs*.jsonl and data/eval_history.jsonl were built by unguarded scripts.
# Nothing here re-runs or overwrites them; the fingerprint below exists so a
# cross-interpreter comparison is detectable instead of silent. Override with
# SRLM_VERIFY_PY to re-pin deliberately.
# ---------------------------------------------------------------------------
# The resolution itself lives in dataset_gate, which is stdlib-only and already
# imported by BOTH interpreters (verify side and training side). One definition,
# imported -- not a copy per caller, which is the failure venv_guard.py was
# written to end. dataset_gate imports nothing from forge, so there is no cycle.
VERIFY_PY = dataset_gate.verify_py()


def verifier_interpreter() -> dict:
    """What the verifier ACTUALLY is, asked of the interpreter rather than
    assumed. Recorded into result artifacts so two numbers produced under
    different ground truth can never be silently compared."""
    ver = dataset_gate.interpreter_fingerprint()["interpreter"].split()[-1]
    return {"executable": VERIFY_PY, "version": ver,
            "pinned_away_from_launcher": VERIFY_PY != sys.executable,
            "launcher_version": sys.version.split()[0]}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
@dataclass
class Task:
    tid: str
    prompt: str          # what the model is asked to do
    entry: str           # function name the tests call
    tests: str           # assert-based test body; must define run_tests()


SEED_TASKS: list[Task] = [
    Task(
        "two_sum",
        "Write `two_sum(nums, target)` returning indices [i, j] (i < j) of the "
        "two distinct elements of `nums` that sum to `target`. Assume exactly "
        "one solution exists.",
        "two_sum",
        """
def run_tests(two_sum):
    assert sorted(two_sum([2,7,11,15], 9)) == [0,1]
    assert sorted(two_sum([3,2,4], 6)) == [1,2]
    assert sorted(two_sum([3,3], 6)) == [0,1]
    assert sorted(two_sum([-1,-2,-3,-4], -6)) == [1,3]
""",
    ),
    Task(
        "roman",
        "Write `to_roman(n)` converting an integer 1..3999 to its Roman "
        "numeral string (uppercase).",
        "to_roman",
        """
def run_tests(to_roman):
    assert to_roman(1) == "I"
    assert to_roman(4) == "IV"
    assert to_roman(9) == "IX"
    assert to_roman(58) == "LVIII"
    assert to_roman(1994) == "MCMXCIV"
    assert to_roman(3999) == "MMMCMXCIX"
""",
    ),
    Task(
        "balanced",
        "Write `is_balanced(s)` returning True iff the brackets in `s` "
        "(){}[] are correctly matched and nested. Ignore other characters.",
        "is_balanced",
        """
def run_tests(is_balanced):
    assert is_balanced("()") is True
    assert is_balanced("([]{})") is True
    assert is_balanced("(]") is False
    assert is_balanced("([)]") is False
    assert is_balanced("a(b)c[d]{e}") is True
    assert is_balanced("(((") is False
""",
    ),
    Task(
        "spiral",
        "Write `spiral_order(matrix)` returning all elements of the 2D list "
        "`matrix` in clockwise spiral order starting from the top-left.",
        "spiral_order",
        """
def run_tests(spiral_order):
    assert spiral_order([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]
    assert spiral_order([[1,2,3,4],[5,6,7,8],[9,10,11,12]]) == [1,2,3,4,8,12,11,10,9,5,6,7]
    assert spiral_order([[1]]) == [1]
    assert spiral_order([[1,2],[3,4]]) == [1,2,4,3]
    assert spiral_order([[1,2,3]]) == [1,2,3]
""",
    ),
    Task(
        "atoi",
        "Write `my_atoi(s)` implementing string-to-32-bit-int: skip leading "
        "spaces, optional +/- sign, read consecutive digits until a non-digit, "
        "return 0 if no digits, and clamp to the signed 32-bit range "
        "[-2147483648, 2147483647].",
        "my_atoi",
        """
def run_tests(my_atoi):
    assert my_atoi("42") == 42
    assert my_atoi("   -42") == -42
    assert my_atoi("4193 with words") == 4193
    assert my_atoi("words and 987") == 0
    assert my_atoi("-91283472332") == -2147483648
    assert my_atoi("2147483648") == 2147483647
    assert my_atoi("+1") == 1
    assert my_atoi("3.14159") == 3
""",
    ),
    Task(
        "lps",
        "Write `longest_palindrome(s)` returning the longest contiguous "
        "palindromic substring of `s`. If several tie, any correct one is fine "
        "for these inputs (each has a unique longest).",
        "longest_palindrome",
        """
def run_tests(longest_palindrome):
    assert longest_palindrome("cbbd") == "bb"
    assert longest_palindrome("bananas") == "anana"
    assert longest_palindrome("forgeeksskeegfor") == "geeksskeeg"
    assert longest_palindrome("z") == "z"
    assert longest_palindrome("abacdfgdcaba"[:5]) == "aba"
""",
    ),
    Task(
        "merge_intervals",
        "Write `merge_intervals(intervals)` that merges all overlapping "
        "[start, end] intervals and returns the merged list sorted by start.",
        "merge_intervals",
        """
def run_tests(merge_intervals):
    assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
    assert merge_intervals([[1,4],[4,5]]) == [[1,5]]
    assert merge_intervals([[1,4],[2,3]]) == [[1,4]]
    assert merge_intervals([[1,2]]) == [[1,2]]
    assert merge_intervals([[1,4],[0,4]]) == [[0,4]]
""",
    ),
    Task(
        "simplify_path",
        "Write `simplify_path(path)` canonicalizing a Unix-style absolute path: "
        "collapse '//' , resolve '.' and '..', drop trailing slash. Root is '/'.",
        "simplify_path",
        """
def run_tests(simplify_path):
    assert simplify_path("/home/") == "/home"
    assert simplify_path("/../") == "/"
    assert simplify_path("/home//foo/") == "/home/foo"
    assert simplify_path("/a/./b/../../c/") == "/c"
    assert simplify_path("/a/../../b/../c//.//") == "/c"
""",
    ),
    Task(
        "decode_ways",
        "Write `decode_ways(s)` counting how many ways a digit string decodes to "
        "letters where '1'->A .. '26'->Z. A leading '0' or invalid '0' yields 0.",
        "decode_ways",
        """
def run_tests(decode_ways):
    assert decode_ways("12") == 2
    assert decode_ways("226") == 3
    assert decode_ways("0") == 0
    assert decode_ways("06") == 0
    assert decode_ways("11106") == 2
    assert decode_ways("1") == 1
""",
    ),
    # --- harder frontier tasks: 8b-q4 fails some of these one-shot, so they
    #     produce genuine failures for repair.py to learn from ---
    Task(
        "three_sum",
        "Write `three_sum(nums)` returning all unique triplets [a, b, c] from "
        "nums with a + b + c == 0. Order of triplets and of elements within a "
        "triplet does not matter; no duplicate triplets.",
        "three_sum",
        """
def run_tests(three_sum):
    def norm(x): return sorted(sorted(t) for t in x)
    assert norm(three_sum([-1,0,1,2,-1,-4])) == norm([[-1,-1,2],[-1,0,1]])
    assert norm(three_sum([0,1,1])) == []
    assert norm(three_sum([0,0,0])) == [[0,0,0]]
    assert norm(three_sum([-2,0,1,1,2])) == norm([[-2,0,2],[-2,1,1]])
""",
    ),
    Task(
        "word_break",
        "Write `word_break(s, words)` returning True iff s can be segmented into "
        "a space-separated sequence of one or more words from the list `words` "
        "(each word reusable). The empty string is segmentable.",
        "word_break",
        """
def run_tests(word_break):
    assert word_break("leetcode", ["leet","code"]) is True
    assert word_break("applepenapple", ["apple","pen"]) is True
    assert word_break("catsandog", ["cats","dog","sand","and","cat"]) is False
    assert word_break("", ["a"]) is True
    assert word_break("a", ["b"]) is False
""",
    ),
    Task(
        "multiply_strings",
        "Write `multiply_strings(a, b)` returning the product of two non-negative "
        "integers given as strings, as a string, WITHOUT using int()/float()/eval "
        "on the whole number (grade-school multiplication).",
        "multiply_strings",
        """
def run_tests(multiply_strings):
    assert multiply_strings("2","3") == "6"
    assert multiply_strings("123","456") == "56088"
    assert multiply_strings("0","999") == "0"
    assert multiply_strings("99","99") == "9801"
    assert multiply_strings("123456789","987654321") == "121932631112635269"
""",
    ),
    Task(
        "next_permutation",
        "Write `next_permutation(nums)` returning the next lexicographically "
        "greater permutation of the list nums as a NEW list; if nums is the "
        "largest permutation, return the smallest (ascending) one.",
        "next_permutation",
        """
def run_tests(next_permutation):
    assert next_permutation([1,2,3]) == [1,3,2]
    assert next_permutation([3,2,1]) == [1,2,3]
    assert next_permutation([1,1,5]) == [1,5,1]
    assert next_permutation([1,3,2]) == [2,1,3]
    assert next_permutation([2,3,1]) == [3,1,2]
""",
    ),
]


# ---------------------------------------------------------------------------
# Ollama actor
# ---------------------------------------------------------------------------
class Actor:
    def __init__(self, url: str, model: str):
        self.chat = f"{url}/api/chat"
        self.model = model
        self.s = requests.Session()

    def generate(self, prompt: str, system: str, temp: float) -> str:
        r = self.s.post(
            self.chat,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "keep_alive": KEEP_ALIVE,
                "options": {"temperature": temp, "num_ctx": 2048},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def release(self) -> None:
        # keep_alive 0 unloads the model from VRAM immediately.
        try:
            self.s.post(
                self.chat,
                json={"model": self.model, "messages": [], "keep_alive": 0},
                timeout=10,
            )
        except requests.RequestException:
            pass


# ---------------------------------------------------------------------------
# Verifier (ground-truth reward)
# ---------------------------------------------------------------------------
CODE_RE = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    """Pull code out of a model reply, tolerant of fence/language-tag noise.

    Handles ```python fences, bare ``` fences, a language tag on its own line,
    and replies where the closing fence was omitted or duplicated.
    """
    text = text.strip()
    m = CODE_RE.search(text)
    code = m.group(1) if m else text
    # drop any stray fence lines and a leading bare language tag
    lines = [ln for ln in code.splitlines() if not ln.strip().startswith("```")]
    if lines and lines[0].strip().lower() in ("python", "py"):
        lines = lines[1:]
    return "\n".join(lines).strip()


@dataclass
class Result:
    code: str
    ok: bool = False        # all tests passed cleanly
    passed: int = 0
    total: int = 1
    runtime: float = 0.0
    error: str = ""
    timed_out: bool = False  # distinct from "wrong": we do not know if it is wrong
    # The completion exactly as the model emitted it, fences and all. `code` is
    # extract_code(raw) and is what the verifier executes; `raw` is what the
    # policy actually produced and is what a preference target must be, or the
    # trainer optimises toward a string no model ever wrote. Defaults to "" so
    # every existing Result(code=...) call site keeps working unchanged.
    raw: str = ""

    @property
    def score(self) -> tuple:
        # higher is better: correctness first, then shorter, then faster.
        # length is deterministic; runtime is last because microbench timing
        # on tiny inputs is dominated by process-startup noise.
        return (self.passed / self.total, -len(self.code), -self.runtime)


def verify(code: str, task: Task) -> Result:
    res = Result(code=code)
    if not code or BANNED.search(code):
        res.error = "empty or contains banned operation"
        return res

    # STRICT RETURN TYPES. Every test body compares with `==`, and `==` is not a
    # fact about values - it is a method call the solution controls. A class whose
    # __eq__ returns True passes every assert in every task at once (red witness:
    # a 6-line _Always class scored ok=True on `roman`). That makes "the tests
    # decide, not the model" false under exactly the optimization pressure this
    # pipeline applies.
    #
    # So the entry point is wrapped once, here, rather than hardening 13 test
    # bodies: the return value must be built from plain builtins, checked by EXACT
    # type (not isinstance - `class S(str)` with a custom __eq__ passes isinstance
    # and still lies). A solution returning anything else fails before its value is
    # ever compared. This closes the class for every current and future task.
    #
    # -I is also load-bearing beyond env hygiene: it implies -E, which discards
    # PYTHONOPTIMIZE. With PYTHONOPTIMIZE=1 the interpreter strips every assert and
    # a wrong answer prints __PASS__ and exits 0. Do not "simplify" -I away.
    guard = (
        "_OK_T = {bool, int, float, str, bytes, type(None), list, tuple, dict,"
        " set, frozenset}\n"
        "def _strict(v):\n"
        "    t = type(v)\n"
        "    if t not in _OK_T:\n"
        "        raise TypeError('solution returned %r; the verifier accepts only'\n"
        "                        ' plain builtins so that == cannot be overridden'\n"
        "                        % (t.__name__,))\n"
        "    if t in (list, tuple, set, frozenset):\n"
        "        return t(_strict(x) for x in v)\n"
        "    if t is dict:\n"
        "        return {_strict(k): _strict(x) for k, x in v.items()}\n"
        "    return v\n"
        f"_entry = {task.entry}\n"
        "def _checked(*a, **k):\n"
        "    return _strict(_entry(*a, **k))\n"
    )
    harness = (
        f"{code}\n\n{task.tests}\n"
        f"{guard}"
        "import time as _t\n"
        "_start = _t.perf_counter()\n"
        "run_tests(_checked)\n"
        "print('__PASS__', round((_t.perf_counter()-_start)*1000, 2))\n"
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(harness)
        path = fh.name

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [VERIFY_PY, "-I", path],        # -I: isolated, ignore env/site
                                            # VERIFY_PY, not sys.executable: see
                                            # the pin block above and section 71
            capture_output=True, text=True, timeout=CAND_TIMEOUT,
        )
        res.runtime = time.perf_counter() - t0
        if proc.returncode == 0 and "__PASS__" in proc.stdout:
            res.ok = True
            res.passed = res.total  # assert-based: all-or-nothing here
        else:
            res.error = (proc.stderr or proc.stdout or "failed").strip()[-400:]
    except subprocess.TimeoutExpired:
        # A TIMEOUT IS NOT A WRONG ANSWER. A correct-but-slow solution, or a busy
        # machine, produces this -- and wall-clock means the same bytes can time
        # out on one run and pass on the next. Recorded distinctly so it can never
        # become the `rejected` half of a pair, which would teach the model that a
        # correct answer is wrong.
        res.timed_out = True
        res.error = f"timeout >{CAND_TIMEOUT}s"
    finally:
        Path(path).unlink(missing_ok=True)
    return res


# ---------------------------------------------------------------------------
# Critic (grounded rationale, not judge)
# ---------------------------------------------------------------------------
def critique(actor: Actor, task: Task, chosen: Result,
             rejected: Result, reason: str) -> str:
    if reason == "correctness":
        framing = (
            f"Solution A PASSED all unit tests. Solution B FAILED "
            f"({rejected.error or 'wrong output'}).\n\n"
            "In two sentences, state the concrete defect in B that A avoids."
        )
    else:  # conciseness: both correct, A is simpler
        framing = (
            "Both solutions PASS all unit tests, but A is shorter and simpler "
            "than B.\n\nIn two sentences, state what makes A the cleaner "
            "implementation. Do not claim B is incorrect."
        )
    prompt = (
        f"Task: {task.prompt}\n\n"
        f"Solution A:\n```python\n{chosen.code}\n```\n\n"
        f"Solution B:\n```python\n{rejected.code}\n```\n\n"
        f"{framing} Be specific and technical. Do not restate the task."
    )
    try:
        return actor.generate(prompt, "You are a terse code reviewer.", 0.2).strip()
    except requests.RequestException as e:
        return f"(critic unavailable: {e})"


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------
@dataclass
class Stats:
    tasks: int = 0
    pairs: int = 0
    solved: int = 0
    failed: list[str] = field(default_factory=list)
    # pair counts split by reason -> makes length-bias visible, not silent
    by_reason: dict = field(default_factory=lambda: {"correctness": 0, "conciseness": 0})


def run_task(actor: Actor, task: Task) -> tuple[dict | None, dict | None, bool]:
    """Returns (dpo_pair | None, failure_record | None, solved)."""
    results: list[Result] = []
    for i in range(NUM_CANDIDATES):
        temp = 0.0 if i == 0 else GEN_TEMP   # one greedy anchor + diverse rest
        try:
            raw = actor.generate(task.prompt, ACTOR_SYSTEM, temp)
        except requests.RequestException as e:
            print(f"  [gen error] {e}")
            continue
        r = verify(extract_code(raw), task)
        r.raw = raw          # keep the verbatim emission for the preference target
        results.append(r)

    if not results:
        return None, {"tid": task.tid, "prompt": task.prompt,
                      "reason": "no candidates generated"}, False

    results.sort(key=lambda r: r.score, reverse=True)
    best = results[0]
    solved = best.ok

    if not solved:
        # Every candidate failed -> curriculum for the next round.
        return None, {
            "tid": task.tid, "prompt": task.prompt,
            "best_error": best.error,
            "candidates": [{"code": r.code, "error": r.error} for r in results],
        }, False

    # Prefer a genuine correctness gap: chosen passes, rejected demonstrably
    # fails. That is the clean "fix the failure" signal.
    # `rejected` must be demonstrably WRONG, not merely slow or unmeasured.
    failing = [r for r in results
               if not r.ok and not r.timed_out and r.code and r.code != best.code]
    if failing:
        worst, reason = min(failing, key=lambda r: r.score), "correctness"
    elif not EMIT_CONCISENESS:
        return None, None, True  # conciseness pairs disabled (reward-hack risk)
    else:
        # All candidates pass. Only emit a conciseness preference when the
        # length margin is real (>= 40 chars) -- never on timing noise.
        longest = max(results, key=lambda r: len(r.code))
        if len(longest.code) - len(best.code) >= 40:
            worst, reason = longest, "conciseness"
        else:
            return None, None, True  # solved, no reliable preference signal

    pair = {
        "prompt": task.prompt,
        # chosen/rejected stay EXECUTABLE source: clean_dataset.py:26,
        # verify_dataset.py:82 and both dedup hashes run forge.verify on them.
        "chosen": best.code,
        "rejected": worst.code,
        # ...and the verbatim completions alongside, because those two facts are
        # not the same string. extract_code strips the ```python fences that
        # ACTOR_SYSTEM instructs the model to emit, so training on `chosen`
        # optimises toward text no policy ever produced. Found by an independent
        # review pass; red witness recorded in the project log. Additive - every
        # existing consumer keeps reading the fields it already reads.
        "chosen_raw": best.raw,
        "rejected_raw": worst.raw,
        "meta": {
            "tid": task.tid,
            "reason": reason,
            "chosen_runtime_ms": round(best.runtime * 1000, 2),
            "rejected_error": worst.error,
            "rationale": critique(actor, task, best, worst, reason),
        },
    }
    return pair, None, True


def main(tasks: list[Task]) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    dpo_path = OUT_DIR / "dpo_pairs.jsonl"
    fail_path = OUT_DIR / "failures.jsonl"

    actor = Actor(OLLAMA_URL, MODEL_NAME)
    # Fail fast with a clear message if Ollama/model isn't ready.
    try:
        tags = actor.s.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
        have = {m["name"] for m in tags.get("models", [])}
        if MODEL_NAME not in have:
            print(f"[!] Model '{MODEL_NAME}' not pulled. Have: {sorted(have) or 'none'}")
            print(f"    Run:  ollama pull {MODEL_NAME}")
            return
    except requests.RequestException as e:
        print(f"[!] Ollama not reachable at {OLLAMA_URL} ({e}). Start it and retry.")
        return

    # Dedup across rounds: skip pairs whose (prompt, chosen, rejected) already
    # exist, so repeated overnight passes accumulate only new signal.
    seen: set[str] = set()
    if dpo_path.exists():
        for line in dpo_path.open(encoding="utf-8"):
            try:
                p = json.loads(line)
                seen.add(hashlib.sha1(
                    (p["prompt"] + p["chosen"] + p["rejected"]).encode()
                ).hexdigest())
            except (json.JSONDecodeError, KeyError):
                pass

    stats = Stats()
    with dpo_path.open("a", encoding="utf-8") as dpo_f, \
         fail_path.open("a", encoding="utf-8") as fail_f:
        for task in tasks:
            stats.tasks += 1
            print(f"[{task.tid}] generating {NUM_CANDIDATES} candidates...")
            pair, failure, solved = run_task(actor, task)
            if solved:
                stats.solved += 1
            if pair:
                sig = hashlib.sha1(
                    (pair["prompt"] + pair["chosen"] + pair["rejected"]).encode()
                ).hexdigest()
                if sig in seen:
                    print("  -> duplicate pair, skipped")
                    pair = None
            if pair:
                seen.add(sig)
                dpo_f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                stats.pairs += 1
                stats.by_reason[pair["meta"]["reason"]] += 1
                print(f"  -> {pair['meta']['reason']} pair. rationale: {pair['meta']['rationale'][:80]}")
            if failure:
                fail_f.write(json.dumps(failure, ensure_ascii=False) + "\n")
                stats.failed.append(task.tid)
                print(f"  -> unsolved, added to curriculum")
            if solved and not pair:
                print("  -> solved, no pair (candidates tied)")

    actor.release()

    # Per-round instrumentation: reason split + the all-fail frontier.
    # These all-fail ids emit ZERO training gradient today (a DPO pair needs a
    # passing `chosen`); logging them exposes the failure frontier for the
    # reference-solution-injection step that will make them learnable.
    summary = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": MODEL_NAME,
        "tasks": stats.tasks,
        "solved": stats.solved,
        "pairs": stats.pairs,
        "pairs_by_reason": stats.by_reason,
        "all_fail_ids": stats.failed,
    }
    with (OUT_DIR / "round_stats.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    print(
        f"\ndone. tasks={stats.tasks} solved={stats.solved} pairs={stats.pairs} "
        f"(correctness={stats.by_reason['correctness']} "
        f"conciseness={stats.by_reason['conciseness']}) unsolved={stats.failed}"
    )
    print(f"DPO data : {dpo_path}")
    print(f"Curriculum: {fail_path}")
    print(f"Round log : {OUT_DIR / 'round_stats.jsonl'}")


if __name__ == "__main__":
    main(SEED_TASKS)
