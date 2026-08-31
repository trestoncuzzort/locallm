# t — task format

A task is one JSON object. Every field is required unless marked optional.
Two format versions exist. `"t": 0` is frozen: everything in the v0 section
is unchanged and every v0 task remains valid byte-for-byte. `"t": 1` is a
strict superset that opens three expressiveness gates — quantifiers over
sequences, loops with invariants, recursion with termination measures. A v1
task may use any v0 construct; a v0 task may use nothing from v1.

Integer semantics in both versions: **mathematical integers**, unbounded, no
overflow. Backends whose native integers are bounded must add explicit range
obligations or abstain; t does not paper over a semantic difference with a
syntax.

## v0 (`"t": 0`)

```
{
  "t": 0,                          // format version, integer
  "name": "abs",                   // [A-Za-z][A-Za-z0-9_]*
  "params":  [{"name": "x", "type": "int"}],
  "returns": [{"name": "r", "type": "int"}],   // exactly one in v0 and v1
  "requires": [ Expr, ... ],       // conjoined; empty list = true
  "ensures":  [ Expr, ... ],       // conjoined; must be non-empty
  "body": [ Stmt, ... ]            // straight-line + if; must end every path in assign
}
```

### Expr (v0)

```
{"int": n}                                   // integer literal
{"var": "x"}                                 // parameter or return name
{"op": OP, "args": [Expr, ...]}
```

`OP` ∈ arithmetic `+ - * neg` (neg is unary), comparison `== != < <= > >=`,
logic `and or not implies`. `and`/`or` are n-ary; `not`/`neg` unary; the rest
binary. Division and modulo are deliberately absent from v0 AND v1 (their
semantics differ across the WS-7 backends — Euclidean vs truncating — and t
refuses to paper over a semantic difference with a syntax).

### Stmt (v0)

```
{"assign": ["r", Expr]}
{"if": {"cond": Expr, "then": [Stmt, ...], "else": [Stmt, ...]}}
```

## v1 (`"t": 1`) — the three gates

New top-level fields, all optional unless a gate below requires them:

```
"gate": "quantifiers" | "loops" | "recursion"   // which gate the task exercises; informational
"spec_funs": [ SpecFun, ... ]                   // pure recursive definitions usable in specs
"decreases": Expr                               // termination measure for a self-recursive body
```

New type: `"seq"` — a finite immutable sequence of mathematical integers.
Usable as a parameter type only (not a return type in v1). New type:
`"bool"` — usable as a return or local type.

### Definedness

v1 admits one partial operator (`at`, below), so definedness is part of the
semantics and is stated once: `and`, `or` evaluate left to right and the
k-th argument need only be defined when no earlier argument decided the
result (`and`: all earlier args true; `or`: all earlier args false).
`implies p q`: q need only be defined when p is true. `ite`: the taken
branch only. `forall`/`exists`: `lo` and `hi` must be defined; the body must
be defined for every value of the bound variable in `[lo, hi)`. `requires`
clauses are checked left to right, each assuming the earlier ones; each
`ensures` clause may assume `requires` and all earlier `ensures`; each loop
invariant may assume earlier invariants in its list. Every lowering must
either discharge these definedness obligations in its kernel (Dafny-style
well-formedness) or abstain; a lowering that silently totalizes `at` is
wrong.

### Gate 1 — quantifiers + sequences

Semantics: a `seq` value s has a length `len(s) >= 0` and elements
`s[0] … s[len(s)-1]`, each a mathematical integer. Sequences are values —
no aliasing, no mutation, no heap.

New Expr forms:

```
{"bool": true|false}                             // boolean literal
{"op": "len", "args": [Expr]}                    // length of a seq; int >= 0
{"op": "at",  "args": [SeqExpr, IdxExpr]}        // s[i]; DEFINED IFF 0 <= i < len(s)
{"forall": {"var": ID, "lo": Expr, "hi": Expr, "body": Expr}}
{"exists": {"var": ID, "lo": Expr, "hi": Expr, "body": Expr}}
{"ite": {"cond": Expr, "then": Expr, "else": Expr}}   // conditional expression
```

`forall` means: for every integer i with `lo <= i < hi`, body holds. `exists`
means: for some such i. The range is half-open `[lo, hi)`; `hi <= lo` gives
the empty range (forall = true, exists = false). Quantification is bounded by
design — every kernel on the WS-7 list can express a bounded integer
quantifier; unbounded quantification is a later gate, not a notational
convenience to smuggle in. The bound variable is a fresh name scoped to
`body` and must not collide with any name already in scope at that point
(params, returns, locals, enclosing bound variables). `==`/`!=` apply to two
ints or two bools; `< <= > >=` are int-only. `at` outside `[0, len)` is
undefined, and the definedness rules above say who must guard it.

