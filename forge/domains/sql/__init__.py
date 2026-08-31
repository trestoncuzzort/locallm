"""The SQL domain: the second instance, and an instrument rather than a product.

    taskset.py   what the work IS      -- prompts, answer keys, identity, fixture
    harness.py   how it is ATTEMPTED   -- system prompt, schema, extraction
    runtime.py   where it EXECUTES     -- isolation, timeout, safety, identity
    reward.py    what the check RETURNS -- a float in [0, 1], not a bool

Chosen over JSON-schema validation and regex synthesis for one reason: it is the
only candidate whose verifier has STATE. The other two are pure functions of the
candidate string and would drop into `verify(code, task) -> Result` without
changing the signature at all -- which is exactly why they teach nothing. A test
that cannot fail is not evidence, and neither is a second domain that cannot
strain the interface.
"""
from .taskset import TASKS, SqlTask, by_tid          # noqa: F401
from .runtime import SqliteRuntime, QueryResult, identity   # noqa: F401
from .reward import SqlVerifier, SqlScore, score_rows, trl_reward_func  # noqa: F401
from .harness import SQL_SYSTEM, extract_sql, schema_of, user_prompt    # noqa: F401
