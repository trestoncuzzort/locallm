# LLM Council — srlm-forge Monitoring Pass #1

**Date:** 2026-07-25 02:44
**Mode:** Project monitoring (recurring)
**Target:** `C:\Users\t\Projects\srlm-forge`

---

## Framed question

Recurring council review of srlm-forge — a local, failure-driven self-rewarding DPO
data pipeline. A local Ollama model (`llama3:8b-instruct-q4_K_M`) proposes K candidate
solutions to pure-function Python tasks; hidden unit tests are the ground-truth reward
(the model never scores itself); best verified candidate = "chosen", strictly-worse =
"rejected" → DPO pairs; unsolved tasks → `failures.jsonl` curriculum; `train_dpo.py`
does QLoRA DPO and exports GGUF back to Ollama, closing the loop.

**State as of this pass:** Generation pipeline live and verified. Latest run: 6 tasks,
5 solved, 3 valid DPO pairs (1 conciseness, 2 correctness). 1 task (spiral) unsolved.
Training gated on missing Python 3.10–3.12 + CUDA torch + Unsloth env (system is 3.14).
Only ~3 pairs so far. Safety lines held (no privilege escalation, no empathy-suppression).

**Mandate:** Assess trajectory. What's at risk, what's being missed, what's the
highest-value move right now?

---

## Advisor responses

### The Contrarian
The fatal flaw is the ceiling, not the scale. Everyone's worried about "only 3 pairs" —
wrong worry. DPO pairs only exist when the model *already* solves a task; every "chosen"
is self-generated. This is self-distillation with a hard ceiling at the model's existing
capability. `failures.jsonl` is a fiction: tasks no candidate solves produce *zero*
gradient — no "chosen." The pipeline systematically ignores exactly the material that
would teach something new. "Trains on its own failures" is precisely what it *cannot* do.

The conciseness pairs are a reward hack in progress: both pass hidden (weak-proxy) tests,
shorter is labeled "chosen" — training a bias toward terse code that games
under-specified tests. Kill conciseness preferences until there's a robustness signal.

There's no held-out eval, so there's no proof the loop improves anything. QLoRA DPO on
~3 pairs likely *degrades* the model (forgetting) and you'd never know — the loop "closes"
regardless of whether pass@1 went up or down.

**Highest-value move:** Stop. Build a frozen held-out task set and measure pass@k before
scaling or training. Build the ruler before you build the factory.

### The First Principles Thinker
"Python 3.14 blocks training" is not the blocker. Even if `train_dpo.py` ran tonight,
3 pairs trains nothing. The real blocker is structural: a self-rewarding loop can only
mint signal from tasks the generator already half-knows. Genuine failures produce zero
pairs and rot in `failures.jsonl`. The generator is both student and teacher and can't
teach past itself — a ceiling baked into the design, not a scale problem.

Ask the real question: what are you trying to produce? If "a stronger local coder," this
loop is close to the least efficient path — bottlenecked by an 8B q4 bootstrapping off
its own output. Distilling pairs from a *stronger* model against your unit tests would
dominate it in a day.

But the real asset is what was built almost by accident: an objective, test-grounded,
adversarially-filtered preference-pair harness. The reward is ground truth, not model
opinion — that's rare. The model is disposable; the verifier is durable.

**Move:** Decouple the two halves. Point the harness at a strong generator to mass-produce
verified pairs; keep the unit-test reward as filter; let the 8B *train* rather than
*author* its own curriculum.

### The Expansionist
You're all staring at the wrong asset. The DPO pairs are the byproduct. The crown jewel
is a **zero-human-label, zero-self-scoring verified-preference factory** — objective
ground truth manufacturing training signal autonomously.

Three undervalued upsides:
- **Domain-agnostic reward.** Unit tests are just one oracle. Anything checkable plugs
  into the same loop: SQL returning specific rows, regexes matching a set, JSON validated
  against a schema, Lean proofs that compile, shell commands that exit 0. Swapping the
  oracle is a config change, not a rewrite.
- **`failures.jsonl` is a difficulty-frontier discovery engine** — automatically mapping
  the exact boundary of what the model can't yet do. That curriculum signal compounds.
- **The training blocker is a gift.** The generator is a standalone data asset that
  produces verified pairs whether or not you ever train locally. Stockpile the JSONL; any
  env consumes it later. You're conflating manufacturing with consumption.

**Move:** Don't wait on Unsloth. Parallelize K-candidate generation overnight (embarrassingly
parallel) and have the model *auto-generate new tasks plus their tests*, filtered by
coverage — turning a 6-task trickle into a self-expanding thousand-task corpus across
verifiable domains. Training is commoditized; the autonomous verified-data flywheel is the moat.

### The Outsider
You call this "self-rewarding," but the model never rewards itself — hidden unit tests do.
That's just... unit tests. The interesting claim in "self-rewarding" is that the model
judges its own output. Yours doesn't. The name oversells it; be honest about which thing
you're actually building, because the two have very different value.

The math is tiny: 6 tasks, 3 pairs. DPO on 3 examples does effectively nothing. So the
"loop" that's the whole point has never closed, and even if training ran today it'd train
on almost nothing. What convinces you it scales to thousands of pairs? Where do tasks come
from? If a human hand-writes each task and its hidden tests, the "autonomous" part is doing
a lot of quiet work.

