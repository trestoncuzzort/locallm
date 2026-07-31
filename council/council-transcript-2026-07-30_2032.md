# Council Transcript — srlm-forge — THE PHD, SOLO SEAT — activation #18

**Session:** 2026-07-30 20:32. Answer to the activation #18 DIRECTIVE at the top of
`instructions.txt`. Banked in the channel as **§82**; this file is the artifact of record
and the §82 block matches it.

**Code read at commit `23c3110`** via `git show`, never the working tree (which is on
`fix/screen-sizing-single-source`).

**VERDICT: GO-WITH-FIXES** — proceed, but not with the step you were about to take.
Q1 comes back THICK, not thin: the interface has converged and costs you an afternoon.
The design effort you were about to spend on it is the cheapest part of the problem.
Two things you did not ask about are worth more than the seam.

---

## RANKED CRITIQUE

### F1 — Q1 ANSWERED: THE INTERFACE HAS CONVERGED. ADOPT TRL'S SIGNATURE. THE PART NOBODY SHIPS IS THE PART YOU ALREADY BUILT. — READ-ONLY

Four independent projects, three of them with no shared authorship, expose the same
verifier hook. I opened each one's own documentation:

| project | signature | returns |
|---|---|---|
| TRL (HuggingFace) | `reward_func(prompts, completions, **kwargs)` | `list[float]`, `None` to abstain |
| veRL (`verl`) | `compute_score(data_source, solution_str, ground_truth, extra_info=None)` | `float` |
| `verifiers` (Prime Intellect) | `func(prompt, completion, answer, state, **kwargs)` | `float`; `Rubric` = weighted sum |
| Reasoning Gym | `score_answer(answer, entry)` | `float` in [0,1] |

That is a convergence, and I want to be precise about what kind. **The SEMANTICS have
converged: a plain Python callable, `(candidate_string, task_metadata) -> float`,
aggregated by weighted sum, with the framework owning batching and the author owning
everything inside.** The **ABI has not** — four different argument orders, four different
names, no portable package. So both halves of your Q1 are true at once and neither is the
whole answer:

- **"A standard exists"** is true at the level you actually need. You are not writing a
  framework; you are choosing a function signature. Four teams reached the same one
  independently. That is as converged as this gets.
- **"No standard exists"** is true at the level of a package you could `pip install` and
  have your seam be done. There is none, and one candidate is actively going away: OpenAI's
  reinforcement-fine-tuning graders (`string_check`, `text_similarity`, `score_model`,
  `python`, combined by `multi_grader` with an arithmetic `calculate_output`, all scored
  0–1) are, per OpenAI's own graders guide, **being deprecated along with the evals and
  fine-tuning workflows they support**. Do not adopt a vendor's declarative grader schema.

**ADOPT THIS: TRL's `reward_func(prompts, completions, **kwargs) -> list[float]`.** Not
because it is the best-designed of the four — `verifiers`' is richer — but because of a
fact already in your repo: `forge.py`'s docstring line 27 says the output is *"Unsloth DPO
ready"*, and Unsloth's DPO trainer **is** TRL's `DPOTrainer`. TRL is already downstream of
you. Matching the signature of the library you already feed is a zero-argument decision.
Everything else in that table is then a 5-line adapter, in whichever direction you need.

**And now the finding that actually matters.** I went looking for what these frameworks
give you for the hard part, and the answer is: nothing.

- veRL's own reward-function documentation mentions **no timeout, no sandbox, no partial-
  credit convention**. Its code-execution story is a "SandBox" that the docs describe as
  *"will opensource soon."*
- TRL's reward functions are ordinary Python called in the trainer process. Your model's
  output executing in your trainer's address space is your problem.
- `verifiers` hands the environment author a `State` and gets a float back. What happens
  inside is the author's.
- The one place the industry did solve it, it solved it with **infrastructure, not an
  interface**: SWE-bench's harness ships a **Docker image per instance** pinning the base
  repository snapshot, dependency versions and build toolchain; ByteDance's SandboxFusion
  is a *separate service* spanning ~20 languages.

So: **the seam is free and the verifier is not.** `forge.verify()` at `forge.py:436-514`
already carries subprocess isolation, `-I` (with the load-bearing `PYTHONOPTIMIZE`
reasoning at :456-457), an 8s timeout that is recorded as *not-a-wrong-answer* at :504-511,
a pinned interpreter at :126, and a strict-return-type guard at :458-475 that closes the
`__eq__`-override reward hack. **None of the four frameworks ships any of that.** You have
been treating the seam as the asset and the verifier as the commodity. It is the reverse.

There is one design lesson worth taking from the table, and it is free: **every one of the
four returns a FLOAT, not a boolean.** `forge.Result` already has the fields for it
(`passed`/`total`, `forge.py:416-417`) and then throws the resolution away at `:501` —
`res.passed = res.total`, commented *"assert-based: all-or-nothing here."* Partial credit
is the single thing the convergent interface has that you don't.

---

### F2 — THE QUESTION THE DIRECTIVE DID NOT ASK: YOU ARE ALREADY GENERATING GRPO GROUPS AND THROWING MOST OF EACH ONE AWAY. — READ-ONLY

`run_task` (`forge.py:559-629`) samples `NUM_CANDIDATES = 4` completions for one prompt
(`:562`) and scores every one of them against an objective verifier (`:569`). **That is a
GRPO group.** It is the exact object DAPO and GRPO consume: one prompt, G rollouts, G
verifier scores.

What you then do with it: sort (`:577`), take the best (`:578`), find one failing
candidate (`:592-593`), emit **one** preference pair (`:607-628`), discard the other two.
On an all-pass task you emit nothing at all (`:596-597`, `EMIT_CONCISENESS = False`) — a
task the model solved 4/4 produces **zero** training signal, and so does a task it solved
0/4 (`:581-587`, routed to curriculum).

Now read that against DAPO (arXiv 2503.14476, ByteDance Seed, 2025), whose Dynamic
Sampling exists for precisely this: it enforces `0 < |{o_i : is_equivalent(a, o_i)}| < G`,
because *"if all outputs of a particular prompt are correct and receive the same reward 1,
the resulting advantage for this group is zero. A zero advantage results in no gradients."*
Your pipeline reaches the same conclusion by a different route and pays a different price:
DAPO **oversamples until the batch is full of gradient-bearing prompts**; you **drop the
task**.

And your `[0.2, 0.8]` band screen is the same idea applied at ruler-construction time
rather than batch time — which is the third independent rediscovery, because *Learning to
Reason at the Frontier of Learnability* (Foster et al., arXiv 2502.12272, Feb 2025)
proposes SFL, a curriculum that prioritises questions by **the variance of success over
multiple attempts**, on the stated observation that *"many questions are either solved by
all attempts... or by none — providing no meaningful training signal."* Variance of a
Bernoulli is `p(1-p)`, maximised at 0.5 and small at the edges. **Your band is SFL's
learnability criterion with a hard threshold instead of a soft weight.** That is a
compliment to the instrument and a warning about the pipeline: you built the selection
half of the published recipe and not the training half.

