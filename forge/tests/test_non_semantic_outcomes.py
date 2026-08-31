"""Non-semantic outcomes must never become a label, a target, or model feedback.

THE CLASS. Exactly one signal in this pipeline is allowed to reach the model:
whether the hidden tests PASSED. Everything else the harness learns while running
a candidate is either infrastructure (a timeout: the answer is UNKNOWN, not
wrong) or test internals (an exception message, which can carry a hidden-test
argument verbatim). forge.run_task already enforces this -- forge.py:654-656
excludes `timed_out` candidates from the rejected half, and forge.py:672-683
keeps `chosen`/`rejected` executable with the verbatim emissions alongside in
`chosen_raw`/`rejected_raw`.

The rule was enforced in run_task and nowhere else. These probes are the same
rule, asserted on the two paths that grew their own copies of the logic:

    repair.sanitized_feedback  -- shipped str(e) of the candidate's exception
                                  back to the model, hidden-test arguments and all
    repair.harvest_task        -- kept a timed-out candidate as `rejected`
    repair.sanitized_feedback  -- ran candidates under the LAUNCHING interpreter
                                  while forge.verify runs them under the pin
    traces.derive_kto          -- emitted label=False for a timed-out candidate
    traces.derive_dpo          -- emitted FENCED raw text as chosen/rejected

SCOPE, stated because it is the weak part. These are five fixed probes for five
found defects, not a sweep. Nothing here proves a sixth copy of the rule does not
exist somewhere else; the enumerated set is the five call sites above.

Synthetic tasks and synthetic trace rows only: no model, no Ollama, no repo file
read or written. The repair probes DO execute candidate code in a subprocess,
because that is the code path under test.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# dataset_gate.verify_py() refuses to fall back to the launcher (that fallback WAS
# the section-71 defect), so on a box with no .venv-train importing forge is a hard
# exit and these probes cannot run at all. Pin deliberately in that case only --
# NEVER when a real pin exists, because setting SRLM_VERIFY_PY unconditionally
# would silently make the launcher ground truth for every module in the same
# pytest process, which is the defect wearing a test's clothes. Scoped to this
# process either way, and test_feedback_harness_uses_the_pinned_interpreter does
# not depend on the value: it overrides forge.VERIFY_PY with a sentinel.
if not (Path(__file__).resolve().parents[1] / ".venv-train" / "Scripts"
        / "python.exe").exists():
    os.environ.setdefault("SRLM_VERIFY_PY", sys.executable)

import forge  # noqa: E402
import repair  # noqa: E402
import traces as T  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def row(tid, code, ok, *, timed_out=False, runtime=1.0):
    """Same shape as tests/test_trace_views.py:21, kept identical on purpose."""
    return {"schema": T.SCHEMA, "tid": tid, "prompt": f"solve {tid}",
            "entry": tid, "raw": f"```python\n{code}\n```", "code": code,
            "ok": ok, "reward": 1.0 if ok else 0.0, "error": "" if ok else "boom",
            "runtime_ms": runtime, "timed_out": timed_out, "temp": 0.8,
            "model": "test", "verifier": {}, "ts": ""}


class ScriptedActor:
    """Stands in for forge.Actor: replays a fixed list of emissions, then loops
    on its last entry. No network, no model."""

    def __init__(self, script: list[str], tail: str):
        self.script = list(script)
        self.tail = tail
        self.calls = 0

    def generate(self, prompt, system, temp):  # noqa: ARG002
        self.calls += 1
        code = self.script.pop(0) if self.script else self.tail
        return f"```python\n{code}\n```"


ADD_ONE_TASK = forge.Task(
    "probe_add_one",
    "Write `t(x)` returning x + 1.",
    "t",
    "def run_tests(t):\n    assert t(1) == 2\n    assert t(5) == 6\n",
)
TIMEOUT_CODE = "def t(x):\n    while True:\n        pass\n"
GOOD_CODE = "def t(x):\n    return x + 1\n"
WRONG_CODES = ["def t(x):\n    return 0\n",
               "def t(x):\n    return -1\n",
               "def t(x):\n    return -2\n"]


# --------------------------------------------------------------------------
# 1. feedback carries the exception CLASS, never its message
# --------------------------------------------------------------------------
def test_feedback_never_carries_exception_text():
    """repair.py's own docstring promises 'the exception class, or a generic
    wrong output -- never expected values or test source'. str(e) breaks that
    promise the moment a candidate raises with an argument the HIDDEN test
    handed it: `raise ValueError(x)` prints the hidden input verbatim.
    """
    task = forge.Task(
        "probe_leak",
        "Write `solve(x)` returning x unchanged.",
        "solve",
        'def run_tests(solve):\n    assert solve("SECRET42") == "SECRET42"\n',
    )
    fb = repair.sanitized_feedback("def solve(x):\n    raise ValueError(x)\n", task)
    assert "SECRET42" not in fb, f"hidden-test argument leaked into feedback: {fb!r}"
    assert "ValueError" in fb, f"the exception class is the signal we DO keep: {fb!r}"


# --------------------------------------------------------------------------
# 2. a timed-out candidate is not a wrong answer
# --------------------------------------------------------------------------
def test_a_timeout_never_becomes_the_rejected_half():
    """forge.py:654 -- `rejected` must be demonstrably WRONG, not merely slow.
    The base probe here draws one non-terminating candidate FIRST and three
    genuinely wrong ones after it, so taking fails[0] takes the timeout."""
    old_timeout = forge.CAND_TIMEOUT
    forge.CAND_TIMEOUT = 2          # keep the probe to a few seconds
    try:
        actor = ScriptedActor([TIMEOUT_CODE] + WRONG_CODES, tail=GOOD_CODE)
        log, pair = repair.harvest_task(actor, ADD_ONE_TASK, set())
    finally:
        forge.CAND_TIMEOUT = old_timeout
    assert pair is not None, f"the three genuine failures should still pair: {log}"
    assert pair["rejected"].strip() != TIMEOUT_CODE.strip(), \
        f"a timed-out candidate became the rejected half: {log}"
    assert pair["rejected"].strip() in {c.strip() for c in WRONG_CODES}, pair


def test_all_candidates_timing_out_yields_no_pair():
    """The invariant `not verify(rejected).ok` is ALSO satisfied by a timeout,
    so it cannot be the thing standing between a timeout and the dataset. With
    every base candidate non-terminating there is no verified failure at all,
    and the honest output is no pair."""
    old_timeout = forge.CAND_TIMEOUT
    forge.CAND_TIMEOUT = 2
    try:
        timeouts = [TIMEOUT_CODE.replace("pass", f"pass  # {i}")
                    for i in range(forge.NUM_CANDIDATES)]
        actor = ScriptedActor(timeouts, tail=GOOD_CODE)
        log, pair = repair.harvest_task(actor, ADD_ONE_TASK, set())
    finally:
        forge.CAND_TIMEOUT = old_timeout
    assert pair is None, f"a pair was built entirely out of timeouts: {pair}"
    assert log["status"] == "no_verified_failure", log


# --------------------------------------------------------------------------
# 3. the feedback harness runs on the SAME interpreter as ground truth
# --------------------------------------------------------------------------
def test_feedback_harness_uses_the_pinned_interpreter():
    """STRUCTURAL PROBE, and labelled as one. It asserts the launched argv[0] is
    forge.VERIFY_PY rather than sys.executable. It is structural so that it
    discriminates on ANY box, including one where only a single interpreter is
    installed and no behavioural difference is observable.

    The behavioural witness exists and is recorded in this commit's message
    rather than here, because it needs two specific Python versions: with the
    repo's own pin (.venv-train, 3.11.9) and launcher 3.12.10, the candidate
    `def solve[T](x: T) -> T: return x` -- PEP 695, valid on 3.12, SyntaxError
    on 3.11 -- produced, on the same bytes:
        forge.verify(...).ok    = False        (ground truth, under the pin)
        sanitized_feedback(...) = 'OK'         (feedback, under the launcher)
    The model was told its solution was fine by the same run that rejected it.
    Making that a test here would add a second box-dependent red alongside
    test_verifier_pin.py::test_the_probe_can_actually_discriminate, so the
    portable assertion is kept and the measurement is written down.
    """
    sentinel = str(Path("C:/srlm-probe-pin/python.exe"))
    assert sentinel != sys.executable
    captured: dict = {}

    class FakeCompleted:
        stdout = "__OK__\n"
        stderr = ""

    def fake_run(cmd, **kw):
        captured["cmd"] = list(cmd)
        captured["kw"] = kw
        return FakeCompleted()

    orig_run, orig_pin = repair.subprocess.run, forge.VERIFY_PY
    forge.VERIFY_PY = sentinel
    repair.subprocess.run = fake_run
    try:
        repair.sanitized_feedback(GOOD_CODE, ADD_ONE_TASK)
    finally:
        repair.subprocess.run = orig_run
        forge.VERIFY_PY = orig_pin

    assert captured["cmd"][0] == sentinel, (
        "the repair feedback harness launched a candidate under "
        f"{captured['cmd'][0]!r}, not the pinned verifier {sentinel!r}")
    assert "-I" in captured["cmd"], captured["cmd"]


# --------------------------------------------------------------------------
# 4. the KTO view does not label a timeout
# --------------------------------------------------------------------------
def test_kto_view_excludes_timeouts():
    """label=False asserts the candidate is UNDESIRABLE. A timeout says the
    candidate did not finish inside the budget -- its correctness was never
    determined -- so labelling it False trains against an unknown. derive_dpo
    already excludes timeouts (traces.py:163); this is the same rule for KTO.
    """
    rows = [row("t_kto", "def t_kto():\n    return 1", True),
            row("t_kto", "def t_kto():\n    while True: pass", False,
                timed_out=True)]
    kto = T.derive_kto(rows)
    assert len(kto) == 1, f"a timed-out candidate got a KTO label: {kto}"
    assert all("while True" not in r["completion"] for r in kto), kto
    assert kto[0]["label"] is True, kto


def test_kto_still_labels_a_genuine_failure_false():
    """The exclusion must be about TIMEOUTS, not about failures. A candidate
    that ran and got the wrong answer is exactly the negative KTO exists for."""
    rows = [row("t_kto2", "def t_kto2():\n    return 2", False)]
    kto = T.derive_kto(rows)
    assert len(kto) == 1 and kto[0]["label"] is False, kto


# --------------------------------------------------------------------------
# 5. chosen/rejected are executable source, raw emissions travel alongside
# --------------------------------------------------------------------------
def test_dpo_view_emits_executable_chosen_and_rejected():
    """THE DATASET CONTRACT, set by forge.run_task (forge.py:672-683) and relied
    on downstream: verify_dataset.py runs forge.verify on `chosen`/`rejected`,
    clean_dataset.py and both dedup hashes read them as source, and
    train_native.training_target() RE-FENCES them when no `_raw` is present.
    A view that puts fenced text in those fields hands the gates something that
    does not compile and hands the trainer a double-fenced target.
    """
    rows = [row("t_dpo", "def t_dpo():\n    return 1", True),
            row("t_dpo", "def t_dpo():\n    return 2", False)]
    pairs = T.derive_dpo(rows)
    assert len(pairs) == 1, pairs
    p = pairs[0]
    assert not p["chosen"].lstrip().startswith("```"), \
        f"chosen is a fenced emission, not executable source: {p['chosen']!r}"
    assert not p["rejected"].lstrip().startswith("```"), \
        f"rejected is a fenced emission, not executable source: {p['rejected']!r}"
    compile(p["chosen"], "<chosen>", "exec")      # the gates execute this field
    compile(p["rejected"], "<rejected>", "exec")
    assert p["chosen"] == "def t_dpo():\n    return 1", p
    assert p["rejected"] == "def t_dpo():\n    return 2", p


def test_dpo_view_keeps_the_verbatim_emissions():
    """The raw completions are not discarded -- they move to the fields forge
    already writes them to, so training_target() gets the real bytes instead of
    its re-fenced reconstruction."""
    rows = [row("t_dpo2", "def t_dpo2():\n    return 1", True),
            row("t_dpo2", "def t_dpo2():\n    return 2", False)]
    p = T.derive_dpo(rows)[0]
    assert p["chosen_raw"] == "```python\ndef t_dpo2():\n    return 1\n```", p
    assert p["rejected_raw"] == "```python\ndef t_dpo2():\n    return 2\n```", p


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails.append(name)
                print(f"FAIL {name}: {e}")
    print(f"\n{len(fails)} failed")
    raise SystemExit(1 if fails else 0)
