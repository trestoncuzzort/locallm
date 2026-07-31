# COUNCIL RESPONSE — THE PHD, SOLO SEAT

**Activation #18 answered: prior art for a pluggable verifier seam; discover-or-design;
what verifier discipline transfers; multi-domain mixing.**

*Filename date follows the one named in the activation (2026-07-31). The actual clock at
writing was 2026-07-30 20:31 local. Recording the discrepancy rather than silently
adopting either.*

*Section-number check performed immediately before writing, not trusted from the DIRECTIVE:
`grep -oE '^[0-9]+\. (EXECUTOR|COUNCIL|THE PHD)' instructions.txt` returned 77-81 as the
tail, highest header 81, no duplicates. 82 was free. No renumbering was needed this round.*

---

## VERDICT

**GO-WITH-FIXES.** Class: **claim-scope defects — two shipped claims are materially
narrower than the channel states — plus one control-flow regression in the freeze path.**

The strategic direction is right and the prior-art instinct was correct and paid off. The
loop *is* close to domain-general. But the DIRECTIVE's own structural count is short, the
ingestion claim is false for entire writing systems, and the fix that closed a council
finding in §77 left a broken `else` behind that still ships at HEAD.

---

## EVIDENCE READ

**Commit actually read from.** `git log -1 --format=%H` → **`40f926d97541cea2ba2466e83c9e023307eb1a7e`**.
HEAD is **NOT** 23c3110. All code below was read via `git show 23c3110:<path>`, i.e. the
pinned commit `23c3110eee3f5380a189bd03e6100973e8b7ff86`, as instructed. Where I checked
whether a defect survives to HEAD I say so explicitly and name 40f926d.

**Channel.** `instructions.txt` lines 10218–10724 (sections 77, 78, 79, 80, 81) read in
full. Section 76's header/scope line (9513–9515) and 75's (8533–8536) read only to match
formatting convention. Total file 10,724 lines.

**Code at 23c3110, read in full:**
- `forge.py` (721 lines) — `Task`, `SEED_TASKS`, `Actor`, `extract_code`, `Result`,
  `verify`, `critique`, `run_task`, `main`, plus `ACTOR_SYSTEM`, `BANNED`, `VERIFY_PY`,
  `verifier_interpreter`
- `eval.py` (292), `build_ruler.py` (387), `ruler_noise.py` (527, read to line 470)
- `localllm/make_corpus.py` (185), `localllm/start_studio.py` (87),
  `localllm/test_ingest.py` (read in full — not in the assigned scope, opened to attack
  the closed-class claim's own green witness)
- Grep across all non-`localllm` `.py` at 23c3110 for `ACTOR_SYSTEM|extract_code`:
  8 files hit — `forge.py` (7), `train_native.py` (6), `repair.py` (6),
  `tests/test_training_seam.py` (3), `eval.py` (3), `screen_tasks.py` (2),
  `measure.py` (2), `eval_heldin_direct.py` (2). Matching lines in the five
  non-scope files read directly.
- `tests/` listing: `test_ruler_noise.py`, `test_screen_sizing.py`,
  `test_training_seam.py`, `test_verifier_pin.py`. Grep for
  `build_ruler|verify_frozen|cmd_freeze` across `tests/` returns exactly one hit, and it
  is a **comment** (`test_verifier_pin.py:4`).

**EXECUTED (read-only, in a temp directory, never the repo, no training/generation/screening):**
- `git show 23c3110:localllm/make_corpus.py` copied to a tempdir; `looks_like_text` and
  `is_trainable_file` driven against five constructed files and then against 400 synthetic
  files per writing system. Full outputs quoted in Finding 1.
- Existence/size check on `data/ruler_noise.jsonl` (209,606 bytes, present).
- `git show 40f926d:build_ruler.py` diffed by grep against 23c3110 for the Finding 3 defect.

**Web sources fetched this round — all NEW, none in the ledger (URLs):**

| Source | Status |
|---|---|
| https://raw.githubusercontent.com/PrimeIntellect-ai/verifiers/main/verifiers/rubrics/rubric.py | VERIFIED (raw source) |
| https://raw.githubusercontent.com/PrimeIntellect-ai/verifiers/main/verifiers/types.py | VERIFIED (raw source) |
| https://www.primeintellect.ai/blog/verifiers-v1 | VERIFIED (primary vendor doc) |
| https://raw.githubusercontent.com/PrimeIntellect-ai/verifiers/main/README.md | VERIFIED-AS-THIN (fetched; contains no API detail — recorded as a negative) |
| https://huggingface.co/docs/trl/rewards | VERIFIED (official TRL docs, v1.9.2) |
| https://verl.readthedocs.io/en/latest/preparation/reward_function.html | VERIFIED (official veRL docs) |
| https://developers.openai.com/api/docs/guides/graders | VERIFIED (official OpenAI API docs) |
| https://raw.githubusercontent.com/open-thought/reasoning-gym/main/README.md | VERIFIED (raw README) |
| arXiv:2505.24760 — Reasoning Gym (NeurIPS 2025 Spotlight) | VERIFIED (abstract verbatim) |
| arXiv:2506.19733 — Breaking Barriers (ICLR 2026) | VERIFIED (abstract verbatim) |
| arXiv:2507.17512 — Can One Domain Help Others? | VERIFIED (abstract verbatim) |
| arXiv:2509.24086 — Do Repetitions Matter? | VERIFIED (abstract verbatim) |

**UNVERIFIED / POINTER (named by search, primary source NOT opened — do not cite as evidence):**
SkyRL-Gym's `Env.step` signature (search gloss only; DeepWiki is not a primary source),
NeMo Gym's `/verify` endpoint and its "34 verifiers / 5 sandboxed Ray" breakdown (blog
gloss only), OpenRLHF's remote-reward interface (not opened at all this round — I ran out
of budget before it and I am not going to describe an interface I did not read),
arXiv:2602.01365 (asymmetric cross-domain effects), arXiv:2511.12344 (rubric rewards).

**CARRIED from the ledger, not re-fetched:** none were load-bearing this round. The
ledger's note was right — Chen et al., CodeDPO, DSTC, Tajwar, Song, Yue, Pan, Xu, Gu/Zhong,
Wang one-shot RLVR and Miller do not bear on an ecosystem survey. Yue et al. and Miller are
referenced below only as already-established context, carrying no new claim.

---

## FINDINGS

### F1. The ingestion closed-class claim is FALSE for entire writing systems, and its stated scope does not disclose it. **EXECUTED.**

**Target:** `localllm/make_corpus.py`, `is_trainable_file(path, exts=None, probe_bytes: int = 8192)`
→ `head = path.open("rb").read(probe_bytes)` → `looks_like_text(head)` →
`text = data.decode("utf-8")` inside a bare `try/except UnicodeDecodeError: return False`.

**The claim under attack**, verbatim from activation #18:

> Scope: "text" here means UTF-8-decodable with >=90% printable characters. It will refuse
> UTF-16 and other encodings, which is a real limitation and is not covered by any test.

