#!/usr/bin/env python3
"""harness_smells.py — a statement-level taxonomy of verdict-channel-forgery
patterns in candidate code, checked BEFORE execution.

WHY THIS EXISTS. forge.verify()'s nonce defends the sentinel string, but its
own comment names the residual: "the nonce lives in a module global while the
candidate runs in that same namespace, so code written deliberately against
THIS harness could still read it back out." poscontrol/red_witness_nonce_exploit.py
demonstrates this is not theoretical: `print('__PASS__' + _NONCE)` is accepted
as a full pass by the current verifier, live, on this branch.

The dynamic nonce check cannot close this on its own — the candidate and the
check share a namespace by construction (they're one concatenated script).
What CAN close it is refusing to execute code that exhibits the pattern, before
execution, the same way a static analyzer flags a malicious package before it
runs. That is the shape of Rahman et al.'s "Unveiling malicious logic: Towards
a statement-level taxonomy and dataset for securing python packages" (2025):
classify SPECIFIC syntactic patterns into named categories, each independently
checkable by walking the AST, rather than one broad heuristic.

Three categories, scoped to what this harness's own residual actually needs:

  HARNESS_INTROSPECTION — any reference to the harness's own internal names
    (_NONCE) or to globals()/vars()/locals() with no arguments, which is
    exactly how a candidate would discover the nonce without hardcoding its
    name. A legitimate task solution never needs to introspect its own module.

  SENTINEL_FORGERY — the literal string "__PASS__" appearing anywhere in
    candidate code. No task's intended solution ever needs to reference the
    harness's own protocol string.

  PREMATURE_TERMINATION — a call to exit()/quit()/os._exit(), or `raise
    SystemExit`, anywhere in candidate code. No task's intended solution
    terminates the interpreter; this is exactly what the original Failure-1
    exploit and the nonce-reading exploit both use to skip real test
    execution.

This is defense in depth, not a sandbox, exactly like the code it sits next
to: a sufficiently indirect construction (e.g. building "__PASS__" one
character at a time, or reaching _NONCE through an exec() the BANNED filter
also happens to block) is not claimed to be caught. What this closes is the
demonstrated exploit and every direct variant of it -- the same scope the
nonce fix itself claimed for the sentinel-forgery class it closed.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

HARNESS_NAMES = {"_NONCE", "_os", "_OK_T", "_strict", "_entry", "_checked"}
INTROSPECTION_CALLS = {"globals", "vars", "locals"}
TERMINATION_CALLS = {"exit", "quit"}
SENTINEL = "__PASS__"


@dataclass
class Smell:
    category: str
    detail: str
    lineno: int


class _Visitor(ast.NodeVisitor):
    def __init__(self):
        self.smells: list[Smell] = []

    def visit_Name(self, node: ast.Name):
        if node.id in HARNESS_NAMES:
            self.smells.append(Smell(
                "HARNESS_INTROSPECTION",
                f"references harness-internal name {node.id!r}",
                node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (
            fn.attr if isinstance(fn, ast.Attribute) else None)
        if name in INTROSPECTION_CALLS and not node.args and not node.keywords:
            self.smells.append(Smell(
                "HARNESS_INTROSPECTION",
                f"calls {name}() with no arguments -- introspects the module "
                f"namespace the candidate shares with the harness",
                node.lineno))
        if name in TERMINATION_CALLS:
            self.smells.append(Smell(
                "PREMATURE_TERMINATION", f"calls {name}()", node.lineno))
        if (isinstance(fn, ast.Attribute) and fn.attr == "_exit"
                and isinstance(fn.value, ast.Name) and fn.value.id in ("os", "_os")):
            self.smells.append(Smell(
                "PREMATURE_TERMINATION", "calls os._exit()", node.lineno))
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        exc = node.exc
        target = exc.func if isinstance(exc, ast.Call) else exc
        if isinstance(target, ast.Name) and target.id == "SystemExit":
            self.smells.append(Smell(
                "PREMATURE_TERMINATION", "raises SystemExit", node.lineno))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str) and SENTINEL in node.value:
            self.smells.append(Smell(
                "SENTINEL_FORGERY",
                f"string literal contains {SENTINEL!r}", node.lineno))
        self.generic_visit(node)


def scan(code: str) -> list[Smell]:
    """Every smell found in `code`, or [] if it parses clean and finds none.

    A SyntaxError candidate is not this function's problem to report -- forge.py's
    own execution path already produces a clear result for code that does not
    parse; scan() only classifies code that DOES parse, since a candidate has to
    parse to be executed at all, let alone forge a verdict.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    v = _Visitor()
    v.visit(tree)
    return v.smells
