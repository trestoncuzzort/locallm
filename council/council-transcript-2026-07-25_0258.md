# LLM Council — srlm-forge Monitoring Pass #2

**Date:** 2026-07-25 02:58
**Mode:** Project monitoring (recurring, watcher-armed)
**Trigger:** Executor posted a new DIRECTIVE + EXECUTOR LOG (ruler shipped)

---

## The executor's ask

The frozen ruler now exists (baseline pass@1=0.88, pass@3=0.90; `rotate`=0/5 hard
frontier, `rle`=4/5). The only on-box model is llama3:8b-q4. Design item-1's
reference-solution injection for all-fail tasks **without** a stronger on-box model:
where does an above-frontier, verifier-checked `chosen` come from, and how do we keep
it honest (no leaking hidden-test internals into the pair)? Rank the options.

Options framed: (1) off-box cloud teacher, verified; (2) massive rejection sampling of
the same 8B + execution-feedback retry; (3) human reference; (4) trusted corpus
retrieval; (5) curriculum decomposition.

---

## Advisor responses

### The Contrarian
If the 8B *cannot* produce `rotate`, every scheme here is distillation wearing a
self-improvement costume — name it, because it changes what "success" means. The poison:
DPO rewards the token log-ratio between chosen and rejected, not "correct." An injected
canonical solution (opts 1/3/4) shares almost no tokens with the model's mangled attempt,
so the gradient is dominated by nuisance *style* — you teach "look like the teacher," and
that style pressure can regress pass@1=0.88 on tasks it already passes. The only honest
contrastive pair is a **minimal edit** of the rejected that flips it green; a from-scratch
reference is the wrong shape for code-*repair* DPO. Test-overfit is the leak you think you
closed: "verified" only means it passed the hidden asserts — a source optimized against
those asserts hands you a chosen that hardcodes edge cases. Option 2 (STaR self-sampling)
is the only real self-improvement, but dead where you need it: rotate=0/5 ≈ zero
probability mass; cranking K samples louder noise. Ranking: **4 (corpus, as minimal-edit
target) > 5 (where subtask rate >0) > 2 (where base rate >0) > 1 (most capable, most
silently a distillation channel, most assert-overfit-prone).**

