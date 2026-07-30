"""Ground truth must not depend on which script called it.

THE CLASS. forge.verify() launched [sys.executable, "-I", path], so the verifier
inherited its interpreter from the caller. screen_tasks.py and build_ruler.py go
through venv_guard and system Python has no pyarrow, so they ALWAYS re-exec under
.venv-train (3.11); eval.py, ruler_noise.py and forge.py are unguarded and run
under system Python (3.14). The screen that admitted the ruler and the eval that
scores it were therefore verifying against different Pythons.

RED WITNESS (section 71): 310 completions banked once and replayed through
verify() under both launchers -- identical code bytes, identical task objects.
    before the pin:  3.14 -> 172/310 (0.5548)   3.11 -> 154/310 (0.4968)
    after the pin:   3.14 -> 154/310            3.11 -> 154/310
18 disagreements, all one way, on 6 of 31 tasks. Cause: PEP 649/749 deferred
annotation evaluation. `def f(x: List[int])` with no import raises NameError at
def time on 3.11 and is harmless on 3.14. Measured consequence: 5 ruler tasks at
0.60-0.80 under 3.11 become dead channels at 1.000 under 3.14, and the count
outside the [0.2,0.8] band goes from 2/31 to 7/31.

WHAT THIS FILE ASSERTS, and what it does not. It is pin-AGNOSTIC on purpose: it
never hard-codes 3.11 as the right answer, because the pin is a decision that may
change. It asserts only that the two launchers reach the SAME verdict and that
the verdict is the pinned interpreter's. Scope: the annotation case is the one
mechanism actually found. Other cross-version semantic differences exist and are
NOT enumerated here -- this is a fixed probe for a known divergence plus a
structural check that the interpreter is no longer inherited, not a general
cross-version compatibility scanner.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import forge  # noqa: E402

VENV_PY = ROOT / ".venv-train" / "Scripts" / "python.exe"

# The decisive case: annotations naming typing generics that were never imported.
# Valid on 3.14 (PEP 649 defers evaluation), NameError at def time on <=3.13.
PROBE_CODE = (
    "def solve(xs: List[int]) -> Tuple[int, int]:\n"
    "    return (min(xs), max(xs))\n"
)
PROBE_TESTS = (
    "def run_tests(_f):\n"
    "    solve = _f\n"
    "    assert solve([3, 1, 2]) == (1, 3)\n"
)

# Run verify() in a child process so the LAUNCHER can be varied. Prints one JSON
# line so the parent does not have to parse prose.
CHILD = (
    "import json, sys; sys.path.insert(0, r'%s'); import forge\n"
    "t = forge.Task('probe', 'p', 'solve', %r)\n"
    "r = forge.verify(%r, t)\n"
    "print(json.dumps({'ok': bool(r.ok), 'launcher': sys.version.split()[0],\n"
    "                  'fp': forge.verifier_fingerprint()}))\n"
) % (ROOT, PROBE_TESTS, PROBE_CODE)


def _run_under(exe):
    p = subprocess.run([str(exe), "-c", CHILD], capture_output=True, text=True,
                       timeout=180, cwd=str(ROOT))
    assert p.returncode == 0, f"child failed under {exe}: {p.stderr[-400:]}"
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_verifier_is_not_the_launching_interpreter():
    """The structural check: the pin exists and points somewhere deliberate."""
    if not VENV_PY.exists():
        print("    (skipped: .venv-train absent, nothing to pin away from)")
        return
    assert forge.VERIFY_PY == str(VENV_PY), \
        f"VERIFY_PY is {forge.VERIFY_PY!r}, expected the pinned {VENV_PY!r}"
    fp = forge.verifier_fingerprint()
    assert fp["version"] != "unknown", "the verifier interpreter did not answer"


def test_both_launchers_reach_the_same_verdict():
    """The class check. This is the assertion that would have caught the bug."""
    if not VENV_PY.exists():
        print("    (skipped: .venv-train absent)")
        return
    a = _run_under(sys.executable)
    b = _run_under(VENV_PY)
    assert a["launcher"] != b["launcher"], \
        f"both children ran the same Python ({a['launcher']}); test is blind"
    assert a["ok"] == b["ok"], (
        f"SAME code, SAME task, different verdict by launcher: "
        f"{a['launcher']}->{a['ok']} vs {b['launcher']}->{b['ok']}")
    assert a["fp"]["executable"] == b["fp"]["executable"], \
        "the two launchers pinned to different verifiers"


def test_the_probe_can_actually_discriminate():
    """Control. If the probe passed on every Python it would prove nothing, so
    confirm the two interpreters really do disagree about the raw snippet when
    each evaluates it directly."""
    if not VENV_PY.exists():
        print("    (skipped: .venv-train absent)")
        return
    snippet = PROBE_CODE + "print('DEFINED_OK')\n"
    outs = {}
    for exe in (sys.executable, VENV_PY):
        p = subprocess.run([str(exe), "-I", "-c", snippet],
                           capture_output=True, text=True, timeout=60)
        outs[str(exe)] = (p.returncode == 0)
    assert len(set(outs.values())) == 2, (
        "the probe does not discriminate between the two interpreters "
        f"({outs}); it can no longer witness the divergence it was written for")


def test_env_override_is_honoured():
    """SRLM_VERIFY_PY must be able to re-pin deliberately, or the pin is a
    hard-coded assumption rather than a decision."""
    child = ("import sys; sys.path.insert(0, r'%s'); import forge; "
             "print(forge.VERIFY_PY)" % ROOT)
    env = dict(os.environ, SRLM_VERIFY_PY=r"C:\some\other\python.exe")
    p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                       text=True, timeout=60, env=env, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr[-300:]
    assert p.stdout.strip() == r"C:\some\other\python.exe", \
        f"override ignored; got {p.stdout.strip()!r}"


def test_eval_records_the_verifier():
    """A number is only comparable if the artifact says what decided it."""
    import eval as ev
    src = pathlib.Path(ev.__file__).read_text(encoding="utf-8")
    assert '"verifier": forge.verifier_fingerprint()' in src, \
        "eval.evaluate must record the verifier fingerprint in its result"


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails.append(name); print(f"FAIL {name}: {e}")
    print(f"\n{len(fails)} failed")
    raise SystemExit(1 if fails else 0)