"Trains on its own current failures" — but you make pairs only from successes and throw
failures into a bucket. It trains on its successes. That's the opposite of the tagline.

Plainly: the loop has never run once end-to-end; the closing step is blocked on a Python/GPU
install. Until it closes once, is this a self-improving system, or a data generator with an
aspirational README? What single result would prove this works — and how far are you from it?

### The Executor
The data problem outranks the environment problem — you can't train on 3 pairs, so fixing
the env first just leaves you idling. But both can run in parallel.

**Track A — scale data TODAY (no new deps):** Stop hand-writing tasks. MBPP gives ~970
pure-function problems with hidden tests already shaped like your pipeline. `requests`
already works — pull `mbpp.jsonl`, write a ~20-line adapter mapping `text`/`test_list`/`code`
into your task schema, point `forge.py` at it, kick off an overnight run at K=8. That alone
takes you from 3 pairs to hundreds. Highest-leverage, zero env work.

**Track B — build the training env in parallel:** `winget install Python.Python.3.12`
(side-by-side, don't touch 3.14). Then `py -3.12 -m venv .venv312`, install torch from the
cu121 index, then unsloth/trl/peft. cu121 matches the known-good cuda_v12 lane on driver
591.86 — do NOT let it pull a cu13 wheel. Smoke-test `torch.cuda.is_available()`.

**Sequencing:** Launch Track A first (long pole, unattended), set up Track B while it churns.
Don't run training until ~500 pairs — below that the QLoRA signal is noise.

---

## Cross-critique (folded into chairman synthesis)

- Contrarian's **conciseness reward-hack** flag is the blind spot in every "scale it now"
  answer: MBPP at K=8 scales the biased signal too, unless conciseness pairs are gated.
- Executor's is the only answer with real commands — but every MBPP pair is still a
  self-solved *success*, so it scales volume of the *ceilinged* signal. Combining
  Executor's mechanics with First Principles' "source chosen from a stronger generator"
  fixes both at once.
- Contrarian + First Principles + Outsider independently converged on the
  self-distillation ceiling and the "failures produce no gradient / tagline is inverted"
  point — the highest-confidence signal in the room.
- Expansionist + First Principles converged from opposite temperaments on the same asset
  reframe: the durable thing is the **verifier-grounded preference factory**, not the model.

---

## CHAIRMAN VERDICT

### Where the council agrees
1. **The self-distillation ceiling is real and structural.** Three advisors caught it
   independently: pairs form only from tasks the model already solves, so genuine failures
   yield zero gradient. "Trains on its own failures" is inverted — it trains on its
   successes. This is the highest-confidence finding.
2. **Data volume, not the Python env, is the true bottleneck.** 3 pairs trains nothing;
   fixing the env first just idles.
3. **The durable asset is the verifier-grounded preference factory, not the 8B model.**
   The model is disposable; the objective, test-grounded reward harness is the rare part.
4. **The loop has never closed and there's no eval, so nothing about improvement is proven.**

### Where the council clashes
- **Whose output feeds the harness.** First Principles: stop self-generation, point it at
  a *stronger* generator so the 8B trains instead of bootstrapping off itself.
  Expansionist: keep it autonomous, expand oracles/domains, auto-generate tasks — build a
  flywheel. Both are right about the asset; they disagree on whether to preserve the
  "self" in self-improvement. Reasonable disagreement because it depends on the actual
  goal (a stronger local coder vs. an autonomous data-generation primitive).
- **Sequencing: measure first vs. scale first.** Contrarian: STOP and build a held-out
  eval before anything. Executor: launch the MBPP data run tonight. These reconcile — the
  eval is cheap and the data run is unattended, so they run in parallel — but if forced to
  order them, the eval wins because everything downstream is unmeasurable without it.

### Blind spots the council caught
- The **conciseness preference is a reward hack** (both pass weak tests, shorter wins) —
  and every "scale it" plan would silently mass-produce that bias. Gate or drop it.
- **Scaling via MBPP still only scales self-solved successes** — more of the ceilinged
  signal. Volume without a stronger "chosen" source or a real eval is motion, not progress.
- **"Self-rewarding" is a misnomer** for what's built (it's test-rewarded). Naming it
  honestly changes how its value is judged.

### The recommendation
**Reframe the project from "self-improving local model" to "verifier-grounded preference-data
factory," and prove it with a ruler before scaling the factory.** Concretely:
1. Build a **frozen held-out eval** (20–50 tasks never used for pair generation); measure
   baseline pass@k now.
2. **Gate or drop conciseness pairs** until a robustness signal exists — don't scale a
   reward hack.
3. Scale data via **MBPP overnight (Executor's Track A)** — but treat self-sourced pairs as
   capped at current ability, and plan to source "chosen" from a stronger generator (First
   Principles) for anything past the ceiling.
4. Build the **Py3.12 + cu121 training env in parallel** (Track B) — cheap insurance, not
   the bottleneck.
5. Train only once a checkpoint can be shown to **beat baseline on the held-out set.**

### The one thing to do first
**Build the frozen held-out pass@k eval harness** — 20–50 tasks that never enter pair
generation, and record the base model's baseline score today. Until that ruler exists,
every other move (scaling, training, closing the loop) is unverifiable. The data run can
start in parallel, but the ruler comes first.
