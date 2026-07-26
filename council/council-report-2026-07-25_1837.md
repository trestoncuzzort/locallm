# Council Report — srlm-forge · Pass #6

**Date:** 2026-07-25 18:37 · **Trigger:** DIRECTIVE watcher (autonomous) · **Scope:** instructions.txt + proprietor-granted repo reads (The PhD, The Asshole)
**Roster:** debut of **The PhD** (member #7) — 21 tool calls, primary sources fetched, repo data measured
**Deliverable:** run-1 rulings → written to channel §14

## The ask
Gate PASSED (1 poisoned legacy conciseness pair removed → 1,272 clean; known_hard reconciled —
multiply_strings had 41 solves). Training env unblocked **Windows-native** (no WSL/admin:
py3.11.9, torch 2.5.1+cu121 sees the 4080; transformers 4.46.3 / trl 0.12.2 / peft 0.14.0 /
bnb 0.45.0). Asks: (a) bless native-HF-**DPO** over ORPO/Unsloth for run 1? (b) confirm
null-re-export-as-baseline → prereg → one epoch on "the 1,272 frontier pairs (repair excluded)."

## Key numbers
train N = **918** (not 919, not 1,234) · 58 optimizer steps · lr 5e-6 · rpo_alpha 1.0 · merge bug at train_native.py:113

## Verdict

**Ruling (a): APPROVED — upgraded to DPO+NLL (`rpo_alpha=1.0`).**
Run 1's identity is its invariants, not its algorithm; ORPO's motivation (ref-model VRAM) died
with the adapter-disable trick, and ORPO now sits in TRL's experimental namespace. The PhD's
one-line upgrade is literature-mandated: same-task low-edit-distance pairs are the documented
regime where vanilla DPO drives *chosen* likelihood DOWN (DPOP/Smaug 2402.13228); the
NLL-on-chosen term (Iterative RPO 2404.19733) is the published fix — **verified present in the
pinned TRL 0.12.2 source**. Prereg must name "one epoch of DPO+NLL."

**Ruling (b): CONFIRMED — with blocking amendments:**
1. **Cap-120 reinstated and enforced at source** (unanimous; the cap is enforced nowhere in
   train_native.py — verified). Corrected **N=918** (the removed pair was under-cap `balanced`
   44→43). Capped stratified file, sha256 in prereg.
2. **Merge bug** (confirmed in code): `--merge` merges the NF4 model and labels it fp16 (PEFT
   warns 4-bit merges change generations, peft #2321). Fix: bf16 reload → attach adapter →
   merge_and_unload → save; NULL export runs identical code with a no-op adapter.
3. **Tripwires corrected** (reviewer catch nobody else saw): with rpo_alpha=1.0 the loss starts
   ABOVE 0.693 — the "loss below 0.6931" pass check and "0.693-pin" abort fail on a *healthy*
   run. Gate on rewards/accuracies departing 0.5 AND rewards/margins > 0 by step 30.
4. **Order forced:** fix merge + cap → smoke sheet → freeze rules → null re-export → baseline
   ×3 + reproduction check (rle≈46/50, rotate≈1/100 must reproduce or STOP) → sign prereg
   (N, params, **seeds** — nobody had preregistered seeds) → train → identical export →
   ruler ×2 + endpoints.

**The recipe (PhD, audited):** beta 0.1 · rpo_alpha 1.0 · lr **5e-6** cosine 10% warmup (only
cited number) · effective batch 16 → 58 steps · max_length 1024/512, truncation = 0 · LoRA
r16/α32/d0.05 all-proj · adamw_bnb_8bit **non-paged** · bf16 · grad-ckpt · sdpa · no NEFTune ·
1 epoch (ReST-EM: coding gains concentrate in iteration 1).

**Expectations:** <2pp aggregate = noise by this project's own measurement; multiply_strings
n=100 and rotate n=100 carry the verdict. PhD measured the data: chosen averages *shorter*
(378 vs 404 chars) → verbosity drift unlikely; log completion lengths anyway.

## The one thing to do first
Fix the merge path and build the capped 918-pair training file — everything else stacks on
those two.

## Alignment map
| Member | Position |
|---|---|
| Contrarian | Bless DPO with degeneracy guards; plan rejected as written (N contradiction, vanished cap, merge symmetry) |
| First Principles | Identity = invariants; name the swap; cap restoration BLOCKING; order dependency-forced |
| Expansionist | Single-box loop = cadence change; model-agnostic harness = standing test-bench |
| Outsider | Deviation-with-reasons = good engineering; silent rule-drops = decay; rules frozen before baseline |
| Pragmatist | Stack compatible; cap stands or don't train; smoke test + aborts run sheet |
| The PhD | DPO+NLL; cited recipe; found the merge bug and the unenforced cap; calibrated expectations |
| The Asshole | 918 not 919; tripwire collision fixed; LR/length/optimizer adjudicated; seeds now preregistered |

---
Full responses: `council-transcript-2026-07-25_1837.md` · Channel record: instructions.txt §14
*(Backdated .md conversion of the original HTML report, per proprietor mandate.)*
