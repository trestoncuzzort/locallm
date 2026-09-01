"""t/interp.py — a reference interpreter for a t body over a FIXED bounded
input domain, and the witness search that makes a twin a measurement.

Why this file exists, measured: over 1395 tasks from fuzz_lower.py's
generator (7 seeds x 200, less the 5 its own well-formedness check rejects),
129 twins — 9.2%, 13 to 22 per seed — compute the same value as the real
body on every input the fuzzer sampled. On those tasks the twin is not a broken
program, so a REFUTED verdict is luck and a VERIFIED one cannot be told apart
from a vacuous spec.
harness.make_twin therefore accepts a mutation only with a WITNESS produced
here: an input where real and twin disagree (the value-changing operators) or
a loop state the surviving invariants no longer cover (INVARIANT-DROP, whose
mutation is to the proof and not to the computed value).

Not shared with fuzz_lower.py's interpreter: that module imports harness and
harness imports this one, so importing it back would be a cycle. The
duplication buys a cross-check no single implementation gets — run over the
seed-1 corpus the two agreed on the returned value at all 7793 (task, input)
pairs both of them decided, with 0 disagreements (2026-09-01). One
deliberate divergence, stated because it is a semantic choice
and not an accident: a self-call inside a TWIN body resolves to the twin
(SPEC.md gate 3 — the self-call denotes the task's own function, and in the
twin lowering that function is the twin), where fuzz_lower.twin_semantics
resolves it to the real body.

The domain is enumerated, never sampled: the same task always yields the same
witness, because harness.make_twin's selection must stay deterministic and
content-derived like the operators it chooses between.
"""
from __future__ import annotations

import itertools

# Per-input caps. An input that exceeds one is DISCARDED (no verdict), never
# counted as agreement: a twin that merely runs out of budget has not been
# shown to compute the same value.
MAX_STEPS = 60_000
MAX_LOOP = 2_000
MAX_DEPTH = 40
MAX_RANGE = 5_000

# Domain caps. Points are enumerated in shell order (below) so the small,
# witness-dense corner of the product comes first and the cap trims the
# far corner, not the near one.
MAX_POINTS = 2048        # inputs per (real, twin) comparison
MAX_STATES = 20_000      # loop states per INVARIANT-DROP check;
                         # 4096 left fz_v1scan_085's first
                         # invariant unmeasurable at arity 4
                         # (s, x, i, r), which silently moved
                         # the twin to the second invariant.


class Undef(Exception):
    """SPEC.md "Definedness": `at` outside [0, len) has no value, and neither
    does a read of a return name before its first assignment. Never a Python
    IndexError or a None that compares — either would be the totalization
    SPEC.md calls wrong."""


class Budget(Exception):
    """A cap above was hit; this input decides nothing."""


class St:
    __slots__ = ("n", "d")

    def __init__(self):
        self.n = 0
        self.d = 0

    def tick(self):
        self.n += 1
        if self.n > MAX_STEPS:
            raise Budget("step cap")


# ---------------------------------------------------------------------------
# SPEC.md semantics.
# ---------------------------------------------------------------------------

