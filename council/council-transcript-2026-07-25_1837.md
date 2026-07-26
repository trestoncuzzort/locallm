# LLM Council — srlm-forge Monitoring Pass #6

**Date:** 2026-07-25 18:37
**Trigger:** DIRECTIVE watcher (autonomous) — executor posted §13: gate cleared + env unblocked
**Roster:** first convening of **The PhD** (member #7). Six advisors + The Asshole reviewing.
**Scope:** instructions.txt; proprietor-granted read-only repo access exercised by The PhD and The Asshole.

---

## The executor's ask (§13)

Gate §12.1a done: 1,273 pairs re-verified bidirectionally; exactly 1 rejected-passes pair
found (dpo_pairs[0], the legacy conciseness pair — both sides correct by construction);
removed → 1,272 clean, re-run PASS. known_hard reconciled (multiply_strings: 41 verified
solves; quarantine now empty). Env unblocked **Windows-native** (no WSL — no distro;
headless install risky): per-user Python 3.11.9, torch 2.5.1+cu121 sees the RTX 4080;
stack transformers 4.46.3 / trl 0.12.2 / peft 0.14.0 / accelerate 1.2.1 / datasets 3.2.0 /
bitsandbytes 0.45.0. Deviations flagged for ruling: no Unsloth (avoids triton/xformers);
**DPO not ORPO** (stable TRL API; QLoRA adapter-disable ref = no second model in VRAM).
train_native.py written (model-agnostic; repair 38 excluded by default; --merge for GGUF).

**Asks:** (a) is native-HF-DPO acceptable for run 1, or does the council insist on
ORPO/Unsloth? (b) confirm: null-re-export the untrained model through the SAME
merge→GGUF→Ollama path as the trained one (operative baseline), then prereg + one epoch
on "the 1,272 frontier pairs (repair 38 excluded)."

---

## Advisor responses

### The Contrarian
Reject the plan **as written** — two defects before a single gradient step. The arithmetic
is broken on its face: "one epoch on the 1,272 frontier pairs (repair 38 excluded)" is
self-contradictory — 1,272 *includes* repair; excluding gives 1,234; a prereg recording
the wrong N is violated at signing. Worse: §12's adjudicated cap-120 curation (919 pairs)
has silently vanished — training on 1,234 restores the exact skew confound already ruled
on; the executor doesn't relitigate by omission. And 919 was derived pre-gate — re-derive.

Accept native-HF-DPO — but the risk isn't speed, it's **silent degeneracy**: if the
adapter-disable ref no-ops (wrapper mismatch, modules_to_save), the ref tracks the policy,
loss pins at 0.6931, and the epoch trains nothing while looking green. Require logged
chosen/rejected reward margins and an assert that loss departs 0.693 within N steps.
Sharper trap — **merge symmetry**: if the trained export merges the adapter onto a
dequantized-4bit base while the null export loads fp16 weights, every weight differs by
quantization noise and the safety co-primary is confounded. "Same path" must mean
identical load→merge→GGUF code, null run with a no-op adapter. (bnb 0.45 Windows wheels
are real; avoid paged optimizers — least-tested path there.)

The gate found exactly the one pair already predicted because it reuses the verifier that
built the pairs — that proves internal consistency, not audit power; verifier blind spots
are structurally invisible to it. Before training, on the re-export: 3× full ruler runs
(no −2σ bars exist otherwise), multiply_strings n=100 pre, rotate n=100 pre, and confirm
rle≈46/50 / rotate≈1/100 reproduce — if not, the export pipeline itself moves scores and
everything downstream is uninterpretable.

### The First Principles Thinker
Run 1's identity is its **invariants**, not its algorithm: verifier-grounded pairs, single
variable, prereg-before-training, like-for-like export, frozen ruler. ORPO was never
load-bearing — chosen to avoid ref-model VRAM, a motivation the adapter-disable trick
dissolves; insisting on it now means preferring an experimental TRL namespace for a dead
reason, and insisting on Unsloth courts the exact Windows fragility the council itself
flagged. **Bless native-HF-DPO** — but honesty requires the prereg to name the swap and
scope every conclusion to "one epoch of DPO preference training on these pairs."

The cap is different in kind: DPO was a forced deviation; dropping the 919-pair curation
is an **unforced, silent reversal of an adjudicated ruling**. The cap exists for
attribution — if the ruler drops after training on 1,234 pairs where three tasks hold
54%, "preference training unstable" and "overfit three templates" are indistinguishable,
and the safety co-primary becomes uninterpretable precisely when it fires. The full set
is a legitimate run-2 variable with run 1 as its control. **Restore the cap. Blocking.**

Ordering is dependency-forced: smoke test → null re-export → baseline ruler ×3 → prereg
commit → train one epoch → identical-path export → ruler ×2.

### The Expansionist
Bless both. The **single-box loop is the real prize** — generation, training, export,
eval on one Windows machine, no WSL/admin/reboot, is a cadence change: overnight-per-
round, unattended, once run 1 lands. config.py made the harness **model-agnostic before
the first run even fired** — any 8B-class model with an HF base slots into the same
frozen ruler, gate, and prereg discipline; cross-model comparability is a rarer asset
than any single result. The gate predicted-and-caught its first real defect and the
quarantine self-corrected against fresh evidence — trust infrastructure just graduated
from designed to **field-validated**; write the bidirectional re-verification +
reconciliation down as a standalone reusable protocol. Compounding path if run 1 is
clean: family pack on identical rails, ORPO/GRPO head-to-head where the only variable is
the objective, dose-response across epochs. Every follow-up is cheap because the
expensive things — verification, prereg, baseline — are amortized. Lock it and fire.

### The Outsider
The deviation is fine; **the silence isn't**. An engineer who reroutes around the fragile
dependency you yourself flagged, says so out loud, and gives reasons — that's a proposal,
not insubordination; accept it. Tooling is means; the council's authority lives in ends —
data, exam, scoring rules, packaging — all untouched. Slower-but-boring is exactly what a
first-ever run wants. But the balancing rule is the same behavior **minus the honesty**:
a ruling that evaporates unargued teaches you decisions here decay by default. Block until
re-decided on the record. Related: 1,272 audited-clean, but the plan trains on 1,234 —
where did 38 cards go? Possibly innocent; unexplained numbers before run #1 are not.

The audit is mildly circular — a check built to spec finds what the spec anticipated;
"clean" means "passed the checks we wrote." The telling find is the stale impossible-list
(solved 41 times, still listed): metadata drifts silently here. On (b): baselining the
untrained model through the identical pipeline is the best idea on the page — with one
fix: **commit the scoring rules BEFORE scoring the baseline**; rules written with
baseline output in view bend, even innocently, toward flattering the delta.

### The Pragmatist
Bless (a): the stack (torch 2.5.1+cu121 / trl 0.12.2 / transformers 4.46.3 / peft 0.14.0 /
bnb 0.45.0) is coherent and mutually compatible; bnb has native Windows cu121 wheels
since 0.43.x; DPOTrainer with ref_model=None is the standard QLoRA path. **Cap stands** —
a §12 adjudication doesn't lapse by silent omission: train 919 stratified fixed-seed with
a sha1 manifest, or don't train. Run sheet: bitsandbytes smoke (`python -m bitsandbytes`
SUCCESS), nf4 load + forward, 10-step dry run on 16 pairs (VRAM <14.5GB — the card also
drives the display); cap → 919, truncation assert; batch 1×16 → 58 steps; max_length
1024/512; bf16; grad-ckpt (use_reentrant=False); paged_adamw_8bit; sdpa; beta 0.1, lr
1e-5 cosine, warmup 6 steps, 1 epoch, no sweeps. Export: reload base fp16 → PeftModel →
merge_and_unload → save fp16 (never merge into the 4-bit base); coder must fetch
llama.cpp (convert_hf_to_gguf.py, pip install gguf) + a prebuilt Windows llama-quantize;
f16 GGUF → q4_K_M → ollama create with copied template. Aborts: OOM → max_length 768
once, second OOM aborts; NaN aborts; loss pinned at 0.693 / reward-acc ~0.5 after 30
steps aborts. ~6–9h total.

