"""RUNTIME — where the check executes. Isolation, timeout, safety, identity.

This is the component the Python domain has and does not know it has: in
forge.py the runtime is scattered through verify() as [VERIFY_PY, "-I", path],
CAND_TIMEOUT, a tempfile, and the BANNED regex. Pulling it out as its own object
is the whole point of the second instance, and three of its four concerns came
out DIFFERENT here, which is the evidence the seam is real:

  ISOLATION   code domain: a subprocess.       SQL: a fresh in-memory database
              per candidate, rebuilt from the fixture. No process at all. The
              subprocess was never "how you isolate" -- it was how you isolate a
              PYTHON interpreter.
  TIMEOUT     code domain: wall-clock on a subprocess.   SQL: an instruction
              -counting progress handler inside the same process. Both are
              timeouts; neither mechanism transfers.
  SAFETY      code domain: a regex blocklist over source text.   SQL: SQLite's
              own authorizer callback, which decides per OPERATION and cannot be
              spelled around. See the red witness in the docstring below.
  IDENTITY    code domain: an interpreter path + version.   SQL: an engine name
              + library version. Both are "the answer depends on the engine, so
              record the engine", and the STRUCT that carries it does not
              survive -- verifier_interpreter() has a field called `executable`
              and there is no executable here.

WHY THE REGEX HAD TO GO, WITH THE WITNESS. forge.BANNED is defence-in-depth for
executing model output, expressed in Python syntax. Run it against SQL payloads
(EXECUTED, tests/test_sql_domain.py pins this):

    BANNED blocks 'DROP TABLE machines;'                        -> False
    BANNED blocks "ATTACH DATABASE '/etc/passwd' AS p;"         -> False
    BANNED blocks "PRAGMA temp_store_directory = 'C:/';"        -> False
    BANNED blocks 'DELETE FROM readings;'                       -> False
    BANNED blocks 'UPDATE machines SET line = 1;'               -> False

Zero of five. Reusing it here would have produced a safety layer that never
errors, never warns, blocks nothing, and leaves every log line saying the
pipeline is filtered -- the section 65/67 helper-reuse failure, except silent and
green instead of loud. It is also wrong in the other direction: a query whose
text merely contains "open(" would be refused for a Python builtin that is not
there.

So safety here is STRUCTURAL rather than textual. The authorizer refuses anything
that is not a read, at the engine, after parsing -- which means it cannot be
evaded by comments, case, whitespace, or a spelling nobody thought of. That is
the difference between a blocklist and a chokepoint, and it is the one place
where "close the class" was cheaper than "handle the instances".

NOT A SANDBOX, AND SAYING SO. This is in-process. A SQLite bug is a process bug.
For untrusted input at scale the honest end state is the one SWE-bench arrived
at -- a container per instance -- and every regex or authorizer is a deferral of
that. The blast radius here is a temp-file-free in-memory database built from a
fixture this repo wrote, so the deferral is defensible; it is not a claim of
safety against a hostile user.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

# Authorizer actions that a read-only query legitimately needs. Anything not in
# here is denied: INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, DETACH, PRAGMA,
# CREATE, TRANSACTION, and every action added by a future SQLite -- an allowlist
# fails closed as the engine grows, a blocklist fails open.
_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    getattr(sqlite3, "SQLITE_RECURSIVE", -1),   # WITH RECURSIVE; older builds lack it
}

# Denied by name even though SQLITE_FUNCTION is allowed as a class.
_DENIED_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}

DEFAULT_TIMEOUT_S = 2.0
_PROGRESS_INSTRUCTIONS = 1000        # how often the deadline is checked


@dataclass
class QueryResult:
    """What running one candidate produced. Deliberately NOT a bool.

    `rows` is the object the reward function scores. `denied` and `timed_out`
    are kept apart from `error` for the same reason forge.Result keeps
    `timed_out` apart from `ok`: a candidate we could not judge is not a
    candidate we judged wrong.
    """
    ok: bool = False
    rows: list[tuple] = field(default_factory=list)
    error: str = ""
    denied: str = ""             # the operation the authorizer refused, if any
    timed_out: bool = False
    runtime_s: float = 0.0


def identity() -> dict:
    """What the verifier ACTUALLY is, asked of the engine rather than assumed.

    The Python domain's verifier_interpreter() returns
    {executable, version, pinned_away_from_launcher, launcher_version}. Not one
    of those fields means anything here: there is no executable, no launcher,
    and nothing to be pinned away from. What survives is the PRINCIPLE -- ground
    truth is a function of source x runtime, so the runtime goes in the receipt
    -- and the shape it wants is domain-opaque:

        {"engine": str, "version": str, "fingerprint": sha256}

    Note `sqlite3.sqlite_version` (the C library actually linked), never
    `sqlite3.version` (the Python module's own version string, and REMOVED in
    Python 3.14 -- it raises AttributeError on the interpreter this repo runs).
    """
    engine, version = "sqlite3", sqlite3.sqlite_version
    fp = hashlib.sha256(f"{engine}\x00{version}".encode()).hexdigest()
    return {"engine": engine, "version": version, "fingerprint": fp}


class _Session:
    """One candidate's view of one task's fixture. Torn down after it."""

    def __init__(self, conn: sqlite3.Connection, timeout_s: float):
        self._conn = conn
        self._timeout_s = timeout_s

    def query(self, sql: str) -> QueryResult:
        res = QueryResult()
        if not sql.strip():
            res.error = "empty query"
            return res

        refused: list[str] = []

        def authorizer(action, arg1, arg2, dbname, source):
            if action == sqlite3.SQLITE_FUNCTION and arg2 in _DENIED_FUNCTIONS:
                refused.append(f"function {arg2}")
                return sqlite3.SQLITE_DENY
            if action in _ALLOWED_ACTIONS:
                return sqlite3.SQLITE_OK
            refused.append(_action_name(action))
            return sqlite3.SQLITE_DENY

        deadline = time.perf_counter() + self._timeout_s
        self._conn.set_authorizer(authorizer)
        self._conn.set_progress_handler(
            lambda: 1 if time.perf_counter() > deadline else 0,
            _PROGRESS_INSTRUCTIONS)
        t0 = time.perf_counter()
        try:
            cur = self._conn.execute(sql)
            res.rows = cur.fetchall()
            res.ok = True
        except sqlite3.Error as e:
            # ONE except, on purpose. An authorizer denial surfaces as
            # DatabaseError("not authorized") while a progress-handler abort
            # surfaces as OperationalError("interrupted"), and catching the
            # narrower class first silently dropped `denied` on the floor --
            # the refusal still happened, the REPORT of it did not. Which
            # exception class the engine picks is not the fact worth branching
            # on; whether the authorizer refused something is.
            msg = str(e)
            if refused:
                res.denied = refused[0]
                res.error = f"refused: {res.denied} is not allowed here"
            elif "interrupt" in msg.lower():
                res.timed_out = True
                res.error = f"timed out after {self._timeout_s}s"
            else:
                res.error = f"{e.__class__.__name__}: {msg}"
        finally:
            res.runtime_s = time.perf_counter() - t0
            self._conn.set_progress_handler(None, 0)
            self._conn.set_authorizer(None)
        return res


def _action_name(action: int) -> str:
    for name in dir(sqlite3):
        if name.startswith("SQLITE_") and getattr(sqlite3, name) == action:
            return name
    return f"action {action}"


class SqliteRuntime:
    """Rebuilds the fixture per candidate. Nothing survives a session.

    Isolation matters more here than it did in the Python domain and for a
    reason the Python domain could not raise: without a rebuild, candidate N's
    UPDATE scores candidate N+1. The authorizer already refuses writes, so this
    is belt AND braces -- but the rebuild is what makes the guarantee
    structural rather than dependent on the authorizer being right.
    """

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.timeout_s = timeout_s

    @contextmanager
    def session(self, fixture: str):
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(fixture)      # setup: before the authorizer is on
            conn.commit()
            yield _Session(conn, self.timeout_s)
        finally:
            conn.close()                     # teardown: the database ceases to exist

    def run(self, fixture: str, sql: str) -> QueryResult:
        """setup -> run -> teardown, for one candidate."""
        with self.session(fixture) as s:
            return s.query(sql)