That scope note is true and insufficient. The function does not decode the *file*. It
decodes the *first 8192 bytes*. If byte offset 8192 lands inside a multi-byte UTF-8
sequence, the probe raises `UnicodeDecodeError` and a perfectly valid UTF-8 text file is
refused — **as UTF-8**, not as some other encoding.

**RED WITNESS (executed).** A file of 8191 ASCII `x`, then `é`, then 100 `y` — valid UTF-8
throughout:

```
CASE1 whole-file decodes as UTF-8 : True
CASE1 probe(8192) looks_like_text : False
CASE1 is_trainable_file           : (False, 'content is not text (binary or undecodable)')
```

**Sized (executed, 400 synthetic files per row, lengths 9–40 kB, seed 7):**

```
CJK-only text  (3-byte chars)      refused: 100.0%
Cyrillic/Greek (2-byte chars)      refused:  45.2%
EU accented ~10% non-ascii         refused:   2.8%
pure ASCII                         refused:   0.0%
```

100.0% is not a sampling artifact — with uniform 3-byte characters, offset 8192 is never a
sequence boundary (8192 mod 3 = 2), so the refusal is **deterministic**: *every* CJK text
file over 8 kB is refused.

**What breaks.** This is the identical failure the whole §81 change existed to end — a
genuine text file silently refused — reintroduced one layer down, with a *worse* error
message, because "content is not text (binary or undecodable)" tells the user their text
file is binary. For a project whose stated goal is "trained on ANYTHING… commercial and
industrial," refusing 100% of Japanese, Chinese and Korean machine logs is not a corner.

**How bad:** high, and cheap to fix. One line: trim the trailing incomplete UTF-8 sequence
from the probe before decoding (or decode the probe with the last ≤3 bytes dropped). The
test file must gain a per-script case; `test_looks_like_text_rejects_mojibake` currently
passes `"temperature 88.4°C — within tolerance\n".encode("utf-8")` — a 40-byte string,
far below the probe boundary, so the existing multi-byte test cannot reach this bug.

**Three further ingestion cases I checked (executed), reported honestly including the ones that held:**

```
CASE2 ansi log accepted           : (True, 'text')      # 4.8% non-printable, well under the 10% bar
CASE3 bom.csv accepted            : (True, 'text')
CASE3 U+FEFF isprintable          : False
CASE4 empty.txt                   : (False, 'content is not text (binary or undecodable)')
CASE5 utf-16 text                 : (False, 'content is not text (binary or undecodable)')
```

CASE2 **holds** — I expected ANSI-coloured build logs to trip the 90% printable bar and
they do not; the claim survives that attack. CASE5 confirms the disclosed UTF-16 limit.
CASE3 is minor but real: a UTF-8 BOM is accepted and `U+FEFF` is **not** printable, so it
enters a character-level tokenizer as a permanent junk vocabulary entry — precisely the
mojibake harm `looks_like_text`'s own docstring says it exists to prevent, surviving in one
instance. CASE4 is a wrong *reason*, not a wrong verdict: an empty file is reported as
binary.

### F2. The four-places claim is short by at least two, and the fifth place is welded into the TRAINING seam, not the prompt. **READ-ONLY.**

**Target:** the DIRECTIVE's claim —