Scope rule (v0 had it implicitly): `requires` sees params; `ensures` sees
params and returns; body expressions see params, returns, and locals declared
above them; invariants see all of those.

### Gate 2 — loops + invariants

New Stmt forms:

```
{"var": {"name": ID, "type": "int"|"bool", "init": Expr}}    // local, initialized
{"while": {"cond": Expr,
           "invariants": [Expr, ...],       // conjoined; may be empty
           "decreases": Expr,               // required on every loop
           "body": [Stmt, ...]}}
```

`assign` now targets any return or local name in scope. Loop semantics are
the standard partial-correctness-plus-termination package: every invariant
must hold on entry and be preserved by one iteration (assuming the guard);
after the loop, invariants hold and the guard is false. `decreases` is an
int-valued expression that is `>= 0` whenever the guard holds and strictly
decreases across every iteration; it is required, not optional — a t task
never states a loop it cannot bound. The kernel discharges all of it; t
checks nothing itself.

### Gate 3 — recursion + termination

A SpecFun is a pure total function defined by well-founded recursion,
usable in `requires`, `ensures`, `invariants`, and bodies:

```
{"name": ID,
 "params": [{"name": ID, "type": "int"|"seq"}, ...],
 "result": "int"|"bool",
 "decreases": Expr,          // int-valued over the params
 "body": Expr}               // may call itself and earlier spec_funs
```

New Expr form:

```
{"call": {"fun": ID, "args": [Expr, ...]}}
```

`fun` is a spec_fun name, or — inside the task's own body only — the task's
own name (direct self-recursion; no mutual recursion in v1). Semantics:

- A spec_fun call denotes the unique function satisfying its defining
  equation; well-definedness is exactly the termination obligation: at every
  self-call (and every call to an earlier spec_fun there is nothing to
  check), the callee's `decreases` measure evaluated at the call's arguments
  is `>= 0` and strictly less than the caller's measure at its own
  parameters. The kernel discharges this.
- A self-call of the task denotes a value about which exactly the task's
  contract is known (modular reasoning: callee `requires` must hold at the
  call site; callee `ensures` may be assumed of the result). A body that
  self-calls MUST carry a task-level `"decreases"` measure with the same
  obligation as above. Lowerings may hoist expression-position self-calls
  into call statements; the meaning is call-by-value, evaluated left to
  right, and (in v1) self-calls appear only in contexts where evaluation
  order is unobservable — specs and assignments.

The spec side of a recursive task is anchored by a spec_fun (`ensures r ==
fact(n)`), never by the task's own name: an `ensures` that referenced the
task itself would be redefined by the twin along with the body, and the flip
would measure nothing.

## The twins

Two mutation operators. Neither is optional or configurable; the choice is
derived from the body by one deterministic rule, applied identically to every
task, so "the twin failed" always means the same thing for a given body
shape. The twin never touches `requires`, `ensures`, `spec_funs`, or the
task/loop `decreases` clauses that survive in the mutated body — the spec is
the fixed instrument; the body and its annotations are what gets broken.

**COLLAPSE-IF** (v0, unchanged in meaning): the first `if` in pre-order
(descending into loop bodies) is replaced by its then-branch. A semantic
mutation: the twin computes something else. Twin REFUTED means the spec has
teeth; twin VERIFIED means the spec is vacuous and the task is refused.

**INVARIANT-DROP** (v1): the FIRST invariant of the FIRST loop (pre-order)
that states any invariant is deleted. An annotation mutation: the twin
computes the same thing with a weaker proof. Twin REFUTED means that
invariant is load-bearing — the kernel cannot re-derive it, so the stated
proof outline is real work. Twin VERIFIED means the dropped invariant was
dead weight (or the spec vacuous) and the task is refused: a task author must
place a load-bearing invariant first, and the flip rule enforces it by
measurement rather than by trust.

Selection: a body containing a loop with at least one invariant gets
INVARIANT-DROP; otherwise a body containing an `if` gets COLLAPSE-IF;
otherwise no twin exists and the task is refused. A task counts ONLY when
the real lowering is VERIFIED and the twin is REFUTED by the actual kernel —
both measured, never predicted.

## What v1 does not claim

No unbounded quantifiers. No arrays-with-mutation, no heap, no aliasing —
`seq` is a value. No division or modulo. No overflow semantics (mathematical
integers; bounded backends owe explicit range obligations). One return
value. No mutual recursion, no higher-order functions, no seq-valued
returns or seq literals. These are gates to open with measurements, not
omissions to apologize for.
