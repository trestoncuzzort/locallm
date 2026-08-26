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

## R-5 — The training code does not run on a current install

**Problem.** `train_native.py` passes `rpo_alpha` to `DPOConfig`. Current TRL
(1.9.2, installed fresh 2026-08-04) does not accept it and the script dies at
config construction before any training begins:
`TypeError: DPOConfig.__init__() got an unexpected keyword argument 'rpo_alpha'`.
Reproducing the run requires `trl==0.12.2`, which in turn pins
`transformers==4.46.3` and `tokenizers==0.20.3`. The code names 0.12.2 in a
comment; nothing enforces it.

**Live reproduction, 2026-08-04.** Fresh `.venv-train` built for the replication
resolved `trl` to 1.9.2 from the unpinned requirement. The retrain failed
immediately. After `pip install trl==0.12.2`, the same command ran and reported
`57` optimizer steps, matching the count derived independently from the author's
recovered `training_args.bin` (918 pairs / effective batch 16).

**Why deferred.** Correct pins depend on decisions this run should not make
unilaterally: whether to freeze the training stack at 0.12.2 permanently, or to
port `rpo_alpha` to whatever the current TRL calls it and accept that the ported
objective is not byte-identical to the one the paper describes. That is a
methods decision, not a packaging one.

**Discharge condition.** Either `requirements.txt` (or a separate
`requirements-train.txt`) pins the training stack such that a clean venv runs
`train_native.py` unmodified, or the code is ported and the paper states which
TRL produced its adapter. Note the paper currently states neither.

**Pointers.** `train_native.py` `DPOConfig(...)` block and its TRL-0.12.2 comment;
`requirements.txt` as added on `fix/repo-hygiene-and-publish-guards`;
`poscontrol/retrain.log` (first run, the traceback; second run, the 57 steps).

---

## R-6 — The trained pairs carry no verbatim completions

**Problem.** Loading `data/dpo_pairs_capped.jsonl` for training reports:
`918 pairs ...; 0 carry verbatim completions, 918 fall back to re-fenced source`.
`training_target()` therefore reconstructs every optimisation target by
re-fencing executable source, rather than using the text the policy actually
emitted. The `chosen_raw`/`rejected_raw` fields the function looks for are absent
from every row of the capped file.

**Why this is recorded and NOT fixed here.** It is identical in the author's run
— same data file — so it is not a difference between the original and the
replication and cannot explain any divergence between them. It is a property of
what BOTH adapters were trained on. Changing it would make the replication a
different experiment.

**Discharge condition.** Pairs are regenerated by a builder that preserves the
verbatim emissions (the `chosen_raw`/`rejected_raw` contract restored in the
non-semantic-outcomes work), and any claim about what the policy was optimised
toward is re-derived against those rows.

**Pointers.** `train_native.py` `training_target()`; `traces.py` `derive_dpo()`
field contract; `poscontrol/retrain.log` loader line.

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
