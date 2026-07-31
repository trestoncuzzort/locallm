"""TASKSET — what the work is. Prompts, ground truth, and task identity.

THE FIXTURE IS PART OF THE TASK, NOT PART OF THE ENVIRONMENT. In the Python
domain a task is (prompt, entry, tests) and that is the whole of it: the tests
carry their own inputs. A SQL task cannot: "which machines ran hot last week" has
no meaning without the rows. So the task's ground truth is a function of the
fixture's bytes, and the fixture's sha256 goes INTO task_sha256 alongside the
prompt.

That is the first thing this domain broke. `forge.Task` has nowhere to put a
resource, and neither does veRL's `compute_score(data_source, solution_str,
ground_truth, extra_info)`. Prime Intellect's v1 runtime API is
`run` PLUS `read`/`write` precisely because tasks own files; the Python domain
never needed `write`, so nothing in forge.py knows a task can have resources.

GROUND TRUTH IS DERIVED, AND THAT MAKES THE ENGINE PART OF IT. The expected rows
are not typed out here -- they are produced by executing a REFERENCE query
against the fixture. Typing them would be a second source of truth that goes
stale the moment a fixture row changes. The consequence is the interpreter-pin
lesson (section 71) arriving in a new domain: the answer key is a function of
reference_sql x fixture x ENGINE VERSION, so the engine has to be in the receipt
or two runs are not comparable. See runtime.identity().

ORDER IS TASK METADATA, NOT A GLOBAL. `SELECT` without `ORDER BY` returns rows in
an order SQLite does not promise. So "compare the rows" is under-specified until
the task says which comparison it means, and `ordered` is a per-task field. The
Python domain never had to say this because an assert either passes or does not.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# The fixture. One plant, three tables, small enough to read in full and big
# enough that a wrong join is visible in the row counts.
#
# Deliberately NOT generated randomly: the fixture's bytes are part of every
# task's identity, so it has to be stable across processes and machines. A
# seeded generator would still be a second thing to keep in sync.
# ---------------------------------------------------------------------------
PLANT_FIXTURE = """
CREATE TABLE machines (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    line    TEXT NOT NULL
);
CREATE TABLE readings (
    id         INTEGER PRIMARY KEY,
    machine_id TEXT NOT NULL REFERENCES machines(id),
    ts         TEXT NOT NULL,
    temp_c     REAL NOT NULL,
    status     TEXT NOT NULL
);
CREATE TABLE maintenance (
    id         INTEGER PRIMARY KEY,
    machine_id TEXT NOT NULL REFERENCES machines(id),
    ts         TEXT NOT NULL,
    kind       TEXT NOT NULL,
    hours      REAL NOT NULL
);

INSERT INTO machines (id, name, line) VALUES
    ('PUMP-01',  'Feed Pump 1',      'A'),
    ('PUMP-02',  'Feed Pump 2',      'A'),
    ('MIX-01',   'Mixer 1',          'A'),
    ('DRY-01',   'Dryer 1',          'B'),
    ('DRY-02',   'Dryer 2',          'B'),
    ('PACK-01',  'Packer 1',         'C');

INSERT INTO readings (id, machine_id, ts, temp_c, status) VALUES
    (1,  'PUMP-01', '2026-07-20 08:00', 71.2, 'OK'),
    (2,  'PUMP-01', '2026-07-20 09:00', 88.4, 'ALARM'),
    (3,  'PUMP-01', '2026-07-20 10:00', 91.0, 'ALARM'),
    (4,  'PUMP-01', '2026-07-20 11:00', 69.5, 'OK'),
    (5,  'PUMP-02', '2026-07-20 08:00', 64.0, 'OK'),
    (6,  'PUMP-02', '2026-07-20 09:00', 66.3, 'OK'),
    (7,  'MIX-01',  '2026-07-20 08:00', 55.1, 'OK'),
    (8,  'MIX-01',  '2026-07-20 09:00', 86.7, 'ALARM'),
    (9,  'MIX-01',  '2026-07-20 10:00', 58.2, 'OK'),
    (10, 'DRY-01',  '2026-07-20 08:00', 102.4, 'ALARM'),
    (11, 'DRY-01',  '2026-07-20 09:00', 104.9, 'ALARM'),
    (12, 'DRY-01',  '2026-07-20 10:00', 99.8, 'OK'),
    (13, 'DRY-02',  '2026-07-20 08:00', 95.0, 'OK'),
    (14, 'DRY-02',  '2026-07-20 09:00', 97.6, 'OK'),
    (15, 'PACK-01', '2026-07-20 08:00', 41.0, 'OK');

INSERT INTO maintenance (id, machine_id, ts, kind, hours) VALUES
    (1, 'PUMP-01', '2026-07-18', 'seal',     2.5),
    (2, 'PUMP-01', '2026-07-21', 'bearing',  4.0),
    (3, 'MIX-01',  '2026-07-19', 'blade',    1.5),
    (4, 'DRY-01',  '2026-07-15', 'element',  6.0),
    (5, 'DRY-01',  '2026-07-22', 'thermo',   3.0);
"""


def sha256(*parts: str) -> str:
    """Same construction as build_ruler.sha: NUL-separated so ('ab','c') and
    ('a','bc') cannot collide."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


