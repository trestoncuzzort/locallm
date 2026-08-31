"""The second domain, checked. Includes the BANNED red witness council #18 asked
for BEFORE anything else was built (section 83, recommended prompt item 1).

Everything here runs in-process against an in-memory SQLite built from the
fixture. No model, no network, no GPU, no repo file written.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from domains.sql import harness, reward, runtime, taskset  # noqa: E402

# ---------------------------------------------------------------------------
# THE RED WITNESS FOR BANNED, asked for before the domain was built.
# ---------------------------------------------------------------------------
SQL_PAYLOADS = [
    "DROP TABLE machines;",
    "ATTACH DATABASE '/etc/passwd' AS p;",
    "PRAGMA temp_store_directory = 'C:/';",
    "DELETE FROM readings;",
    "UPDATE machines SET line = 1;",
]


def test_the_python_safety_filter_blocks_nothing_in_this_domain():
    """forge.BANNED is Python syntax. Off Python it is a silent no-op.

    Read out of forge.py rather than imported, so this test cannot be the thing
    that breaks the no-forge-import rule the next test enforces.
    """
    src = (ROOT / "forge.py").read_text(encoding="utf-8")
    m = re.search(r"BANNED = re\.compile\(\s*(.*?)\s*,\s*re\.IGNORECASE",
                  src, re.DOTALL)
    assert m, "BANNED's definition not found in forge.py"
    pattern = "".join(re.findall(r'r"([^"]*)"', m.group(1)))
    banned = re.compile(pattern, re.IGNORECASE)

    blocked = [p for p in SQL_PAYLOADS if banned.search(p)]
    assert not blocked, (
        f"unexpected: BANNED now blocks {blocked}. If the regex grew SQL "
        f"keywords, this domain's safety story changed and the runtime's "
        f"authorizer docstring needs revisiting.")
    # And the other direction: it refuses text for containing a Python builtin
    # that is not there.
    assert banned.search("SELECT * FROM t WHERE note LIKE '%open(%'"), \
        "the false-positive half of the finding no longer reproduces"


def test_the_authorizer_refuses_what_the_regex_missed():
    """The structural replacement. Same payloads, at the engine, after parsing."""
    rt = runtime.SqliteRuntime()
    admitted = []
    for payload in SQL_PAYLOADS:
        res = rt.run(taskset.PLANT_FIXTURE, payload)
        if res.ok:
            admitted.append(payload)
        else:
            assert res.denied, f"{payload!r} failed but not by the authorizer: {res.error}"
    assert not admitted, f"write/DDL statements executed: {admitted}"


def test_a_denied_statement_cannot_change_the_next_candidate():
    """Isolation, which the code domain got from a subprocess and this one gets
    from rebuilding the database per candidate."""
    rt = runtime.SqliteRuntime()
    rt.run(taskset.PLANT_FIXTURE, "DELETE FROM readings;")
    after = rt.run(taskset.PLANT_FIXTURE, "SELECT COUNT(*) FROM readings")
    assert after.ok and after.rows[0][0] == 15, after


def test_no_module_in_this_domain_imports_forge():
    """The point of the exercise. Two instances cannot discover a seam they
    share, so the prompt contract must be written twice and diffed."""
    offenders = []
    for p in sorted((ROOT / "domains").rglob("*.py")):
        src = p.read_text(encoding="utf-8")
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("import forge") or s.startswith("from forge "):
                offenders.append(f"{p.relative_to(ROOT).as_posix()}: {s}")
    assert not offenders, f"domains/ imports forge: {offenders}"


# ---------------------------------------------------------------------------
# The scalar reward
# ---------------------------------------------------------------------------
def test_the_reward_is_a_float_and_partial_credit_is_real():
    e = [("PUMP-01", 1), ("MIX-01", 2), ("DRY-01", 3)]
    assert reward.score_rows(e, e, ordered=False) == 1.0
    assert reward.score_rows([e[0], e[1]], e, ordered=False) == 2 / 3
    assert reward.score_rows([e[0]], e, ordered=False) == 1 / 3
    assert reward.score_rows([], e, ordered=False) == 0.0
    # ... and it is genuinely between 0 and 1, which forge.Result cannot express
    mid = reward.score_rows([e[0], e[1]], e, ordered=False)
    assert 0.0 < mid < 1.0


def test_padding_the_answer_cannot_raise_the_score():
    """The obvious hack against an overlap metric, closed by the denominator."""
    e = [("A",), ("B",)]
    honest = reward.score_rows([("A",)], e, ordered=False)
    padded = reward.score_rows([("A",), ("X",), ("Y",), ("Z",)], e, ordered=False)
    assert padded < honest, f"padding paid: {padded} >= {honest}"
    assert reward.score_rows(e + [("X",)], e, ordered=False) < 1.0


def test_order_is_task_metadata_not_a_global():
    """SELECT without ORDER BY has undefined row order, so set-vs-sequence
    comparison is a property of the task."""
    e = [(1,), (2,), (3,)]
    shuffled = [(3,), (1,), (2,)]
    assert reward.score_rows(shuffled, e, ordered=False) == 1.0
    assert reward.score_rows(shuffled, e, ordered=True) < 1.0
    ordered_tasks = [t.tid for t in taskset.TASKS if t.ordered]
    assert ordered_tasks == ["sql_top3_hottest"], ordered_tasks


def test_exactly_right_scores_exactly_one():
    v = reward.SqlVerifier()
    for t in taskset.TASKS:
        s = v.score(f"```sql\n{t.reference}\n```", t)
        assert s.exact and s.reward == 1.0, f"{t.tid}: {s}"
        assert s.judgeable


def test_every_reference_query_runs_and_returns_rows():
    """The answer key is derived, so a broken reference is a broken task rather
    than a hard candidate. It has to fail loudly."""
    v = reward.SqlVerifier()
    empty = []
    for t in taskset.TASKS:
        rows = v.answer_key(t)
        if not rows:
            empty.append(t.tid)
    assert not empty, f"tasks whose answer key is the empty set: {empty}"


def test_a_wrong_but_runnable_query_lands_strictly_between_0_and_1():
    """Partial credit has to be reachable by a plausible mistake, not only by a
    hand-built row list."""
    t = taskset.by_tid()["sql_hot_machines"]
    v = reward.SqlVerifier()
    # threshold 85 instead of 90: correct shape, over-inclusive answer
    s = v.score("```sql\nSELECT machine_id, MAX(temp_c) FROM readings "
                "GROUP BY machine_id HAVING MAX(temp_c) > 85\n```", t)
    assert 0.0 < s.reward < 1.0, s
    assert not s.exact


# ---------------------------------------------------------------------------
# Identity, and the fixture in the hash
# ---------------------------------------------------------------------------
def test_the_fixture_is_part_of_the_task_hash():
    t = taskset.TASKS[0]
    moved = taskset.SqlTask(tid=t.tid, prompt=t.prompt, reference=t.reference,
                            fixture=t.fixture.replace("'Feed Pump 1'",
                                                      "'Feed Pump One'"),
                            ordered=t.ordered)
    assert moved.task_sha256 != t.task_sha256, \
        "changing a fixture row left the task's identity unchanged"
    same = taskset.SqlTask(tid=t.tid, prompt=t.prompt, reference=t.reference,
                           fixture=t.fixture, ordered=t.ordered)
    assert same.task_sha256 == t.task_sha256


def test_comparison_mode_is_part_of_the_task_hash():
    t = taskset.TASKS[0]
    flipped = taskset.SqlTask(tid=t.tid, prompt=t.prompt, reference=t.reference,
                              fixture=t.fixture, ordered=not t.ordered)
    assert flipped.task_sha256 != t.task_sha256


def test_task_hashes_are_distinct_and_stable():
    hashes = {t.tid: t.task_sha256 for t in taskset.TASKS}
    assert len(set(hashes.values())) == len(taskset.TASKS), "two tasks collide"
    again = {t.tid: t.task_sha256 for t in taskset.TASKS}
    assert hashes == again


def test_the_runtime_identity_names_no_python_concept():
    """verifier_interpreter() returns {executable, version,
    pinned_away_from_launcher, launcher_version}. None of those exist here."""
    ident = runtime.identity()
    assert set(ident) == {"engine", "version", "fingerprint"}
    assert ident["engine"] == "sqlite3"
    assert len(ident["fingerprint"]) == 64
    assert "executable" not in ident and "launcher_version" not in ident
    # sqlite3.version was removed in Python 3.14; sqlite_version is the library.
    import sqlite3
    assert ident["version"] == sqlite3.sqlite_version


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
def test_extraction_survives_the_noise_chat_models_produce():
    want = "SELECT id, name FROM machines WHERE line = 'A'"
    for reply in (f"```sql\n{want}\n```",
                  f"```\n{want}\n```",
                  f"```\nsql\n{want}\n```",
                  f"Here you go:\n```sql\n{want};\n```\nHope that helps!",
                  f"```sql\n{want};\nDROP TABLE machines;\n```"):
        got = harness.extract_sql(reply)
        assert got == want, f"{reply!r} -> {got!r}"


def test_the_schema_reaches_the_prompt():
    p = harness.user_prompt("anything?", taskset.PLANT_FIXTURE)
    for table in ("machines", "readings", "maintenance"):
        assert f"CREATE TABLE {table}" in p, f"{table} missing from the prompt"


def test_the_trl_signature_is_a_five_line_adapter():
    """The convergence claim from council #18, made testable: everything above
    is written to its own shape, and TRL's signature falls out in five lines."""
    t = taskset.by_tid()["sql_line_a_machines"]
    out = reward.trl_reward_func(
        prompts=[t.prompt, t.prompt],
        completions=[f"```sql\n{t.reference}\n```", "```sql\nSELECT 1\n```"],
        task=[t, t])
    assert isinstance(out, list) and len(out) == 2
    assert all(isinstance(x, float) for x in out), out
    assert out[0] == 1.0 and out[1] < 1.0, out


# ---------------------------------------------------------------------------
# The failure modes that are NOT wrong answers
# ---------------------------------------------------------------------------
def test_a_refused_statement_is_scored_zero_but_stays_judgeable():
    t = taskset.TASKS[0]
    s = reward.SqlVerifier().score("```sql\nDROP TABLE machines\n```", t)
    assert s.reward == 0.0 and s.judgeable and s.denied, s


def test_a_timeout_is_marked_unjudgeable_rather_than_wrong():
    """forge.py:504-511 insists a timeout must never become the `rejected` half
    of a pair; OpenAI's grader contract scores an exception as 0. The two
    conventions disagree, so the flag is carried and the caller decides."""
    t = taskset.TASKS[0]
    v = reward.SqlVerifier(runtime.SqliteRuntime(timeout_s=0.05))
    bomb = ("```sql\nWITH RECURSIVE c(x) AS (SELECT 1 UNION ALL "
            "SELECT x + 1 FROM c) SELECT COUNT(*) FROM c\n```")
    s = v.score(bomb, t)
    assert s.reward == 0.0, s
    assert not s.judgeable, f"a timeout was reported as a judged wrong answer: {s}"


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
