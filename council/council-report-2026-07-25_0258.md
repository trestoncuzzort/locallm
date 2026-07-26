# Council Report — srlm-forge · Pass #2

**Date:** 2026-07-25 02:58 · **Trigger:** executor DIRECTIVE + §6 log (ruler shipped) · **Scope:** instructions.txt only
**Deliverable:** injection design ruling → written to channel §7
*(No HTML was ever produced for this pass — the session was interrupted mid-turn; this .md is
its first report artifact, reconstructed from the transcript.)*

## The ask
The frozen ruler now exists (baseline pass@1 = 0.88, pass@3 = 0.90; `rotate` = 0/5 hard
frontier). Only local model is llama3:8b-q4. Design reference-solution injection for all-fail
tasks WITHOUT a stronger on-box model: where does an above-frontier, verifier-checked `chosen`
come from, and how is it kept honest? Rank the options.

## Key numbers
Ruler: 10 held-out tasks, n=5 · baseline 0.88 / 0.90 · rotate 0/5 · rle 4/5

## Verdict

**Agrees:**
- For genuinely-absent capability, a `chosen` must come from outside the model — that is
  **distillation**; name it honestly ("no stronger model on THIS box, but cloud is fine" is a
  location preference, not a principle).
- **Verification ≠ honesty.** A mechanical gate is required for any external source:
  held-out ~20% test slice the source never sees + AST ban on test-input literals +
  mutation check.
- The failure frontier is a self-directing curriculum; the durable asset is the
  provider-agnostic transfer harness.

**Corrects activation #1:** "Inject a reference so a chosen exists" assumed DPO — wrong
mechanism. **DPO on an alien reference vs a garbage attempt trains style-mimicry** (token
log-ratio, not correctness) and can regress the 0.88 baseline. Correct primitives:
- True 0-mass capability → **SFT on the verified reference** (or a minimal-edit chosen derived
  from the model's own failing attempt).
- Near-frontier (e.g. rle 4/5) → **DPO on SELF-sampled pairs**.

**Recommendation — two lanes, routed by measured base rate:**
1. **Self lane:** rejection sampling K=64 / temp ~1.0 + 3-round execution-feedback retry →
   self-sampled pairs. Use wherever base rate >0 at budget.
2. **Transfer lane:** for the residual true-0-mass core — external verified reference via SFT,
   corpus-first (auditable), cloud as sniper, labeled distillation. Decomposition shrinks the
   bucket throughout.

## The one thing to do first
Measure frontier reachability BEFORE sourcing anything external: K=64 + retry sweep over the
all-fail tasks; log per-task pass counts + wall-clock. That measurement routes every task into
self vs transfer. Stub `honesty_gate(solution, task)` alongside.

## Alignment map
| Member | Position |
|---|---|
| Contrarian | DPO rewards token log-ratio, not correctness — alien references teach style; corpus > cloud for overfit resistance; STaR dead at 0-mass |
| First Principles | Split by margin, not "all-fail": SFT for absent capability, DPO for near-frontier; decomposition is bucket-reduction |
| Expansionist | 8B is a bigger teacher than it looks at K=64; verified capability ledger; adaptive spend (cheap self-lane, expensive sniper) |
| Outsider | Cloud model IS the stronger model; the proof is a different same-shape task passed cold |
| Pragmatist* | Build the reusable honesty_gate first; 8B retry-loop primary source, cloud backstop; emit rejected = model's own best failing attempt |

\* Renamed from "The Executor" on 2026-07-25.

---
Full responses: `council-transcript-2026-07-25_0258.md` · Channel record: instructions.txt §7