@dataclass(frozen=True)
class SqlTask:
    tid: str
    prompt: str                 # what the model is asked for, in plain words
    reference: str              # the answer key, as a query -- never as rows
    fixture: str = PLANT_FIXTURE
    ordered: bool = False       # does row ORDER count? (per-task, see docstring)
    note: str = ""              # what this task is meant to exercise

    @property
    def fixture_sha256(self) -> str:
        return sha256(self.fixture)

    @property
    def task_sha256(self) -> str:
        """Identity = prompt x answer key x FIXTURE x comparison mode.

        Every one of those changes the correct answer, so every one of them is
        in the hash. Note what is NOT here: no field names a SQL concept, so the
        same construction works for the Python domain and for the next one.
        """
        return sha256(self.prompt, self.reference, self.fixture_sha256,
                      "ordered" if self.ordered else "unordered")


TASKS: list[SqlTask] = [
    SqlTask(
        tid="sql_line_a_machines",
        prompt="List the id and name of every machine on production line A.",
        reference="SELECT id, name FROM machines WHERE line = 'A'",
        note="single table, WHERE",
    ),
    SqlTask(
        tid="sql_readings_per_machine",
        prompt="For each machine id, how many readings are recorded? "
               "Return the machine id and the count.",
        reference="SELECT machine_id, COUNT(*) FROM readings GROUP BY machine_id",
        note="GROUP BY, COUNT",
    ),
    SqlTask(
        tid="sql_hot_machines",
        prompt="Which machines recorded a temperature above 90 degrees at any "
               "point? Return the machine id and its highest recorded "
               "temperature.",
        reference="SELECT machine_id, MAX(temp_c) FROM readings "
                  "GROUP BY machine_id HAVING MAX(temp_c) > 90",
        note="GROUP BY with HAVING on an aggregate",
    ),
    SqlTask(
        tid="sql_never_maintained",
        prompt="Which machines have no maintenance records at all? Return the "
               "machine id and name.",
        reference="SELECT m.id, m.name FROM machines m "
                  "LEFT JOIN maintenance x ON x.machine_id = m.id "
                  "WHERE x.id IS NULL",
        note="anti-join; the classic place an INNER JOIN silently loses rows",
    ),
    SqlTask(
        tid="sql_avg_temp_per_line",
        prompt="What is the average recorded temperature for each production "
               "line? Return the line and the average.",
        reference="SELECT m.line, AVG(r.temp_c) FROM readings r "
                  "JOIN machines m ON m.id = r.machine_id GROUP BY m.line",
        note="join then aggregate; averaging per line not per machine",
    ),
    SqlTask(
        tid="sql_top3_hottest",
        prompt="Give the three hottest readings. Return the machine name and "
               "the temperature, hottest first.",
        reference="SELECT m.name, r.temp_c FROM readings r "
                  "JOIN machines m ON m.id = r.machine_id "
                  "ORDER BY r.temp_c DESC LIMIT 3",
        ordered=True,
        note="THE ORDERED ONE. Row order is the answer here, not incidental.",
    ),
    SqlTask(
        tid="sql_alarm_share",
        prompt="For each machine id, what fraction of its readings have status "
               "'ALARM'? Return the machine id and the fraction as a number "
               "between 0 and 1.",
        reference="SELECT machine_id, "
                  "CAST(SUM(CASE WHEN status = 'ALARM' THEN 1 ELSE 0 END) AS REAL)"
                  " / COUNT(*) FROM readings GROUP BY machine_id",
        note="conditional aggregate; integer division is the trap",
    ),
    SqlTask(
        tid="sql_maint_hours_per_line",
        prompt="Total maintenance hours per production line, for lines with "
               "more than 5 total hours. Return the line and the total.",
        reference="SELECT m.line, SUM(x.hours) FROM maintenance x "
                  "JOIN machines m ON m.id = x.machine_id "
                  "GROUP BY m.line HAVING SUM(x.hours) > 5",
        note="join + GROUP BY + HAVING",
    ),
    SqlTask(
        tid="sql_above_line_average",
        prompt="Which machines have a maximum temperature higher than the "
               "average temperature of their own production line? Return the "
               "machine id.",
        reference="SELECT r.machine_id FROM readings r "
                  "JOIN machines m ON m.id = r.machine_id "
                  "GROUP BY r.machine_id HAVING MAX(r.temp_c) > ("
                  "  SELECT AVG(r2.temp_c) FROM readings r2 "
                  "  JOIN machines m2 ON m2.id = r2.machine_id "
                  "  WHERE m2.line = m.line)",
        note="correlated subquery against a per-group aggregate",
    ),
    SqlTask(
        tid="sql_first_reading_each",
        prompt="For each machine, give the temperature of its earliest reading "
               "by timestamp. Return the machine id and that temperature.",
        reference="SELECT machine_id, temp_c FROM ("
                  "  SELECT machine_id, temp_c, ROW_NUMBER() OVER ("
                  "    PARTITION BY machine_id ORDER BY ts) AS rn FROM readings"
                  ") WHERE rn = 1",
        note="window function; a plain MIN(ts) does not carry temp_c with it",
    ),
]


def by_tid() -> dict[str, SqlTask]:
    return {t.tid: t for t in TASKS}
