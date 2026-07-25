# LLM Council — srlm-forge Monitoring Pass #3

**Date:** 2026-07-25 03:17
**Mode:** Project monitoring (activation-driven)
**Trigger:** Proprietor relayed the executor's expanded directive (the file's DIRECTIVE
block still showed the #2 ask; the paste added Q3 and new state)
**Scope:** instructions.txt only

---

## The executor's ask (expanded #2 directive)

State: frozen ruler live — baseline pass@1 = 0.88, pass@3 = 0.90; `rotate` (a RULER
task) = 0/5 hard frontier; `rle` = 4/5. Conciseness reward-hack pairs gated OFF, dedup
ON, detached overnight local-Ollama loop accumulating clean correctness pairs. Executor
is mid-implementation of activation #2's verdict (K=64 + execution-feedback reachability
sweep; honesty_gate stub). Only local model: llama3:8b-q4.

Design the reference-solution injection for all-fail tasks:
1. Where does an above-frontier, verifier-checked `chosen` come from without a stronger
   on-box model?
2. How do we keep it honest — no leaking test internals into the pair, no circular
   "the pipeline wrote both the task and its answer"?
3. **What's the smallest change that proves it moves the ruler above baseline noise,
   before we invest in scale?**

Deliver a ranked critique plus ONE concrete recommended next prompt.

---

## Advisor responses

### The Contrarian
Your ruler cannot see the thing you're about to chase. At 44/50, the entire measurable
range is six samples, and they aren't independent — they're clustered in two tasks.
Eight tasks sit at ceiling; the instrument is effectively `rotate` (0/5) plus one spare
`rle` sample. Binomial SE at 0.88, n=50 is ~4.6 points — a single run can't distinguish
0.88 from anything below ~0.97. Worse: the noise floor was never measured. Has eval.py
ever been run twice on the *same* checkpoint at temp>0? Until you have the run-to-run
distribution of the unchanged model, every delta is uninterpretable.

So the smallest proving change is not an injection: (1) rerun the frozen ruler 5x on
the baseline checkpoint — one evening — for empirical variance; (2) raise n from 5 to
20 on the same frozen tasks (the tasks are frozen; n is a knob) so `rotate` has
resolution; (3) snapshot the corpus and PAUSE the overnight loop during the experiment
— if it keeps appending while you inject, you have two variables and zero attribution,
and an unattended Ollama hiccup can meanwhile stuff failures.jsonl with degenerate junk
your retry loop will dutifully target.

Then the laundering trap: you inject rotate-adjacent tasks, `rotate` flips 0/5→5/5,
you call it generalization. Null hypothesis: you trained a paraphrase of the ruler task
and DPO memorized the answer key. Pre-register an AST/n-gram similarity threshold
between injected and ruler tasks *before* training, and define victory as: movement
replicates across two eval seeds AND zero regression on the eight ceiling tasks. DPO's
likeliest real outcome here is `rotate` up, one 5/5 down — net zero, cherry-picked as
a win.

### The First Principles Thinker
You're asking "what's the smallest change that moves the ruler?" That's the wrong
question until you ask what the ruler can physically detect. Strip it down:

**The aggregate is fake resolution.** Eight of ten tasks sit at 5/5; pass@1's total
headroom is six samples, and the SE at n=50 is ±4.6 points — you'd need ~+9 points to
clear noise with ~12 available, nearly all from one task. Aggregate pass@1 structurally
cannot certify injection. The ruler's only detectable event is `rotate`.

**But 0/5 is not zero.** The 95% CI on 0/5 extends to a ~45% true pass rate. So the
smallest change is to the *instrument*, not training: sample `rotate` at n=100. Frozen
means no gradients, not no inference — measurement doesn't contaminate. Two outcomes:
nonzero base rate → rotate is self-lane and the injection premise itself weakens;
0/100 → you now own a zero-background detector where a pre-registered ≥5/100
post-injection is significant (Fisher ~0.03).