### The PhD (first convening — 21 tool uses; primary sources fetched; repo data measured)
**(a) Keep DPO — but run it as DPO+NLL.** Set `rpo_alpha=1.0` (verified present in the
pinned TRL 0.12.2 source; docstring cites the paper's recommendation of 1.0). Same-task,
low-edit-distance pairs are the documented regime where vanilla DPO drives *chosen*
likelihood down while the margin grows (Pal et al. 2024, DPOP/Smaug, arXiv:2402.13228);
the added NLL-on-chosen term (Pang et al. 2024, Iterative RPO, arXiv:2404.19733) is the
published fix. The adapter-disable ref voids reference-free methods' systems argument —
two no-grad forwards, zero extra VRAM, and the KL anchor the safety co-primary depends on
stays. SimPO's +6.4 AlpacaEval-2 over DPO (arXiv:2405.14734) is ~60k-chat-pair evidence,
not ~1k-pair, and deletes that anchor — keep as round-2 ablation via stable
`CPOTrainer(loss_type="simpo")`. KTO targets unpaired signals this project doesn't have.
ORPO correctly avoided (experimental namespace). Length bias: **measured this repo's
pairs** — chosen is *shorter* on average (378 vs 404 chars; longer in only 29.5%), so
verbosity amplification is unlikely; still log mean ruler completion length pre/post.

**(b) Recipe:** beta 0.1 (DPO paper default); **rpo_alpha 1.0 (add)**; **lr 5e-6 cosine,
warmup 0.1** (alignment-handbook zephyr-7b-beta QLoRA-DPO config — the current 8e-6
default is uncited); effective batch 16 (~57 steps on 919); 1 epoch (ReST-EM: coding
gains concentrate in iteration 1, arXiv:2312.06585); max_length 768/384 (measured p95
prompt+completion 848 chars, max 1,272); LoRA r=16, alpha=32, dropout 0.05, all 7 proj
targets (QLoRA arXiv:2305.14314 + handbook); paged_adamw_8bit (Dettmers 8-bit Adam
lossless, arXiv:2110.02861); no NEFTune (SFT-only evidence, ~nil on code).

**(c) Corrections to the standing plan:** (1) add rpo_alpha=1.0 — one line, targets the
documented failure mode. (2) **Fix the merge path**: train_native.py --merge calls
merge_and_unload() on the NF4 model and labels the output "fp16" — PEFT warns 4-bit
merges change generations via rounding (peft issue #2321); merge into a bf16 reload
instead. The null-re-export design stays correct — q4_K_M re-quant error hits both arms,
exactly what it controls for; additionally score the intermediate f16 GGUF once (~200s
per ruler pass, per night1_measurement.json) to attribute regression to re-quant vs
training. (3) **Calibrate expectations**: aggregate movement under ~2pp is noise by this
project's own measurement; RLEF-scale gains (arXiv:2410.02089) came from multi-turn
execution-feedback RL, not 918 offline pairs — the preregistered task endpoints are where
a real effect can clear the floor. **Compliance flag:** train_native.py loads ALL of
data/dpo_pairs.jsonl (1,234 lines, no per-task field) — the 120/task cap is not enforced
anywhere in the training path; apply it upstream.

Sources: TRL 0.12.2 dpo_config.py / cpo_config.py (fetched raw), TRL experimental docs,
SimPO (2405.14734), Iterative RPO (2404.19733), DPOP/Smaug (2402.13228),
alignment-handbook zephyr QLoRA-DPO config, ReST-EM (2312.06585), RLEF (2410.02089),
peft issue #2321 + PEFT quantization guide, QLoRA (2305.14314), 8-bit Adam (2110.02861).

---

## THE ASSHOLE'S REVIEW (4 tool uses; rpo_alpha verified in pinned TRL source)

**Corrections:** (1) "919" is stale everywhere — balanced sits under the cap (44→43 after
the gate removal), so the capped total is **918**; prereg N=918. (2) The Outsider's
"missing 38" is already on the record — the repair exclusion (1,272−38=1,234, matches the
file, verified); that block condition is moot, and the cap needs *enforcement*, not
"re-deciding." (3) The coder's "1,272 frontier pairs (repair 38 excluded)" is
self-contradictory — prereg language: "918 pairs (post-gate, repair-excluded, 120/task
cap)." (4) **Unreconciled collision nobody caught:** with rpo_alpha=1.0 the logged loss =
DPO+NLL and starts well above 0.693 — the Pragmatist's "loss below 0.6931" dry-run pass
criterion *fails on a healthy run* and the 0.693-pin abort is meaningless; gate instead
on rewards/accuracies departing 0.5 AND rewards/margins > 0 by step 30; log NLL
separately. (5) Steps = ceil(918/16) = **58**. (6) **Merge bug confirmed in code** at
train_native.py:113 — fix to bf16-reload-then-merge before the *null* export too, or
symmetry dies.

**Adjudications:** LR **5e-6** (the only cited number; conservative suits the added NLL
term). max_length **1024/512** (PhD measured chars then prescribed tokens; at batch-1
padding a higher ceiling costs nothing — and tighten the truncation assert to ZERO).
Optimizer: **adamw_bnb_8bit non-paged** (headroom assert means paging never fires; zero
upside, nonzero least-tested-Windows risk — Contrarian wins on dominance). rpo_alpha=1.0
**adopted** (verified in pinned source; DPOP correctly characterized). Prereg order:
freeze rules **before** baseline scoring; append measured baseline as a pre-training
amendment; sign; train (satisfies both FP and Outsider).

**Missed by all six:** the tripwire collision (#4); the prereg must NAME "DPO+NLL
(rpo_alpha=1.0)" — First Principles' own naming rule, unapplied to the PhD's swap; the
cap must be applied upstream into a 918-line file whose sha256 goes in the prereg;
**nobody preregistered seeds** (train + ruler).

**Verdict:** Bless (a) as native-HF **DPO+NLL**; approve (b) as amended: fix merge +
cap-at-source (918, SHA'd) → smoke sheet with corrected tripwires → freeze rules → null
re-export (no-op adapter, identical path) → baseline ruler ×3 + reproduction checks →
sign prereg (N=918, lr 5e-6, 1024/512, adamw_bnb_8bit, 58 steps, seeds) → train 1 epoch
→ identical-path export → score. Expect <2pp aggregate = noise; task endpoints carry the
verdict.

---

## CHAIRMAN VERDICT

As written to instructions.txt §14: ruling (a) approved as **DPO+NLL (rpo_alpha=1.0)**
with the swap named in the prereg; ruling (b) confirmed with blocking amendments —
cap-120 reinstated and enforced at source (N=918, sha256 in prereg), merge path fixed
(bf16 reload; null export identical code + no-op adapter), tripwires corrected for the
NLL term, dependency-forced order (smoke → freeze rules → null re-export → baseline ×3 +
reproduction check → sign prereg with seeds → train → identical export → ruler ×2 +
endpoints). PhD's audited recipe adopted (beta 0.1, lr 5e-6 cosine 10% warmup, batch
1×16 = 58 steps, max_length 1024/512 truncation-zero, LoRA r16/α32/d0.05 all-proj,
adamw_bnb_8bit, bf16, no NEFTune, 1 epoch). Expectations calibrated: <2pp aggregate =
noise; multiply_strings n=100 and rotate n=100 carry the verdict. ONE prompt delivered
in §14.
