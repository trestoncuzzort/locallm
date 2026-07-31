# Council Report — srlm-forge — THE PHD, SOLO SEAT — activation #18

**Session:** 2026-07-30 20:32 — answer to the activation #18 DIRECTIVE at the top of
`instructions.txt`.
**Banked as:** **§83**, verbatim. *(§82 was free when I started and taken when I went to
append — a second seat answered the same activation and wrote at 20:36. See "The numbering
race" below.)*
**Read scope:** `instructions.txt` lines 1–260 and §77–§81 (10218–10725), plus code at
commit **`23c3110`** via `git show` — never the working tree, which is on
`fix/screen-sizing-single-source`.
**Research:** 12 web searches, **7 primary sources opened and read** (5 arXiv abstracts,
verl docs, rLLM docs). Browser seats available but **not used** — rung 1 sufficed.
**Verdict:** **GO-WITH-FIXES** — proceed, but the step you were about to take is the cheap
one, and two things you didn't ask about are worth more.

---

## The one-line answer

**Q1 came back THICK, not thin. The verifier interface has converged and costs you an
afternoon. The sandbox-plus-receipt discipline you already built is the part nobody ships.
You have been carrying the seam as the asset and the verifier as the commodity, and it is
the other way round.**

---

## Key numbers

| finding | number |
|---|---|
| Frameworks converging on `(candidate, task) -> float` | **4** (TRL, veRL, `verifiers`, Reasoning Gym) — verified 2 primary, 2 secondary |
| Of those shipping a sandbox / timeout / runtime pin in the interface | **0** (veRL's own docs: sandbox *"will opensource soon"*) |
| `forge.BANNED` blocking non-Python payloads (**executed**) | **0 of 6** — `DROP TABLE`, `ATTACH DATABASE`, `writefile()`, `PRAGMA temp_store_directory`, JSON `$ref`, `(a+)+$` |
| Python-welded sites in `forge.py` — claimed vs found | **4 claimed, ≥6 found** (`ACTOR_SYSTEM` :68, `BANNED` :76 omitted) |
| Rollouts scored per task vs. rollouts used | **4 scored → 1 pair**; 4/4 and 0/4 tasks emit **zero** gradient |
| Sampler-noise floor you have measured | **~3pp**, 40 replicates, 4 decimals, with a CI |
| Verifier-permissiveness you have **not** measured | **unmeasured**; EvalPlus's estimate at this test density is **up to 19.3–28.9 pts** |
| Asserts per task in `SEED_TASKS` | **4–8** (EvalPlus needed ~764/problem to close the gap) |
| Ingestion: text file refused for its NAME before a byte is read (**executed**) | `blob.bin` (pure ASCII) → `'binary file type (.bin)'` |
| NULs entering a char-level vocab past the 8KB probe (**executed**) | **3**, gate says `True | 'text'` |

---

## Ranked critique (compressed)

**F1 — Q1: the interface converged; adopt TRL's signature. READ-ONLY.**
TRL `reward_func(prompts, completions, **kwargs) -> list[float]`; veRL
`compute_score(data_source, solution_str, ground_truth, extra_info=None) -> float`;
`verifiers` `func(prompt, completion, answer, state, **kwargs) -> float` with `Rubric` =
weighted sum; Reasoning Gym `score_answer -> float in [0,1]`. **Semantics converged; ABI did
not.** ADOPT **TRL's**, because `forge.py:27` says output is *"Unsloth DPO ready"* and
Unsloth's DPO trainer **is** TRL's — matching the library you already feed is a
zero-argument decision. **Do not adopt OpenAI's grader schema: it is being deprecated.**
The decisive half: **none of the four ships timeout, sandbox, partial-credit convention or
a runtime pin.** SWE-bench solved it with a **Docker image per instance**; ByteDance with a
separate service. `forge.verify()` (:436–514) already has subprocess isolation, `-I`,
timeout-is-not-wrong (:504–511), a pinned interpreter (:126) and a strict-return-type guard
(:458–475). That is the asset. One free lesson: **all four return a float**; `Result` has the
fields (:416–417) and throws the resolution away at `:501`.

**F2 — the unasked question: you are generating GRPO groups and discarding 75% of each.
READ-ONLY.**
`run_task` samples K=4 (:562), scores all objectively (:569), emits **one** binary pair
(:607) and drops the rest; 4/4-solved emits nothing (:596), 0/4 goes to curriculum (:581).
**DAPO** (arXiv 2503.14476) exists for exactly this — it enforces `0 < |correct| < G`
because *"A zero advantage results in no gradients"* — and oversamples where you **drop the
task**. Your `[0.2,0.8]` band is the same idea at build time: **SFL** (arXiv 2502.12272)
selects by *"the variance of success over multiple attempts"*, i.e. `p(1-p)`. **You built
the selection half of a published recipe and not the training half.** Whether this should be
offline DPO or online GRPO is upstream of every question the DIRECTIVE asked.

**F3 — "only four places are Python-specific" is ≥6, and the two omitted are the dangerous
ones. EXECUTED.**
`ACTOR_SYSTEM` (:68–72) is **imported by `eval.py:35`** — a domain switch breaks the
evaluator, in a file the four-place map doesn't name. `BANNED` (:76–80) blocks **0 of 6**
non-Python payloads. This is the `venv_guard` §65/67 shape **except it fails silently and
green** — the filter becomes a no-op and every log line still says "filtered". Corrections
in your favour: `CODE_RE` (:393) is language-agnostic, so `extract_code` is Python-specific
in **one line** (:407), not one function.

**F4 — Q3: the band screen survives, because your verifier is already deterministic.
READ-ONLY.**
`ruler_noise.decompose()` computes `p["correct"]/p["n"]` over **sampled candidates**
(:263) — it always measured the **sampler**, never the verifier. RLVR *is* the
deterministic-verifier setting; DAPO and SFL operate on sampler stochasticity too. Nothing
in band/Wilson/replicates/MDE is code-specific. **The real hazard is degeneracy, not
determinism** — at temp 0, `p ∈ {0,1}` and the instrument collapses; §77 already measured
the greedy draw constant on **31/31 tasks**. **Consequence: `GEN_TEMP` is a load-bearing
instrument parameter and must be in the receipt beside the verifier bytes. I did not verify
whether it is — `pending`, and if absent it is the §71 defect class, third occurrence.**
Travels unchanged: byte receipt, gate, band, Wilson, MDE, `verify_frozen()`. Does not:
`BANNED`, the strict-type guard (Python object model), the 8s timeout's *value*. The
interpreter pin's **principle travels, mechanism doesn't** — SQL's runtime is
`sqlite3.sqlite_version` + fixture sha + PRAGMA defaults; JSON's is the schema draft;
regex's is the engine.

**F5 — the unmeasured error term is ~7× the measured one. READ-ONLY.**
**EvalPlus** (arXiv 2305.01210, NeurIPS 2023): 80× more tests, pass@k drops **up to
19.3–28.9%**. Your tasks carry 4–8 asserts. **The instrument is precise about the small term
and silent about the big one.** The strict-type guard closes one known hack; it says nothing
about a solution that special-cases five asserted inputs. Cheapest fix: **mutation testing
on the 13 `SEED_TASKS`** — an hour of CPU, no GPU. Note `forge.py:64–65` already scoped
mutation tests as a prerequisite for `EMIT_CONCISENESS`; you found the fix and filed it
under the wrong problem. It is a **ground-truth** fix.

**F6 — Q2: SQL is right; your stated reason is the weak one. READ-ONLY.**
*"sqlite3 is stdlib"* argues **cheap**; you asked for **informative**. The real argument:
**SQL is the only candidate whose verifier has STATE.** JSON-schema and regex are pure
functions of the candidate string — they would fit `verify(code, task) -> Result`
**unchanged**, which is a test that cannot fail. SQL forces four things the interface
doesn't have: (1) fixture setup/teardown between candidates; (2) genuine verifier
non-determinism — `SELECT` without `ORDER BY` is undefined row order, so set-vs-sequence
comparison becomes **task metadata**; (3) natural partial credit (row-set overlap); (4) it
**breaks `BANNED` on contact**, cheaply, where you own the blast radius. Keep regex as a
*third* domain for the timeout channel. **Caution: author your own fixture DB — an
off-the-shelf text-to-SQL benchmark will not sit in `[0.2, 0.8]`.**

**F7 — Q4: mixing helps where pretraining already went; not otherwise. READ-ONLY.**
**Guru** (arXiv 2506.14965, 7B/32B, six domains): *"domains frequently seen during
pretraining (Math, Code, Science) easily benefit from cross-domain RL training, while
domains with limited pretraining exposure (Logic, Simulation, Tabular) require in-domain
training."* **arXiv 2507.17512** (Qwen-2.5-7B, GRPO): *"mutual enhancements and conflicts."*
**Applied to you: SQL will mix fine; a PLC config or proprietary industrial schema is the
exotic case and gets no discount — which is exactly the commercial goal.** Two caveats
bigger than the result: **nobody in this literature is on QLoRA/16GB**, and **all of it is
online RL, not offline DPO** — F2 arriving from another direction. **Product answer: ship
the factory of adapters; run the mixed model as an experiment with the factory as control.**

**F8 — the closed-class claim is PARTIALLY TRUE. EXECUTED.**
**TRUE:** one place. `is_trainable_file` defined once at `make_corpus.py:71–95`,
`start_studio.py:22` imports it, `:37` calls it. No second copy.
**NOT TRUE:** acceptance is not content-only. `BINARY_EXTS` (40 entries, :28–35)
short-circuits at **:87, before a single byte is read** (:90). Executed: a `.bin` holding
pure ASCII → `'binary file type (.bin)'`; a CSV named `.db` → same. **Your own GREEN witness
records this and reads past it** — the RED defect was *"blob.bin refused for its NAME"*, and
GREEN's `'binary file type'` string is emitted from **the extension branch**. Only the
unknown `.dat` exercises the content path. **Plus an unlisted hole:** `looks_like_text`
probes 8192 bytes; NUL is valid UTF-8, so NULs past the window pass the gate *and* survive
`read_text` — 3 NULs enter a char-level vocabulary whose docstring says the vocabulary **is**
the corpus. **Plus:** `start_studio.py:56,59` still print *"Put some .txt/.md/.py files
in:"* — the code stopped advertising the allowlist; the prose didn't.
**Shippable claim, per "when a claim over-reaches, DELETE it":** *"an unknown extension is
never refused for being unknown, and the decision lives in one place."* True, checked,
enough.

---

## THE ONE RECOMMENDED NEXT PROMPT

> Build the SQL domain as a second real instance, and let the seam be discovered. Do not
> design a plugin interface first — Q1 found the interface is a one-line signature that four
> independent frameworks converged on, and the one to match is TRL's
> `reward_func(prompts, completions, **kwargs) -> list[float]`, because `forge.py`'s output
> already feeds Unsloth's DPO trainer, which is TRL's.
>
> Scope it to a fixture SQLite database you author, 12–20 tasks, screened into `[0.2, 0.8]`
> on the same base model, with the same freeze/receipt/gate discipline. Three things must
> come out as evidence, not prose:
>
> 1. **A red witness for `BANNED`** — show it blocks none of `DROP TABLE`,
>    `ATTACH DATABASE`, `writefile()`, `PRAGMA temp_store_directory`, then decide whether the
>    filter goes per-domain or is deleted as security theatre. It is a silent no-op off
>    Python: the §65/67 shape with a green log line.
> 2. **The receipt must pin the SQL runtime and the sampler** — `sqlite3.sqlite_version`
>    (not `sqlite3.version`), the fixture DB's sha256, and `GEN_TEMP`. Check first whether
>    `GEN_TEMP` is already in the frozen ruler artifact for Python; if not, that is the §71
>    defect in a third costume and it is one line to close.
> 3. **Answer the two questions only a stateful verifier can ask, and record what the
>    interface had to grow:** how the fixture is isolated between candidates, and whether row
>    comparison is set- or sequence-equality (task metadata, not a global).
>
> Then bring back the diff between what `verify(code, task) -> Result` provides and what the
> SQL verifier actually needed. **That diff is the interface** — generated from two real
> instances rather than typed by hand.
>
> Separately, and rank it yourself: `run_task` already samples K=4 and scores all four — that
> is a GRPO group (DAPO, arXiv 2503.14476) — and it emits one binary pair and discards the
> rest, with 4/4 and 0/4 tasks yielding no gradient at all. Whether this pipeline should be
> offline DPO or online GRPO is a larger question than which domain is second, and it was not
> on the DIRECTIVE.

---

## The numbering race — §82 was taken while I worked

`grep -c "^82\."` returned **0** when I started and **1** when I went to append;
`instructions.txt` grew **10,724 → 11,667** lines underneath me. A second PhD seat answered
**this same activation #18** and filed `council-report-2026-07-31_2031.md` at **20:36**, two
minutes before my transcript hit disk at 20:38. Per the DIRECTIVE, I appended at **§83**. No
section number is duplicated.

**This is §75/§76 recurring on the very next activation.** §77 recorded that as UNEXPLAINED
and adopted "number from the append" as the fix — which worked perfectly for both seats and
**did nothing about the cause**. By the protocol's own stop rule, this is now a class:
**two seats dispatched for one activation, neither dispatcher aware of the other.** That is
a dispatch defect, not a channel defect, and it costs double quota in a council that was cut
to one seat **specifically to conserve quota** (mandate 2026-07-28).

**My body was sealed to disk before I read any of §82** — sealed sideways, per protocol —
and nothing was revised. Reading ~50 lines of it afterwards as **evidence**: it independently
reports **the structural count is short** (my F3) and **the ingestion claim is narrower than
stated** (my F8). Two blind passes converging raises the weight of both. It also names two
things **I did not check**: a broken `else` in the freeze path still shipping at HEAD
`40f926d`, and an ingestion failure affecting entire writing systems. **Unverified by me —
go to the bytes.** Its coverage of `test_ingest.py` and `screen_tasks.py` is better than
mine; I read neither.

---

## Evidence read

- **Channel:** `instructions.txt` 1–260 (OPERATING PROTOCOL 3–97, full activation #18
  DIRECTIVE 98–227); §77 (10218–10338), §78 (10340–10450), §79 (10452–10544), §80
  (10546–10635), §81 (10637–10725).
- **Code at `23c3110`:** `forge.py` **read in full (721 lines)**; `localllm/make_corpus.py`
  **in full (185)**; `localllm/start_studio.py` **in full (87)**; `ruler_noise.py` ~250 of
  527; `build_ruler.py` ~120 of 387; `eval.py` ~40 of 292.
- **Executed probes** (scratchpad copies of pinned bytes — **no repo file touched, no repo
  code run**): NUL-past-probe-window; `blob.bin`/`data.db` refusal path; `BANNED` vs six
  non-Python payloads; line-number enumeration of Python-welded sites.
- **Primary sources opened:** arXiv 2503.14476 (DAPO), 2502.12272 (SFL), 2305.01210
  (EvalPlus), 2506.14965 (Guru), 2507.17512 (multi-domain), verl reward-function docs, rLLM
  verifiers-integration docs.
- **Not read:** `screen_tasks.py`, `dataset_gate.py`, `venv_guard.py`, `config.py`,
  `tests/`, `localllm/test_ingest.py`, `publish/dpo_README.md`, `data/*`, §1–§74.

## Leftover risks

1. Two domains do not make an interface either — you are buying evidence, not closure.
2. Verifier adequacy (F5) stays unmeasured; building SQL does not measure it.
3. The typing confound (12.8%) is still live and will contaminate any multi-domain result.
4. **`GEN_TEMP` in the receipt is `pending`** — I flagged it and did not verify it.
5. `BANNED` is not a sandbox and a per-domain `BANNED` isn't either; its own comment
   (:74–75) says the end state is a container.
6. **If F2's answer is GRPO, building SQL inside the DPO shape means building it twice.**
   That is a real cost of my own recommendation — the cheapest ordering may be to settle F2
   first.
7. Adapter capacity at 16GB/QLoRA is untested by anyone; you'd be the experiment.
8. The channel still has no write lock, and it fired again this round.

## Non-claims — what this pass did not check

No repo code run; no repo file touched but the three sanctioned writes. Did not read
`screen_tasks.py`/`dataset_gate.py`/`tests/`, so **did not verify `wilson()`,
`BAND_LO`/`BAND_HI`, or whether `GEN_TEMP` is in the receipt**. "≥6 Python-specific sites"
is a **floor and a hand-built list** — the exact thing the protocol says not to trust; no
"all/every/swept" claim. **The `verifiers` interface is UNVERIFIED-AGAINST-SOURCE** (four
404s, `gh` unauthenticated); TRL's exact signature, OpenAI's grader deprecation, SWE-bench's
Docker details, SandboxFusion and Reasoning Gym are **secondary-only** — F1 rests on veRL
and rLLM, which I did open. A claimed Feb-2026 OpenAI SWE-bench audit (59.4% flawed tests)
is **unverified and carries no finding**. **Neither browser seat was used.** Did not check
§1–§74, so if a prior pass raised F2 or F3 I have re-raised them as new. Did not verify the
Unsloth→TRL lineage in this repo's trainer. **Single seat, no peer review; F2 is a strategic
opinion on which reasonable researchers disagree.**

---

*THE PHD, solo seat. Advisory only — no code written, no code modified, no training,
generation or screening command run. Three writes: §83 in `instructions.txt`, this report,
and `council/council-transcript-2026-07-30_2032.md` (the artifact of record).*

**standing by**
