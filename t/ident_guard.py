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

The fix is ONE half, and this file is it. Before a lowering emits anything,
every identifier the task DECLARES is tested against ITS OWN adapter's WHOLE
ban pattern, imported from verifiers.<kernel> so the two cannot drift, and a
hit is an ABSTAIN (NotImplementedError, which the drivers record as a cell
that declined to run). A hit in emitted source can then only have come from
a construct, which is what the ban scan always meant it to mean.

The other half was tried and reverted 2026-09-05. It split each adapter's
pattern into the rows a bare identifier could match and the rows it could
not, and gave every word row \\b boundaries. Two gate rounds measured what
that cost F*: `\\badmit\\b` does not see `admitted` inside
`[@@FStar.Attributes.admitted]`, so a false lemma carrying that attribute
scored VERIFIED with ok=True; an added attribute regex was then walked past
by `[@@ (* ] *) FStar.Attributes.admitted]`, VERIFIED ok=True again, because
F* reads the comment as whitespace and a regex reads the `]` inside it as
the attribute's end. A regex over a language with comments and strings does
not win that race, so the patterns are the ones they always were and the
guard alone carries the fix.

The cost is stated plainly because it is real: the guard refuses on ANY
match, and several of those patterns are substring scans, so a task whose
own name merely EMBEDS a family word — `admitted`, `magicNumber`,
`assumed`, `externals` — ABSTAINs. Such a task is reported unmeasured, and
it is: the alternative is not "measured", it is being mislabelled VACUOUS
(and counted as a cheat) by a scan that cannot see the difference. Renaming
the identifier for the task was considered and refused: it would change
every emitted byte for every task, and the emitted artifacts are the verdict
basis. The name is the task author's to change.
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


def check(kernel: str, ban_re, task: dict, body: list | None = None
          ) -> None:
    """Raise NotImplementedError if a declared name matches ANY row of the
    kernel adapter's ban pattern. `ban_re` is that adapter's own compiled
    BANNED/BANNED_RE, imported from verifiers.<kernel>: one source, so the
    guard cannot drift from the scan it is protecting, and no second pattern
    to keep in step.

    ANY match, including a substring: several of those patterns are
    deliberately unbounded, so `admitted` matches F*'s `admit` row and
    `assumed` matches Dafny's `assume\\w*`. Refusing those names is the
    intended cost — the scan would otherwise call a real proof VACUOUS (see
    the module docstring). Rows no identifier can spell — pragma
    punctuation, multi-word vernacular — simply never fire here.

    Sorted order, so the named identifier is the same on every run and
    platform."""
    for name in declared_names(task, body):
        m = ban_re.search(name)
        if m:
            raise NotImplementedError(
                f"identifier {name!r} collides with the {kernel} adapter's "
                f"cheat scan (matched {m.group(0)!r})")