**Proof = specificity, not improvement.** Ruler disjointness means a memorized
reference can't cross the task boundary — unless training tasks near-duplicate ruler
tasks. So the minimal causal chain is two arms, identical pair count and steps: arm A
injects one rotation-family reference, arm B one unrelated-family reference. Capability
is proven only if A moves `rotate`, B doesn't, and the nine saturated tasks hold.
Report nearest-neighbor similarity between the injected reference and `rotate`
alongside, or the result is uninterpretable.

**Pre-commit on negative:** conclude "one reference at this dose doesn't cross the
task boundary" — next lever is dose-response — not "injection dead." And admit the
structural flaw: a one-task frontier can't certify a method. Before scaling, build a
small same-family probe set, never trained, not the ruler.

### The Expansionist
If `rotate` flips, don't file it as a result — file it as the first execution of a
template. The minimal proof is secretly a pipeline spec: ruler finds a 0/5 frontier
task → build a targeted task-family pack → train → verified flip. Frontier discovery,
family curriculum, flip — nothing in that loop is rotate-specific, and `rle` at 4/5 is
the second customer already queued. The unit of progress stops being "more pairs" and
becomes "frontier tasks flipped," a metric that compounds: each flip makes the
overnight factory's actor stronger, and a stronger actor re-mines failures.jsonl —
yesterday's all-fail tasks become today's partially-solvable ones, converting the
failure log from graveyard into a frontier queue. That's the flywheel: flip, stronger
actor, re-mine, next frontier.

eval_history.jsonl is the sleeper asset. Kept per-task rather than aggregate, it's a
longitudinal growth chart: which families move together when you train one pack is
free structural signal about which skills share substrate, and an argmax for "which
pack next." And when `rotate` flips, read the rest of the ruler — if `rle` ticks to
5/5 too, the pack taught a skill, not a task; transfer measured for free.

Cheap now, priceless later: (1) auto-family-tag every generated task — one metadata
field, unlocks per-family slicing forever; (2) a frontier ledger (task, family,
pass-rate, first-flip checkpoint); (3) have the overnight loop append a per-task eval
row with checkpoint hash each morning, so the growth chart writes itself while the
builder sleeps. Upside case: the ruler becomes the curriculum generator, and when it
saturates, the ledger says it's time to mint a frozen ruler v2 — versioned rulers as
capability milestones.

### The Outsider
The studying/cheating line: studying practices the *skill*; cheating practices the
*answer*. Concretely, it's cheating if any training task is an exam question or a
near-duplicate of one — and as described, nobody checks that. The stated integrity
check ("no hardcoding test answers") catches literal fraud, not the quieter version:
importing the canonical solution to a problem that's 95% the same as "rotate." Missing
piece: an automated similarity audit comparing every new training example against all
10 exam questions and solutions, printing the nearest match for a human to eyeball.

Subtler leak: you say the model never trains on the exam, but *you* read the exam and
aim the pipeline at its failures. That turns your test set into a dev set — the human
is the leakage channel. The current 10 questions are already partially burned.

Circularity worry #2: "correct" means "passes the tests." Who audits the tests? A weak
test suite lets a wrong imported solution in, and you'd train on confidently-wrong
code. That's a bigger honesty hole than hardcoding.

On statistics: 88% is 44 of 50 attempts. One flipped attempt moves the score 2%. Five
tries per question genuinely is judging a shooter on five free throws — the 4-of-5
question may just be a coin wobble.

Smallest convincing experiment: pre-register it. Run "rotate" 100 times now (expect
~0/100). Train only on the new data. Run 100 again. If it goes 0/100 to 60+/100, the
other nine questions hold at high attempt counts, and you can display the nearest
training example proving it isn't rotate-in-disguise — a total stranger believes that.
Then retire these 10 and seal a fresh exam written after training.