def ev(e: dict, env: dict, funs: dict, st: St):
    st.tick()
    if "int" in e:
        return e["int"]
    if "bool" in e:
        return e["bool"]
    if "var" in e:
        if e["var"] not in env:
            raise Undef(f"unbound {e['var']}")
        v = env[e["var"]]
        if v is None:
            raise Undef(f"{e['var']} read before assignment")
        return v
    if "ite" in e:
        c = e["ite"]
        return ev(c["then" if ev(c["cond"], env, funs, st) else "else"],
                  env, funs, st)
    if "forall" in e or "exists" in e:
        kind = "forall" if "forall" in e else "exists"
        q = e[kind]
        lo = ev(q["lo"], env, funs, st)
        hi = ev(q["hi"], env, funs, st)
        if hi - lo > MAX_RANGE:
            raise Budget("quantifier range")
        acc = kind == "forall"
        # SPEC.md: the body must be defined for EVERY value in [lo, hi), so
        # every point is evaluated even after the result is decided; an empty
        # range decides without the body and is therefore defined.
        for i in range(lo, hi):
            sub = dict(env)
            sub[q["var"]] = i
            v = ev(q["body"], sub, funs, st)
            acc = (acc and v) if kind == "forall" else (acc or v)
        return acc
    if "call" in e:
        c = e["call"]
        f = funs.get(c["fun"])
        if f is None:
            raise Undef(f"no spec_fun {c['fun']}")
        args = [ev(a, env, funs, st) for a in c["args"]]
        sub = {p["name"]: a for p, a in zip(f["params"], args)}
        if "_exec" in f:
            body, ret = f["_exec"]
            st.d += 1
            if st.d > MAX_DEPTH:
                st.d -= 1
                raise Budget("self-call depth")
            try:
                sub[ret] = None
                exec_body(body, sub, funs, st)
                if sub[ret] is None:
                    raise Undef("self-call returned no value")
                return sub[ret]
            finally:
                st.d -= 1
        return ev(f["body"], sub, funs, st)
    op = e["op"]
    if op == "and":
        for a in e["args"]:
            if not ev(a, env, funs, st):
                return False
        return True
    if op == "or":
        for a in e["args"]:
            if ev(a, env, funs, st):
                return True
        return False
    if op == "implies":
        return (not ev(e["args"][0], env, funs, st)
                or bool(ev(e["args"][1], env, funs, st)))
    a = [ev(x, env, funs, st) for x in e["args"]]
    if op == "neg":
        return -a[0]
    if op == "not":
        return not a[0]
    if op == "len":
        return len(a[0])
    if op == "at":
        s, i = a
        if not (0 <= i < len(s)):
            raise Undef(f"at index {i} outside [0,{len(s)})")
        return s[i]
    if op == "+":
        return a[0] + a[1]
    if op == "-":
        return a[0] - a[1]
    if op == "*":
        return a[0] * a[1]
    if op == "==":
        return a[0] == a[1]
    if op == "!=":
        return a[0] != a[1]
    if op == "<":
        return a[0] < a[1]
    if op == "<=":
        return a[0] <= a[1]
    if op == ">":
        return a[0] > a[1]
    if op == ">=":
        return a[0] >= a[1]
    raise ValueError(f"t has no operator {op!r}")


def exec_body(body: list, env: dict, funs: dict, st: St) -> None:
    """Run statements for their VALUE only. Invariants and `decreases` are not
    checked here: this interpreter answers "what does the twin compute", and a
    twin whose annotations are broken is exactly what the kernel is asked to
    detect."""
    for s in body:
        st.tick()
        if "assign" in s:
            name, e = s["assign"]
            env[name] = ev(e, env, funs, st)
        elif "var" in s:
            d = s["var"]
            env[d["name"]] = ev(d["init"], env, funs, st)
        elif "if" in s:
            c = s["if"]
            exec_body(c["then"] if ev(c["cond"], env, funs, st) else c["else"],
                      env, funs, st)
        elif "while" in s:
            w = s["while"]
            it = 0
            while ev(w["cond"], env, funs, st):
                exec_body(w["body"], env, funs, st)
                it += 1
                if it > MAX_LOOP:
                    raise Budget("loop cap")
        else:
            raise ValueError(f"t has no statement {s!r}")


def self_calls(node, name: str) -> bool:
    """Does `node` (any JSON subtree of a task) call `name`?"""
    if isinstance(node, dict):
        c = node.get("call")
        if isinstance(c, dict) and c.get("fun") == name:
            return True
        return any(self_calls(v, name) for v in node.values())
    if isinstance(node, list):
        return any(self_calls(v, name) for v in node)
    return False


def funs_of(task: dict, body: list) -> dict:
    """spec_funs, plus the task itself when `body` self-calls (gate 3). The
    body passed in is the one that DEFINES the function: a twin's self-calls
    resolve to the twin."""
    funs = {f["name"]: f for f in task.get("spec_funs", [])}
    if self_calls(body, task["name"]):
        funs[task["name"]] = {"params": task["params"],
                              "_exec": (body, task["returns"][0]["name"])}
    return funs


