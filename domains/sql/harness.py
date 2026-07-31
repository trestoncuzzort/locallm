"""HARNESS — how the task is attempted. The system prompt and the extraction.

WRITTEN WITHOUT LOOKING AT forge.ACTOR_SYSTEM, ON PURPOSE. Council #18 (section
82, Q2) named the methodological hole in "build a second domain and let the seam
be discovered": two instances cannot discover a seam they SHARE. Code-in-a-fence
and SQL-in-a-fence both want a fenced block, so importing the Python system
prompt would have made the prompt contract look domain-general when section 84
counts it as the third Python-welded site and train_native.py:52-60 reconstructs
the fenced form because ACTOR_SYSTEM demands it.

So this prompt was written for the job from scratch. `python -m domains.sql.diff`
prints the sentence-level diff against ACTOR_SYSTEM; what the two SHARE is a
candidate parameter of the harness interface, and what they do not is evidence
the interface has to carry it. The diff is the deliverable, not this string.

THE PROMPT NEEDS THE FIXTURE, WHICH forge.Task CANNOT EXPRESS. A Python task
prompt is self-contained: "write a function that reverses a list" needs nothing
else. "Which machines ran hot" is meaningless without the schema, so the harness
has to READ from the task's resource before it can even ask the question. That
is why Prime Intellect's v1 runtime API is `run` PLUS `read`/`write`, and it is
the second thing this domain broke that the code domain could not have shown.
"""
from __future__ import annotations

import re

from .runtime import SqliteRuntime

SQL_SYSTEM = (
    "You are a careful SQL analyst. Given a database schema and a question, "
    "answer with a single SQLite SELECT statement inside one ```sql fenced "
    "code block. Return exactly the columns asked for and nothing else. The "
    "database is read-only. No prose, no explanation, no comments."
)

# Any fence, any language tag -- the same shape forge.CODE_RE uses, and section
# 84 records that CODE_RE was never the Python-specific part.
FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)
_TAGS = ("sql", "sqlite")


def schema_of(fixture: str, runtime: SqliteRuntime | None = None) -> str:
    """The CREATE statements, read out of the fixture by the engine itself.

    Not re-typed here. A schema written twice is a schema that goes stale on one
    side, and the fixture is already the source of truth for the task's identity
    (taskset.SqlTask.fixture_sha256).
    """
    runtime = runtime or SqliteRuntime()
    with runtime.session(fixture) as s:
        res = s.query("SELECT sql FROM sqlite_master WHERE type = 'table' "
                      "ORDER BY name")
    if not res.ok:
        raise RuntimeError(f"could not read the fixture schema: {res.error}")
    return ";\n".join(row[0].strip() for row in res.rows if row[0]) + ";"


def user_prompt(question: str, fixture: str,
                runtime: SqliteRuntime | None = None) -> str:
    return (f"Schema:\n{schema_of(fixture, runtime)}\n\n"
            f"Question: {question}")


def extract_sql(text: str) -> str:
    """Pull one statement out of a model reply.

    Tolerant of the same noise extract_code handles -- fences, a language tag on
    its own line, a missing closing fence -- because that noise is a property of
    chat models, not of Python. Then two things that ARE SQL-specific: a leading
    `sql`/`sqlite` tag, and taking only the first statement, because a reply
    ending in a stray second statement should not silently run both.
    """
    text = text.strip()
    m = FENCE_RE.search(text)
    body = m.group(1) if m else text
    lines = [ln for ln in body.splitlines() if not ln.strip().startswith("```")]
    if lines and lines[0].strip().lower() in _TAGS:
        lines = lines[1:]
    body = "\n".join(lines).strip()
    # One statement only. A trailing ';' is fine; a second statement is dropped.
    parts = [p for p in body.split(";") if p.strip()]
    return (parts[0].strip() if parts else "")
