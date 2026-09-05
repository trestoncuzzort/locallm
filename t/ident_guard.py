"""ident_guard.py — a task's own names must not read as a kernel's cheat word.

Every adapter carries a lexical ban scan that DECIDES the outcome: a hit in
the source is VACUOUS whatever the kernel said. The scan reads emitted text,
so it cannot tell a construct from a name that merely spells like one, and a
task is free to name a parameter `assumed` or `magicNumber`. Measured
2026-09-05 on this worktree, abs.json with its int parameter renamed:

    param     kernel  kernel's own tally                 adapter verdict
    assumed   dafny   1 verified, 0 errors, exit 0       VACUOUS
    admitted  fstar   4 solver-logged unsat, exit 0      VACUOUS
    magicNumber fstar 4 solver-logged unsat, exit 0      VACUOUS
    trustCompiler lean  (kernel never ran)               VACUOUS

VACUOUS means "accepted, but for the wrong reason" (verifiers/__init__.py).
A file the kernel verified for the RIGHT reason must never carry it, so
those four cells are wrong labels, not conservative ones.

The fix has two halves and this file is the second. First half: each
adapter's ban pattern is split into the rows a bare identifier could match
(KEYWORD_RE) and the rows it could not — pragma/attribute punctuation, or a
multi-token construct (SYNTAX_RE) — and every keyword row is given \\b
boundaries so it stops swallowing longer identifiers. Second half, here:
before a lowering emits anything, every identifier the task DECLARES is
tested against ITS OWN adapter's KEYWORD_RE, imported from
verifiers.<kernel> so the two cannot drift, and a hit is an ABSTAIN
(NotImplementedError, which the drivers record as a cell that declined to
run). Together they make the ban decision honest again: a keyword hit in
emitted source can now only have come from a construct.

Renaming the identifier instead was considered and refused: it would change
every emitted byte for every task, and the emitted artifacts are the
verdict basis. ABSTAIN reports the task as unmeasured, which is what it is.
"""
from __future__ import annotations


def declared_names(task: dict, body: list | None = None) -> list[str]:
    """Every identifier the task DECLARES, sorted.

    The declaration sites are SPEC.md's: the task name, param and return
    names, spec_fun names and their param names, `var` local declarations
    ({"var": {"name": ID, ...}}), and quantifier bound variables
    ({"forall"|"exists": {"var": ID, ...}}). All but the last spell the
    identifier under a "name" key, so one walk over "name" plus the two
    quantifier forms covers them.

    A bare {"var": ID} is a REFERENCE, not a declaration, and is skipped:
    in a well-formed task every reference resolves to one of the names
    above, so nothing is lost, and skipping keeps the refusal message
    pointing at the site the task author can actually change.
    """
    out: set[str] = set()

    def go(x) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "name" and isinstance(v, str):
                    out.add(v)
                elif k in ("forall", "exists") and isinstance(v, dict):
                    if isinstance(v.get("var"), str):
                        out.add(v["var"])
                go(v)
        elif isinstance(x, list):
            for v in x:
                go(v)

    go(task)
    if body is not None:
        go(body)
    return sorted(out)


def check(kernel: str, keyword_re, task: dict, body: list | None = None
          ) -> None:
    """Raise NotImplementedError if a declared name matches the kernel
    adapter's KEYWORD_RE. `keyword_re` is the compiled pattern imported from
    verifiers.<kernel>: one source, so the guard cannot drift from the scan
    it is protecting. Sorted order, so the named identifier is the same on
    every run and platform."""
    for name in declared_names(task, body):
        m = keyword_re.search(name)
        if m:
            raise NotImplementedError(
                f"identifier {name!r} collides with the {kernel} adapter's "
                f"cheat scan (matched {m.group(0)!r})")