# ---------------------------------------------------------------------------
# The bounded domain. Ladders ordered so index 0 is the most witness-dense
# value, because the arity cap trims the tail; CONTENT-DERIVED, because a
# generic ladder misses the constants the task itself talks about (measured:
# with a fixed [-3..5] alphabet, fz_v1scan_085's exit witness needs a sequence
# containing -3, the literal its own ensures compares against, and no
# reachable point of a task-independent seq ladder had one).
# ---------------------------------------------------------------------------

# [-40, 40] as the task report's domain, with +/-10^6 and the 32-bit
# boundaries at index 5-9 rather than after +/-5: an arity-3 task reaches
# only ladder index ~11 within MAX_POINTS, and with the boundaries at 11-15
# fz_v0if_144's collapse-if witness (z = -10^6) was outside the domain and
# the ladder fell through to a weaker operator. Small values are not lost by
# this: `ladders` puts the task's OWN literals in front of the whole list.
INTS = ((0, 1, -1, 2, -2)
        + (10 ** 6, -10 ** 6, 2 ** 31, -2 ** 31 - 1, 2 ** 31 - 1)
        + (3, -3, 4, -4, 5, -5)
        + tuple(v for k in range(6, 41) for v in (k, -k)))

BOOLS = (False, True)

ALPHA = 8               # sequence element alphabet size


def _dedup(vs):
    out, seen = [], set()
    for v in vs:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def literals(node) -> list[int]:
    """Every integer literal in the task, in pre-order of first appearance —
    the constants the spec and the body actually compare against."""
    out = []
    if isinstance(node, dict):
        if "int" in node and isinstance(node["int"], int):
            out.append(node["int"])
        for v in node.values():
            out += literals(v)
    elif isinstance(node, list):
        for v in node:
            out += literals(v)
    return out


def _seq_ladder(alpha: tuple) -> tuple:
    """Sequences over the task's own alphabet, short first: every length-0 and
    length-1 sequence, then lengths 2-5 in shell order under a per-length cap,
    so the near corner (small indices in every position) comes first."""
    out = [()] + [(a,) for a in alpha]
    out += [c for c in _shell([alpha, alpha], 24)]
    out += [c for c in _shell([alpha, alpha, alpha], 32)]
    quad = [alpha[:4]] * 4
    out += [c for c in _shell(quad, 16)]
    out += [tuple(alpha[:1]) * 5, tuple(alpha[:5])]
    return tuple(_dedup(out))


def _around(lits: list[int]) -> list[int]:
    """Each literal and its two neighbours. A spec that compares against k
    needs k-1, k, k+1 in the domain or `<` and `<=` are indistinguishable;
    measured on fz_v1scan_154, whose exit witness needs a sequence element
    ABOVE the literal 4 and whose alphabet contained no such value."""
    out = []
    for v in lits:
        out += [v, v + 1, v - 1]
    return out


def ladders(task: dict) -> dict:
    lits = literals(task)
    ints = tuple(_dedup([0, 1, -1] + _around(lits) + list(INTS)))
    alpha = tuple(_dedup([0, 1, -1] + _around(lits)
                         + [2, -2, 3, -3])[:ALPHA])
    return {"int": ints, "seq": _seq_ladder(alpha), "bool": BOOLS}


def _shell(lists: list, limit: int):
    """Cartesian product in shell order: every tuple whose largest ladder
    index is d, for d ascending. Lexicographic order would hold the first
    parameter at its first value for the whole cap and never reach a witness
    that needs two parameters to move."""
    if not lists:
        yield ()
        return
    n = 0
    for d in range(max(len(x) for x in lists)):
        for combo in itertools.product(*[range(min(d + 1, len(x)))
                                         for x in lists]):
            if max(combo) != d:
                continue
            yield tuple(lists[k][c] for k, c in enumerate(combo))
            n += 1
            if n >= limit:
                return


