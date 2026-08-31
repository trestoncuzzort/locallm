"""Probe for one bounded class: screen_tasks.py restating superseded decisions.

The class (N=4 as found): sizing figures and provenance status were retyped in
the docstring, the --target default, the completion print, and the --stratum
help text. Four copies, four chances to go stale independently. Section 54
superseded the sizing; council section 59 superseded evol's status.

This is NOT a general staleness scanner. It is a fixed list of the four
superseded strings actually found, plus a check that sizing numbers are defined
in exactly one place. A new site is not caught automatically.
"""
import re, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
SRC = pathlib.Path(__file__).resolve().parents[1] / "screen_tasks.py"
TEXT = SRC.read_text(encoding="utf-8")

SUPERSEDED = {
    "docstring target prose": "the target is ~30 admitted tasks",
    "docstring k=5 sizing":   "~30 at k=5",
    "completion print":       "~30 supports detecting +3%",
    "evol provenance":        "evol is unverified",
    # Section 71 measured the noise floor. The status was carried in TWO places
    # (the SIZING comment and the completion print), which is the same class this
    # file already guards: one superseded claim, two chances to go stale. It is
    # now defined once in NOISE_FLOOR and the banner computes from it.
    "sizing comment status":  "noise floor is UNMEASURED",
    "completion print status": "measure it before trusting",
}

def test_no_superseded_strings():
    hits = {k: v for k, v in SUPERSEDED.items() if v in TEXT}
    assert not hits, f"superseded text still present: {hits}"

def test_target_default_not_hardcoded():
    m = re.search(r'--target".*?default=([^,\)]+)', TEXT, re.S)
    assert m, "--target argument not found"
    assert m.group(1).strip() != "30", "--target still hardcoded to superseded 30"

def test_sizing_defined_once():
    assert TEXT.count("SIZING = {") == 1, "SIZING block must be defined exactly once"


def test_noise_floor_defined_once_and_not_retyped():
    assert TEXT.count("NOISE_FLOOR = {") == 1, \
        "NOISE_FLOOR must be defined exactly once"
    # The measured sd must appear only inside that definition -- if the literal
    # shows up a second time, someone retyped it and the two can now diverge.
    import screen_tasks as st
    lit = f"{st.NOISE_FLOOR['run_level_sd']:.4f}".lstrip("0")
    assert TEXT.count(lit) == 1, (
        f"the measured sd {lit} appears {TEXT.count(lit)} times; it belongs only "
        f"in NOISE_FLOOR, with every other use computed from it")

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
