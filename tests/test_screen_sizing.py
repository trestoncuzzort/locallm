"""Probe for one bounded class: screen_tasks.py restating superseded decisions.

The class (N=4 as found): sizing figures and provenance status were retyped in
the docstring, the --target default, the completion print, and the --stratum
help text. Four copies, four chances to go stale independently. Section 54
superseded the sizing; council section 59 superseded evol's status.

This is NOT a general staleness scanner. It is a fixed list of the four
superseded strings actually found, plus a check that sizing numbers are defined
in exactly one place. A new site is not caught automatically.
"""
import re, pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "screen_tasks.py"
TEXT = SRC.read_text(encoding="utf-8")

SUPERSEDED = {
    "docstring target prose": "the target is ~30 admitted tasks",
    "docstring k=5 sizing":   "~30 at k=5",
    "completion print":       "~30 supports detecting +3%",
    "evol provenance":        "evol is unverified",
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
