# LLM Council — srlm-forge Monitoring Pass #5

**Date:** 2026-07-25 17:50
**Trigger:** DIRECTIVE watcher fired autonomously on the executor's §11 edit (first
autonomous activation — task byj6hpvo9)
**Roster change (proprietor):** advisor #5 renamed **The Pragmatist** (was "The
Executor" — collided with the coder's EXECUTOR role); new member #6 added: **The
Asshole**, final-pass reviewer with web access, replaces the folded peer-critique step.
**Scope:** instructions.txt only

---

## The executor's ask (§11)

Corrections, all verified: stockpile = 1,235 sha1-unique pairs (+38 repair), per-task
{atoi 231, decode_ways 240, next_permutation 195, spiral 116, simplify_path 126,
lps 124, two_sum 64, balanced 44, multiply_strings 40, three_sum 29, merge_intervals 14,
word_break 7, roman 5}; train∩ruler = EMPTY; conciseness = 0; no collision filter as
running code (disjointness by construction); model at ZERO gradient steps, ruler
0.88 → 0.88. **Rank by fewest steps to a first real, honest signal:** (i) author 4
family tasks + mine 120 more, then train — vs (ii) lean shot: WSL2/Unsloth env → ONE
ORPO epoch on existing audited pairs → re-measure with the prereg bar.

---

## Advisor responses

### The Contrarian
Rank (ii) then (i) — but (ii) has more steps than advertised, and one ledger
contradiction blocks both. (1) The records disagree: known_hard quarantines
multiply_strings, the ledger credits it 40 pairs; repair provenance covers only 38
pairs total, so normal-lane multiply_strings solves exist; either quarantine, ledger,
or audit is wrong — re-run hidden tests on those chosens before training; if they
don't verify, "1,235 audited" is unproven everywhere. (2) 1,235 is really ~666: top-3
= 54%; sha1-unique excludes only byte-identity — renames/whitespace pass; effective
diversity plausibly a few dozen solution modes; expected honest outcome: flat.
(3) "Flat-but-intact = positive" needs a falsifier or it's a consolation prize —
prereg a positive control on held-out items from TRAINED tasks. (4) Prereg-evaluable
requires pre-training measurements (ii) omits: rle n=200 re-baseline; noise floor
re-estimated at matched n; and a NULL RE-EXPORT — push the untrained model through
the full WSL2/merge → q4_K_M path, else quant drift confounds every delta. (i) ranks
last beyond step count: authoring ruler-family neighbors with no collision filter as
code erodes the only contamination defense.

### The First Principles Thinker
Rank (ii) decisively — but relabel the prereg first. Run 1 cannot test transfer: zero
rotation/RLE-family pairs in the set, so preregistering rotate ≥10/100 as headline
preregisters a question the design can't answer. PRIMARY = ruler intact within the
noise band after one true epoch (0.88 → 0.88 at zero steps is the null; this is its
first non-trivial test). Rotate/rle movement = exploratory bonus — and if rotate
moved anyway, contamination check before celebration. §10 decomposes: "mine 120
more" was dose (moot at 1,235); "author family tasks" was mechanism (real — but
round 2's experiment; bundling confounds "does training work" with "does family data
transfer"). spiral 116 / multiply_strings 40 prove the mining half closed:
"unsolvable" was a sampling artifact. Confound: 54% of pairs from three tasks — if
the ruler drops, you can't distinguish "ORPO unstable" from "overfit three
templates." Cheap fix by selection only: cap ~50/task → balanced ~490-pair set.

### The Expansionist
Rank (ii) by a wide margin — three steps to signal; (i) inserts work into the half of
the loop that's already proven. The mining half has receipts before a single gradient
step: spiral (all-fail, zero pairs possible at round 1) → 116 pairs; multiply_strings
walked out of quarantine with 40. Headline: the flywheel's front half already converts
"impossible" into verified training signal using a model that has never learned
anything. The first completed cycle pays out whichever way the ruler moves — up =
first self-improvement signal; flat-but-intact = loop proven non-destructive and the
env/config/harness become permanent reusable capital; down = a real dose-response
baseline. The family pack appreciates by waiting: at round 2 it's a targeted
mechanism experiment against a trusted toolchain. Capture now, cheap: per-task eval
snapshots, checkpoint hashes in the ruler ledger, and the frontier ledger — spiral
and multiply_strings its first entries.

### The Outsider
A stranger's name for this project: a library with no reader. 1,273 flashcards, zero
study sessions — the one step that was ever the point has never happened; every
additional card is the most comfortable way to avoid finding out whether any of this
works. "Mine 120 more first" is a ~10% bump graded by a 10-question exam —
undetectable; perfectionism wearing rigor's clothes. Designing curriculum before
observing the student is backwards; one run converts every future card decision into
targeted repair. The lopsided pile is a round-2 problem. The two record
contradictions bother me more — both point at stale status lists, which is currently
a guess: the 10-minute fix doubles as the go/no-go gate — re-run the verifiers on the
multiply_strings and spiral cards; pass = stale labels, annotate and go; fail = the
"verified" stamp itself is broken, and that is the one condition where training now
is a mistake. Snapshot the base model first so run 1 is reversible.

