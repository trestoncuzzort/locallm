# t v0 — task format

A task is one JSON object. Every field is required unless marked optional.

```
{
  "t": 0,                          // format version, integer
  "name": "abs",                   // [A-Za-z][A-Za-z0-9_]*
  "params":  [{"name": "x", "type": "int"}],
  "returns": [{"name": "r", "type": "int"}],   // exactly one in v0
  "requires": [ Expr, ... ],       // conjoined; empty list = true
  "ensures":  [ Expr, ... ],       // conjoined; must be non-empty
  "body": [ Stmt, ... ]            // straight-line + if; must end every path in assign
}
```

## Expr

```
{"int": n}                                   // integer literal
{"var": "x"}                                 // parameter or return name
{"op": OP, "args": [Expr, ...]}
```

`OP` ∈ arithmetic `+ - * neg` (neg is unary), comparison `== != < <= > >=`,
logic `and or not implies`. `and`/`or` are n-ary; `not`/`neg` unary; the rest
binary. Division and modulo are deliberately absent from v0 (their semantics
differ across the WS-7 backends — Euclidean vs truncating — and t refuses to
paper over a semantic difference with a syntax).

## Stmt

```
{"assign": ["r", Expr]}
{"if": {"cond": Expr, "then": [Stmt, ...], "else": [Stmt, ...]}}
```

## The twin

The broken twin is the same task with the body's first `if` replaced by its
`then` branch. It is not optional and not configurable in v0: one mutation
operator, applied identically to every task, so "the twin failed" always means
the same thing. A task whose twin still verifies is refused as vacuous.

## What v0 does not claim

No quantifiers, arrays, loops, heap, overflow semantics (t v0 integers are
mathematical integers, which is why Dafny's `int` is the correct first target
and why C/Rust backends will need explicit range obligations later). One
return value. No recursion. These are gates to open with measurements, not
omissions to apologize for.
