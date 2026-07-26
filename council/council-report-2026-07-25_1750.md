# Council Report — srlm-forge · Pass #5

**Date:** 2026-07-25 17:50 · **Trigger:** DIRECTIVE watcher — **first autonomous activation** · **Scope:** instructions.txt only
**Roster:** advisor #5 renamed **The Pragmatist**; debut of **The Asshole** (member #6, review pass, replaces peer-critique)
**Deliverable:** lean-shot vs full-plan ranking → written to channel §12

## The ask
Executor's verified corrections: stockpile is **1,235 pairs** (+38 repair), NOT ~60;
train∩ruler = EMPTY (the "mine rotate/rle" error was directive wording, never a data fact);
model still at ZERO gradient steps (ruler 0.88 → 0.88). Rank by fewest steps to a first real,
honest signal: (i) author 4 family tasks + mine 120 more, then train — vs (ii) lean shot: build
env, ONE ORPO epoch on existing pairs, re-measure under the prereg bar.

## Key numbers
1,235 + 38 pairs · top-3 tasks = 54% of set · verdict 5/5 + reviewer for (ii) · cap 120 → 919 · torch 2.5.1 = last cu121 wheel

## Verdict

**Unanimous: (ii) the lean shot — behind ONE gate.**
- (i) would author ruler-family neighbor tasks with no collision filter as running code —
  eroding the only working contamination defense. Family pack → round 2.
- **The gate** (reviewer's merge of three advisors' checks): (a) re-verify all 1,273 pairs
  **bidirectionally** — chosen must pass, rejected must FAIL (nobody had checked the rejected
  side); (b) **null re-export**: the untrained model through the full WSL2→merge→GGUF→q4_K_M
  path — the re-exported GGUF *becomes* the operative baseline, its 3× ruler runs the real
  noise floor.
- Curation by selection: cap 120/task → 919 pairs (58 steps); exclude the 38 repair pairs.
- Prereg relabeled: co-primary safety (non-inferior vs re-exported baseline, −2σ) +
  co-primary efficacy (multiply_strings n=100 lift) + exploratory rotate.
- "A library with no reader" (Outsider): 1,273 flashcards, zero study sessions — more cards is
  perfectionism wearing rigor's clothes.

**The Asshole's corrections (highlights of 10):** the ledger sums to exactly 1,235 *excluding*
repair — ALL 40 multiply_strings pairs are normal-lane (the quarantine contradiction is total);
cap-50 = "a smoke test masquerading as an epoch"; the old noise floor is statistically
worthless; honest wall-clock 12–16h. **Adopt-don't-build (web-verified):** TRL ORPOTrainer
(now `trl.experimental.orpo` — pin), Unsloth GGUF fallback (merged-16bit →
convert_hf_to_gguf.py → llama-quantize), ollama template from `ollama show --modelfile`,
**pin torch 2.5.1 (last cu121 wheel)**, pandas stratified sample, MinHash dedup, scipy
binomtest.

## The one thing to do first
The gate: bidirectional re-verification of all 1,273 pairs (~1–2h). Any failure = the
"verified" stamp itself is broken — the one condition under which training now is a mistake.

## Alignment map
| Member | Position |
|---|---|
| Contrarian | (ii) but the records disagree — re-verify before training; null re-export or quant drift confounds all |
| First Principles | (ii); relabel prereg — intact primary, rotate exploratory; family pack = round 2's mechanism test |
| Expansionist | (ii); mining has receipts (spiral 0→116); first full cycle is a no-lose trade |
| Outsider | (ii); "library with no reader"; re-verify the contradiction cards as go/no-go |
| Pragmatist | (ii), 9 steps vs 14; cap 120 → 919; exclude repair pairs; full run sheet |
| The Asshole | Concurs; 10 corrections, 7 adopt-don't-build items, one merged gate |

---
Full responses: `council-transcript-2026-07-25_1750.md` · Channel record: instructions.txt §12
*(Backdated .md conversion of the original HTML report, per proprietor mandate.)*