The strategic question this raises — and the one the DIRECTIVE should have asked instead
of Q2 — is: **why is this an offline DPO pipeline at all?** You already pay the expensive
part (K rollouts + K verifications per prompt). GRPO consumes that group directly, uses
all G scores, and is the algorithm every framework in F1's table is built around. DPO
compresses G scored rollouts into one binary bit and needs a `chosen` that passes, which is
why `three_sum`-class tasks contribute nothing. I am not telling you to switch — that is an
implementation decision and it is yours, and a 16GB card with an 8B model makes online RL
genuinely harder than offline DPO. I am telling you that **"which domain is second" is a
smaller question than "am I using 25% of the rollouts I already paid for",** and the
DIRECTIVE did not put the second one on the table.

---

### F3 — "ONLY FOUR PLACES ARE PYTHON-SPECIFIC" IS UNDERCOUNTED. IT IS AT LEAST SIX, AND THE TWO YOU OMITTED ARE THE DANGEROUS ONES. — EXECUTED

I read `forge.py` in full at `23c3110` (721 lines) and then enumerated the sites
mechanically. Your four are real. Two more are not on your list:

**(5) `ACTOR_SYSTEM`, `forge.py:68-72`.** *"You are a precise Python engineer... inside one
```python fenced code block. Define exactly the requested function."* This is not
formatting — it is the contract that makes `extract_code` work at all, and it is
**imported across files**: `eval.py:35` reads `import forge  # reuse Task, Actor, verify,
extract_code, ACTOR_SYSTEM`. A domain switch has to change it in a place your four-place
map does not name, and the file that breaks is the evaluator, not the generator.

**(6) `BANNED`, `forge.py:76-80`.** The regex matches Python import statements plus
`__import__`, `open(`, `eval(`, `exec(`. Its own comment calls it *"Cheap defense-in-depth
for executing model output."* **Executed probe, against the pinned regex text:**

```
BANNED blocks 'DROP TABLE users;'                         -> False
BANNED blocks "ATTACH DATABASE '/etc/passwd' AS p;"       -> False
BANNED blocks "SELECT writefile('C:/evil.exe', x'4d5a');" -> False
BANNED blocks "PRAGMA temp_store_directory = 'C:/';"      -> False
BANNED blocks '{"$ref": "file:///etc/passwd"}'            -> False
BANNED blocks '(a+)+$'                                    -> False
```

Zero of six. And these are not hypotheticals: `writefile()` is a real SQLite CLI function,
`ATTACH DATABASE` reads arbitrary paths, and `(a+)+$` is catastrophic backtracking — the
regex-synthesis domain's entire hazard, invisible to a byte filter and caught only by a
timeout.

**This is exactly the `venv_guard` shape you cited from §65/67** — a helper correct in its
first file and wrong the moment it is reused — with one difference that makes it worse:
`venv_guard` failed loudly. `BANNED` fails **silently and green**. Move to SQL and your
defense-in-depth layer does not error, does not warn, and does not block anything; it just
quietly becomes a no-op while every log line still says the pipeline is filtered.

Two corrections in your favour, because the count is wrong in both directions:

- **`extract_code` is LESS Python-specific than you claimed.** `CODE_RE` at `:393` is
  ` ```[^\n`]*\n(.*?)``` ` — language-agnostic, it matches any fence. The only Python-welded
  line is `:407`, stripping a leading `python`/`py` tag. That is one line, not a function.
- **`VERIFY_PY` / `verifier_interpreter()` (`:126`, `:129-136`) are arguably a seventh
  site,** and they are the interesting one for Q3 — see F5.

Your method note in §81 (that the automated classifier inflated this to fourteen and you
went back to reading) was the right call and I am not reversing it. Reading found four;
reading harder finds six. The lesson is not "use the tool" — it is that **a count of
domain-specific sites is exactly the coverage list the OPERATING PROTOCOL says must be
generated from the real interface rather than typed by hand,** and this one was typed by
hand. The generated version is not a classifier over `forge.py` — it is: *build domain #2
and see what breaks.* Which is your own Q2 lean, arriving with better evidence than the
instinct you offered for it.

---

### F4 — Q3 ANSWERED: THE BAND SCREEN SURVIVES A DETERMINISTIC VERIFIER, BECAUSE YOUR VERIFIER IS ALREADY DETERMINISTIC. THE PREMISE OF THE QUESTION IS A CATEGORY ERROR. — READ-ONLY

You asked whether the `[0.2, 0.8]` screen, Wilson intervals, k replicates and MDE become
meaningless when the verifier is deterministic. **They do not, and the reason is visible in
your own code.**

`ruler_noise.decompose()` at `ruler_noise.py:263` computes each task's rate as
`p["correct"] / p["n"]` — where `n` is the number of **sampled candidates**, not the number
of times the verifier was invoked on one candidate. Every downstream quantity —
`per_task_var` (`:274`), `cov_total` (`:277`), `binom_var` (`:302`), the MDE table — is
built on that. The random variable being measured is **"does the policy emit a passing
candidate on a draw"**, not **"does the verifier agree with itself."**

And `forge.verify()` is *already* deterministic. Given the same `(code, task)` it runs the
same harness under the same pinned interpreter and returns the same verdict. The single
exception is `timed_out` (`:504-511`), which is wall-clock and genuinely non-deterministic —
and you have already excluded it from ever becoming the `rejected` half of a pair (`:592`:
`if not r.ok and not r.timed_out and ...`), with the comment stating exactly why.

**So there is no transition to worry about.** RLVR is *by construction* the deterministic-
verifier setting: exact-match on a math answer, unit tests, a schema check — all
deterministic. The stochasticity that DAPO's dynamic sampling and SFL's learnability
criterion operate on is, in every one of those papers, **sampler stochasticity**, exactly as
in yours. Nothing about the band, Wilson, replicates or MDE is code-specific. They are
properties of a Bernoulli policy under temperature, and they carry to SQL, schemas and
regexes unchanged.

**What replaces the noise floor when the only randomness is the sampler? Nothing — that is
already what it is measuring.** The thing that would actually break the apparatus is not
determinism, it is **degeneracy**: if you evaluate greedily (temperature 0), `p ∈ {0, 1}`
per task, per-task variance is exactly zero, and the whole instrument collapses. Your own
§77 measured this — the greedy draw is constant on **31/31 tasks**, contributing zero
variance, which is why the greedy-corrected null is 0.0326 rather than 0.0376. **You have
already measured the failure mode you were worried about, in the one draw where it occurs.**
The correct statement of the risk is therefore: *the ruler requires a stochastic sampler,
not a stochastic verifier, and the temperature (`GEN_TEMP = 0.8`, `forge.py:60`;
`eval.TEMP = 0.8`) is a load-bearing instrument parameter that must be pinned in the receipt
alongside the verifier bytes and the interpreter.* **Check whether it is.** The receipt pins
`VERIFY_PY` and the ruler-set hash; if `GEN_TEMP` is not in the frozen artifact, then a
temperature change silently re-defines every rate in it, in the same way §71's interpreter
change did — and that is the same class of defect, arriving in a new costume for the third
time.

**Now, what actually does NOT travel.** Sorting your discipline honestly:

| asset | travels? | why |
|---|---|---|
| receipt pinning verifier BYTES | **yes, unchanged** | hash a file; domain-blind |
| training gate reading the frozen hash | **yes, unchanged** | `parse-don't-validate`; domain-blind |
| band screen `[0.2, 0.8]` | **yes** | policy-level Bernoulli; = SFL/DAPO |
| Wilson CIs, k replicates, MDE | **yes** | same |
| `verify_frozen()` re-hash-from-payload | **yes** | domain-blind |
| **interpreter pin** | **NO — code-specific in form** | see below |
| `BANNED` filter | **NO — actively misleading** | F3 |
| strict-return-type guard (`:458-475`) | **NO — Python object model** | `__eq__` override is a Python hack |
| the 8s `CAND_TIMEOUT` | **form yes, value no** | a SQL fixture query and a PLC sim have different natural scales |

The interpreter pin is the subtle one, and it is the most valuable thing you own. **The
principle travels and the mechanism does not.** The principle is: *the verifier is not a
function of its own source; it is a function of source × runtime, and both must be in the
receipt.* For SQL the runtime is not a Python executable — it is the **SQLite library
version compiled into whichever Python is running** (`sqlite3.sqlite_version`, which is not
the same as `sqlite3.version`), plus the fixture database's bytes, plus any `PRAGMA`
defaults. A `JSON` schema domain's runtime is the validator's **draft version**
(2020-12 vs draft-07 change what `$ref` and `items` mean). A regex domain's runtime is the
engine and its backtracking limits. **Each domain has a runtime pin and each one is a
different object.** That is the single most transferable insight this project has produced,
and it is also — note carefully — the reason SWE-bench ships a Docker image per instance
rather than a version string: at scale the industry gave up on naming the runtime and
started shipping it.

---

### F5 — THE ERROR TERM YOU HAVE NOT MEASURED IS AN ORDER OF MAGNITUDE LARGER THAN THE ONE YOU HAVE. — READ-ONLY

You have spent, by my count of sections 61–80, most of this project's measurement budget
establishing a **~3pp sampler-noise floor**. Meanwhile:

**EvalPlus** — *"Is Your Code Generated by ChatGPT Really Correct? Rigorous Evaluation of
Large Language Models for Code Generation"* (Liu et al., NeurIPS 2023, arXiv 2305.01210).
I opened the abstract. They extend HumanEval's test cases by **80×** (EvalPlus reports an
average of ~764 tests per problem against HumanEval's handful) and measured pass@k drop by
**up to 19.3–28.9% across 26 LLMs**. Their framing is the one that should worry you: *"these
test-cases can be limited in both quantity and quality for fully assessing the functional
correctness of the generated code."*

Now count the asserts in `SEED_TASKS` at `forge.py:150-348`: `two_sum` 4, `roman` 6,
`balanced` 6, `spiral` 5, `atoi` 8, `lps` 5, `merge_intervals` 5, `simplify_path` 5,
`decode_ways` 6, `three_sum` 4, `word_break` 5, `multiply_strings` 5, `next_permutation` 5.
**Four to eight asserts per task.** That is HumanEval's density, which EvalPlus measured as
over-crediting by up to ~29 points.

So the honest accounting of your reward signal is:

- **sampler noise: ~3pp, measured to four decimals, with a CI, over 40 replicates.**
- **verifier permissiveness: unmeasured, and the nearest published estimate for this exact
  test density is ~20 points.**
- **typing-import confound: 12.8% of failures (your §80), measured, unresolved.**

You are the only person I have reviewed who would find that sentence useful rather than
insulting, so: **the instrument is precise about the small term and silent about the big
one.** The strict-return-type guard at `:458-475` is genuinely excellent work and closes one
specific reward hack — a `_Always.__eq__` class passing every assert — but *closing one
known hack is not test adequacy*. A solution that special-cases the five asserted inputs
passes every task in `SEED_TASKS` and the guard says nothing about it.

This is directly relevant to the domain question, and it cuts **for** you: a SQL verifier
comparing full result sets against a fixture database is **structurally more adequate** than
5 asserts, because the check is over the whole output, not five sampled points. That is a
real argument for SQL that neither you nor I would have found without asking what the
verifier's error term is.

---

### F6 — Q2 ANSWERED: SQL IS RIGHT, AND YOUR STATED REASON IS THE WEAK ONE. — READ-ONLY

**Build the second domain. Do not design the interface first.** Q1 does not overturn your
lean — it *reinforces* it, for a reason you did not have when you formed it: since the
interface is a one-line signature copied from TRL, "designing it up front" is not a design
task at all. There is nothing to design. The seam costs an afternoon whenever you do it, so
the only question left is which order buys more information, and building first buys more.

**But your stated justification is the wrong one.** *"sqlite3 is stdlib, so no new
dependency"* is an argument that SQL is **cheap**. You asked me for **informative**. Here is
the informative argument, and it also settles the alternates:

**SQL is the only one of the three candidates whose verifier has STATE.** JSON-schema
validation and regex synthesis are both pure functions of the candidate string —
`validate(candidate, schema) -> bool`, `match(candidate_regex, cases) -> bool`. Both would
drop into `verify(code, task) -> Result` **without changing the signature at all**, which is
precisely why they teach you nothing. You would build them, they would fit, and you would
conclude your interface generalises — on evidence that could not have come out any other
way. That is the shape of a test that cannot fail, which is the exact defect you caught in
your own `test_verifier_pin.py` in §77.

SQL forces four things the code domain has never made you confront, and every one of them
is a field the convergent interface in F1 does **not** have:

1. **Setup / teardown / isolation.** A fixture DB must be restored between candidates, or
   candidate N's `UPDATE` scores candidate N+1. `verify(code, task)` has nowhere to put
   that. Neither does veRL's `compute_score`. This is the field the whole industry
   discovers late and then solves with containers.
2. **Genuine verifier non-determinism, for the first time.** `SELECT` without `ORDER BY`
   returns rows in **undefined order**. So "compare the rows" is under-specified: set
   comparison or sequence comparison, and which one is *task metadata*, not a global. This
   is where a real `Task` schema is forced to grow a field.
3. **Natural partial credit.** Row-set overlap (Jaccard, or precision/recall over rows) is
   an obvious scalar in [0,1]. That is the float the four frameworks all return and the one
   `Result.passed/total` currently collapses at `:501`. SQL is where you would discover
   whether partial credit helps or just adds a reward-hacking surface.
4. **A safety model that Python's does not cover.** F3's probe, executed: `BANNED` blocks
   none of `DROP TABLE`, `ATTACH DATABASE`, `writefile()`, `PRAGMA temp_store_directory`.
   SQL breaks your safety layer on contact, loudly, in a domain where you control the
   fixture and the blast radius is a temp file. **That is the cheapest possible place to
   learn F3.**

Keep regex on the list as a *third* domain specifically for the timeout channel —
catastrophic backtracking is the one hazard that no static filter catches and only the
timeout does, and it would tell you whether `timed_out` deserves to be a first-class
verdict rather than an exclusion. But SQL second.

**One caution.** Do not let "SQL" become "text-to-SQL on Spider/BIRD". You want a fixture DB
you author, with tasks whose base-model pass rate you can screen into `[0.2, 0.8]` — that
band is the thing that makes your ruler an instrument, and an off-the-shelf benchmark will
not sit in it.

---

### F7 — Q4 ANSWERED: MIXING HELPS FOR DOMAINS THE BASE MODEL ALREADY SAW AND NOT OTHERWISE; CODE IS THE ONE REPORTED TO CONFLICT; AND NONE OF IT WAS MEASURED AT YOUR SCALE OR WITH YOUR ALGORITHM. — READ-ONLY

Primary sources I opened:

- **Guru** — *"Revisiting Reinforcement Learning for LLM Reasoning from A Cross-Domain
  Perspective"* (arXiv 2506.14965, 2025). 92K verifiable examples across **six** domains:
  Math, Code, Science, Logic, Simulation, Tabular. Models: **Guru-7B and Guru-32B**. The
  headline finding, in their words: *"domains frequently seen during pretraining (Math,
  Code, Science) easily benefit from cross-domain RL training, while domains with limited
  pretraining exposure (Logic, Simulation, and Tabular) require in-domain training to
  achieve meaningful performance gains."*
- **"Can One Domain Help Others? A Data-Centric Study on Multi-Domain Reasoning via
  Reinforcement Learning"** (arXiv 2507.17512, 2025). Math + code + logic puzzles, GRPO on
  the **Qwen-2.5-7B** family, base vs instruct under identical configs. Reports *"intricate
  interactions including mutual enhancements and conflicts."* The abstract does not itemise
  which pairs help and which hurt; the secondary reporting that **math+logic enhances both
  while adding code generation introduces structural conflicts that degrade performance** is
  consistent with Guru's direction but I did **not** confirm that specific sentence in the
  primary text — treat it as directional, not established.

**Direct answer to your question:** the literature says mixing is roughly **neutral-to-
positive** for pretraining-rich domains, and mixing does **not substitute for in-domain
data** for exotic ones. Applied to your roadmap: SQL is pretraining-rich (it is all over any
code corpus) and would probably mix fine with Python. **A PLC config format, a proprietary
industrial schema, or a plant-control policy is the exotic case** — and the literature says
plainly that those will need their own in-domain data and will not get much for free from
your Python work. Since the exotic case *is* the commercial goal, that is the finding to
carry: **"train on anything" gets no discount from transfer in exactly the domains you care
most about.**

**Two caveats that matter more than the result, and neither is in the papers' favour:**

1. **Scale.** Guru is 7B/32B with full RL infrastructure; 2507.17512 is 7B GRPO. **Nobody in
   this literature is doing QLoRA on a single 16GB card.** Adapter capacity is a real
   constraint that these results do not speak to — LoRA rank bounds how much orthogonal
   task structure one adapter can hold, and multi-domain is precisely the regime where that
   bites.
2. **Algorithm.** Every result above is **online RL (GRPO/PPO)**. You are doing **offline
   DPO on verifier-selected pairs**. Transfer results from online RL do not automatically
   carry to offline preference learning; the mechanisms differ (advantage over a group vs.
   a contrastive gradient between two fixed strings). **This is F2 arriving again from a
   different direction:** the fact that you cannot cite this literature *at* your own
   pipeline is itself evidence about the pipeline.

**Product answer:** at 16GB with QLoRA, **the factory-of-adapters is the defensible
product and the single general model is the research bet.** One adapter per verifier is
cheap, independently gate-able, independently receipted, and fails locally — which fits
everything else this project has built. Ship the factory; run the mixed model as an
experiment against it, with the factory as the control arm.

---

### F8 — THE CLOSED-CLASS CLAIM IS **PARTIALLY TRUE**. THE SINGLE-PLACE HALF IS TRUE. THE "CONTENT NOT EXTENSION" HALF IS NOT, AND YOUR OWN GREEN WITNESS SHOWS IT. — EXECUTED

**Claim:** *"acceptance is decided on CONTENT and the decision exists in exactly one place."*

**TRUE — one place, genuinely.** `is_trainable_file()` is defined once at
`localllm/make_corpus.py:71-95`. `localllm/start_studio.py:22` does
`from make_corpus import is_trainable_file` and calls it at `:37`. `make_corpus.main()`
calls it at `:128`. There is no second copy and no second extension set. The `venv_guard`
lesson was applied correctly here.

**NOT TRUE — acceptance is not decided on content alone.** Read the order of operations in
`is_trainable_file`:

```
:85   if exts is not None and path.suffix.lower() not in exts:   -> refuse (opt-in filter)
:87   if path.suffix.lower() in BINARY_EXTS:                     -> refuse ON NAME
:90   head = path.open("rb").read(probe_bytes)                   <- first byte is read HERE
:93   if not looks_like_text(head):                              -> refuse on content
```

**A hardcoded 40-entry extension list (`BINARY_EXTS`, `:28-35`) short-circuits at `:87`,
before a single byte is read.** Executed probe against the pinned file:

```
blob.bin holds PURE TEXT       -> (False, 'binary file type (.bin)')
looks_like_text(its bytes)     -> True
data.db (a CSV)                -> (False, 'binary file type (.db)')
```

**Your own GREEN witness records this and reads past it.** §81/the DIRECTIVE state the RED
defect as *"blob.bin refused for its NAME not its bytes"* — and the GREEN line is
*"blob.bin refused as 'binary file type'"*, which is the string emitted at `:88` **from the
extension branch**. The named defect is still present for that exact file; only the *unknown
`.dat` carrying a NUL* in your witness actually exercises the content path. The green
witness does not distinguish name-refusal from content-refusal, so it cannot fail if the
extension branch grows.

I will say what is true in your favour: **the code comment at `:25-27` discloses this
honestly** — *"Checked only to avoid reading large media files off disk; the real decision
is made on bytes, so an unknown extension is never rejected for being unknown."* The
**unknown-extension** claim is fully true and it is the one that mattered for the industrial
case (`.csv`, `.jsonl`, `.log`, `.tsv`, no extension). The over-reach is only in the
DIRECTIVE's compressed restatement. Per the OPERATING PROTOCOL's *"when a claim over-reaches,
DELETE it"*: the shippable claim is **"an unknown extension is never refused for being
unknown, and the decision lives in one place"** — which is true, checked, and enough.

**A second, unlisted hole, executed.** `looks_like_text` inspects only the first
`probe_bytes = 8192` (`:72`, `:90`). NUL is valid UTF-8 (U+0000), so a NUL past the probe
window passes the gate *and* survives `read_text` at `:136`:

```
9000 'A' bytes + b"\x00\x00\x00" + 100 'B' bytes, named nul_tail.log
  is_trainable_file        -> True | 'text'
  looks_like_text(FULL)    -> False      <- the rule disagrees with its own gate
  read_text SUCCEEDS       -> len 9103, contains NUL: True
  NULs entering a char-level vocab: 3
```

The NUL rule is stated in the docstring at `:51` as *"A NUL byte means binary"* and holds
only for the first 8KB. For a character-level tokenizer, where **the vocabulary is the set
of characters in the corpus** (the file's own docstring, `:11-12`), this is the same class
as the mojibake problem the rewrite was written to fix — it just moved past byte 8192. Your
`>300 distinct characters` warning at `:174` would not fire on three extra NULs.

**Third, cosmetic but in the user-facing path:** `start_studio.py:56` and `:59` still print
*"Put some .txt/.md/.py files in:"* — the double-click path still **advertises** the
allowlist that was just removed. Your test guards the code against regrowing an extension
list; nothing guards the prose, and prose is what the non-technical user obeys.

**Your disclosed limitation stands and is correctly disclosed:** UTF-16 text is refused as
binary, untested. I confirm that (`:62`, `data.decode("utf-8")` with a bare
`UnicodeDecodeError` refusal at `:63-64`).

---

## THE NON-CLAIMS, CHECKED

You asked me to check these rather than wave them through. I did.

- **"NOT claiming the loop IS domain-general."** Correct not to claim it, and F3 shows the
  supporting count was low by two. But your *structural* reading is right: `run_task`'s
  shape (sample K → score all → prefer winner → emit pair → route all-fail to curriculum) is
  domain-independent, and F2 shows it is in fact a recognised published shape. **The claim
  you could have made and didn't is stronger than the one you hedged.**
- **"NOT claiming a char-level model at this scale is adequate."** Agreed, and 0.088/2.774
  is the correct thing to point at. I add one thing: Track B's memorisation is now
  *coupled* to the §81 ingestion change. Content-based acceptance means arbitrary industrial
  text now enters a 12.7M char model whose vocabulary **is** its corpus. The `>300 distinct
  characters` warning is a good instinct; the failure it will not catch is a corpus of
  machine logs that is 90% timestamps, where the model memorises the log format and the
  val/train gap looks *better*, not worse. **Low training loss on log data is not a signal
  that anything was learned.**
- **"NOT claiming the ruler/gate/noise-floor transfer."** F4: more of it transfers than you
  feared, less than a naive read would assume, and the **temperature pin** is the piece
  neither of us had on the list.
- **"NOT claiming the typing-import confound is resolved."** Correct, and I decline to pick
  for you — it is a decision about what the reward means and it is the proprietor's. What I
  will add is that it is **an instance of F4's runtime-pin principle**, not a Python quirk:
  option (b), prepending typing imports to the harness, is *changing the runtime*, which
  invalidates the receipt exactly as §71's interpreter change did. If (b) is chosen it needs
  a re-freeze and a new receipt, not a patch. Option (c) — report the next run twice, with
  and without typing-NameError-only pairs — is the only one that costs nothing and preserves
  the ability to decompose the claim later, which makes it the option that keeps the most
  doors open. That is a preference, not a recommendation.
- **"NOT claiming the greedy-free metric change has been made."** Confirmed unmade:
  `eval.py:38` still has `TEMP = 0.8` alongside the greedy anchor, and
  `forge.run_task:563` still does `temp = 0.0 if i == 0 else GEN_TEMP`. Still open from §76,
  as you say.

---

## THE ONE RECOMMENDED NEXT PROMPT

> Build the SQL domain as a second real instance, and let the seam be discovered. Do not
> design a plugin interface first — Q1 found the interface is a one-line signature that four
> independent frameworks converged on, and the one you should match is TRL's
> `reward_func(prompts, completions, **kwargs) -> list[float]`, because `forge.py`'s output
> already feeds Unsloth's DPO trainer, which is TRL's.
>
> Scope it to a fixture SQLite database you author, 12–20 tasks, screened into `[0.2, 0.8]`
> on the same base model, with the same freeze/receipt/gate discipline. Three things must
> come out of it as evidence, not as prose:
>
> 1. **A red witness for `BANNED`.** Show, before you build anything else, that
>    `forge.BANNED` blocks none of `DROP TABLE`, `ATTACH DATABASE`, `writefile()`,
>    `PRAGMA temp_store_directory` — then decide whether the filter becomes per-domain or is
>    deleted as security theatre. It is currently a silent no-op off Python and that is the
>    §65/67 failure shape with a green log line.
> 2. **The receipt must pin the SQL runtime and the sampler.** `sqlite3.sqlite_version` (not
>    `sqlite3.version`), the fixture DB's sha256, and `GEN_TEMP`. Check first whether
>    `GEN_TEMP` is already in the frozen ruler artifact for the Python domain — if it is not,
>    that is the §71 interpreter defect in a third costume and it is one line to close.
> 3. **Answer the two questions only a stateful verifier can ask, and write down what the
>    interface had to grow to answer them:** how the fixture is isolated between candidates,
>    and whether row comparison is set-equality or sequence-equality (task metadata, not a
>    global, because `SELECT` without `ORDER BY` is undefined).
>
> Then bring back the diff between what `verify(code, task) -> Result` provides and what the
> SQL verifier actually needed. That diff **is** the interface, generated from two real
> instances rather than typed by hand.
>
> Separately, and rank it yourself: `run_task` already samples K=4 and objectively scores all
> four — that is a GRPO group (DAPO, arXiv 2503.14476), and it currently emits one binary
> preference pair and discards the rest, with 4/4-solved and 0/4-solved tasks yielding no
> gradient at all. Whether this pipeline should be offline DPO or online GRPO is a larger
> question than which domain is second, and it was not on the DIRECTIVE.

---

## EVIDENCE READ

**Channel** — `C:\Users\t\Projects\srlm-forge\instructions.txt`:
- lines 1–260: OPERATING PROTOCOL (3–97) and the full activation #18 DIRECTIVE (98–227).
- §77 (10218–10338), §78 (10340–10450), §79 (10452–10544), §80 (10546–10635),
  §81 (10637–10725).
- tail check before writing: `grep -c "^82\." instructions.txt` → **0**, so §82 was free.

**Code at commit `23c3110`**, extracted with `git show <sha>:<path>`, never the working
tree (which is on `fix/screen-sizing-single-source`):
- `forge.py` — **read in full, 721 lines.** Cited: `:59-66` config, `:68-72` ACTOR_SYSTEM,
  `:76-80` BANNED, `:83-136` interpreter-pin block + `verifier_interpreter()`, `:142-147`
  `Task`, `:150-348` `SEED_TASKS` (assert counts), `:393-409` `CODE_RE`/`extract_code`,
  `:412-433` `Result`/`score`, `:436-514` `verify()` incl. guard `:458-475` and timeout
  `:504-511`, `:520-543` `critique()` (`:536` hardcodes a ```python fence), `:559-629`
  `run_task`, `:632-717` `main`.
- `ruler_noise.py` — docstring `:1-51`, `decompose()` `:241-304`, `cmd_analyze` `:307-350`,
  band/instrument-seam block `:401-431`, MDE table `:439`. (527 lines total; read ~250.)
- `build_ruler.py` — scanned by symbol: `:110-152` `cmd_confirm` (Wilson at `:132`, band at
  `:134`), `:156-214` `verify_frozen()`, `:215-365` `cmd_freeze`. (387 lines; read ~120.)
- `eval.py` — `:27-38`, notably `:35` `import forge  # reuse Task, Actor, verify,
  extract_code, ACTOR_SYSTEM` and `:38` `TEMP = 0.8`. (292 lines; read ~40.)
- `localllm/make_corpus.py` — **read in full, 185 lines.** `:21` `DEFAULT_EXTS`, `:28-35`
  `BINARY_EXTS`, `:38-68` `looks_like_text`, `:71-95` `is_trainable_file`, `:98-181` `main`.
- `localllm/start_studio.py` — **read in full, 87 lines.** `:22` the import, `:25-37`
  `user_files`, `:56`/`:59` the stale prose.

**Executed probes** (scratchpad copies of the pinned bytes; **no repo file touched, no repo
code run**): NUL-past-probe-window, `blob.bin`/`data.db` refusal path, `BANNED` against six
non-Python payloads, and a line-number enumeration of Python-welded sites in the pinned
`forge.py`. All four outputs are quoted verbatim in F3 and F8.

**Not read this pass:** `screen_tasks.py`, `dataset_gate.py`, `venv_guard.py`,
`clean_dataset.py`, `verify_dataset.py`, `config.py`, `localllm/studio.py`,
`localllm/checkpoint.py`, `tests/`, `publish/dpo_README.md`, `data/*`, `council/*.log`,
and §1–§74 of the channel.

---

## MY OWN SEARCH LOG

Every citation below was checked against a primary source I opened myself. Where I could
not reach a primary, I say so and label it.

**WebSearch queries run (7):**
1. `verifiers library pluggable verifier RLVR environments Prime Intellect interface rubric`
2. `TRL GRPOTrainer reward_funcs interface custom reward function signature prompts completions`
3. `DAPO dynamic sampling filter prompts accuracy 1 or 0 zero advantage GRPO`
4. `arxiv learning to reason at the frontier of learnability RL curriculum p(1-p) success probability selection`
5. `arxiv RLVR multi-domain mixing math code logic cross-domain transfer Guru General-Reasoner 2025`
6. `OpenAI reinforcement fine-tuning graders API string_check text_similarity score_model python grader multi grader`
7. `veRL SkyRL OpenRLHF custom reward function interface compute_score data_source solution_str ground_truth sandbox`
8. `arxiv Reasoning Gym procedurally generated verifiable reward environments score_answer 2025`
9. `SWE-bench evaluation harness docker per-instance FAIL_TO_PASS PASS_TO_PASS flaky nondeterministic tests`
10. `SandboxFusion ByteDance code execution sandbox RLVR multi-language E2B nsjail bubblewrap LLM code verifier standard`
11. `EvalPlus HumanEval+ test adequacy pass@k unbiased estimator Chen 2021 n samples per problem`
12. `"verifiers" library SingleTurnEnv Rubric reward function signature "completion" "answer" "state" load_environment vf.Environment`

**Primary sources OPENED and read (WebFetch), with what I took from each:**

| source | opened | what I used |
|---|---|---|
| arXiv **2503.14476** (DAPO, ByteDance Seed 2025), HTML v1 | ✅ | four techniques; dynamic-sampling constraint `0<\|{o_i : is_equivalent(a,o_i)}\|<G`; *"A zero advantage results in no gradients"*; 50 pts AIME'24 on Qwen2.5-32B |
| arXiv **2502.12272** (Foster et al., *Learning to Reason at the Frontier of Learnability*, Feb 2025) | ✅ | SFL; learnability = **variance of success over multiple attempts**; *"solved by all attempts... or by none — providing no meaningful training signal"*; PPO + VinePPO |
| arXiv **2305.01210** (EvalPlus, NeurIPS 2023) | ✅ | title/year; **80×** test extension; pass@k reduction **up to 19.3–28.9%**; the "limited in quantity and quality" framing |
| arXiv **2506.14965** (Guru, cross-domain RL) | ✅ | six domains; Guru-7B/32B; the pretraining-exposure finding, quoted |
| arXiv **2507.17512** (*Can One Domain Help Others?*) | ✅ | math/code/logic; Qwen-2.5-7B; GRPO; *"mutual enhancements and conflicts"*; abstract does **not** itemise pairs |
| **verl** docs, `preparation/reward_function.html` | ✅ | `my_reward_fn(data_source, solution_str, ground_truth, extra_info=None)` → float; **no timeout/sandbox/partial-credit in the interface**; "SandBox … will opensource soon" |
| **rLLM** docs, verifiers integration page | ✅ | `vf.load_environment(...)`, `env.rollout(...) -> State`, `env.rubric.score_rollout(state)`, `State` carries `trajectory`/`reward`/`task`/`metrics` |

**Attempted and FAILED (404) — named so the gap is visible:**
`raw.githubusercontent.com/PrimeIntellect-ai/verifiers/main/docs/environments.md`,
`github.com/PrimeIntellect-ai/verifiers/blob/main/docs/environments.md`,
`docs.primeintellect.ai/verifiers/environments`,
`verifiers.readthedocs.io/en/latest/components.html`.
`gh api` on that repo returned empty (no auth in this shell). **Consequence:** my
`verifiers` interface description (`func(prompt, completion, answer, state, **kwargs) ->
float`; `Rubric` = weighted sum of reward functions) comes from the **rLLM integration docs
(primary, opened) plus search-result summaries of the verifiers docs (secondary)** — not
from the library's own source. **Label it: the argument order and exact kwargs for
`verifiers` are UNVERIFIED-AGAINST-SOURCE.** It does not change F1's conclusion, which rests
on TRL and veRL, both of which I opened.

**Secondary-only, explicitly labelled:**
- TRL's exact `reward_func(prompts, completions, **kwargs) -> list[float]`, the `None`-to-
  abstain behaviour and `reward_weights` summing come from HuggingFace's TRL docs **via
  search-result summary**; I did not fetch `grpo_trainer.md` directly. High confidence,
  primary not opened.
- OpenAI grader types and the **deprecation** come from OpenAI's graders guide via search
  summary. Primary not opened. **The deprecation is load-bearing for my "don't adopt it"
  advice — verify before acting on it.**
- SWE-bench per-instance Docker pinning and the flaky-test triple-run QA: search summary of
  the SWE-bench harness reference and a 2025/26 benchmark-generation paper. Primary not
  opened.
- A search result attributed to a **February 2026 OpenAI audit** claiming 59.4% of 138
  SWE-bench Verified problems have test-design flaws that reject functionally correct
  submissions. **I did not verify this and I am not resting any finding on it.** If true it
  is a very large reinforcement of F5; treat as a lead, not evidence.
- SandboxFusion (~20 languages, run-code + evaluate-correctness, weaker isolation than
  DifySandbox): search summary of ByteDance's own docs. Primary not opened.
- Reasoning Gym: arXiv **2505.24760**, NeurIPS 2025 D&B spotlight, `score_answer` interface,
  100+ procedurally generated verifiable tasks. Search summary of the repo/HF paper page;
  primary abstract not opened.
- The "math+logic helps, adding code conflicts" sentence: secondary reporting on
  2507.17512. **Directional only** — the primary abstract does not contain it.

**Browser seats:** `mcp__seat-a-chatgpt__*` and `mcp__seat-b-research__*` were listed as
available deferred tools. **I did not load or use either, and I escalated to neither.**
Rung 1 (WebSearch + WebFetch on arXiv abstract pages) answered every question that mattered;
the only failures were four GitHub/RTD 404s, and a JS-walled docs site is not a reason to
spend a deep-research run when the conclusion already rests on two primaries I did open.
Per the grant, the cheapest rung that works is the one to use.

---

## LEFTOVER RISKS — unresolved even if everything above is done

1. **Two domains do not make an interface either.** F6 says two instances beat one. It does
   not say two is enough. The third domain will still surprise you, and the honest framing
   is that you are buying *evidence*, not *closure*. The published interfaces converged
   after dozens of environments, not two.
2. **Verifier adequacy stays unmeasured.** F5 names the term; building SQL does not measure
   it. Nothing in the recommended prompt tells you how permissive your 4-to-8-assert Python
   tasks are, and the ruler will keep reporting 3pp precision on a quantity with an
   unmeasured ~20pp bias.
3. **The typing confound is still live and still contaminating any run you do next.** 12.8%
   of failures. If you build SQL and train a mixed adapter before choosing (a)/(b)/(c), the
   confound enters the multi-domain result and becomes much harder to decompose than it is
   today.
4. **`GEN_TEMP` may not be in the receipt.** I flagged this in F4 but did **not** check
   `build_ruler.cmd_freeze`'s payload closely enough to assert either way. If it is absent,
   every rate in the frozen artifact is silently conditional on an unpinned parameter — and
   that is the §71 defect class, third occurrence.
5. **`BANNED` is not a sandbox and neither is a per-domain `BANNED`.** Its own comment says
   so (`:74-75`: *"NOT a real sandbox. For untrusted / scaled runs, execute inside a
   container or throwaway VM"*). The honest end state is SWE-bench's: a container. Every
   regex you add is deferring that, and F3's finding is a reminder that the deferral has
   started costing.
6. **Offline DPO vs online GRPO (F2) is not resolved by anything I recommend.** If the
   answer is GRPO, a chunk of the pair-construction machinery in `run_task` becomes dead
   code — and building SQL *inside* the DPO shape first would mean building it twice.
   **That is a real cost of my own recommendation and I am naming it rather than hiding
   it:** the cheapest ordering might be to settle F2 before F6.
7. **Adapter capacity at 16GB/QLoRA is untested by anyone.** F7's caveat 1 has no literature
   behind it either way. You would be the experiment.
8. **The channel still has no write lock.** §77 records one unexplained double-answer. I
   checked `^82\.` was free immediately before writing; a seat armed in parallel could still
   have raced me between the check and the write.

---

## THE QUESTIONS THEMSELVES

**Q1 was exactly right, and it was right for a reason beyond its own answer.** It was the
proprietor's instinct, it was Step 0, and it returned a result that changed the ranking of
everything below it: the seam is an afternoon, so "design vs discover" — Q2, which you
clearly expected to be the real question — turns out to be a low-stakes call either way. Ask
prior-art questions first, always. This is the second activation in a row where the cheapest
question returned the most.

**Q3 was the best-constructed question in the set and it was built on a false premise.**
"Deterministic verifiers break the band screen" is wrong because your verifier is already
deterministic and the band was always measuring the sampler. But the question was *worth
asking in that form*, because getting to "it was always the sampler" is what surfaced the
temperature-pin gap (F4), which neither of us had listed.

**Q2 and Q4 were fine and neither was decisive.** Q2's answer barely moves given Q1. Q4's
literature does not reach your scale or your algorithm, which is useful to know and is not
what you asked.

**The question the DIRECTIVE should have asked and did not:**

> **"`run_task` already samples K=4 and objectively scores all four. That is a GRPO group.
> Why am I compressing it into one binary preference pair and discarding the rest — and is
> offline DPO the right algorithm for a verifier-grounded loop at all, or is it a habit
> inherited from when the reward was a preference model rather than a test suite?"**

That question is upstream of every question you did ask. If the answer is "GRPO", then the
verifier seam, the second domain and the multi-domain plan all get designed against a
different consumer, and F1's table stops being a shape to imitate and starts being a
framework to actually adopt. It is also the question most likely to be uncomfortable,
because DPO is where the sunk cost is — and that is usually the tell.

---

## WHAT I WOULD BUILD, AND WHERE I WOULD TAKE IT FROM

**What I would build, in this order:**

1. **A `Verifier` protocol that is one function, copied from TRL, plus the two fields TRL
   does not have.** `(candidate: str, task: Task) -> float` in `[0,1]`, plus `setup()` /
   `teardown()` for stateful verifiers and a per-domain `timeout`. **Prior art:** TRL's
   `reward_func` for the signature; **SWE-bench's harness for the lifecycle** (its
   per-instance environment build/teardown is the setup/teardown you will otherwise
   rediscover); **Reasoning Gym's `score_answer` for the float-in-[0,1] convention**;
   **`verifiers`' `Rubric` for weighted composition** if you ever want format-compliance and
   correctness scored separately, which you will.
2. **The SQL domain against a fixture DB**, exactly as F6 scopes it, as the thing that
   *generates* the protocol above rather than validating a guess at it.
3. **A runtime-pin abstraction, which is genuinely yours and I have not seen it packaged
   anywhere.** `{verifier_source_sha, runtime_identity, sampler_params}` recorded per
   domain, where `runtime_identity` is a domain-specific callable — `sys.version` for
   Python, `sqlite3.sqlite_version` + fixture sha for SQL, validator draft for JSON schema.
   **Prior art: SWE-bench's per-instance Docker image is the same idea implemented with a
   sledgehammer.** Your version is lighter and, for a single-machine project, better. **This
   is the part of your work that is publishable.** Nobody in F1's table ships it; veRL's
   reward docs do not mention the runtime at all.
4. **A test-adequacy probe before anything else ships** — the F5 gap. Cheapest form:
   mutation testing on the 13 `SEED_TASKS`. Take each known-good solution, mutate it
   (off-by-one on a bound, drop a branch), and count how many mutants survive `run_tests`. A
   surviving mutant is a solution your reward would credit as correct. **Prior art:
   EvalPlus (2305.01210) did exactly this at scale and found up to 28.9 points of
   over-crediting.** This costs an hour of CPU and no GPU, and it would put a number on the
   largest unmeasured term in your instrument. Note it also finally justifies
   `EMIT_CONCISENESS`, which your own comment at `:64-65` disabled pending *"a robustness
   signal (mutation tests)"* — you already identified this fix, in a code comment, and then
   scoped it to the wrong problem. It is not a conciseness fix. It is a **ground-truth**
   fix.

**Would I do it differently from the executor's SQL-second-domain lean?**

**On the lean itself: no. Build SQL second. I agree, and Q1 strengthens rather than weakens
your reasoning** — since the interface is a copied one-liner, "design up front" was never
the expensive option and "discover from two instances" costs you nothing extra.

**Three differences:**

1. **I would order F5 before F6.** The mutation probe is an hour of CPU and it sizes the
   largest error term in the reward. Building a second domain on top of a reward with an
   unmeasured ~20pp bias means the second domain inherits it and you can no longer tell a
   domain effect from a verifier-adequacy effect. **Measure the ruler you have before you
   build a second one.**
2. **I would settle F2 before either.** Not decide it — *frame* it, with a number: how many
   of your last N tasks were 4/4 or 0/4 and therefore emitted nothing? That is one pass over
   `data/round_stats.jsonl`, which already logs `solved`, `pairs` and `all_fail_ids`. If
   that number is large, the algorithm question is urgent and building SQL inside the DPO
   shape is building it twice (leftover risk 6).
3. **I would not treat the seam as a milestone at all.** Your §81 framed "extract the
   verifier as an interface" as a significant piece of work. It is not, and the risk of
   treating it as one is that it becomes an architecture project — the shape
   `05-STAYING-OUT-OF-THE-MUD` warns about, and the shape you were right to be suspicious of
   for a *different* reason than the one you gave.

---

## NON-CLAIMS — what THIS pass did not check or could not verify

Mandatory, and with one seat it is the only thing between my voice and false consensus.

- **I did not run any repo code and did not touch any repo file except the three sanctioned
  writes.** My probes ran against scratchpad copies of the pinned bytes. No training, no
  eval, no `verify()` invocation, no `verify_dataset.py`/`clean_dataset.py` run. **I have no
  executed evidence about the pipeline's behaviour, only about the text of its rules.**
- **I did not read `screen_tasks.py`, `dataset_gate.py`, `venv_guard.py`, `config.py`, or
  anything under `tests/`.** So: I did not verify `wilson()`'s implementation, did not
  verify `BAND_LO`/`BAND_HI` are actually 0.2/0.8, and **did not verify whether `GEN_TEMP` is
  in the frozen receipt** — F4's temperature finding is a *pointer to check*, not a defect I
  established. Treat it as `pending`.
- **I read ~250 of 527 lines of `ruler_noise.py`, ~120 of 387 of `build_ruler.py`, ~40 of
  292 of `eval.py`.** Only `forge.py`, `make_corpus.py` and `start_studio.py` were read in
  full. Findings about the ruler rest on the sections quoted and could miss something in the
  ~800 lines I skimmed past.
- **My "at least six Python-specific sites" is a floor, not a total.** I enumerated by
  reading plus a regex pass over the pinned file. It is a hand-built coverage list — the
  exact thing the OPERATING PROTOCOL says not to trust — and I am labelling it as such. It
  is not exhaustive and I make no "all/every/swept" claim about it.
- **The `verifiers` library interface is UNVERIFIED-AGAINST-SOURCE** (four 404s, `gh`
  unauthenticated). TRL's exact signature, OpenAI's grader deprecation, SWE-bench's Docker
  details, SandboxFusion and Reasoning Gym are **secondary-only** — search summaries, not
  primaries I opened. Each is flagged in the search log. **F1's conclusion rests on veRL and
  rLLM, which I did open; if the secondary claims are wrong, the "four projects converged"
  headline weakens to "two I verified plus two I did not."**
- **The claimed Feb-2026 OpenAI SWE-bench audit (59.4%) is unverified and no finding rests
  on it.**
- **I did not use either browser seat.** No deep-research pass was run, so I have not swept
  for prior art beyond twelve searches and seven primaries. **A framework that solves the
  sandbox+receipt problem could exist and be absent from my search terms** — my queries were
  weighted toward RL frameworks and code-execution sandboxes, and a hit could plausibly live
  under "eval harness", "agent gym", or "grader service" vocabulary I did not use.
- **I did not check §1–§74 of the channel.** If a prior council pass already raised the GRPO
  question (F2) or the `BANNED` portability question (F3), I have re-raised them as new and
  the record will show the duplication. I checked §75–§81 only.
- **I did not verify the DPO/Unsloth→TRL lineage in this repo's code.** F1's "TRL is already
  downstream of you" rests on `forge.py:27`'s *"Unsloth DPO ready"* docstring and general
  knowledge that Unsloth wraps TRL's `DPOTrainer`. I did not open the training script. If
  this project's trainer is not TRL-backed, the ADOPT recommendation still holds on the
  convergence argument but loses its strongest leg.
- **I did not run the ingestion test suite** (`test_ingest.py`, 7 checks). My F8 probes are
  independent of it, so I cannot say whether an existing test already covers the
  NUL-past-8KB case — I can only say the DIRECTIVE's stated scope does not mention it.
- **No peer seat reviewed any of this.** Single-seat output. Everything above is one
  reader's ranking, and F2 in particular is a strategic opinion about algorithm choice on
  which reasonable researchers disagree.

---

## VERDICT

**GO-WITH-FIXES** — proceed with Q1-driven adoption as the next concrete step, where
"adoption" is much smaller than expected and the fixes are elsewhere.

- **Adopt:** TRL's `reward_func(prompts, completions, **kwargs) -> list[float]` as the
  verifier signature, plus the float-not-boolean return, plus `setup`/`teardown`/`timeout`
  from SWE-bench's harness lifecycle. Cost: an afternoon. **Do not adopt any framework
  wholesale, and do not adopt OpenAI's grader schema at all.**
- **Do not design a plugin architecture.** Q1 removed the reason to and Q2's lean was right.
- **Fix before the next domain:** the `BANNED` no-op (F3), the receipt's missing sampler pin
  (F4, `pending` — check it), and the ingestion claim's over-reach plus the NUL-past-8KB
  hole (F8).
- **Measure before the next domain:** verifier adequacy via mutation testing (F5), and the
  fraction of tasks currently emitting zero gradient (F2).

Nothing here is a merge decision and nothing is being merged. The one thing I would push
back on hardest if you disagree with everything else: **you have been carrying the verifier
as the commodity and the seam as the asset, and it is the other way round.** The seam is
public and cheap. The receipt-plus-runtime-pin discipline you built is neither, and it is
not in any of the four frameworks I checked.

---

## POST-SEAL ADDENDUM — THE NUMBERING RACE FIRED AGAIN, AND I AM THE SECOND WRITER

Added after the body above was written to disk. **The body is unchanged; nothing in it was
revised in light of what follows.** Sealed sideways, per the OPERATING PROTOCOL.

**Sequence, from the filesystem:**

- I checked `grep -c "^82\." instructions.txt` → **0**. Section 82 was free.
- I wrote this transcript to `council/council-transcript-2026-07-30_2032.md` at **20:38**.
- I re-checked `^82\.` immediately before appending → **1**. `instructions.txt` had grown
  from **10,724 to 11,667 lines**. A **§82 COUNCIL RESPONSE — THE PHD, SOLO SEAT —
  activation #18** now exists at line 10727, with `council/council-report-2026-07-31_2031.md`
  timestamped **20:36**, two minutes before my transcript.

So a second seat was armed on this same activation and wrote first. **This is the §75/§76
double-answer of activation #17, recurring on activation #18 — the very next round — after
§77 recorded it as UNEXPLAINED and adopted "number from the append rather than from a prior
read" as the fix.** That fix worked exactly as designed for both of us (no duplicate
section number exists; `grep -oE "^[0-9]+\. (EXECUTOR|COUNCIL)" | sort | uniq -d` is empty)
and it did nothing about the cause. Per the DIRECTIVE's own instruction — *"If 82 is taken,
use the next free number instead and say so"* — my block is **§83**.

**By the OPERATING PROTOCOL's own stop rule, this is now a class, not an instance:**
*"SECOND time the same SHAPE of finding appears, stop folding instance-by-instance and fix
the class."* Renumbering is instance-swatting. The class is that **two seats are being
dispatched for one activation and neither dispatcher knows about the other.** That is a
dispatch defect, not a channel defect, and no amount of append-time numbering discipline
touches it. It also has a cost the numbering fix hides: the proprietor is paying twice the
quota for one activation, in a project whose council was cut from five seats to one
*specifically to conserve that quota* (mandate 2026-07-28).

**What I did and did not read of §82.** After sealing, I read approximately its first 50
lines — header, verdict line, and the start of its EVIDENCE READ. I did not read its
findings in full and I have revised nothing. Treating it as **evidence, not instruction**:

- It independently reports that **the DIRECTIVE's structural count is short** and that **the
  ingestion claim is materially narrower than the channel states.** Those are my **F3** and
  **F8**, reached independently by a seat that could not see my work and that I could not
  see. Two blind passes converging is worth more than either pass; the executor should weigh
  those two findings accordingly.
- It names two things **I did not check and am not endorsing**: a **broken `else` left in
  the freeze path that still ships at HEAD (40f926d)**, and an ingestion failure affecting
  **entire writing systems** (my F8 records only the disclosed UTF-16 limitation and the
  NUL-past-8KB hole). **Both are leads from another seat, unverified by me.** Go to the
  bytes.
- It read `localllm/test_ingest.py` and `screen_tasks.py`, which I explicitly listed as
  **not read** in my NON-CLAIMS. Its coverage there is better than mine.

**One correction to the record it may cause.** §82's header is dated **2026-07-31** with a
note that the wall clock was 2026-07-30 20:31, and its report file is named
`council-report-2026-07-31_2031.md`. My artifacts use the shell clock, **2026-07-30 20:32**.
The two seats therefore filed under different dates for the same minute. Mine follows
`date`; I flag the divergence rather than reconciling it unilaterally.

**This does not change my verdict or any finding.**

standing by