### The First Principles Thinker
The question smuggles a contradiction. "Self-rewarding" already fails — the reward comes
from the verifier, not the model (it's verifier-grounded RL, fine). And "where does an
above-frontier chosen come from for a task the 8B cannot solve" answers itself: from
outside the 8B. That's distillation by definition; stop looking for an honest internal
source for absent capability. Real question: what mechanism teaches genuinely-absent
capability? **DPO is the wrong primitive** — it sharpens a preference between things the
model already samples; on rotate=0/5 there's no signal to sharpen, and pairing an alien
reference against garbage teaches surface mimicry. The honest primitive for absent
capability is **SFT on a verified reference**; reserve DPO for near-frontier (rle=4/5)
where the model already straddles the boundary. Split the set by **margin, not all-fail**:
near-frontier → DPO on self-sampled pairs (opt 2, on-box); genuinely-absent (0/K) → SFT on
external verified reference (opt 1 or 4, auditable). Honesty: the verifier proves
correctness but can't prove non-overfitting — your **frozen ruler** does; keep hidden
asserts out of the teacher's prompt, verify post-hoc only. Option 5 isn't a source of
chosens — it's how you shrink the absent bucket so fewer tasks need injection. Highest
leverage.

### The Expansionist
The compounding asset isn't a repaired-code corpus — it's a **verified capability ledger**:
every injection records a task the 8B provably couldn't do at K, a source that could, and
a passing solution — a growing map of where the frontier sits and what moves it. Three
upsides: (1) the 8B is a bigger teacher than it looks — rotate=0/5 at K=5 is "not yet at
this budget"; execution-feedback rejection sampling at K=64 likely converts many all-fails
into self-sourced pairs (self-distillation, no teacher bill, compounds — each round the
frontier walks forward). (2) The harness is provider-agnostic: "any source in → verified
chosen out" makes cloud/corpus/human just plugins behind one honesty gate — a general
capability-transfer engine; code-repair is the first cartridge. (3) The failure frontier is
a free curriculum — 0/5 tasks auto-rank what to teach next; route cheap self-sampling to
the near-frontier, expensive cloud teachers only to the truly-stuck (adaptive spend).
Rank for upside: **(2) rejection sampling first** (the compounding self-teacher), **(1)
cloud** reserved as the sniper for the residual hard core.

### The Outsider
The thing that doesn't add up: "no stronger model on this computer" but "cloud model is
fine" — that's not a principle, it's a location preference. The cloud model IS the stronger
model. Every option except (2) sources the answer from OUTSIDE the model — so for "rotate"
the model isn't improving itself, it's being taught (fine, but don't call it
self-improvement). What worries me: training the model to reproduce a stranger's clean
solution for the exact task the tests check is the definition of memorizing the answer key.
"Keeping it honest" can't be a style tweak. The one result that settles it: hold out a
DIFFERENT rotate-shaped task with tests it wasn't trained against — after injection, can it
pass THAT one cold, with no reference? If yes it learned rotation; if no you taught it one
poem by heart. By that test, **option 5 (decompose into pieces the model can solve itself)**
is the only one where the model does the reaching — which is what the builder says they want.

### The Executor
Fastest verified-honest path this week: **Option 2 first (Monday), Option 1 as backstop.**
Rejection sampling of the same 8B needs zero new deps. Add execution-feedback retry: on
all-fail, re-sample at K=64, temp 1.0, feed each failing candidate's traceback back into the
prompt for up to 3 rounds. Converts most near-frontier all-fails cheaply; genuinely-hard
rotate likely still fails at K=64 → cloud teacher fires there. Both funnel through one gate.
Pipeline change — `inject_reference(task)`, called only when the normal loop yields zero
passing candidates: (1) source: 8B-retry-loop → else one cloud call; (2) verify against the
FULL hidden tests in the existing sandbox; (3) **honesty gate** (all must pass): held-out
20% test slice the author never saw; AST constant ban (reject if any test-input literal
appears as `ast.Constant`); mutation check (mutate reference, confirm held-out slice fails);
(4) emit pair chosen=verified reference, rejected=model's own best failing attempt.
**Build first:** the reusable `honesty_gate(solution, task)` + full-hidden-test verify — the
trust boundary, reusable across all sources. Wire Option 2 retry same day; cloud second.

---

## Cross-critique (folded into synthesis)

- **Contrarian + First Principles converge hard on the deepest correction:** DPO on an
  alien reference vs a garbage attempt trains style-mimicry and can regress the 0.88
  baseline. The all-fail lane wants **SFT** (or a minimal-edit chosen), not raw DPO. This
  overrides part of activation #1's phrasing.
- **First Principles' "split by margin" reframe** reconciles the Expansionist↔Contrarian
  clash on Option 2: rejection sampling is right where base rate >0 (rle), useless where
  base rate ≈0 (rotate). Measuring the base rate at K=64 IS the routing signal.
- **Contrarian + Outsider converge:** passing the hidden tests ≠ honest; the mechanical
  gate + the frozen ruler's *generalization* test are the real safeguards.
- **First Principles + Outsider converge:** decomposition isn't a chosen-source, it's
  bucket-reduction — and the only lane that is genuinely "self."

---

## CHAIRMAN VERDICT

### Where the council agrees
- For genuinely-absent capability, an above-frontier `chosen` must come from outside the
  model — that's **distillation**; name it honestly.
- **DPO is the wrong primitive** for injecting an alien reference against a failing attempt;
  it trains style, not the fix, and risks regressing the 0.88 baseline.
- **Verification ≠ honesty.** A mechanical gate (held-out test slice + AST input-constant
  ban + mutation check) plus the frozen ruler's generalization test is required.
- The **failure frontier is a self-directing curriculum**; the durable asset is the
  verified capability ledger / provider-agnostic transfer harness.

### Where the council clashes
- **Can the 8B be its own teacher?** Expansionist: yes — K=64 + exec-feedback rescues most
  all-fails (compounds). Contrarian: rotate=0/5 ≈ zero mass; K just amplifies noise.
  Reasonable disagreement because it depends on the task's actual base rate — which is
  *measurable*, so the resolution is empirical, not rhetorical.
- **Which source ranks first for the hard core:** corpus retrieval (Contrarian: auditable,
  overfit-resistant) vs cloud teacher (Executor/Expansionist: most capable sniper). Both
  behind the same honesty gate; corpus preferred when a canonical solution exists.

### Blind spots caught
- Activation #1's "inject a reference so a chosen exists" quietly assumed DPO; peer review
  caught that it must be **SFT / minimal-edit** for the all-fail lane.
- "No stronger on-box model, cloud OK" is a location preference, not a capability
  principle — the honest framing is two labeled lanes (self vs transfer).

### The recommendation
Separate two lanes and **route by measured base rate**, not by "all-fail":
1. **Self lane** — rejection sampling (K=64, temp~1.0) + 3-round execution-feedback retry on
   the same 8B → self-sampled DPO pairs. On-box, compounds. Use for any task with base
   rate >0 at higher budget (expect rle).
2. **Transfer lane** — for the residual true-0-mass core (expect rotate): external verified
   reference via **SFT** (or a minimal-edit chosen), sourced corpus-first (auditable), cloud
   as sniper; labeled as distillation.
Build one reusable **`honesty_gate`** as the trust boundary for any external source. Prove
success on the ruler: a *different* same-shape held-out task passed cold, with no baseline
regression. Apply decomposition to shrink the transfer lane.

### The one thing to do first
**Measure the frontier's reachability before sourcing anything external:** run each all-fail
task at K=64 / temp 1.0 with 3-round execution-feedback retry, and log per-task whether any
candidate now passes the full hidden tests (+ wall-clock). That single measurement routes
every task into the self vs transfer lane and prevents importing a distillation/overfit
problem you don't yet need. Stub `honesty_gate` alongside it. No external teacher, no
training run, until that data is in.
