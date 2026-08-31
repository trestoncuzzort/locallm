"""tests/test_stats_core.py — the published numbers, pinned to the code.

Three layers, each with a reason:

  1. Known t-distribution values — the same self-checks analyze_run1.py has
     always run, so the extraction cannot have changed the machinery.
  2. THE PUBLISHED TABLE 1 AND TOST VALUES, recomputed from the retained rows
     in data/ruler_noise.jsonl. Until stats_core.py existed, the paper's three
     equivalence p-values (.0024 / .0433 / .295) and its 90% interval
     [-0.84, +1.94] pp were hand-derived — reproducible by no code in this
     repository. Now they are asserted to the digit. If the data or the code
     drifts, this file says so before the paper does.
  3. A DELIBERATELY BROKEN TOST kept in this file (test_detectors.py idiom):
     p = min(p_lower, p_upper) instead of max. That is a real bug seen in the
     wild — equivalence declared from one side only — and at the ±1.00 pp
     margin it DECLARES equivalence (p = .034) where the correct test does not
     (p = .295). A test both versions pass is not testing anything; this pair
     cannot both pass.

Run: pytest tests/test_stats_core.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from analyze_run1 import BASE, NULL, TRAINED, load, rate          # noqa: E402
from stats_core import certify, t_crit, t_sf, tost, welch          # noqa: E402


def _arms():
    by = load()
    return ([rate(r) for r in by[TRAINED]], [rate(r) for r in by[NULL]])


# --- 1. machinery ---------------------------------------------------------
def test_t_distribution_known_values():
    assert abs(t_crit(10) - 2.228) < 0.002
    assert abs(t_crit(78) - 1.991) < 0.003
    assert abs(2 * t_sf(2.0, 30) - 0.0546) < 0.001
    # 90% two-sided critical value, used by the TOST interval
    assert abs(t_crit(74, alpha=0.10) - 1.6657) < 0.002


# --- 2. the published numbers, from the retained bytes --------------------
def test_table1_primary_comparison_reproduces():
    tr, nu = _arms()
    assert len(tr) == 40 and len(nu) == 40, "prereg N drifted"
    w = welch(tr, nu)
    assert abs(w["t"] - 0.656) < 0.0005, w["t"]
    assert abs(w["df"] - 74.0) < 0.05, w["df"]
    assert abs(w["p"] - 0.5140) < 0.00005, w["p"]
    assert abs(w["diff"] * 100 - 0.55) < 0.005, w["diff"]
    assert abs(w["ci"][0] * 100 - -1.12) < 0.005
    assert abs(w["ci"][1] * 100 - 2.21) < 0.005


def test_published_tost_values_reproduce():
    tr, nu = _arms()
    # preregistered margin +-2.98 pp -> p = .0024
    assert abs(tost(tr, nu, 0.0298)["p"] - 0.0024) < 0.00005
    # +-2.00 pp -> p = .0433 (the abstract's "rejected +-2 pp or larger")
    assert abs(tost(tr, nu, 0.0200)["p"] - 0.0433) < 0.00005
    # +-1.00 pp -> p = .295 ("simply not resolved at this n")
    assert abs(tost(tr, nu, 0.0100)["p"] - 0.295) < 0.0005
    # the 90% TOST interval, [-0.84, +1.94] pp
    lo, hi = tost(tr, nu, 0.0200)["ci90"]
    assert abs(lo * 100 - -0.84) < 0.005
    assert abs(hi * 100 - 1.94) < 0.005


def test_tost_decisions_match_the_paper():
    tr, nu = _arms()
    assert tost(tr, nu, 0.0298)["equivalent"] is True
    assert tost(tr, nu, 0.0200)["equivalent"] is True
    assert tost(tr, nu, 0.0100)["equivalent"] is False


# --- 3. the broken twin ---------------------------------------------------
def _tost_broken_min(a, b, margin):
    """The bug: min() of the one-sided p-values. Kept so the tests can prove
    they distinguish it from the correct max()."""
    r = tost(a, b, margin)
    return {"p": min(r["p_lower"], r["p_upper"]),
            "equivalent": min(r["p_lower"], r["p_upper"]) < 0.05}


def test_broken_min_tost_fails_where_correct_does_not():
    tr, nu = _arms()
    correct = tost(tr, nu, 0.0100)
    broken = _tost_broken_min(tr, nu, 0.0100)
    # The broken version declares equivalence at +-1 pp; the correct one must not.
    assert broken["equivalent"] is True, "twin lost its bug; the test is dead"
    assert correct["equivalent"] is False
    assert broken["p"] < 0.05 < correct["p"]


# --- Monte Carlo, small run so the suite stays fast -----------------------
def test_certificate_holds_alpha():
    c = certify(sims=2000, verbose=False)
    assert 0.03 < c["welch_fpr_equal_var"] < 0.07
    assert 0.03 < c["welch_fpr_unequal_var"] < 0.07
    assert c["tost_fpr_at_margin"] < 0.07
