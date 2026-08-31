"""The install check, tested without pretending to be a different computer.

What is checkable here is the LOGIC and the CONTRACT: that it degrades instead of
crashing when something is missing, that it writes the schema the studio reads,
and that it reuses the one timing implementation rather than growing a second.
Whether the numbers are right on a machine that is not this one is not something
a test can answer, and this file does not claim to.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_my_computer as chk  # noqa: E402


def test_it_reuses_the_one_timing_implementation():
    """A second copy of "how fast is a step" would drift from bench_device's.

    The whole file is read rather than the import checked, because the failure
    this guards against is someone pasting the timing loop in rather than
    importing it - which no import check would catch.
    """
    src = (HERE / "check_my_computer.py").read_text(encoding="utf-8")
    assert "import bench_device" in src
    assert "bench_device.time_steps(" in src, "it no longer calls the shared timer"
    for copied in ("loss.backward()", "opt.zero_grad(", "clip_grad_norm_"):
        assert copied not in src, \
            f"the training step was copied in ({copied!r}); import it instead"


def test_it_does_not_need_a_corpus_to_run():
    """A fresh install has no corpus.txt. bench_device.py reads one by default,
    which is exactly why this cannot simply be that script."""
    src = (HERE / "check_my_computer.py").read_text(encoding="utf-8")
    assert "SYNTHETIC" in src
    assert "corpus.txt" not in src.split('"""', 2)[2], \
        "the measurement path depends on a corpus file"
    assert len(chk.SYNTHETIC) > 5000, "synthetic text too small to fill batches"


def test_torch_is_imported_late_so_a_missing_install_can_be_reported():
    """If torch were imported at module scope, the machine that most needs a
    clear answer - the one where it is not installed - would get a traceback."""
    src = (HERE / "check_my_computer.py").read_text(encoding="utf-8")
    head = src.split("def main(")[0]
    # Match an actual import STATEMENT, not the words. The first version of this
    # check searched for the substring "import torch" and fired on the file's own
    # docstring explaining why torch is imported late - a scanner tripping over
    # prose about itself, which verify_claims.py already learned the hard way.
    import re
    early = [ln for ln in head.splitlines()
             if re.match(r"\s*(?:import torch\b|from torch\b)", ln)]
    assert not early, \
        f"torch is imported before main(); a missing install will traceback: {early}"
    assert "pip install torch" in src, "no instruction for the missing case"


def test_it_writes_the_schema_the_studio_reads():
    """studio.load_speeds() indexes results by f'{device}/{size}' and reads
    ms_per_step. A different shape here silently disables the studio's time
    estimates rather than failing loudly."""
    try:
        import studio
        import bench_device
    except ImportError:
        return        # no torch on this interpreter; the schema cannot be read
    result = HERE / "bench_device_result.json"
    if not result.exists():
        return                      # nothing measured on this machine yet
    d = json.loads(result.read_text(encoding="utf-8"))
    assert "results" in d
    speeds = studio.load_speeds()
    assert speeds, "the studio could not read the file this writes"
    for name, _ in bench_device.SIZES:
        assert any(k.endswith(f"/{name}") for k in speeds), \
            f"no entry for size {name}"
    for k, v in d["results"].items():
        assert isinstance(v["ms_per_step"], (int, float))
        assert "measured_over_steps" in v, \
            f"{k} does not record how many steps it averaged over"


def test_the_verdict_is_in_plain_words():
    src = (HERE / "check_my_computer.py").read_text(encoding="utf-8")
    for jargon in ("ms/step", "tok/s", "n_embd", "block_size", "perplexity"):
        assert jargon not in src.split("def main(")[1], \
            f"the user-facing output uses {jargon!r}"


def test_human_time_reads_like_a_person_wrote_it():
    assert chk.human(45) == "45 seconds"
    assert chk.human(300) == "5 minutes"
    assert "hours" in chk.human(7200)


def test_it_exits_nonzero_and_explains_when_torch_is_missing():
    """Run it for real under an interpreter that has no torch. This is the whole
    reason the file exists, so it is checked by running it, not by reading it."""
    probe = subprocess.run(
        [sys.executable, "-c", "import torch"],
        capture_output=True, text=True)
    if probe.returncode == 0:
        return          # this interpreter HAS torch; the path cannot be exercised
    r = subprocess.run([sys.executable, str(HERE / "check_my_computer.py")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1, r.returncode
    assert "pip install torch" in r.stdout, r.stdout[-400:]
    assert "Traceback" not in r.stdout + r.stderr, "it crashed instead of explaining"


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
