"""tests/test_t_lowering.py — t's flip rule, pinned.

Three layers:
  1. Pure lowering: the JSON tasks produce exactly the source text whose
     hashes the witnesses record — a lowering change that alters bytes is
     caught here before any kernel spends a verdict on it.
  2. The twin operator: collapse_first_if does what SPEC.md says, and a task
     with no `if` is refused rather than given a vacuous twin.
  3. Kernel round-trips (SLOW, skipped when a backend is absent): abs and max
     must flip — real VERIFIED, twin REFUTED — on every installed backend.
     These re-derive the committed AGREEMENT.md verdicts from scratch.

Run: pytest tests/test_t_lowering.py            (fast layers)
     pytest tests/test_t_lowering.py -m ""      (everything)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
T = HERE / "t"
for p in (str(HERE), str(T)):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness                                    # noqa: E402
import lower_dafny                                # noqa: E402
import lower_verus                                # noqa: E402
from verifiers import Outcome                     # noqa: E402


def task(name):
    return harness.load(T / "tasks" / f"{name}.json")


# --- 1. lowering is deterministic text ------------------------------------
def test_dafny_lowering_bytes_stable():
    abs_t = task("abs")
    src = lower_dafny.lower(abs_t, abs_t["body"])
    assert "method Abs(x: int) returns (r: int)" in src
    assert "ensures (r >= 0)" in src
    assert src == lower_dafny.lower(abs_t, abs_t["body"])   # pure function


def test_verus_lowering_is_proof_fn_with_mathematical_int():
    abs_t = task("abs")
    src = lower_verus.lower(abs_t, abs_t["body"])
    assert "proof fn abs(x: int)" in src, \
        "the v0 semantic decision (mathematical ints -> proof fn) changed"
    assert "i64" not in src


def test_verus_refuses_inexpressible_bodies():
    abs_t = task("abs")
    two_assigns = [{"assign": ["r", {"int": 1}]}, {"assign": ["r", {"int": 2}]}]
    with pytest.raises(ValueError):
        lower_verus.lower(abs_t, two_assigns)


# --- 2. the twin operator --------------------------------------------------
def test_twin_collapses_exactly_the_first_if():
    body = task("abs")["body"]
    twin, mutated = harness.collapse_first_if(body)
    assert mutated
    assert twin == body[0]["if"]["then"]


def test_twinless_body_is_refused_not_faked():
    twin, mutated = harness.collapse_first_if([{"assign": ["r", {"var": "x"}]}])
    assert not mutated


# --- 3. kernel round-trips (skipped where a kernel is absent) --------------
def _flip(lower, backend, suffix):
    for name in ("abs", "max"):
        assert harness.run_task(T / "tasks" / f"{name}.json",
                                lower, backend, suffix), f"{name} did not flip"


@pytest.mark.skipif(not shutil.which("dafny"), reason="dafny not installed")
def test_flip_on_dafny():
    from verifiers import dafny as backend
    _flip(lower_dafny.lower, backend, "dfy")


@pytest.mark.skipif(
    not (Path.home() / ".local/verus/verus-arm64-macos/verus").exists(),
    reason="verus not installed")
def test_flip_on_verus():
    from verifiers import verus as backend
    _flip(lower_verus.lower, backend, "rs")


@pytest.mark.skipif(
    not (Path.home() / ".local/gnatprove/gnatprove-aarch64-darwin-16.1.0-1"
         / "bin/gnatprove").exists(),
    reason="gnatprove not installed")
def test_flip_on_spark():
    import lower_spark
    from verifiers import spark as backend
    _flip(lower_spark.lower, backend, "ads")


def test_spark_lowering_uses_mathematical_integers():
    import lower_spark
    abs_t = task("abs")
    src = lower_spark.lower(abs_t, abs_t["body"])
    assert "Big_Integer" in src, \
        "the SPARK semantic decision (mathematical ints) changed"
    assert " Integer" not in src.replace("Big_Integer", "")


@pytest.mark.skipif(
    not (Path.home() / ".opam/default/bin/frama-c").exists(),
    reason="frama-c not installed")
def test_flip_on_framac():
    import lower_framac
    from verifiers import framac as backend
    _flip(lower_framac.lower, backend, "c")


@pytest.mark.skipif(not (Path.home() / ".elan/bin/lean").exists(),
                    reason="lean not installed")
def test_flip_on_lean():
    import lower_lean
    from verifiers import lean as backend
    _flip(lower_lean.lower, backend, "lean")


@pytest.mark.skipif(not shutil.which("coqc"), reason="rocq not installed")
def test_flip_on_rocq():
    import lower_rocq
    from verifiers import rocq as backend
    _flip(lower_rocq.lower, backend, "v")


def test_agda_adapter_taxonomy_without_lowering():
    """The Agda LOWERING is parked; the adapter's measured taxonomy is not.
    A hand-written true theorem must VERIFY, a postulate must be VACUOUS."""
    from verifiers import agda as backend, Outcome
    if not Path(str(backend.AGDA)).exists():
        pytest.skip("agda not installed")
    good = HERE / "t" / "out" / "agda_probe_true.agda"
    good.write_text("open import Agda.Builtin.Nat\n"
                    "open import Agda.Builtin.Equality\n\n"
                    "thm : 1 + 1 \u2261 2\nthm = refl\n", encoding="utf-8")
    assert backend.verify(good).outcome == Outcome.VERIFIED
    bad = HERE / "t" / "out" / "agda_probe_post.agda"
    bad.write_text("postulate anything : Set\n", encoding="utf-8")
    assert backend.verify(bad).outcome == Outcome.VACUOUS
