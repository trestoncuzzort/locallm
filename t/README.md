# t

**t is a specification interlingua, not (yet) a programming language.** A task is
written once in t — typed signature, preconditions, postconditions, and for now a
small body — and lowered mechanically to established verifiers, whose kernels
supply every verdict. t itself proves nothing and is trusted for nothing; that is
the design, not a temporary weakness. The trust always bottoms out in a kernel
with decades of adversarial history. All seven WS-7 tier-A kernels are wired and
measured on the box: Dafny, Verus, SPARK, Frama-C/WP, Lean 4, Rocq and F\*.
`AGREEMENT.md` carries the tool versions and the per-task table for the run that
produced it, and it is where the current state is read, not from this paragraph.
Agda's adapter is landed with its lowering parked, for a stated reason
(ROADMAP.md 7.2).

Prior art this stands on rather than beside: Why3 (one spec language, many
provers) and Viper (one intermediate verification language, many frontends).

Closest on the mutation side, and both to be read before anyone believes
something here is new. **MutDafny** (Isabel Amaral, Alexandra Mendes, José
Campos, "MutDafny: A Mutation-Based Approach to Assess Dafny Specifications",
arXiv:2511.15403 \[cs.SE], accepted at the 48th IEEE/ACM International
Conference on Software Engineering, ICSE 2026) is a Dafny plugin that mutates
the implementation AST between the parser and the verifier and classifies each
mutant Alive, Killed, Invalid or Timed Out, which is a closely analogous
partition to the one t reached independently and from the same starting point:
a mutant that still verifies is a hint that the specification is weak. Not the
same taxonomy, though — t splits the Killed-like half four ways: REFUTED (the
kernel accepted a certificate restating the measured witness), UNPROVED (the
kernel could not establish the contract it was handed, which is not a claim
about the mutant at all, so the cell does not count), MALFORMED (the mutant
never reached the prover) and TIMEOUT (the budget ran out), with
TOOL_ERROR and VACUOUS beside them. Only REFUTED counts, and the split earns
its keep: a could-not-prove read as a kill is exactly the error the dafny door
(2026-09-02) and the F\* demotion (2026-09-05) each had to correct.
**IronSpec** (Eli Goldweber, Weixin Yu,
Seyed Armin Vakil Ghahani and Manos Kapritsos, "IronSpec: Increasing the
Reliability of Formal Specifications", 18th USENIX Symposium on Operating
Systems Design and Implementation, OSDI '24, USENIX Association, pages 875-891)
mutates the SPECIFICATION rather than the implementation, which is the other
half of the same question.

What t adds, stated as narrowly as it is true. MutDafny's own open problem is
the equivalent mutant: of 284 surviving mutants analysed by hand, 157
were equivalent to the original program (§6.3.1, "Answer to RQ2"), and its
Future Work asks for "automatic techniques to find and discard equivalent ... or
ineffective ... mutants in the context of Dafny" (§7). t answers that by
construction rather than by detection. A twin is accepted only when the bounded
interpreter produces a MEASURED witness, an input satisfying `requires` on which
the real body and the twin differ, and the ladder prefers a witness that
falsifies `ensures`. An equivalent mutant has no such witness by definition, so
it is never accepted and never has to be discarded afterwards — exactly, for
the VALUE witnesses. The annotation mutations rest on a different argument and
are stated separately: an INVARIANT-DROP twin computes the same value as the
real body by construction. `sum_upto`'s twin deletes one `invariant` and
changes no statement: `out/sum_upto_twin.dfy` differs from `out/sum_upto.dfy`
in that one annotation line and in the certificate lemma the twin lowering
appends, in nothing executable. So on that rung there is no value witness to
have, and what the ladder measures instead is a PROOF witness — a loop state
satisfying `requires` and the surviving invariants that falsifies `ensures`
with the guard false, or breaks a surviving invariant in one iteration
(SPEC.md, "The twins")
— which makes such a twin not an equivalent program but an under-annotated one
that a sound kernel must fail to prove. The second
difference is the table: t runs the same task and the same twin through seven
kernels, where MutDafny is single-kernel.

If t ever grows its own checker, that checker gets verified inside Rocq or Lean
(the CakeML path) before anything trusts it — a homemade language certifying a
homemade system is two unaudited instruments signing each other's receipts, and
it is refused here in advance (ROADMAP.md, "The far field").

## v0, honestly scoped

- Types: `int`. No arrays, no quantifiers, no heap, no loops. v0 exists to prove
  the pipeline — task → lowering → kernel verdict → witness — not expressiveness.
- A task is JSON (`tasks/*.json`): no parser to write means no parser to trust.
- Taking the Dafny column as the worked example: `lower_dafny.py` emits Dafny
  and `dafny verify` decides. Exit codes as measured
  on 4.11.0: 0 verified, 2 malformed, 4 could-not-prove, which reads UNPROVED
  (TIMEOUT on "out of resource"). Until 2026-09-02 exit 4 was read as refuted;
  it is not a countermodel and is no longer read as one
  (WITNESS-2026-09-02-dafny-door.md).
- Every lowering also emits a BROKEN TWIN, chosen by a fixed ladder of mutation
  operators and accepted only when the interpreter produces a witness for it
  (SPEC.md, "The twins"). A task only counts when the real lowering VERIFIES
  **and** the twin is REFUTED: one witness for "the spec is provable," one for
  "the spec has teeth." Since 2026-09-02 the twin's REFUTED means the kernel
  accepted a certificate lemma restating the measured witness, not a bare
  failing exit — in the six columns that carry the certificate. F\* does not
  carry it yet: `lower_fstar.py` receives the witness and does not restate it,
  so since 2026-09-05 its adapter reports an unprovable twin as UNPROVED,
  which does not count, instead of REFUTED (`verifiers/fstar.py`, the error-19
  section: F\* answers `unknown`, never `sat`, on a true-but-undecidable spec
  exactly as on a false one). The F\* column therefore reads
  `verified / unproved` on every task and the run ends in DISAGREEMENT until
  that lowering lands, which is the honest reading and not a regression.
  A twin that still verifies is a vacuous spec and the task is
  refused. Where the ladder could only find a witness showing that real and twin
  compute different values, without falsifying `ensures`, the twin is tagged
  `+nonrefuting`: it is reported and it does not count, because a kernel
  verifying a twin that broke nothing is right rather than broken. This is
  dafny_pairs.py's measured-flip rule, applied to t from birth.

## Files

| File | What it is |
|---|---|
| `SPEC.md` | The task format and expression grammar for v0 and v1, complete. |
| `harness.py` | The mutation ladder, the twin's witness rule, the refusal reasons. |
| `interp.py` | The bounded reference interpreter that produces the witness. |
| `lower_dafny.py`, `lower_verus.py`, `lower_spark.py`, `lower_framac.py`, `lower_lean.py`, `lower_rocq.py`, `lower_fstar.py` | One lowering per kernel: t → target source, real and twin. |
| `verifiers/` | One adapter per kernel, plus `agda.py` (adapter landed, lowering parked). |
| `run_all.py`, `run_par.py` | Every task through every present kernel; both write `AGREEMENT.md`. |
| `tasks/` | Tasks in t. |
| `out/` | Lowered source files and verdicts (regenerated; witnesses are committed). |
| `AGREEMENT.md` | Generated by the two runners. Never edited by hand. |

Reading `AGREEMENT.md`: one row per task file, one column per kernel, each
cell the real outcome and the twin outcome separated by a slash, so agreement
means `verified / refuted` in every present column. The header line carries
the run's timestamp and the host that produced it, because a verdict is a
measurement made on a machine and two hosts are two measurements, not one. A
cell may carry a `+nonrefuting` tag; that marks a twin the ladder could only
accept on a witness showing real and twin compute different values without
falsifying `ensures`. Such a cell is reported and does not count, whatever
the kernel returned.
