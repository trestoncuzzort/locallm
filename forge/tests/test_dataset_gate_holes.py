"""tests/test_dataset_gate_holes.py — four ways the data gate said PASS.

verify_dataset.py is the mechanism behind "every training pair was executed and
checked". These are the inputs on which it said so without having checked.

  1. SIGNATURE COLLISION. signature() concatenated prompt + chosen + rejected +
     tid with no delimiter and hashed the result. Concatenation is not
     injective: {"prompt": "ab", "chosen": "c"} and {"prompt": "a",
     "chosen": "bc"} build the same string, so two DIFFERENT pairs got the same
     identity. load_pairs() keeps the first and lets every later file inherit
     its verdict, so the second pair was never executed and still counted as
     verified. The fix hashes a canonical JSON object of the four named fields,
     where the field boundaries survive.
  2. A MALFORMED LINE WAS SKIPPED IN SILENCE. `except json.JSONDecodeError:
     continue`. A truncated write, a half-flushed append, a hand-edit -- the
     row vanished from the count, and the gate reported PASS over the rows it
     could still parse. A file the gate cannot read is not a file the gate has
     cleared.
  3. NO PARTITION CHECK. Nothing asserted that a training pair belongs to the
     training side of the frozen split. A pair labelled with one of the 31
     frozen RULER task ids -- the eval set -- would have been executed,
     verified, and passed, because "chosen passes and rejected fails" is true
     of a contaminating pair too. The gate's own subject matter is which pairs
     may be trained on, so this one it has to answer.
  4. A FILE WITH NOTHING IN IT PASSED AFFIRMATIVELY. Every count the gate
     reports is a count OVER the rows it parsed, so a file truncated to zero
     length -- or left holding only blank lines -- came out zero on all of
     them and the report said "PASS: 0/0 pairs valid" with exit 0. The receipt
     entry, {"pairs": 0, "violations": 0}, is the exact shape
     require_verified() grants permission on, so training then started on it.
     A present pair file with no parseable row is now a violation of its own.

Each test keeps the broken twin beside it (test_stats_core.py idiom) and
asserts the twin STILL misbehaves, so a test that stops discriminating is
itself a failure rather than a silent pass.

THE PIN. Importing verify_dataset pulls in dataset_gate, which SystemExits when
neither .venv-train nor SRLM_VERIFY_PY resolves. Declared here through the
module's own documented override, and only when the operator has not already
chosen -- the same path tests/test_replicate_provenance.py takes, for the same
reason. Nothing here executes a candidate, so the interpreter's identity does
not enter any assertion.

NOTHING HERE WRITES A RECEIPT. main() is never called: every test drives
load_pairs() or partition_violations() against fixtures in a temp directory, or
reads the committed pairs without verifying them. Receipt regeneration is the
maintainer's explicit decision (docs/UBUNTU-BOOTSTRAP.md, step 6).

Run: python tests/test_dataset_gate_holes.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_VENV_PY = ROOT / ".venv-train" / "Scripts" / "python.exe"
if not os.environ.get("SRLM_VERIFY_PY") and not _VENV_PY.exists():
    os.environ["SRLM_VERIFY_PY"] = sys.executable   # see THE PIN, above

import forge                                                      # noqa: E402
import verify_dataset as V                                        # noqa: E402

# The two pairs the audit executed. Same rejected, same tid; the prompt/chosen
# split is the only difference, and concatenation erases exactly that.
PAIR_A = {"prompt": "ab", "chosen": "c", "rejected": "r", "meta": {"tid": "t"}}
PAIR_B = {"prompt": "a", "chosen": "bc", "rejected": "r", "meta": {"tid": "t"}}


def _signature_concat_sha1(d):
    """The bug, verbatim: four fields glued together with no separator."""
    tid = (d.get("meta") or {}).get("tid") or ""
    return hashlib.sha1(
        (d.get("prompt", "") + d.get("chosen", "") +
         d.get("rejected", "") + tid).encode("utf-8")).hexdigest()


def _fixture(*lines: str) -> pathlib.Path:
    """A DATA directory holding one dpo_pairs.jsonl of exactly these lines."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="test_gate_holes_"))
    (d / "dpo_pairs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def _fixture_bytes(body: str) -> pathlib.Path:
    """A DATA directory whose dpo_pairs.jsonl is EXACTLY these bytes. _fixture()
    always terminates the file with a newline, and a zero-length file is one of
    the two shapes under test here."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="test_gate_holes_"))
    (d / "dpo_pairs.jsonl").write_text(body, encoding="utf-8", newline="")
    return d


def _load_from(data_dir):
    saved = V.DATA
    try:
        V.DATA = data_dir
        return V.load_pairs()
    finally:
        V.DATA = saved


# --- 1. signature ---------------------------------------------------------
def test_signature_separates_the_documented_collision_pair():
    assert V.signature(PAIR_A) != V.signature(PAIR_B), (
        "two different pairs share one identity; the second is never executed "
        "and inherits the first one's verdict")
    # The twin must still collide, or this test has stopped testing anything.
    assert _signature_concat_sha1(PAIR_A) == _signature_concat_sha1(PAIR_B), \
        "twin lost its bug; the test is dead"


def test_signature_still_depends_on_all_four_fields():
    base = dict(PAIR_A)
    for field, value in (("prompt", "zz"), ("chosen", "zz"), ("rejected", "zz")):
        assert V.signature(dict(base, **{field: value})) != V.signature(base), \
            f"{field} does not enter the signature"
    assert V.signature(dict(base, meta={"tid": "other"})) != V.signature(base), \
        "tid does not enter the signature"


def test_signature_is_stable_across_key_order_and_extra_keys():
    """Only the four named fields may decide identity: a pair carrying extra
    metadata is the same pair, and dict order is not content."""
    reordered = {"meta": {"tid": "t"}, "rejected": "r", "chosen": "c",
                 "prompt": "ab", "score": 0.5, "round": 3}
    assert V.signature(reordered) == V.signature(PAIR_A)


# --- 2. malformed lines ---------------------------------------------------
def test_a_malformed_line_is_reported_with_file_and_line():
    good = json.dumps(PAIR_A)
    data = _fixture(good, "{not json at all", json.dumps(PAIR_B))
    out = _load_from(data)
    assert len(out) == 3, (
        "load_pairs() still returns only (unique, rows_by_file); a malformed "
        "line has nowhere to be reported")
    unique, rows_by_file, malformed = out
    assert len(malformed) == 1, f"malformed lines not surfaced: {malformed}"
    m = malformed[0]
    assert m["file"] == "dpo_pairs.jsonl", m
    assert m["line"] == 2, f"wrong line number reported: {m}"
    assert not m["ok"] and "json" in m["why"].lower(), m
    # `why` is the stable class (so the type histogram groups); the file and
    # line are carried in `detail` as well as in the fields above.
    assert m["detail"].startswith("dpo_pairs.jsonl:2:"), m
    # the parseable rows are still loaded -- the gate reports, it does not bail
    assert len(unique) == 2, unique
    assert len(rows_by_file["dpo_pairs.jsonl"]) == 2, rows_by_file


def test_a_trailing_blank_line_is_not_a_violation():
    """A file that ends with a newline is not malformed, and calling it that
    would make the gate cry wolf on every well-formed file."""
    data = _fixture(json.dumps(PAIR_A), "", "")
    _, _, malformed = _load_from(data)
    assert malformed == [], malformed


def test_the_committed_pair_files_have_no_malformed_lines():
    """States what the retained bytes actually are, so the fix is known to be
    a new fence rather than a change of verdict on the current data."""
    _, _, malformed = V.load_pairs()
    assert malformed == [], malformed


# --- 3. the frozen split --------------------------------------------------
def test_a_frozen_ruler_tid_in_training_data_is_fatal():
    ruler, _pool = V.load_partition()
    assert len(ruler) == 31, f"the frozen ruler is not 31 tasks: {len(ruler)}"
    contaminating = dict(PAIR_A, meta={"tid": sorted(ruler)[0]})
    bad = V.partition_violations([dict(contaminating, _src="forge", _row=0,
                                       _file="dpo_pairs.jsonl")])
    assert len(bad) == 1, bad
    assert bad[0]["why"] == "ruler_task_in_training_data", bad
    assert not bad[0]["ok"]


def test_a_tid_outside_the_training_pool_is_fatal():
    stray = dict(PAIR_A, meta={"tid": "ace_oss_definitely_not_screened"})
    bad = V.partition_violations([dict(stray, _src="forge", _row=7,
                                       _file="dpo_pairs.jsonl")])
    assert len(bad) == 1, bad
    assert bad[0]["why"] == "tid_outside_training_pool", bad
    assert bad[0]["row"] == 7, bad


def test_a_seed_task_is_allowed_outside_the_pool():
    """SEED_TASKS predate the frozen split and are neither ruler nor pool.
    They are hand-written and were never eval material; refusing them would
    reject the pairs the project started from."""
    seed = sorted(t.tid for t in forge.SEED_TASKS)[0]
    ok = dict(PAIR_A, meta={"tid": seed}, _src="forge", _row=0,
              _file="dpo_pairs.jsonl")
    assert V.partition_violations([ok]) == []


def test_the_ruler_and_the_training_pool_do_not_overlap():
    """The precondition the check rests on. If these two sets ever intersect,
    'in the pool' and 'in the ruler' stop being a decision."""
    ruler, pool = V.load_partition()
    assert not (ruler & pool), sorted(ruler & pool)


def test_the_committed_pairs_are_all_on_the_training_side():
    """The retained data passes the new check -- so it is a fence against the
    next generation run, not a re-verdict on this one."""
    unique, _, _ = V.load_pairs()
    bad = V.partition_violations(list(unique.values()))
    assert bad == [], bad[:5]


# --- 4. a file with nothing verifiable in it ------------------------------
def test_an_empty_pair_file_is_a_violation():
    unique, rows_by_file, malformed = _load_from(_fixture_bytes(""))
    bad = V.empty_file_violations(rows_by_file)
    assert len(bad) == 1, bad
    assert bad[0]["file"] == "dpo_pairs.jsonl", bad
    assert bad[0]["why"] == "no_verifiable_rows", bad
    assert not bad[0]["ok"], bad
    # THE TWIN, in the only form this defect has one: every OTHER signal the
    # gate owns is silent on this file, which is exactly why it used to pass
    # with a clean receipt. If any of them ever starts firing here, this test
    # has stopped being the thing that catches an empty file.
    assert rows_by_file == {"dpo_pairs.jsonl": []}, rows_by_file
    assert unique == {}, unique
    assert malformed == [], malformed
    assert V.partition_violations(list(unique.values())) == []


def test_a_blank_lines_only_pair_file_is_a_violation():
    """A file of newlines is not malformed -- blank lines are legal and there
    is a test above saying so -- so the malformed check cannot be what catches
    this one."""
    _, rows_by_file, malformed = _load_from(_fixture_bytes("\n\n   \n\t\n"))
    assert malformed == [], malformed
    assert [v["why"] for v in V.empty_file_violations(rows_by_file)] == \
        ["no_verifiable_rows"], rows_by_file


def test_a_file_with_a_parseable_row_is_not_flagged_as_empty():
    """The cry-wolf side. One row is something to certify, and a trailing
    blank line does not take it away."""
    _, rows_by_file, _ = _load_from(_fixture(json.dumps(PAIR_A), ""))
    assert V.empty_file_violations(rows_by_file) == []


def test_a_file_of_only_malformed_lines_is_reported_both_ways():
    """Two different true statements about one file: WHICH lines could not be
    read, and that the file as a whole certified nothing. Neither implies the
    other -- an empty file has no malformed line at all."""
    _, rows_by_file, malformed = _load_from(_fixture("{oops", "also not json"))
    assert len(malformed) == 2, malformed
    assert len(V.empty_file_violations(rows_by_file)) == 1, rows_by_file


def test_the_committed_pair_files_all_have_parseable_rows():
    """States what the retained bytes are, so the new check is known to be a
    fence rather than a change of verdict on the current data.

    The row COUNTS are deliberately not pinned -- a generation run is allowed
    to change them, and a test that failed on that would be crying wolf about
    the wrong thing. What is pinned is that all three named files are present
    and none of them is empty, which is the property this class is about."""
    _, rows_by_file, _ = V.load_pairs()
    assert sorted(rows_by_file) == sorted(V.FILES), rows_by_file
    assert V.empty_file_violations(rows_by_file) == []
    assert all(sl for sl in rows_by_file.values()), \
        {n: len(sl) for n, sl in rows_by_file.items()}


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