def domain(task: dict, names: list[tuple[str, str]],
           limit: int = MAX_POINTS):
    """All assignments to `names` (a list of (name, type)) from `task`'s
    ladders, capped at `limit` points in shell order."""
    lad = ladders(task)
    lists = [lad[ty] for _, ty in names]
    for combo in _shell(lists, limit):
        yield {n: v for (n, _), v in zip(names, combo)}


def _names(task: dict) -> list[tuple[str, str]]:
    return [(p["name"], p["type"]) for p in task["params"]]


def _j(v):
    return list(v) if isinstance(v, tuple) else v


def _shown(env: dict) -> dict:
    return {k: _j(v) for k, v in env.items()}


# ---------------------------------------------------------------------------
# Witnesses.
# ---------------------------------------------------------------------------

class Reference:
    """The real body's value on each domain point, computed once and reused
    for every candidate twin: harness.make_twin walks a ladder of operators
    and re-running the real body per candidate dominated the search."""

    def __init__(self, task: dict, limit: int = MAX_POINTS):
        self.task = task
        self.ret = task["returns"][0]["name"]
        self.funs = funs_of(task, task["body"])
        self.points: list[tuple[dict, object]] = []
        self.n_req = 0        # points satisfying `requires`; 0 separates a
                              # vacuous precondition from a body that never
                              # returns a value (probes fz_p_vac_unsat and
                              # fz_p_at_body respectively).
        req = task.get("requires", [])
        for env0 in domain(task, _names(task), limit):
            st = St()
            try:
                if not all(ev(c, env0, self.funs, st) for c in req):
                    continue
                self.n_req += 1
                env = dict(env0)
                env[self.ret] = None
                exec_body(task["body"], env, self.funs, st)
                v = env[self.ret]
                if v is None:
                    continue          # a path that assigns nothing: no value
            except (Undef, Budget, RecursionError):
                continue              # undecided, so it witnesses nothing
            self.points.append((env0, v))

    def witness(self, twin_body: list) -> dict | None:
        """First domain point where the twin disagrees with the real body,
        or None. A twin that is UNDEFINED where the real body has a value
        counts: SPEC.md makes every lowering discharge definedness or
        abstain, so that difference is one a kernel must see."""
        funs = funs_of(self.task, twin_body)
        for env0, real in self.points:
            st = St()
            env = dict(env0)
            env[self.ret] = None
            try:
                exec_body(twin_body, env, funs, st)
                got = env[self.ret]
            except Undef as u:
                w = _shown(env0)
                w.update(_kind="undefined", _real=_j(real), _twin=str(u))
                return w
            except (Budget, RecursionError):
                continue
            if got is None or got != real:
                w = _shown(env0)
                w.update(_kind="value", _real=_j(real),
                         _twin="no value" if got is None else _j(got))
                return w
        return None


def invariant_witness(task: dict, loop: dict, kept: list,
                      names: list[tuple[str, str]],
                      limit: int = MAX_STATES) -> dict | None:
    """INVARIANT-DROP leaves a body that computes the same value, so
    Reference.witness cannot see it. What is measurable is whether the
    SURVIVING invariants still carry the two obligations the dropped one was
    there for: a state satisfying requires and the survivors with the guard
    false but `ensures` false (exit entailment), or one satisfying them with
    the guard true whose single iteration breaks a survivor (preservation).
    Either means a kernel MUST refute the twin. Neither means a twin that
    verifies says nothing, and harness.make_twin moves on."""
    funs = funs_of(task, task["body"])
    req = task.get("requires", [])
    ens = task["ensures"]
    for env in domain(task, names, limit):
        st = St()
        try:
            if not all(ev(c, env, funs, st) for c in req):
                continue
            if not all(ev(c, env, funs, st) for c in kept):
                continue
            if not ev(loop["cond"], env, funs, st):
                if not all(ev(c, env, funs, st) for c in ens):
                    w = _shown(env)
                    w["_kind"] = "exit"
                    return w
                continue
            nxt = dict(env)
            exec_body(loop["body"], nxt, funs, st)
            if not all(ev(c, nxt, funs, st) for c in kept):
                w = _shown(env)
                w["_kind"] = "preservation"
                return w
        except (Undef, Budget, RecursionError):
            continue
    return None