> Welded to Python are four places, three of them formatting: `Task.entry` / `Task.tests`,
> `extract_code` (strips ```python fences), `critique` (prompts about "solutions" and
> "defects"), and `verify()`.

I read for it rather than classifying, as instructed. The four named are real. At least two
more are not on the list.

**FIFTH: `ACTOR_SYSTEM`, `forge.py:68-72`.**

```python
ACTOR_SYSTEM = (
    "You are a precise Python engineer. Given a task, respond with a single "
    "self-contained Python solution inside one ```python fenced code block. "
    "Define exactly the requested function. No prose, no tests, no prints."
)
```

Three Python assumptions in four lines: the persona, the fenced-block output contract, and
"define exactly the requested function" — which is what makes `Task.entry` meaningful at
all. This is the exact site the task asked me to look hard at, and it is not `critique()`.

It is worse than a fifth formatting site, because it is **imported into the training path**.
`train_native.py:52-60` (outside the DIRECTIVE's declared read scope):

```
52:    forge stores `chosen`/`rejected` as extract_code() output - fences stripped -
55:    ACTOR_SYSTEM demands a ```python block, so bare source is a string no policy
60:    That is a RECONSTRUCTION, not the original bytes - close, because ACTOR_SYSTEM
```

The DPO training seam **reconstructs the fenced form** because `ACTOR_SYSTEM` demands it.
So `ACTOR_SYSTEM` is not a prompt string that a new domain would simply rewrite — it is a
contract that the shape of the training data depends on. Change the domain and
`train_native.py`'s reconstruction is wrong, silently, in the file this project already
spent a whole ruling (R1, the "format seam") fixing once.

Blast radius, measured: `ACTOR_SYSTEM`/`extract_code` appear in **8 files** at 23c3110 —
`forge.py`, `train_native.py`, `repair.py`, `eval.py`, `screen_tasks.py`, `measure.py`,
`eval_heldin_direct.py`, `tests/test_training_seam.py`. Six of those eight are outside the
DIRECTIVE's read scope. The count of four is correct *for forge.py* and misleading for the
repository.

**SIXTH: `BANNED`, `forge.py:76-80`.**

```python
BANNED = re.compile(
    r"\b(import\s+(os|sys|subprocess|socket|shutil|ctypes|requests|urllib|http)"
    r"|__import__|open\s*\(|eval\s*\(|exec\s*\()", re.IGNORECASE)
```

This is the sandbox policy, expressed in Python source syntax, and `verify()` consults it
before anything else (`if not code or BANNED.search(code): res.error = "empty or contains
banned operation"`). It is not merely inert in another domain — it is *wrong* in another
domain in both directions. For SQL the dangerous operations are `DROP`, `ATTACH DATABASE`,
`PRAGMA`, `load_extension`, none of which this matches; meanwhile a SQL query or a config
file containing the substring `open(` would be refused for containing a Python builtin it
does not contain. A safety filter that is silently inert in the new domain is the worst
kind of thing to carry across a seam.

**Two more, weaker, named for completeness rather than pressed:** `Result.total` is
hard-coded to 1 with the comment `# assert-based: all-or-nothing here` (`forge.py:501`) —
the partial-credit collapse is a property of assert-based Python tests, not of the loop
(see F5); and `Actor.generate` sends `"options": {"temperature": temp, "num_ctx": 2048}`
(`forge.py:371`), a 2048-token context that is ample for a LeetCode prompt and is not
obviously ample for a SQL task carrying a fixture schema or a JSON-Schema config task
carrying the schema. That is a domain assumption in the actor, not in the four places.

**How bad:** medium-high. It does not falsify "the loop is domain-general" — I agree with
that reading and Q1/Q2 below assume it. It falsifies the *count*, and the count is what the
"one function" plan is sized against.

### F3. `build_ruler.py:295` — an orphaned `else:` prints a false warning on every successful freeze. Introduced by the §77 fix for a council finding. Still live at HEAD. **EXECUTED (read + artifact existence check).**

**Target:** `build_ruler.py`, `cmd_freeze`. Line 277 opens `if problems:` … line 280
`raise SystemExit("refusing to freeze an inconsistent ruler")`. Then thirteen lines of
comment. Then, at **line 295**:

```python
    else:
        print(f"[!] {NOISE.name} absent - freezing without eval-instrument rates. "
              f"The band is then confirmed only under the SCREEN's sampler.")
```

Python permits comments between an `if` body and its `else`, so this `else` binds to
`if problems:` — **not** to any test of whether `ruler_noise.jsonl` exists. There is no
`if NOISE.exists():` anywhere in `cmd_freeze`; the §77 edit that stripped sample-dependent
figures from the frozen artifact removed the `if` head and left the `else` attached to the
nearest preceding `if`.

**Consequence:** the branch runs **exactly when `problems` is empty** — i.e. on every
successful freeze. `data/ruler_noise.jsonl` exists on disk at **209,606 bytes** (checked).
So the tool prints "`ruler_noise.jsonl absent — freezing without eval-instrument rates. The
band is then confirmed only under the SCREEN's sampler`" while the file is present and the
statement is false. If the file were genuinely absent *and* there were problems, the
`SystemExit` fires first and the warning never prints. The condition the message describes
and the condition under which it prints are disjoint.

**Still at HEAD:** `git show 40f926d:build_ruler.py` has the same `if problems:` at 277 and
the same `else:`/print at 295-296. Not fixed by anything after 23c3110.

**No test can see it:** grep for `build_ruler|verify_frozen|cmd_freeze` across `tests/`
returns one hit, a comment in `test_verifier_pin.py:4`. `cmd_freeze` has no test.

**How bad:** low in blast radius, high in class. §79 wrote the rule this violates, in this
channel, one section earlier: *"A green check that reads like a red one is worse than no
check, because the next person believes the text over the mark."* This is the inverse — a
red warning printed on a green path, about the artifact the band screen's validity depends
on. It was introduced *by* the remediation of council finding F2. That is the third
instance in three sections of "the verification machinery is code and has bugs at the same
rate," which §80 named as the pattern and which is now recurring inside the fix for the
finding that named it.

### F4. Q3's premise is refuted by this project's own measurement. Verifier determinism does not zero per-task variance, because the randomness was never in the verifier. **READ-ONLY, resting on §77's numbers.**

**Target:** the DIRECTIVE's Q3 —

> A deterministic verifier (schema validation, a constraint solver) returns the same answer
> every time, so per-task variance is zero and the entire screening apparatus — band,
> Wilson intervals, k replicates, MDE — may be meaningless.

The premise conflates two different sources of randomness. A per-task success *probability*
`p_i` is not a property of the verifier. It is
`p_i = P( the sampler emits an output the verifier accepts )`. The verifier can be a pure
function and `p_i` is still strictly between 0 and 1, because the *sampler* is stochastic at
`TEMP = 0.8`. Bernoulli variance `p(1-p)` is unchanged. The band screen, the Wilson
intervals, the replicate count and the MDE all survive verbatim.

**The decisive evidence is already in this repo, and it is stronger than any citation.**
`forge.verify()` is *already* essentially deterministic — it runs fixed assertions on fixed
inputs. And §77 reports, from `ruler_noise.py`'s CAUSE 1 check, that the greedy draw is
**constant on 31/31 tasks** across replicates. Temperature 0 removes the sampler's
randomness; the measured result is zero variance on every task. That is a direct
experimental demonstration that the verifier contributes ~nothing to run-to-run variance
and the sampler contributes essentially all of it. Q3 is asking what happens when you
remove a noise source that has already been measured at zero.

**The one residual I found, named because it is not zero:** `verify()` launches
`[VERIFY_PY, "-I", path]`, and `-I` implies `-E`, which discards `PYTHONHASHSEED`. Python's
hash randomization is therefore *on*, per-process. A candidate whose output order depends
on `set`/`dict` iteration over strings can pass on one run and fail on the next with
identical bytes. The wall-clock `CAND_TIMEOUT = 8` is the other, and `forge.py:505-509`
already documents it: *"wall-clock means the same bytes can time out on one run and pass on
the next."* Both are small. Neither is what Q3 was worried about.

**How bad:** the finding is good news, and it retires a question the executor was about to
spend a design round on. But it inverts the risk: the thing that *does* break the band
screen in a new domain is not determinism, it is **degeneracy** — a domain where `p_i`
piles up at 0 or 1 for structural reasons, leaving no tasks in `[0.2, 0.8]` to screen for.
Schema-validation is the likeliest such domain, and it is one of the DIRECTIVE's own
alternates.

### F5. Every framework surveyed expects a scalar reward. This project's reward is boolean by construction, and it turned scalar shaping OFF on purpose. That conflict is unexamined. **READ-ONLY.**

**Target:** `forge.py:415-433` and `:501`, against the Q1 evidence.

The interfaces (all verified, see Q1):

| Framework | Verifier returns |
|---|---|
| TRL | `list[float]`, or `None` to skip the example |
| verifiers (PrimeIntellect) | `float \| list[float] \| dict[str, float]` |
| veRL | numeric (`return len(solution_str)/100` in the official example) |
| OpenAI RFT python grader | `float`; "*any other result (exception, invalid float value, etc.) will be marked as invalid and return a 0 grade*" |
| Reasoning Gym | `float`, with a documented "cascade scorer" giving progressively lenient partial credit |

srlm-forge's verifier returns a `Result` whose `total` is hard-coded to 1 —
`res.passed = res.total  # assert-based: all-or-nothing here` (`forge.py:501`) — so
`score`'s first component is exactly `{0.0, 1.0}`. The only graded components are
`-len(self.code)` and `-self.runtime`, and `EMIT_CONCISENESS = False` (`forge.py:64`) with
the comment *"length-preference is a reward-hack; off until a robustness signal (mutation
tests) exists"* disables the one that reaches a pair.

So the project has *already decided*, deliberately and with a stated reason, that its scalar
channel is a reward hack — while every candidate framework's interface is scalar-shaped.
"Adopt a pluggable verifier" therefore silently means "adopt a reward type you rejected."
It is resolvable (a `float` that only ever takes 0.0 or 1.0 satisfies every signature above)
but it is not free: TRL's `accuracy_reward` returning `None` to skip an unparseable example,
and OpenAI's "invalid → 0 grade", are *different* answers to the case forge handles as
`res.timed_out` — and `forge.py:504-511` is emphatic that a timeout must never become the
`rejected` half of a pair. OpenAI's grader would score it 0 and it would become exactly
that. That is a real semantic incompatibility, not a type mismatch.

**How bad:** medium. It is a decision to make before a seam is designed, not a defect.

### F6. The freeze gate — named as the crown jewel that transfers — has a Python field baked into its hash input. **READ-ONLY.**

**Target:** `build_ruler.py`, `verify_frozen()` and `cmd_freeze`:

```python
if sha(c["prompt"], c["entry"], body) != rec["task_sha256"]:
```