Oversold: the crisp-sounding "88%." It's fifty noisy coin flips wearing a lab coat.

### The Executor
**Target family:** `rotate`-class repairs (slice/modular-index/reversal bugs). Why:
ruler is 44/50 with eight tasks saturated — the only measurable headroom is rotate 0/5
(+rle 4/5). This family is also where self-lane mass is ~0, so it isolates the
injection question.

**Data (~4h):** Filter MBPP+HumanEval by AST features (slicing, `%` indexing, reverse)
→ ~120 tasks; seed 2 mutations each → ~240 repair tasks; corpus tests = verifier.
Local K=8: solvable → self-lane pair; 0/8 → transfer-lane (chosen = minimal-edit
reference revert, rejected = top failing sample). Ship ≥150 pairs.

**Guards:** Every pair carries `{task_src, chosen_src, test_src}`; hard-reject if
model authored task *and* tests in-run — tests must be corpus-origin. Ruler collision
filter: normalized-prompt 5-gram Jaccard ≥0.35 **or** solution AST-hash match vs any
ruler task → reject, log to `ruler_collisions.jsonl`.

**Statistics:** n=5 can't detect anything at 0.88. Bump eval to n=20 on rotate+rle
only (n=5 elsewhere). Re-run rotate/rle baseline at n=20 *before* training.

**Pre-registered (commit `prereg_exp1.json` first):** SUCCESS = rotate ≥6/20 post vs
~0/20 pre (Fisher one-tailed p≈0.01) AND aggregate ≥0.84 AND no saturated task <4/5.
FAIL = rotate <4/20. Between = inconclusive, one repeat max.

**Env (minimal):** WSL2 Ubuntu 22.04, py3.11 venv, cu121 torch, Unsloth QLoRA ORPO,
1 epoch. Merge → GGUF q4_K_M → Ollama — **same quant as baseline**, like-for-like.

**Log:** prereg file, pair provenance, collisions, loss curve, eval_history pre/post.
**Abort:** <150 pairs post-guards; 2 training crashes; post-aggregate <0.80 → drop
adapter, keep data. **Wall-clock:** ~7h — one overnight.

---

## Cross-critique (folded into synthesis, per monitoring mode)

- **Four advisors independently hit the instrument problem** (SE ±4.6pts; eight tasks
  at ceiling; 0/5's CI reaching ~45%; "five free throws") — the strongest convergence
  of any pass so far. The Executor's n=20 is the floor; First Principles' n=100
  zero-background detector strictly dominates and costs under an hour of sampling.
- **First Principles' two-arm specificity control** is the only design that separates
  "learned the skill" from "any training wobbles the ruler" — no other advisor had it;
  the chairman adopts it as the confirmatory step gated on a flip.
- **Contrarian's attribution point** (stockpile keeps growing during the experiment =
  two variables) is resolved by training on the curated pack ONLY, rather than pausing
  the loop — the loop just must not feed this run.
- **The Outsider's two holes are genuinely new** (builder-as-leakage-channel → ruler
  partially burned → sealed v2; unaudited corpus tests → mutation-adequacy on test
  suites) and were missed by every technical advisor across three passes.

---

## CHAIRMAN VERDICT

(As written to instructions.txt §8: ranked critique 1–5 — instrument first (3× baseline
reruns, rotate n=100/rle n=50, self-lane reroute if >0/100); the pre-registered
single-variable frontier-flip run (~150-pair rotate-family pack, ORPO 1 epoch, same
quant back, two post-eval runs, aggregate/ceiling guards, prereg committed first,
unrelated-family control before any capability claim); mechanical laundering +
circularity guards (ruler-collision filter, provenance triple, nearest-neighbor
disclosure); the two new honesty holes (sealed ruler v2 selected blind to v1, probe
set, mutation-adequacy on test suites); and the flip-as-template ledger. ONE prompt:
the two-night measurement-then-experiment sequence.)
