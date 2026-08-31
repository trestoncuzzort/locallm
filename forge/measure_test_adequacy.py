#!/usr/bin/env python3
"""How permissive is the reward? Mutation testing on the tasks that define it.

THE GAP THIS MEASURES, named by council #18 (section 83, F5). Sections 61-80 spent
most of this project's measurement budget establishing a ~3pp SAMPLER noise floor,
to four decimals, with a confidence interval, over 40 replicates. Meanwhile the
other error term in the same instrument -- how often the tests call a WRONG
solution right -- has never been measured at all.

The nearest published estimate is large. EvalPlus (Liu et al., NeurIPS 2023,
arXiv 2305.01210) extended HumanEval's tests by ~80x and measured pass@k falling
by up to 19.3-28.9% across 26 LLMs. forge.SEED_TASKS carries FOUR TO EIGHT
asserts per task, which is HumanEval's density, not EvalPlus's.

THE METHOD, which is EvalPlus's own logic run backwards. Instead of adding tests
until solutions fail, take solutions that ALREADY PASS, break them on purpose,
and see how many the tests still wave through. A mutant that survives is a
concrete, exhibitable wrong program this project's reward would score as correct
and hand to DPO as a `chosen`.

WHERE THE SOLUTIONS COME FROM: data/dpo_pairs.jsonl `chosen` fields. Those are not
hand-written -- they are real model outputs that forge.verify() already accepted,
so this measures the verifier against the exact population it actually judges.

WHAT THIS CANNOT TELL YOU, stated up front because it bounds every number below.
Some mutants are EQUIVALENT: they change the source without changing behaviour on
any input (`x = x + 0`, reordering independent statements, a branch that cannot be
reached). An equivalent mutant survives every possible test suite, so counting it
as a survivor overstates weakness. Detecting equivalence is undecidable in
general and no attempt is made here. The survival rate is therefore an UPPER
BOUND on inadequacy, and the honest reading of a survivor is "candidate evidence
of a hole, worth looking at" rather than "proven hole".

    python measure_test_adequacy.py --solutions 3 --max-mutants 40
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import statistics
import time
from pathlib import Path

import forge

PAIRS = Path(__file__).with_name("data") / "dpo_pairs.jsonl"
OUT = Path(__file__).with_name("data") / "test_adequacy.json"


# ---------------------------------------------------------------------------
# Mutation operators. Deliberately SMALL and behaviour-changing: each is a bug a
# person could plausibly write, not a random token scramble. A scrambled program
# usually crashes, and "the tests caught a syntax error" measures nothing.
# ---------------------------------------------------------------------------
_CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
             ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv,
             ast.FloorDiv: ast.Mult}
_BOOL_SWAP = {ast.And: ast.Or, ast.Or: ast.And}


class _Mutator(ast.NodeTransformer):
    """Applies exactly ONE mutation, the `target`-th site of its kind."""

    def __init__(self, kind: str, target: int):
        self.kind, self.target, self.seen, self.applied = kind, target, 0, None

    def _hit(self, label: str) -> bool:
        if self.seen == self.target:
            self.seen += 1
            self.applied = label
            return True
        self.seen += 1
        return False

    def visit_Constant(self, node):
        if self.kind == "int_offby1" and isinstance(node.value, int) \
                and not isinstance(node.value, bool):
            if self._hit(f"int {node.value} -> {node.value + 1}"):
                return ast.copy_location(ast.Constant(value=node.value + 1), node)
        return self.generic_visit(node)

    def visit_Compare(self, node):
        if self.kind == "cmp_swap" and len(node.ops) == 1 \
                and type(node.ops[0]) in _CMP_SWAP:
            new = _CMP_SWAP[type(node.ops[0])]
            if self._hit(f"{type(node.ops[0]).__name__} -> {new.__name__}"):
                node = ast.copy_location(
                    ast.Compare(left=node.left, ops=[new()],
                                comparators=node.comparators), node)
                return self.generic_visit(node)
        return self.generic_visit(node)

    def visit_BinOp(self, node):
        if self.kind == "arith_swap" and type(node.op) in _BIN_SWAP:
            new = _BIN_SWAP[type(node.op)]
            if self._hit(f"{type(node.op).__name__} -> {new.__name__}"):
                node = ast.copy_location(
                    ast.BinOp(left=node.left, op=new(), right=node.right), node)
                return self.generic_visit(node)
        return self.generic_visit(node)

    def visit_BoolOp(self, node):
        if self.kind == "bool_swap" and type(node.op) in _BOOL_SWAP:
            new = _BOOL_SWAP[type(node.op)]
            if self._hit(f"{type(node.op).__name__} -> {new.__name__}"):
                node = ast.copy_location(
                    ast.BoolOp(op=new(), values=node.values), node)
                return self.generic_visit(node)
        return self.generic_visit(node)

    def visit_If(self, node):
        if self.kind == "negate_if":
            if self._hit("negate an if condition"):
                node = ast.copy_location(
                    ast.If(test=ast.UnaryOp(op=ast.Not(), operand=node.test),
                           body=node.body, orelse=node.orelse), node)
                return self.generic_visit(node)
        return self.generic_visit(node)


KINDS = ("int_offby1", "cmp_swap", "arith_swap", "bool_swap", "negate_if")


def mutants(code: str, cap: int) -> list[tuple[str, str, str]]:
    """(kind, description, mutated source). One mutation each."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    for kind in KINDS:
        for i in range(60):                    # site index within this kind
            m = _Mutator(kind, i)
            try:
                new = ast.fix_missing_locations(m.visit(ast.parse(code)))
            except RecursionError:
                break
            if m.applied is None:
                break                          # no i-th site of this kind
            try:
                src = ast.unparse(new)
            except Exception:                  # noqa: BLE001
                continue
            if src.strip() != ast.unparse(tree).strip():
                out.append((kind, m.applied, src))
            if len(out) >= cap:
                return out
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solutions", type=int, default=3,
                    help="distinct passing solutions to mutate per task")
    ap.add_argument("--max-mutants", type=int, default=40,
                    help="cap per solution")
    args = ap.parse_args()

    tasks = {t.tid: t for t in forge.SEED_TASKS}
    by_tid: dict[str, list[str]] = collections.defaultdict(list)
    for line in PAIRS.open(encoding="utf-8"):
        r = json.loads(line)
        tid = r["meta"]["tid"]
        if tid in tasks and r["chosen"] not in by_tid[tid]:
            by_tid[tid].append(r["chosen"])

    print(f"verifier: {json.dumps(forge.verifier_interpreter())}")
    print(f"tasks   : {len(tasks)}  |  asserts per task: "
          f"{ {t: tasks[t].tests.count('assert') for t in sorted(tasks)} }")
    print()

    results, t0 = {}, time.perf_counter()
    for tid in sorted(tasks):
        task = tasks[tid]
        sols = by_tid[tid][:args.solutions]
        if not sols:
            print(f"{tid:20s} no banked passing solution, skipped")
            continue

        killed = survived = invalid = 0
        survivors: list[dict] = []
        for si, sol in enumerate(sols):
            # The unmutated solution must pass, or nothing below means anything.
            base = forge.verify(sol, task)
            if not base.ok:
                print(f"{tid:20s} banked solution #{si} does NOT pass now "
                      f"({base.error[:40]}) - skipped")
                continue
            for kind, desc, src in mutants(sol, args.max_mutants):
                res = forge.verify(src, task)
                if res.timed_out:
                    invalid += 1            # unjudged, not survived
                elif res.ok:
                    survived += 1
                    if len(survivors) < 3:
                        survivors.append({"kind": kind, "change": desc,
                                          "solution_index": si, "code": src})
                else:
                    killed += 1

        total = killed + survived
        rate = survived / total if total else 0.0
        results[tid] = {"asserts": task.tests.count("assert"),
                        "solutions_mutated": len(sols),
                        "mutants": total, "killed": killed,
                        "survived": survived, "unjudged_timeouts": invalid,
                        "survival_rate": round(rate, 4),
                        "example_survivors": survivors}
        print(f"{tid:20s} asserts {results[tid]['asserts']:2d}  "
              f"mutants {total:4d}  killed {killed:4d}  survived {survived:4d}  "
              f"SURVIVAL {rate:6.1%}")

    dt = time.perf_counter() - t0
    tot_m = sum(r["mutants"] for r in results.values())
    tot_s = sum(r["survived"] for r in results.values())
    overall = tot_s / tot_m if tot_m else 0.0
    per_task = [r["survival_rate"] for r in results.values()]

    print()
    print("=" * 78)
    print(f"mutants run                      : {tot_m:,}")
    print(f"survivors (tests said CORRECT)   : {tot_s:,}")
    print(f"OVERALL SURVIVAL RATE            : {overall:.1%}")
    print(f"per-task survival, mean          : {statistics.fmean(per_task):.1%}")
    print(f"per-task survival, worst         : "
          f"{max(per_task):.1%} ({max(results, key=lambda t: results[t]['survival_rate'])})")
    print(f"per-task survival, best          : "
          f"{min(per_task):.1%} ({min(results, key=lambda t: results[t]['survival_rate'])})")
    print(f"elapsed                          : {dt:.0f}s")

    OUT.write_text(json.dumps({
        "kind": "test_adequacy_mutation",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "verifier": forge.verifier_interpreter(),
        "solutions_per_task": args.solutions,
        "max_mutants_per_solution": args.max_mutants,
        "operators": list(KINDS),
        "overall_survival_rate": round(overall, 4),
        "mutants": tot_m, "survived": tot_s,
        "caveat": "Equivalent mutants are not detected, so this is an UPPER "
                  "BOUND on test inadequacy, not a count of proven holes.",
        "by_task": results,
    }, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print()
    print("A SURVIVOR IS AN EXHIBIT, NOT A STATISTIC: each one is a wrong program "
          "this\nreward would score as correct and hand to DPO as a `chosen`. "
          "Equivalent mutants\nare not detected, so treat the rate as an upper "
          "bound and read the examples.")


if __name__ == "__main__":
    main()
