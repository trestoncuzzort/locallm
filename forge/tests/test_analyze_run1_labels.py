"""tests/test_analyze_run1_labels.py — the greedy-provenance label, and the
numeric tie it used to read as an absence.

analyze_run1.py reports which construction produced each arm's BANKED aggregate:
greedy-free (the sampled draws only), or greedy-anchored (the temp-0 greedy draw
counted as one more draw). The label is DERIVED -- both constructions are
recomputed and compared against the stored number -- so it cannot drift off the
data. But when the two come out equal the stored number cannot say which one
produced it, and the label answered that tie with "greedy-free (no greedy draw
was banked)". The parenthetical is a claim about what is IN the row, and no
comparison of two equal numbers can support it.

THE WITNESS, executed: one row with greedy=True, sampled=[1, 1], aggregate 1.0.
Greedy-free that is (1+1)/2 = 1.0; greedy-anchored it is (1+1+1)/3 = 1.0. The
row plainly banks a greedy draw, and the old label said none was banked.

Presence is a fact about the ROW SHAPE, so it is read from the row shape
(has_greedy_draw). On a tie the stored value is reported as greedy-ANCHORED
whenever a greedy draw exists -- the anchored reading is then true of the number
-- and the claim of absence is made only when no row carries one.

The broken twin is kept here verbatim (test_stats_core.py idiom) and asserted to
STILL mislabel the witness, so a test that stops discriminating is itself a
failure rather than a silent pass.

NOTHING HERE CHANGES A PUBLISHED NUMBER, and the last two tests say why against
the retained bytes rather than asserting it: the two compared arms bank no
greedy draw at all, so their label was true and is now checked; the base arm
banks one on every entry but its aggregate matches only the anchored
construction, so it is discriminated numerically and never reaches the tie.

Run: python tests/test_analyze_run1_labels.py   (self-executing; the runner at
the bottom is the same one every other file in tests/ carries)
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_run1 as A                                          # noqa: E402
from analyze_run1 import BASE, NULL, TRAINED                      # noqa: E402


def _row(greedy, sampled, aggregate, tid="t1"):
    return {"model": "fixture", "aggregate": aggregate,
            "per_task": [{"tid": tid, "greedy": greedy, "sampled": sampled}]}


# 1.0 greedy-free and 1.0 greedy-anchored: the two constructions cannot be told
# apart on this row, and it HAS a banked greedy draw.
WITNESS = [_row(True, [1, 1], 1.0)]
# The same three numbers with no greedy draw -- the one shape for which "no
# greedy draw was banked" is a true thing to say.
NO_GREEDY = [_row(None, [1, 1], 1.0)]


def _stored_construction_numeric_only(rows):
    """The bug, verbatim: the tie answered by asserting the absence."""
    if not rows:
        return "no rows"
    free = all(v is not None and abs(A.rate(r) - v) <= A._TOL
               for r, v in ((r, A.greedy_free_rate(r)) for r in rows))
    anch = all(v is not None and abs(A.rate(r) - v) <= A._TOL
               for r, v in ((r, A.greedy_anchored_rate(r)) for r in rows))
    if free and not anch:
        return "greedy-free"
    if anch and not free:
        return "greedy-ANCHORED"
    if free and anch:
        return "greedy-free (no greedy draw was banked)"
    return "UNRECOGNISED (matches neither construction)"


def test_the_two_constructions_really_do_tie_on_the_witness():
    """The precondition every test below rests on. If these three numbers ever
    stop being equal, the witness has stopped being a witness."""
    r = WITNESS[0]
    assert A.greedy_free_rate(r) == 1.0, A.greedy_free_rate(r)
    assert A.greedy_anchored_rate(r) == 1.0, A.greedy_anchored_rate(r)
    assert A.rate(r) == 1.0, A.rate(r)


def test_a_banked_greedy_draw_is_never_labelled_absent():
    label = A.stored_construction(WITNESS)
    assert "no greedy draw was banked" not in label, label
    assert label.startswith("greedy-ANCHORED"), label
    # The twin must still lie, or this test has stopped testing anything.
    assert _stored_construction_numeric_only(WITNESS) == \
        "greedy-free (no greedy draw was banked)", "twin lost its bug"


def test_presence_is_read_from_the_row_shape_not_from_the_numbers():
    """Identical stored numbers, opposite row shapes. Only something that looks
    at the row can tell these apart, and the twin -- which looks only at the
    numbers -- gives them one answer."""
    assert A.has_greedy_draw(WITNESS) is True
    assert A.has_greedy_draw(NO_GREEDY) is False
    assert A.stored_construction(WITNESS) != A.stored_construction(NO_GREEDY)
    assert _stored_construction_numeric_only(WITNESS) == \
        _stored_construction_numeric_only(NO_GREEDY), "twin lost its bug"


def test_the_absence_claim_survives_where_it_is_true():
    """The fix must not answer the lie by refusing to say anything: where no
    row carries a greedy draw, the label still says so."""
    assert A.stored_construction(NO_GREEDY) == \
        "greedy-free (no greedy draw was banked)"


def test_a_numerically_discriminating_aggregate_still_reads_greedy_free():
    """greedy=False, sampled=[1, 1], aggregate 1.0: free is 1.0, anchored is
    2/3, and the stored number matches only free. Here the number itself says
    the greedy draw was left OUT of the aggregate, so the plain greedy-free
    label stands even though a greedy draw exists -- that label makes no claim
    about presence. Labelling this one ANCHORED would be a new false statement,
    not a fix."""
    rows = [_row(False, [1, 1], 1.0)]
    assert abs(A.greedy_anchored_rate(rows[0]) - 2 / 3) < 1e-12
    assert A.has_greedy_draw(rows) is True
    assert A.stored_construction(rows) == "greedy-free"


def test_a_genuinely_anchored_arm_is_still_labelled_anchored():
    rows = [_row(True, [1, 0], 2 / 3)]
    assert A.stored_construction(rows) == "greedy-ANCHORED"


def test_an_aggregate_matching_neither_construction_is_still_unrecognised():
    rows = [_row(True, [1, 1], 0.25)]
    assert A.stored_construction(rows).startswith("UNRECOGNISED"), \
        A.stored_construction(rows)


def test_the_compared_arms_bank_no_greedy_draw_in_the_retained_data():
    """Why no published number moves: the label on the two compared arms was
    TRUE all along -- it just was not checked. Now it is."""
    by = A.load()
    rows = by[TRAINED] + by[NULL]
    assert len(rows) == 80, len(rows)
    assert A.has_greedy_draw(rows) is False
    assert A.stored_construction(rows) == \
        "greedy-free (no greedy draw was banked)"


def test_the_base_arm_never_reaches_the_tie_branch():
    """It banks a greedy draw on every entry, and its stored aggregate matches
    only the anchored construction -- discriminated by the numbers, so its
    printed label is untouched by this fix."""
    rows = A.load()[BASE]
    assert A.has_greedy_draw(rows) is True
    assert A.stored_construction(rows) == "greedy-ANCHORED"


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails.append(name); print(f"FAIL {name}: {e}")
            except Exception as e:                                # noqa: BLE001
                fails.append(name)
                print(f"FAIL {name}: raised {type(e).__name__}: {e}")
    print(f"\n{len(fails)} failed")
    raise SystemExit(1 if fails else 0)
