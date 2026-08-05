# Residuals opened during the 2026-08-04 replication

Four fields per residual: the problem · why it is deferred · the discharge
condition · pointers.

---

## R-1 — The hash gate is line-ending dependent, and it fired

**Problem.** `dataset_gate.verifier_fingerprint()` hashes working-tree bytes.
`core.autocrlf=true` is set in this repo and there is no `.gitattributes`
normalization (`.gitattributes` carries only `data/*.jsonl merge=union`), so the
same file has two different hashes depending on how git materialized it.

**Live reproduction, 2026-08-04.** `task_bank.py` was authored in a worktree with
LF endings; the receipt regenerated there recorded
`b28a47cb95f1e3488b6e14213032d103ce37646ee1617c34a55700d0430bc736`. Checked out
into the main tree, git wrote CRLF and the on-disk hash became
`15770d4d658308d6af19ad9bae2ff8f9dac70161ae6329a2872d493bfb72d8b3`. The gate
refused with a VERIFIER-CHANGED error on byte-identical source. Confirmed by
recomputation: the LF-normalized digest of the CRLF file equals the receipt value
exactly (1,485 bytes, 30 CRLF, 0 bare LF). Git restated the hazard unprompted on
the very next commit: *"LF will be replaced by CRLF the next time Git touches
it."*

**Why deferred.** The fix (`* text=auto eol=lf`, or `* -text`) renormalizes every
tracked file, which changes every hash in the receipt and forces a full
re-verification. That is a repo-wide change and belongs in its own reviewed PR,
not inside a measurement run. Regenerating the receipt in-tree unblocked the run
and left the defect intact — deliberately, so the reproduction survives.

**Discharge condition.** A `.gitattributes` normalization lands, the receipt is
regenerated once under it, and a probe demonstrates that a checkout under
`core.autocrlf=false` and one under `true` produce the same fingerprint. Until
then, any clone with different line-ending settings — or any Linux/CI runner —
gets a gate refusal that reads like tampering.

**Pointers.** `dataset_gate.py` `VERIFIER_FILES`/`TASK_SOURCE_FILES` and
`sha256_file`; `.gitattributes`; `data/dataset_verification.json`. Prior
statement of the same hazard for one file: `OPEN-ITEMS.md:114-119`, which treats
it as a quirk of `dpo_pairs_capped.jsonl` rather than a property of the gate.

---

## R-2 — `analyze_run1.py` pools what `ruler_noise.py` refuses to pool

**Problem.** `analyze_run1.load()` groups replicates by `model` alone. The base
arm's 50 rows span two samplers (greedy-anchored and greedy-free) and two
verifier states (10 pre-pin rows M=.5910 vs 40 pinned M=.5150; Welch between them
p=1.9e-8). `ruler_noise.cmd_measure` explicitly refuses exactly this pooling for
the arms and prints "ignoring N replicate(s) banked under a different verifier".
The guard exists; the analysis path bypasses it.

**Why deferred.** It is an analysis-layer defect, not a measurement one, and the
current run does not depend on `analyze_run1.py`. Fixing it changes published
figures and should ship with the paper correction, together.

**Discharge condition.** `load()` partitions on the verifier fingerprint and the
sampler, refuses to pool across either, and the base-vs-arms figures are
recomputed under the partition.

**Pointers.** `analyze_run1.py:144,153`; `ruler_noise.py` cmd_measure resume
block; measured effect in `poscontrol/ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md` §4.

---

## R-3 — Raw completions are not retained, so exact-output agreement is not computable

**Problem.** The banked replicate rows carry aggregates and per-task counts only.
A string-field census of `data/ruler_noise.jsonl` found the longest string in the
file is 61 characters (a path). The question "do the two arms ever emit
byte-identical completions, and at what rate" therefore cannot be answered from
any retained artifact — for the original run or for this replication.

**Why deferred.** Adding retention changes the row schema and the disk footprint
(12,400 generations per arm-pair) and should be designed, not bolted onto a run
already in flight.

**Discharge condition.** A retention option exists, is off by default, and a
recorded run carries per-generation text; agreement rate is then computable
directly rather than inferred from per-task correlation.

**Pointers.** `poscontrol/ZERO-COMPUTE-DIAGNOSTICS-2026-08-04.md` §6 C3;
`eval.py` generation path.

---

## R-4 — Appendix B's reproduction commands do not match the CLI

**Problem.** The draft's Appendix B instructs `python build_ruler.py verify`.
That subcommand does not exist; `build_ruler.py` accepts only
`{nominate, confirm, freeze}`. A reviewer following the paper's own reproduction
section fails at step one.

**Why deferred.** Documentation correction, no runtime effect; belongs with the
paper edits.

**Discharge condition.** Appendix B lists commands that execute as written on a
clean checkout, or the missing subcommand is added.

**Pointers.** `build_ruler.py` argparse block; draft Appendix B.
