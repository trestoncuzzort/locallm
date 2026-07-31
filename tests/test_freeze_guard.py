"""Probe for one defect: build_ruler.cmd_freeze warns about a file that is there.

THE BUG (council #18, section 82 F3). `cmd_freeze` had, at build_ruler.py:277,
`if problems:` ... `raise SystemExit(...)`, then thirteen lines of comment, then
at :295 a bare `else:` printing

    [!] ruler_noise.jsonl absent - freezing without eval-instrument rates.

Python allows comments between an `if` body and its `else`, so that `else` bound
to `if problems:` -- not to any test of whether the file exists. There was no
`if NOISE.exists():` anywhere in the function: the section-77 edit that stripped
sample-dependent figures out of the frozen artifact removed the `if` head and
left the `else` attached to the nearest preceding `if`. The branch therefore ran
exactly when `problems` was EMPTY, i.e. on every SUCCESSFUL freeze, announcing a
missing file while data/ruler_noise.jsonl sat on disk at 209,606 bytes. When the
file really was absent AND there were problems, the SystemExit fired first and
the warning never printed. The condition the message described and the condition
under which it printed were disjoint.

WHY IT SURVIVED: `cmd_freeze` had no test of any kind. Grepping tests/ for
`build_ruler|verify_frozen|cmd_freeze` returned one hit and it was a comment.

These tests assert on the OUTPUT TEXT, not the exit code. Section 80's lesson,
in this channel: "0 failed was never wrong" -- a command that exits 0 while
printing a false statement is exactly what an exit-code check cannot see.

Everything runs against a synthetic ruler in a temp directory. No repo file is
read or written, and data/ruler_frozen.json is never touched.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import build_ruler  # noqa: E402

WARNING_MARK = "absent"


def _tids(side: str, n: int) -> list[str]:
    """Fixture tids that really do hash to the side we need.

    Generated from split_side rather than typed, because cmd_freeze checks the
    hash side itself and a hand-picked tid would fail the check for a reason
    that has nothing to do with what is being tested.
    """
    out, i = [], 0
    while len(out) < n:
        tid = f"fixture_task_{i}"
        if build_ruler.split_side(tid) == side:
            out.append(tid)
        i += 1
    return out


def _build(tmp: pathlib.Path, with_noise: bool) -> dict:
    """A minimal but internally consistent ruler, on disk, in tmp."""
    ruler_tids = _tids("ruler", 2)
    train_tids = _tids("train", 2)

    screen = tmp / "screen_results.jsonl"
    with screen.open("w", encoding="utf-8") as f:
        for tid in ruler_tids + train_tids:
            f.write(json.dumps({
                "tid": tid, "admitted": True, "rate": 0.5,
                "task": {"prompt": f"solve {tid}", "entry": "f",
                         "tests": [f"assert f(1) == 1  # {tid}"]},
            }) + "\n")

    (tmp / "ruler_nominees.json").write_text(json.dumps({
        "ruler_nominees": ruler_tids, "train_reserved": train_tids,
        "band": [0.2, 0.8], "ruler_share": build_ruler.RULER_SHARE,
        "screen_rates": {t: 0.5 for t in ruler_tids},
    }), encoding="utf-8")

    (tmp / "ruler_confirmed.json").write_text(json.dumps({
        "model": "fixture-model", "band": [0.2, 0.8],
        "kept": [{"tid": t, "confirmed_rate": 0.5, "n": 60,
                  "wilson95": [0.38, 0.62]} for t in ruler_tids],
        "dropped": [],
    }), encoding="utf-8")

    noise = tmp / "ruler_noise.jsonl"
    if with_noise:
        noise.write_text(json.dumps({"replicate": 0, "note": "fixture"}) + "\n",
                         encoding="utf-8")

    return {"SCREEN": screen,
            "NOMINEES": tmp / "ruler_nominees.json",
            "RULER": tmp / "ruler_confirmed.json",
            "FROZEN": tmp / "ruler_frozen.json",
            "NOISE": noise}


@contextlib.contextmanager
def _freeze_in(tmp: pathlib.Path, with_noise: bool):
    """Run cmd_freeze against the fixture, yielding (stdout, paths)."""
    paths = _build(tmp, with_noise)
    saved = {k: getattr(build_ruler, k) for k in paths}
    for k, v in paths.items():
        setattr(build_ruler, k, v)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            build_ruler.cmd_freeze(argparse.Namespace(force=False))
        yield buf.getvalue(), paths
    finally:
        for k, v in saved.items():
            setattr(build_ruler, k, v)


def test_a_successful_freeze_does_not_claim_the_noise_file_is_missing():
    """THE RED. ruler_noise.jsonl is present; the freeze succeeds; the warning
    about it being absent must not appear."""
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        with _freeze_in(tmp, with_noise=True) as (out, paths):
            assert paths["NOISE"].exists(), "fixture is wrong: noise file missing"
            assert paths["FROZEN"].is_file(), f"freeze wrote nothing:\n{out}"
            offending = [l for l in out.splitlines() if WARNING_MARK in l]
            assert not offending, (
                "a successful freeze printed a warning that the noise file is "
                f"absent while it exists at {paths['NOISE']}:\n  "
                + "\n  ".join(offending))


def test_the_warning_still_fires_when_the_noise_file_really_is_absent():
    """The other half. Without this, deleting the warning outright would pass
    the test above, and the check would be asserting nothing."""
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        with _freeze_in(tmp, with_noise=False) as (out, paths):
            assert not paths["NOISE"].exists(), "fixture is wrong: noise file present"
            assert any(WARNING_MARK in l for l in out.splitlines()), (
                "the noise file is genuinely absent and nothing said so:\n" + out)


def test_the_freeze_still_produces_a_usable_frozen_ruler():
    """Guard against fixing the branch by breaking the command."""
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        with _freeze_in(tmp, with_noise=True) as (out, paths):
            frozen = json.loads(paths["FROZEN"].read_text(encoding="utf-8"))
    assert frozen["n_ruler"] == 2, frozen["n_ruler"]
    assert len(frozen["ruler_set_sha256"]) == 64
    assert len(frozen["checks_passed"]) == 5
    for tid, rec in frozen["ruler"].items():
        assert build_ruler.split_side(tid) == "ruler"
        assert len(rec["task_sha256"]) == 64
    assert "FROZEN 2 ruler tasks" in out


def test_an_inconsistent_ruler_is_still_refused():
    """The `if problems:` arm the broken `else` was attached to. If a fix
    rewired the branch wrongly, a bad ruler could start freezing silently."""
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        paths = _build(tmp, with_noise=True)
        # Put a ruler tid into the training pool: the disjointness check must fire.
        nom = json.loads(paths["NOMINEES"].read_text(encoding="utf-8"))
        nom["train_reserved"] = nom["train_reserved"] + nom["ruler_nominees"][:1]
        paths["NOMINEES"].write_text(json.dumps(nom), encoding="utf-8")

        saved = {k: getattr(build_ruler, k) for k in paths}
        for k, v in paths.items():
            setattr(build_ruler, k, v)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    build_ruler.cmd_freeze(argparse.Namespace(force=False))
                    raised = None
                except SystemExit as e:
                    raised = str(e)
        finally:
            for k, v in saved.items():
                setattr(build_ruler, k, v)
    assert raised and "refusing to freeze" in raised, \
        f"an overlapping ruler/training pool was frozen anyway (exit={raised})"
    assert "OVERLAP" in buf.getvalue(), buf.getvalue()
    assert not paths["FROZEN"].exists(), "an inconsistent ruler was written to disk"


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