`entry` is *a Python function name*. It is a member of the tuple that defines a task's
identity, and therefore of `ruler_set_sha256`. In a SQL domain there is no entry point; in a
JSON-Schema domain there is no entry point. The gate's *shape* (parse-don't-validate,
re-hash from stored payload, refuse to hand over the ruler otherwise) transfers perfectly
and is genuinely excellent. Its *schema* does not. §81 says the discipline "transfers
wholesale"; it transfers with one field renamed, and that rename changes every
`task_sha256`, which is the migration bill in O2 below.

**How bad:** low as a defect, high as a correction to the record — because "transfers
wholesale" is exactly the kind of sentence that gets planned against.

### F7. The closed-class test is a spelling check, and the extension list survives in user-facing prose in the very file the change was about. **READ-ONLY.**

**Target:** `localllm/test_ingest.py::test_the_two_callers_share_one_rule` and
`localllm/start_studio.py`.

The test that activation #18 offers as class closure — *"including one that fails if
start_studio regrows its own extension list"* — is:

```python
assert 'EXTS = {".txt"' not in src, \
    "start_studio has its own hardcoded extension set again"
```

That is a search for one exact 15-character string. `EXTS = {'.txt'` (single quotes),
`EXTS={".txt"` (no spaces), `ALLOWED = {".txt"...}`, or a tuple instead of a set all pass.
It pins one spelling of one regression, not the class.

And the extension list *did* survive, in the same file, in the two messages the
non-technical user actually reads (`start_studio.py`, `main()`):

```python
print(f"To train on your own writing, put .txt/.md/.py files in:\n  {DATA}\n")
...
print(f"Put some .txt/.md/.py files in:\n  {DATA}\nthen run this again.")
```

The code will now happily ingest a folder of `.csv`. The tool still tells the user, twice,
that it wants `.txt/.md/.py`. A user with a folder of sensor exports, reading the message
this file exists to show them, concludes exactly what they concluded before the fix. The
decision moved to one place; the *advertisement* of the decision did not, and no test looks
at strings the user sees.

