# Results

One place to find what this project has actually measured, and what it has not.

Everything here either **is** a result or **points at** one. Nothing in this folder is a
copy of a data file that lives somewhere else — copies drift, and then two files disagree
and neither one says which is right. The raw records stay where the tools write them; this
folder tells you where that is and what came out.

---

## Headline: the trained adapter did not beat its control

**Track A, run 1 — measured 2026-08-04. Both arms complete, 40 replicates each.**

| Arm | What it is | Mean pass@1 | sd | n |
|---|---|---|---|---|
| `llama3-forged` | the DPO-trained adapter | **0.4976** | 0.0415 | 40 |
| `llama3-forged-null` | same export path, no training | **0.4921** | 0.0327 | 40 |
| `llama3:8b-instruct-q4_K_M` | untouched base model | 0.5302 | 0.0467 | 50 |

**Primary test** (Welch, two-sided, unpooled — fixed before any score was seen):

```
difference   +0.55 pp   (trained minus null)
95% CI       [-1.12, +2.21] pp
t = 0.656    df = 74.0   p = 0.5140
prereg MDE   2.98 pp  ->  does NOT clear
alpha 0.05   ->  not significant
```

The confidence interval straddles zero. The difference is a fifth of the smallest effect
the experiment was built to detect. A paired-by-task secondary view agrees (+0.55 pp,
p = 0.7028).

**Plainly: on this instrument, DPO training produced no detectable improvement over its own
control.** That is a real finding, not a failed run — the experiment was designed to be able
to come back empty, and it did.

Full output: [`track-a-run1-aggregate.txt`](track-a-run1-aggregate.txt)

### One thing that is *not* a preregistered result

The untouched base model scored **higher** than both trained arms (0.5302 vs 0.4976 and
0.4921) — a gap of roughly 3–4 pp. The null arm exists precisely to control for the export
path, and the base-vs-null gap is where you would look if you suspected the export itself
costs accuracy.

**No test was run on that comparison and none should be read into it here.** The base
replicates were banked separately as a free reference point; they were never part of the
preregistered design. Running a test on a comparison you chose *after* seeing the numbers is
the exact thing preregistration exists to prevent. It is written down as an observation
worth a properly designed follow-up, and nothing more.

---

## What this result cannot show

Stated by the analysis itself, and it matters:

> One checkpoint per arm. Zero training-seed variance by construction, so this cannot
> support a claim about DPO at any k. A look, not a verdict.

Two more limits already on the record:

- **Task breadth.** The training bank is 13 tasks, effective 9.93 after accounting for
  repetition. That bounds what any result here may claim.
- **Nothing swept.** This is the one adapter that exists. No search was run over learning
  rate, beta, or `rpo_alpha`. "This recipe showed no effect" is not "DPO does not work."

---

## Where the underlying data lives

| Path | What it holds |
|---|---|
| `data/ruler_noise.jsonl` | the 130 per-replicate records behind the table above |
| `data/prereg_track_a_run1.json` | the design, signed before the first replicate was scored |
| `data/ruler_frozen.json` | the frozen 31-task measuring instrument |
| `analyze_run1.py` | the analysis, implementing exactly the preregistered test |
| `data/bank_concentration.json` | how repetitive the training bank is |
| `data/test_adequacy.json` | how good the task tests are at catching wrong answers |
| `council/ruler_noise_analysis_*.txt` | instrument noise characterisation |
| `council/council-report-*.md` | independent review passes, dated |

### Reproducing the headline number

```
python analyze_run1.py
```

Pure standard library, no GPU, a second or two. It self-checks its own t-distribution
against known critical values before it will print a p-value.

---

---

## Unit tests

**54 passed, 0 failed** — run 2026-08-04. Full output:
[`unit-tests.txt`](unit-tests.txt)

```
tests/test_freeze_guard.py     6 passed   the ruler cannot be frozen dishonestly
tests/test_ruler_noise.py      7 passed   the noise decomposition is real
tests/test_screen_sizing.py    4 passed   sizing constants defined once, not retyped
tests/test_sql_domain.py      19 passed   the second (non-Python) domain and its sandbox
tests/test_trace_views.py      6 passed   SFT/KTO/DPO are views of one trace
tests/test_training_seam.py    5 passed   what the model trains on == what it sampled
tests/test_verifier_pin.py     7 passed   the verifier cannot silently use the wrong Python
```

These check the *machinery* — that the measuring instrument is honest, that the sandbox
refuses what it should, that the training seam matches the sampling seam. **A green suite
here says the apparatus is sound. It says nothing about whether the model got better** —
that is the Track A result at the top, and it came back null.

Reproduce with `python -m pytest tests/ -v` from the repo root. Note these ran on system
Python 3.14, not the `.venv-train` 3.11.9 training environment, which has no pytest
installed.

## What is *not* here

- **Raw run logs.** `council/*.log` (`run1_rescore.log`, `ruler_noise_n40.log`) are excluded
  from version control by `.gitignore` and exist only on the machine that ran them.

## Reading the rest

`instructions.txt` is the project's working channel and single source of truth — 94 numbered
sections, newest last. Section 94 covers this measurement. `OPEN-ITEMS.md` tracks what is
parked and why.
