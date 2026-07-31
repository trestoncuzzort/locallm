"""The deliverable of the two-instance exercise: what the two prompts SHARE.

SQL_SYSTEM was written without reading ACTOR_SYSTEM (harness.py says why). This
prints the sentence-level diff between them. Council #18's instruction, and the
reason it matters:

    "do not import forge.ACTOR_SYSTEM -- write a fresh system prompt, then diff
    the two and treat every shared sentence as a candidate harness parameter."

A sentence in BOTH is a thing every domain's harness needs, so it belongs in the
interface as a parameter. A sentence in ONE is domain knowledge, so it belongs to
that domain's harness and must not be hoisted.

forge.py is READ, never imported -- ACTOR_SYSTEM's literal is pulled out with
`ast` so that the "nothing under domains/ imports forge" invariant stays absolute
and mechanically checkable (tests/test_sql_domain.py).

    python -m domains.sql.diff
"""
from __future__ import annotations

import ast
import pathlib
import re

from .harness import SQL_SYSTEM

FORGE = pathlib.Path(__file__).resolve().parents[2] / "forge.py"


def actor_system_literal() -> str:
    """ACTOR_SYSTEM's value, read out of forge.py's source without importing it."""
    tree = ast.parse(FORGE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "ACTOR_SYSTEM":
                    return ast.literal_eval(node.value)
    raise SystemExit("ACTOR_SYSTEM not found in forge.py")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _shape(s: str) -> str:
    """A sentence with its domain nouns removed, so 'a single self-contained
    Python solution inside one ```python fenced code block' and 'a single SQLite
    SELECT statement inside one ```sql fenced code block' can be recognised as
    the same REQUIREMENT wearing two domains."""
    s = s.lower()
    s = re.sub(r"```\w*", "```", s)
    for noun in ("python", "sqlite", "sql", "select statement", "solution",
                 "function", "engineer", "analyst", "code", "database",
                 "columns", "tests", "prints", "comments"):
        s = s.replace(noun, "<X>")
    s = re.sub(r"<x>( <x>)+", "<X>", s)
    return re.sub(r"[^a-z<>` ]+", " ", s).split()


def overlap(a: str, b: str) -> float:
    sa, sb = set(_shape(a)), set(_shape(b))
    return len(sa & sb) / max(len(sa | sb), 1)


def main() -> None:
    actor, sql = actor_system_literal(), SQL_SYSTEM
    a_s, s_s = sentences(actor), sentences(sql)

    print("=" * 78)
    print("ACTOR_SYSTEM (forge.py, read not imported)")
    print("=" * 78)
    for s in a_s:
        print(f"  - {s}")
    print()
    print("=" * 78)
    print("SQL_SYSTEM (domains/sql/harness.py, written without reading the above)")
    print("=" * 78)
    for s in s_s:
        print(f"  - {s}")

    print()
    print("=" * 78)
    print("SHARED REQUIREMENTS -> candidate parameters of a harness interface")
    print("=" * 78)
    shared, sql_only = [], list(s_s)
    for a in a_s:
        best = max(s_s, key=lambda b: overlap(a, b))
        if overlap(a, best) >= 0.4:
            shared.append((a, best))
            if best in sql_only:
                sql_only.remove(best)
    for a, b in shared:
        print(f"  PY  : {a}")
        print(f"  SQL : {b}")
        print()
    print(f"{len(shared)} of {len(a_s)} Python sentences have a SQL counterpart.")

    print()
    print("=" * 78)
    print("IN ONE DOMAIN ONLY -> stays in that domain's harness")
    print("=" * 78)
    matched_py = {a for a, _ in shared}
    for s in a_s:
        if s not in matched_py:
            print(f"  PY-ONLY  : {s}")
    for s in sql_only:
        print(f"  SQL-ONLY : {s}")


if __name__ == "__main__":
    main()