**How bad:** medium. The closed-class claim as written ("acceptance is decided on CONTENT
and the decision exists in exactly one place") is true of the code and false of the product.

---

## ANSWERS

### Q1 — PRIOR ART. Has the seam already been designed and implemented?

**Short answer: the proprietor's instinct was right and the answer is split. There is a
convergent SHAPE and there is NO convergent STANDARD. Do not adopt a dependency. Adopt one
specific decomposition, and it is not the one the DIRECTIVE is reasoning with.**

**Where the field HAS converged — the reward function signature, and it is nearly trivial.**
Five independent implementations, verified from primary sources, all reduce to *a callable
that receives the model's output plus a bag of per-task data and returns a float*:

- **TRL** (https://huggingface.co/docs/trl/rewards, v1.9.2). Verbatim: reward functions take
  `completions` (`list[list[dict[str, str]]]`, each a one-message list with a `"content"`
  key), the dataset's other columns by name (e.g. `solution: list[str]`), and `**kwargs` —
  *"required in the function signature to ensure compatibility with trainers like
  GRPOTrainer."* Returns `list[float]`; `accuracy_reward` returns **`None` to skip an
  example** when the gold answer is unparseable. Multiple reward functions are supported and
  may be `async def`. **TRL ships no sandbox, no timeout, no execution runtime whatsoever.**
- **veRL** (https://verl.readthedocs.io/en/latest/preparation/reward_function.html).
  Verbatim signature: `def my_reward_fn(data_source, solution_str, ground_truth, extra_info=None)`,
  returning a number; registered by *path + name* config
  (`custom_reward_function.path` / `.name`, defaulting to `compute_score`). Sandboxing is
  **not addressed** in the reward-function docs; the docs mention a sandbox only for code
  datasets and describe it as *"will opensource soon."*
- **OpenAI RFT graders** (https://developers.openai.com/api/docs/guides/graders). Five
  types: `string_check`, `text_similarity`, `score_model`, `python`, `multi`. Python grader
  signature verbatim: `def grade(sample: dict[str, Any], item: dict[str, Any]) -> float`.
  *"Any other result (exception, invalid float value, etc.) will be marked as invalid and
  return a 0 grade."* Limits, verbatim: **2 minutes**, **2 GB memory**, **1 GB disk**, **2
  CPU cores** (throttled above), **no network access**, source **< 256 kB**, and a **fixed
  allow-list of packages pinned to a dated image tag** (numpy, scipy, sympy, pandas,
  rapidfuzz, scikit-learn, rouge-score, deepdiff, jsonschema, pydantic, pyyaml, nltk,
  sqlparse, rdkit, scikit-bio, ast-grep-py; "image tag 2025-05-08"). `multi` combines
  sub-grader scores through a user-written formula in `calculate_output`, supporting
  `+ - * / ^` and `min, max, abs, floor, ceil, exp, sqrt, log`.
- **Reasoning Gym** (raw README + arXiv:2505.24760). `data.score_answer(answer=..., entry=...)`
  → float; entries are `{'question', 'answer', 'metadata'}`; difficulty is a **keyword
  argument to `create_dataset`**, and the library is *"over 100 data generators and
  verifiers"* whose *"key innovation is the ability to generate virtually infinite training
  data with adjustable complexity."*
- **verifiers** — see below.

That is the convergence: **a float, a task-bag, and nothing else.** It is convergent because
it is nearly content-free. Writing that interface is an afternoon; it is not what is hard,
and adopting it buys almost nothing.

**Where the field has NOT converged — the execution substrate, which is the entire actual
problem.** TRL: nothing. veRL: nothing shipped. OpenAI: a hard-limited, network-less,
fixed-image sandbox you cannot configure. verifiers v1: a pluggable runtime abstraction.
NeMo Gym (POINTER, not verified): sandboxed Ray workers behind a `/verify` endpoint. That
is four incompatible answers to "where does the check run," and it is why nothing has
converged: *the reward signature is the easy half and everyone agrees; the sandbox is the
hard half and nobody does.*

**The one library that has actually named the seam this project is looking for:
`verifiers` (PrimeIntellect-ai/verifiers, formerly willccbb/verifiers).** And its answer is
**better than the DIRECTIVE's framing**, which is the most useful thing I found this round.

The **v0** API — verified from `verifiers/rubrics/rubric.py` and `verifiers/types.py` on
`main` — is Environment + Rubric:

```python
def __init__(self, funcs: list[RewardFunc | GroupRewardFunc] | None = None,
             weights: list[float] | None = None, parser: vf.Parser | None = None):
```
`RewardFunc = IndividualRewardFunc | GroupRewardFunc`, where
`IndividualRewardFunc = Callable[..., float | Awaitable[float]]`. Reward functions receive
`prompt`, `completion`, `answer`, optional `task`, `**kwargs` and return
`float | list[float] | dict[str, float]`. Dataset rows carry
`TASK_INPUT_FIELDS = {"prompt", "answer", "info", "example_id"}`; `Info = dict[str, Any]`;
scoring is `async def score_rollout(self, state: State)`, writing `state["reward"]` and
`state["metrics"]`. **Rubric supports `weights` — i.e. weighted multi-objective reward out
of the box**, which is the graded-reward machinery F5 says this project would need.

**The v1 answer, and this is the load-bearing part**
(https://www.primeintellect.ai/blog/verifiers-v1, verified): v1 **breaks the environment
into three pieces** —

- **Taskset** — *what* the work is. `Taskset[TaskType, ConfigType]` with a `load()`
  returning `Task` objects; each task carries a `TaskData` subclass with domain fields and
  a `@vf.reward`-decorated async method taking a `Trace` and returning a float.
- **Harness** — *how* it is solved: *"the program that solves the task and produces a
  rollout: a ReAct loop, CLI-based harnesses such as Codex or Terminus 2, or your own
  agent."*
- **Runtime** — *where* it executes. Local `subprocess` and `docker`; remote `prime` and
  `modal`. Core API, verbatim: `async run(argv, env) -> ProgramResult`,
  `async read(path) -> bytes`, `async write(path, data) -> None`.

**Map that onto srlm-forge's four places and the seam falls out immediately:**

| srlm-forge | verifiers v1 |
|---|---|
| `Task.entry` / `Task.tests` | `TaskData` fields (typed, per-taskset) |
| `ACTOR_SYSTEM` + `extract_code` + `critique` | **harness** |
| the *checking* half of `verify()` | `@vf.reward` → float |
| `VERIFY_PY`, `-I`, `CAND_TIMEOUT`, `BANNED`, tempfile | **runtime** |

This is the answer to the DIRECTIVE's "only `verify()` is conceptually hard." `verify()` is
hard because it is **two things wearing one coat**: a scoring predicate and an execution
substrate. Split those and the scoring predicate becomes as easy as the other three, and all
the genuinely hard engineering (isolation, timeout, resource limits, environment pinning)
concentrates in one replaceable component that has *nothing to do with the domain*. That
split also explains F2's sixth site: `BANNED` is a *runtime* concern that has leaked into
the scoring function, which is why it is domain-wrong.

**So: ADOPT THIS, or ADOPT THE DEPENDENCY?** My recommendation is
**ADOPT THE DECOMPOSITION (taskset / harness / runtime), DO NOT ADOPT THE PACKAGE — yet**,
for four reasons I can defend:

1. **It is mid-migration, by its own account.** Verbatim: *"The legacy code path is now
   frozen and will not be actively maintained. We aim to fully deprecate it in the future."*
   v0 is what existing environments use; v1 is what is being built. Adopting a library
   during its own breaking rewrite, in a repo whose defining problem is instrument
   stability, is the wrong trade.
2. **The whole stack is async** (`score_rollout`, `run`, `read`, `write` are all `async`).
   srlm-forge is synchronous top to bottom.
3. **It assumes an OpenAI-compatible client.** Ollama exposes one, so this is surmountable,
   but it is not free.
4. **The migration is not free either — see O2 for the number.**

**Rejected as the standard answer, with reasons:** TRL and veRL because their reward
interface is real but their execution story is absent — adopting them gives this project
*less* than it already has (it already has an isolated, interpreter-pinned, timeout-bounded
subprocess verifier; TRL has none of that). OpenAI RFT because the grader runs on OpenAI's
infrastructure against OpenAI models, which contradicts the local-from-scratch goal
outright. Reasoning Gym because it is a *task* library, not a seam — but see Q2/Q3, it
contributes the single best idea in this survey. SkyRL, OpenRLHF and NeMo Gym I did not
verify from primary sources and I will not rank what I did not read.

**Stated plainly, as the DIRECTIVE asked for:** *No standard exists.* The reward-callable
shape is universal and near-worthless; the verifier *execution* contract has four
incompatible implementations and one library (verifiers v1) that has correctly identified
the decomposition and is still building it. Designing your own is justified. Designing it
**as taskset / harness / runtime** is not inventing — it is copying the one group that has
thought about this longest, without taking on their in-flight rewrite.

### Q2 — DISCOVER OR DESIGN?

**Build the second domain first. Your lean is right, and Q1 does not overturn it — it
*sharpens* it, because you now know the shape to aim for and can check whether a second
instance actually produces it.**

But the DIRECTIVE's plan has a methodological hole that matters more than the choice of
domain:

**The two-instance method systematically cannot discover a seam the two instances share.**
Code-in-a-fence and SQL-in-a-fence are both "generate source text in a fenced block,
extract it, execute it against a pinned engine." Build those two and the seam you discover
will be fence-shaped and execution-shaped — and F2's fifth site (`ACTOR_SYSTEM`'s
`fenced code block` contract, reconstructed inside `train_native.py`) will survive both
instances *invisibly*, because both need it. You would ship a "domain-general" seam with a
Python-fence assumption in the training path, and find out on domain three.

So the choice of second domain should be made on **which assumptions it breaks**, not on
cost or on plausibility as a product. Scored against the assumptions I can enumerate from
the code:

| Assumption in the current code | SQL + fixture DB | JSON-Schema config | Regex synthesis |
|---|---|---|---|
| Reward is all-or-nothing (`forge.py:501`) | **BREAKS** — rows matched / rows expected is a natural scalar | no (valid/invalid) | partial (pass rate over a test-string set) |
| Verifier is a subprocess of a language interpreter | **BREAKS** — `sqlite3` is in-process | **BREAKS** | **BREAKS** |
| Verifier is stateless | **BREAKS** — needs fixture setup/teardown per task | no | no |
| Verifier needs a wall-clock timeout | keeps (a bad query can hang) | **BREAKS** (removes it) | keeps (catastrophic backtracking) |
| Answer arrives as a fenced code block | keeps | **BREAKS** | keeps |
| `BANNED` (Python-syntax safety filter) | **BREAKS** — needs `DROP`/`ATTACH`/`PRAGMA` | **BREAKS** (nothing to ban) | **BREAKS** |
| Environment pin = a Python interpreter path | **BREAKS** → `sqlite3.sqlite_version` | **BREAKS** → validator version + schema draft | **BREAKS** → `re` vs `regex` |
| `p_i` lands inside `[0.2, 0.8]` (F4) | plausible | **at risk of degeneracy** | plausible |

**SQL against a fixture database is the most informative second instance, and it is also
the cheapest — those coincide here, which is unusual and worth taking.** It breaks five
assumptions including the three that matter most:

1. **Natural partial credit.** This is the one thing the code domain *cannot* teach, and F5
   says it is the thing every candidate framework assumes you have. `|rows correct| /
   |rows expected|` is a real graded reward that is not a length heuristic and not a
   reward hack — it is the objective check itself, at finer resolution. Discovering the seam
   against a domain that produces a genuine scalar is the difference between a seam that
   fits the field's interfaces and one that does not.
2. **Per-task external state.** The fixture DB must be created, populated, torn down, and
   *pinned* (the fixture bytes are part of ground truth exactly as `tests` are). This is the
   single feature that reveals the runtime/scoring split empirically rather than by my
   assertion — verifiers v1's runtime API is `run` **plus `read` and `write`** precisely
   because tasks need files. The code domain never needed `write`, so nothing in `forge.py`
   knows that tasks can have resources.
3. **The environment pin generalizes or it does not, and you find out cheaply.**
   `sqlite3.sqlite_version` is the exact analogue of the §71 interpreter pin — and it is a
   *library* version rather than a *process* version, which tests whether
   `verifier_interpreter()`'s design (executable path + version + `pinned_away_from_launcher`)
   survives when there is no separate executable at all. My prediction, offered as a
   falsifiable one: it does not survive, and it wants to become an opaque
   `{"engine": str, "version": str, "fingerprint": sha256}` record with no fields naming
   Python.

**What SQL will NOT teach you, stated so it is not discovered late:** it keeps the fenced
block, so `ACTOR_SYSTEM`/`extract_code`/`critique` will look domain-general when they are
not (F2). **Mitigation, and I would make it a hard requirement of the exercise:** do not let
the SQL harness import `forge.ACTOR_SYSTEM`. Write a second system prompt from scratch,
then *diff the two* and treat every shared sentence as a candidate for the harness
interface. That converts the blind spot into the deliverable.

**Against JSON-Schema as the second instance:** it breaks more *formatting* assumptions but
is at real risk of the degeneracy in F4 — schema validation of a generated config is close
to a format check, `p_i` will pile up near 1 once the model learns the shape, and you will
have built a domain the band screen cannot find tasks in. Keep it as domain three, where it
is the right instrument for testing whether the seam survives a non-fenced answer.

### Q3 — WHAT TRAVELS AND WHAT DOES NOT.

**Travels unchanged:**
- **The freeze gate's *shape*** — parse-don't-validate, re-hash from the stored payload,
  make the checked object the only way to obtain the ruler. Domain-agnostic, and the best
  single piece of engineering in the repo. Its *schema* does not travel (F6: `entry`).
- **The deterministic tid-hash split** (`split_side`, `sha256(tid)[:8]/0xFFFFFFFF <
  RULER_SHARE`) and the ruler/train disjointness checks. Nothing about them is code-shaped.
- **Nominate → confirm → freeze**, i.e. treating admission as a *nomination* re-measured at
  higher `n`. That is regression-to-the-mean control and it is domain-independent.
- **Refusing to pool replicates across verifier fingerprints** (`ruler_noise.cmd_measure`'s
  `foreign` count). The *concept* is universal; the *key* it compares on
  (`verifier.version`) is F6's problem again.
- **The band screen, Wilson intervals, k replicates, MDE — all of it.** See F4.

**Secretly code-specific:**
- **The interpreter pin's implementation.** `dataset_gate.verify_py()` returns a Python
  executable path; `verifier_interpreter()` returns `{executable, version,
  pinned_away_from_launcher, launcher_version}`. Every field names a Python process. The
  *principle* — "ground truth depends on the engine, so record the engine" — is the
  project's genuine intellectual asset and it generalizes completely. The struct does not.
- **`task_sha256 = sha(prompt, entry, tests)`** (F6).
- **`BANNED`** (F2), which is a runtime policy misfiled as a scoring precondition.
- **`Result.total = 1`** (F5).

**Is verifier-grounded training on deterministic checks a studied setting?**
Yes, and it is the *default* setting — it is simply not framed that way, which is why the
question feels unanswered. Reasoning Gym (arXiv:2505.24760, VERIFIED) is *"over 100 data
generators and verifiers"* whose verification is entirely algorithmic and deterministic;
the paper's abstract reports RL results with them and never treats determinism as a
statistical problem, because it is not one. OpenAI's `string_check` and `python` graders are
deterministic by construction. The literature does not discuss "the deterministic-verifier
case" for the same reason it does not discuss "the deterministic-ruler case" in physics.

**What replaces the noise floor?** **Nothing, because nothing is lost.** The noise floor was
never measuring the verifier. Re-read what `ruler_noise.py` actually decomposes: greedy-draw
determinism, marginal per-task rates, and inter-task covariance — three properties of *the
sampler and the task set*, with the verifier appearing nowhere as a variance source. The
eval-variance literature makes the same assumption explicitly: arXiv:2509.24086 (VERIFIED)
concludes *"use ≥ 2 repetitions **under stochastic decoding**"* and attributes the whole
problem to decoding — grading is assumed deterministic and is not a term in their
mixed-effects model. That paper is worth banking for a second reason: *"10/12 slices (83%)
invert at least one pairwise rank relative to the three-run majority"* and *"two runs remove
~83% of single-run inversions"* — independent, published support for R7's replicate-count
reasoning, from a different field of eval.

**What genuinely changes in a fully-deterministic-verifier domain**, and this is the real
Q3 answer:
1. **Nothing, if you keep sampling at T>0.** `p_i` remains a sampler property.
2. **Everything, if you move to greedy decoding.** At T=0 with a deterministic verifier the
   whole instrument collapses to a single bit per task, variance is exactly zero, and the
   *only* remaining "noise" is between training seeds. Then the estimand changes from
   "this model's pass rate" to "this training procedure's pass rate," and Miller's `omega^2`
   heterogeneity term (already banked) becomes the live one. This is the version of Q3
   worth worrying about, and it is a *decoding* decision, not a verifier decision — which
   makes it the same decision as the still-open greedy-free metric change from §76.
3. **Degeneracy replaces stochasticity as the threat** (F4). And the field's answer to
   degeneracy is **not** a band screen over a fixed pool — it is Reasoning Gym's:
   *"generate virtually infinite training data with adjustable complexity"*, difficulty as
   a **keyword argument**, not a survivor of a screen. For any domain where tasks can be
   *generated* (SQL against a fixture DB absolutely can be), a difficulty knob strictly
   dominates the screen: no selection-on-noise, no regression-to-the-mean drop-outs, no
   "the ruler is spent" (§64) — you just generate more at the same difficulty. That is the
   single most valuable transferable idea in this survey and it does not require adopting
   anyone's code.

### Q4 — MULTI-DOMAIN: does mixing verifiable domains help, hurt, or is it neutral?

**The literature says: it does all three, the sign is domain-pair-specific, and the two
best-identified results point away from "one general model" at this scale.**

- **arXiv:2506.19733**, *"Breaking Barriers: Do Reinforcement Post Training Gains Transfer
  To Unseen Domains?"* (ICLR 2026; abstract VERIFIED verbatim). Two studies —
  observational across open-weight RPT models, and interventional (single-domain RPT, then
  evaluate across domains). Both converge: *"although RPT brings substantial gains on tasks
  similar to the fine-tuning data, the gains generalize inconsistently and can vanish on
  domains with different reasoning patterns."* This is the direct answer to "does training
  on code buy you SQL," and it is *no, not reliably*.
- **arXiv:2507.17512**, *"Can One Domain Help Others? A Data-Centric Study on Multi-Domain
  Reasoning via Reinforcement Learning"* (abstract VERIFIED verbatim). GRPO on
  Qwen-2.5-7B across math, code, and logic puzzles; examines *"the intricate interactions
  including mutual enhancements and conflicts that emerge during combined cross-domain
  training."* Both signs occur. **I did not extract numbers** — the abstract carries none
  and I did not open the tables, so I am not reporting a magnitude. Search glosses claiming
  "math aids logic, math impedes code" are consistent with the abstract's framing but I did
  not verify them against the paper and they should not be treated as evidence (the §62
  precedent on arXiv:2603.20100).

**Two caveats that make this shape-only evidence, and they are severe.** Both papers study
**online RL (GRPO/RPT) at 7B+ with full-size datasets.** srlm-forge is **offline DPO**, LoRA
r=16, on a 31-task ruler — and Track B is a 12.7M-parameter char model. This is the same
off-domain-interpolation situation as Flan in §62, and it deserves the same label: *the
shape of the finding transfers, the numbers do not.*

**My answer to the product question, which is what Q4 is really asking.**
"Train on ANYTHING" should be built as **a factory that produces many narrow models, not one
general model** — for three reasons, only the first of which is the literature:
1. 2506.19733 says the transfer you would be betting on is unreliable and can vanish.
2. Every framework in Q1 that supports multiple domains does so by **composing tasksets and
   weighting rewards** (verifiers' `Rubric(funcs, weights)`; OpenAI's `multi` grader with an
   explicit `calculate_output` formula), i.e. the field's own answer to multi-domain is a
   *configurable mixture per training run*, which is a factory.
3. It is the only one of the two products that this project's actual assets serve. The
   assets are the *discipline* — pin the engine, freeze the ruler, gate the training data,
   size the noise floor. Those are per-domain machinery. A customer with a machine-checkable
   spec wants a model that is right about *their* spec, verifiably, on their hardware.
   That is a much better fit for "commercial and industrial" than a model that is mediocre
   at three domains and whose cross-domain interference nobody can predict.

If one general model is genuinely wanted later, 2507.17512's existence of *conflicts* means
mixture weights become a tuned hyperparameter, and you would need the MDE budget to detect
interference — at ~3pp MDE with 4,960 generations per arm, a per-domain interference effect
smaller than 3pp is invisible to this instrument. That is a reason to defer, not a reason to
refuse.

---

## LEFTOVER RISKS (unresolved even if every fix above lands)

1. **The 90% printable / UTF-8 rule still refuses UTF-16, UTF-32 and every legacy codepage**
   (CP1252, Shift-JIS, GB18030). Fixing F1's boundary bug does not touch this. For
   "industrial data" this is the larger share of the problem — exported CSVs from Windows
   tooling are frequently CP1252 or UTF-16LE. The disclosed scope is honest; the limitation
   is not small.
2. **`make_corpus` holds every file's full text in `seen` and `parts` simultaneously, then
   builds `body = "\n\n".join(parts)` and writes it whole.** Peak memory ≈ 3× corpus size.
   "Train on anything" applied to a real industrial log directory is an OOM, not a slow run.
   Nothing in the ingestion change addressed scale.
3. **F4's residuals are real but unmeasured:** hash randomization under `-I` (which discards
   `PYTHONHASHSEED`) and the wall-clock `CAND_TIMEOUT`. Both inject genuine verifier
   non-determinism. Nobody has measured how many of the 31 ruler tasks are hash-order
   sensitive.
4. **The greedy-free metric decision from §76 is still open**, and F4/Q3 make it *more*
   consequential, not less: it is now also the decision about what the instrument's estimand
   becomes in a deterministic-verifier domain.
5. **The typing-import confound (12.8%) is still unchosen**, and it interacts with any
   domain change: option (b) — prepending typing imports to the harness — becomes a *runtime*
   concern under the Q1 decomposition, which is a cleaner place to put it than either of
   the other two options implies.
6. **Track B has no verifier at all.** Everything in this response is about Track A. A
   character model trained on a corpus by next-token prediction has no objective check to
   plug anything into. The stated goal covers both tracks; Q1–Q4 cover one.

---

## FIX CLASSES (the kind of change, not the change)

- **F1** — *boundary-safe probing*: any fixed-size read used to decide a whole-file property
  must be truncated at a unit boundary before decoding. Plus a per-writing-system test case
  above the probe size. This is a **class**, not an instance: the same shape will recur
  anywhere a `read(n)` feeds a decoder.
- **F2** — *inventory by grep across the tree, not by reading one file*. The four-places
  figure came from reading `forge.py`; the fifth and sixth sites are visible in one grep.
  Record the corrected count in the channel before any seam is sized against it.
- **F3** — *control-flow left dangling by a deletion*, plus **the absent test that would have
  caught it**: `cmd_freeze` has no test at all. Restore the guard the `else` lost, and add
  a test that runs a freeze and asserts on its output text, not its exit code (§80's own
  lesson: "0 failed was never wrong").
- **F5** — *decide the reward type before designing the seam*, and decide what a timeout
  scores. Not a code change; a recorded decision.
- **F6** — *schema neutrality in the identity hash*: the frozen task hash must not name a
  Python concept. Rename to a domain-opaque field before a second domain exists, while the
  re-freeze costs one artifact instead of two.
- **F7** — *user-visible strings are claims too*: the claim-checker discipline of §79/§80
  applies to `print()` output, not only to READMEs, and the class-closure test should assert
  on behaviour (a `.csv` in a temp `training_data/` is found) rather than on the absence of
  one exact source string.

---

## OMISSION ATTACK — what activation #18 did not ask

**O1. Does "pluggable verifier" imply pluggable reward *shaping*?** Yes, and the answer
matters. Covered in F5: five frameworks, five scalar interfaces, versus a project that
disabled its only graded channel as a reward hack. Unasked and load-bearing.

**O2. What does adopting an external task schema actually cost?** Not free, and the number
is computable. The frozen ruler's identity is `sha(prompt, entry, tests)` per task and
`ruler_set_sha256` over all of them. Renaming fields to any external schema
(`{prompt, answer, info, example_id}` for verifiers; `sample`/`item` for OpenAI) changes
every `task_sha256`, which changes the set hash, which **fires `verify_frozen()`** — and
`ruler_noise` obtains the ruler *only* through that gate, by design. The ruler's identity
changes, so the banked replicates are no longer replicates of the same instrument. The bill,
from the code: `len(tasks) * ev.N_SAMPLES` = 31 × 5 = **155 generations per replicate ×
40 banked replicates = 6,200 generations discarded**, plus a re-freeze that must be
announced in the channel (`--force` requires it). That is the real price of "adopt X," and
activation #18 asked which framework to adopt without asking what adoption costs.

**O3. Is the interpreter-pinned receipt — the project's claimed differentiator — addressed
by any of these frameworks?** Partly, and the honest answer is less flattering than the
channel assumes. **TRL and veRL: no.** Neither ships an execution environment, so neither
has the bug class or the fix; §71's defect genuinely cannot arise there because the
capability does not exist. **OpenAI: yes, and more strongly** — the grader sandbox pins a
dated *image tag* with an explicit package list, which is a strictly stronger pin than an
interpreter path (it pins the libraries too, which `-I` does not). **verifiers v1: yes, and
architecturally better** — a `docker` runtime pins by image digest. So the differentiator is
real against the training libraries and *already surpassed* by the two systems that took
execution seriously. The correct read is not "we have something nobody has"; it is "we
independently rediscovered why serious systems containerise their verifiers, and the
container is the general form of our pin." That is still a good position. It is a different
claim.

**O4. Where do the tasks come from?** This is the one I would have put first. Every
framework in Q1 assumes a task bank with ground truth already exists — TRL wants a dataset
column of `solution`, veRL wants `ground_truth`, verifiers wants `answer`, OpenAI wants
`item`. srlm-forge draws from AceCode-89K. For "trained on ANYTHING, commercial and
industrial," the binding constraint is not the verifier interface — it is that a customer
has a machine-checkable spec and **no labelled task bank**, and no amount of seam design
produces one. Reasoning Gym's answer is procedural generation, which is why it is the most
useful thing in this survey despite not being a seam at all (Q3). Activation #18 asked how
to plug a verifier in and never asked what it would be pointed at.

**O5. Is DPO even the right consumer of a pluggable verifier?** Every interface surveyed is
built to be called **inside an online RL loop, per rollout** — GRPO, PPO, RLOO, RPT.
srlm-forge's `forge.py` runs offline and writes jsonl. Adopting any of these frameworks'
seams therefore also means adopting an online trainer, which is a far larger change than
"extract `verify()`." And the channel already has the argument for it: §62 banked Song et
al. (coverage) and the still-unacted arXiv:2504.20571 (one-shot RLVR moving
Qwen2.5-Math-1.5B 36.0%→73.6% via *on-policy* RLVR). The verifier-seam question and the
offline-vs-online question are the same question wearing different clothes, and #18 asked
only one of them.

**O6. Which track is this about?** §81 puts the ingestion change (Track B, char model) and
the structural finding (Track A, DPO) in one section under one restated goal, and Q1–Q4
address only Track A. The closed-class claim this round is Track B. Nothing asks how a
verifier seam relates to a from-scratch character model that has no objective check — and
"from scratch on whatever machine is used" is a *Track B* promise while "improve against an
objective check" is a *Track A* promise. They are two products.

---

## THE QUESTIONS THEMSELVES — did activation #18 ask the right four?

**Q1 was the right question and it was right to make it the round.** It returned more than
expected: not just "who has done this" but a *better decomposition than the one the
DIRECTIVE was reasoning with*. The proprietor's instinct ("there's probably an implemented
way this switch has been done before") was correct, and the payoff was not a library to
adopt — it was the taskset/harness/runtime split that dissolves "only `verify()` is
conceptually hard."

**Q2 was right but under-specified.** It asked *which* second domain and not *what property
a second domain must have*. Without the discriminating list, "cheapest genuinely different"
was doing the work, and cheapness would have selected a domain that shares the fence
assumption and hides F2's fifth site.

**Q3 was asked on a false premise**, and the premise is refuted by this project's own
`ruler_noise` output (F4). The question worth asking in its place is *"at what point does
the estimand change from 'this model's pass rate' to 'this training procedure's pass rate',
and does the instrument still work there?"* — which is the greedy-free decision from §76,
still open, now more consequential.

**Q4 was right, well-scoped, and honestly caveated by the answer** (7B online RL vs. this
project's offline DPO — shape only).

**The questions it should have asked and did not**, ranked:
1. **"Where do tasks come from in a new domain?"** (O4) — the actual commercial blocker, and
   the one with the best answer available in the literature.
2. **"Is offline DPO the right consumer of a verifier seam at all?"** (O5) — the seam
   question and the online question are entangled, and the channel already holds the
   evidence for the online side.
3. **"What does the reward have to *be* — bool, scalar, or structured — and what does a
   timeout score?"** (O1/F5) — this is upstream of the interface, and the interface cannot
   be designed without it.
4. **"What does migrating the ruler cost?"** (O2) — 6,200 generations, computable from the
   code, and not mentioned.
5. **"Does any of this apply to Track B?"** (O6).

---

## ONE RECOMMENDED NEXT PROMPT

> Two fixes with red witnesses first, then the second domain, built to break named
> assumptions rather than to be cheap.
>
> **(1) Fix the ingestion probe.** `make_corpus.is_trainable_file` reads 8192 bytes and
> strict-decodes them, so a valid UTF-8 text file is refused whenever the boundary splits a
> multi-byte character — deterministically for 3-byte scripts. Red witness: 8191 ASCII
> chars + `é` + 100 chars is refused as "content is not text". Trim the trailing incomplete
> sequence before decoding. Add test cases per writing system (CJK, Cyrillic, EU-accented,
> ASCII) at sizes above the probe boundary; the existing multi-byte test uses a 40-byte
> string and cannot reach this. Also fix the two `start_studio.py` messages that still tell
> the user to supply `.txt/.md/.py`, and change
> `test_the_two_callers_share_one_rule` from a string search to a behavioural test
> (a `.csv` written into a temp `training_data/` must be found by `user_files()`).
>
> **(2) Fix `build_ruler.cmd_freeze`.** Line 295's `else:` binds to `if problems:` at line
> 277, not to any check of `ruler_noise.jsonl` — so every successful freeze prints
> "ruler_noise.jsonl absent" while the file is present at 209,606 bytes. Restore the intended
> guard and add the first test that `cmd_freeze` has ever had; assert on its printed output,
> not its exit code.
>
> **(3) Correct the record in the channel** before sizing anything against it: the
> domain-welded count in `forge.py` is at least six, not four — `ACTOR_SYSTEM` (`forge.py:68`)
> and `BANNED` (`forge.py:76`) are the additions, and `ACTOR_SYSTEM` is load-bearing in
> `train_native.py:52-60`, where the DPO seam reconstructs the fenced form because
> `ACTOR_SYSTEM` demands it. Grep, don't read one file: `ACTOR_SYSTEM|extract_code` hits
> 8 files.
>
> **(4) Then build SQL-against-a-fixture-DB as the second domain**, under three hard
> constraints that make it a discovery instrument rather than a second product:
> (a) **do not import `forge.ACTOR_SYSTEM`** — write a fresh system prompt, then diff the
> two and treat every shared sentence as a candidate harness parameter;
> (b) **emit a genuine scalar reward** (rows correct / rows expected), not a boolean, so the
> partial-credit question is answered by an instance instead of by argument;
> (c) **give tasks a fixture resource** that must be written before the check runs and
> pinned into the task hash, so the runtime-vs-scoring split is discovered rather than
> asserted.
> Structure the result as **taskset / harness / runtime** — the decomposition
> PrimeIntellect's `verifiers` v1 arrived at (https://www.primeintellect.ai/blog/verifiers-v1)
> — but do **not** take the dependency: v0 is frozen and slated for deprecation, v1 is
> mid-rewrite, and the whole stack is async while this one is not.
>
> **(5) Two decisions to record, not to code.** What does the reward *return* — every
> surveyed framework wants a float, and this project disabled its only graded channel as a
> reward hack; and what does a **timeout** score, given `forge.py:504-511` insists a timeout
> must never become a `rejected`, while OpenAI's grader contract scores an exception as 0.
>
> Do **not** migrate the ruler to any external schema yet. It costs the 40 banked replicates
> (31 tasks × 5 samples × 40 = 6,200 generations) because renaming task fields changes
> `task_sha256`, changes `ruler_set_sha256`, and fires `verify_frozen()` by design.

---

*THE PHD, solo seat. Advisory only; no code was modified and no training, generation or
screening command was run. The only executed work was read-only inspection of pinned bytes
and of `make_corpus`'s pure functions in a temporary directory.*