### The Pragmatist
(ii) wins — a strict subset of (i): ~9 steps vs ~14, and a null result's env/baseline/
export work is fully reusable. Run sheet: (1) WSL2 + py3.11 + cu121 + Unsloth, 10-step
QLoRA smoke test; (2) pre-baselines the prereg needs — rle n=200 (the 194/176 bars are
uninterpretable against n=50) + multiply_strings n=100; (3) curation: per-task cap
120 → ~919 pairs (skew 54%→39%), stratified, seed-fixed, sha1 manifest; EXCLUDE the
38 repair pairs (different mechanism, single-variable; ~3% power loss); (4) prereg
update before training: promote multiply_strings n=100 to primary efficacy endpoint
(in-distribution, 40 trained pairs); rotate = exploratory (bars stand); rle n=200 =
regression guard → rollback; (5) ORPO one epoch, batch 2 × accum 8, lr 8e-6, no
sweeps; (6) merge → q4_K_M same quant, sha256 the GGUF; (7) ruler pass ×2; (8) log
seeds, pair sha1s, checkpoint + prereg commit hashes. Wall-clock ~8–11h.

---

## THE ASSHOLE'S REVIEW (member #6 — final pass, web-verified: 4 lookups)

**Corrections:**
1. Contrarian understates his own catch: the per-task ledger sums to exactly 1,235
   *excluding* the 38 repair pairs — so ALL 40 multiply_strings chosens are
   normal-lane, not "at least two." The known_hard contradiction is total.
2. Outsider's re-verify scope is wrong: at seconds/pair, all 1,273 re-verify in
   ~1–2h — skip the 156-pair half-measure. And nobody checked the REJECTED side: a
   rejected that passes hidden tests makes the pair preference noise. Verify both
   directions.
3. First Principles overclaims "the design can't answer transfer":
   next_permutation (195 pairs) trains suffix reversal — the literal
   rotate-by-reversal primitive — and rle's neighbors (atoi 231, simplify_path 126)
   are abundant. Demoting rotate from primary: right. "Unanswerable": wrong.
4. Cap fight: Pragmatist wins. Cap 50 → 489 pairs → ~31 optimizer steps = a smoke
   test, not an epoch. Cap 120 → 919 (verified), skew 39.2% (verified). Pedantry:
   919/16 = 57.4 → 58 steps.
5. Primary endpoint: merge all three — co-primary safety (ruler non-inferior vs the
   RE-EXPORTED baseline) + co-primary efficacy (multiply_strings n=100 lift, valid
   only after its pairs re-verify) + exploratory rotate.
6. Contrarian's null re-export: best catch, wrong spec. "Confirm 0.88" fails for
   boring reasons (Ollama's shipped q4_K_M has different quant provenance/template).
   Reframe: the re-exported untrained GGUF BECOMES the operative baseline; ruler 3×
   on it at matched n — which also replaces the worthless noise floor (a 3-run std
   has a 95% CI of ~0.5×–6.3×σ).
7. Expansionist and First Principles cite multiply_strings-40 as a mining receipt
   while it's disputed; spiral 116 stands, the other is conditional on #2.
8. Pragmatist's 8–11h omits re-verification and the null re-export + its ruler runs:
   realistic 12–16h.
9. rle rollback ≤176/200 is pinned to 46/50 (95% CI ~81–98%): derive the threshold
   from the actual n=200 re-baseline (−2σ), not a pre-baked constant.
10. Outsider's "snapshot the base": LoRA never touches the Ollama blob; sha256
    logging already covers it.

**Already-solved — adopt, don't build:** TRL ORPOTrainer/ORPOConfig (current TRL
moved it to `trl.experimental.orpo` — use Unsloth's pinned TRL or pin pre-move);
Unsloth's documented GGUF→Ollama path (known `save_pretrained_gguf` breakage;
fallback merged-16bit → `convert_hf_to_gguf.py` → `llama-quantize`); `ollama create`
with template from `ollama show --modelfile` (template mismatch = classic silent
eval-killer); pandas `groupby().sample(n, random_state)` for the stratified cap;
MinHash (datasketch/text-dedup) or AST-normalize-then-hash for real near-dup
detection (sha1 = byte-twins only); scipy `binomtest` / statsmodels
`proportion_confint` for thresholds; **pin torch 2.5.1 — the last cu121 wheel**
(2.6 ships cu118/cu124/cu126 only; a blind upgrade bricks this driver-591.86 box).

**Verdict:** Agree — (ii), decisively. The single highest-leverage change: collapse
the council's scattered preflight into ONE gate before the frozen prereg — full
1,273-pair bidirectional re-verification plus the null re-export whose 3× ruler runs
double as the real baseline and real noise floor. That turns run 1 from "hope the
stamps are real" into an instrumented experiment, and every later round inherits the
instrument for free.

**Sources:** TRL ORPO trainer docs (huggingface.co/docs/trl/en/orpo_trainer); TRL
orpo_trainer.md experimental namespace (github.com/huggingface/trl); Unsloth "Saving
to Ollama" docs (unsloth.ai/docs); Unsloth issues #2581, #1781 (GGUF/quantize
failures); PyTorch previous-versions matrix (pytorch.org).

---

## CHAIRMAN VERDICT

As written to instructions.txt §12: unanimous (ii) lean shot behind ONE preflight
gate (bidirectional re-verification of all 1,273 pairs + null re-export as operative
baseline with its own 3× noise floor); curation cap 120 → 919 pairs, repair pairs
excluded; prereg relabeled to co-primary safety + co-primary efficacy
(multiply_strings) + exploratory rotate, thresholds derived from the gate's own
measurements; family pack + collision filter + MinHash dedup deferred to round 2;
adopt-don't-build list delivered to the executor; honest wall-clock 12–16h. Roster
note: The Pragmatist rename + The Asshole's addition are recorded in the §12 ROLE
NOTE. COUNCIL ACK appended after the executor's 16:05 model-agnostic config addendum:
verdict unchanged; flag raised on train_dpo's new combine-repair-pairs default vs the
run-1 single-variable exclusion.
