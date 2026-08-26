PROJECT CONTEXT — srlm-forge, state of evidence as of 2026-08-22 (supersedes the manuscript where they differ)

The project is a local single-GPU (RTX 5080, 16GB, shared lab PC that wipes on logoff, no admin) execution-verified preference pipeline for Python code:
sample K candidates from llama3-8b-instruct via Ollama, execute each against hidden unit tests, chosen=passing, rejected=failing,
train a LoRA-DPO adapter (r=16, alpha=32, 7 target modules, 918 pairs from 13 tasks, lr 5e-6, 1 epoch, 57 steps, adamw_bnb_8bit, trl 0.12.2 / peft 0.20 / transformers 4.46.3),
serve the adapter via the Ollama ADAPTER directive on the unmodified Q4 GGUF base, evaluate on a frozen 31-task AceCode-derived benchmark screened to [0.2,0.8] base pass rate,
40 replicates per arm (155 generations each), preregistered Welch t-test, same-session interleaved arms, verifier fingerprint on every row.
Costs on this machine: ~25 min per 1-epoch training run (24.3 s/step), 69 min for 3 epochs, ~4 min export, 2.15 min per null replicate, 2.76 min per adapter replicate, ~3.3 h for a 40x2 interleaved comparison, ~75 min for 15x2.

FINDINGS (F-numbers as used throughout; corrections marked NEW):
 F1. The original adapter: +0.55pp vs null (p=.51), TOST rejects |effect|>=2pp; replicated on other hardware (-0.03pp) and in a same-session control (-0.04pp).
 F2. Three RETRAINS from identical code/data/config on an RTX 4090: +10.1, +11.4, +8.8pp raw vs same-session nulls, statistically indistinguishable from each other.
     NEW (verified 2026-08-22 on the raw rows): 51-58% of each retrain's gain is the model learning to emit `from typing import List` — the pinned Python 3.11 verifier
     raises NameError on un-imported typing annotations, and the AceCode prompts carry annotated signatures. Typing NameErrors fall from ~11 per 155 generations (all nulls AND
     the original adapter) to ~2 in the retrains. Using the harness's own upper-bound counterfactual (aggregate_if_typing_imported), the retrains are +4.3 / +5.6 / +3.7pp.
     The residual gain is concentrated on two tasks (ace_oss_17851 +42pp, ace_oss_24748 +38pp, both with ~0 typing failures) with a consistent LOSS on ace_oss_3243 (-23pp).
 F3. The training script sets no seed. NEW (byte-level, from installed libraries): trl 0.12.2 DPOTrainer.__init__ calls get_peft_model at dpo_trainer.py:376 and
     super().__init__ (which runs set_seed(42) at transformers trainer.py:424) at line 640 — so lora_A is drawn from the unseeded default torch RNG BEFORE the seed is set,
     while data order (SeedableRandomSampler) and dropout are seeded. lora_A is the single unseeded draw in the training graph. The same ordering exists in TRL main for
     DPO/SFT/GRPO trainers, so any TRL-based LoRA post-training run that passes peft_config and does not seed manually has unseeded adapter init.
     NEW: even in the 40x-lr, 3-epoch adapter, 96% of lora_A entries remain inside the kaiming-uniform init box (std ratio 1.02, kurtosis 2.05 vs 1.80 uniform); at the
     original recipe the sum-of-lr bound caps A movement at ~2%. So dW = B·A0 lies in the random 16-dim row-space of A0, and the expected cosine between two independent
     random 16x4096 projections is 1/sqrt(r*fan_in) ≈ 0.0039 — the replication measured 0.0042 ± 0.0044. Weight-space orthogonality is therefore a near-tautology of
     lazy-A LoRA; the NON-trivial finding is functional identity (below).
 F4. The manuscript's leading hypothesis for the original null is a silent Windows TDR kernel abort during training. NEW caveat: vendor documentation says a TDR leaves the
     CUDA context reporting errors, so "silent, no exception" needs a mechanism (per-engine reset with packet resubmission is a documented but unstudied candidate).
     The one supporting datum is a +10.3pp run on the original stack after raising TdrDelay, reported in prose only. The original adapter's weights are NOT on this machine.
 F5. The original (null) adapter is not a no-op: per-task rates redistributed (15 up / 14 down), whole-profile permutation p<5e-5. NEW: its per-task delta profile has
     split-half reliability only 0.21 (replication session) / 0.52 (control session) and correlates 0.47 with itself across sessions; it correlates -0.10 / +0.07 with the
     retrains' profile, i.e. it is NOT a scaled-down version of the successful solution but an unrelated (weakly reliable) direction in behavior space.
 F5b. NEW — the central new result: the three weight-orthogonal retrains have IDENTICAL per-task behavioral profiles. Delta-profile Pearson r: rep1-rep2 0.970, rep1-rep3 0.863,
     rep2-rep3 0.834, against split-half reliabilities 0.92 / 0.90 / 0.69 → disattenuated r = 1.06 / 1.08 / 1.06 (at the instrument's reliability ceiling). The same holds on the
     typing-forgiven metric (r 0.953 / 0.806 / 0.774; disattenuated 1.12 / 1.13 / 1.11): the same two tasks gain +40pp, the same task loses -23pp, in all three runs.
     Three random 16-dim subspaces per layer, one function. Permutation p<1e-4 for each pair.
 F5c. NEW — the positive control (lr 2e-4, 3 epochs; 9 of 40 replicates banked — an interim look, prereg N=40 unchanged) has the SAME raw mean gain (+11.4pp) but a DIFFERENT
     per-task solution: profile r = 0.43 / 0.42 / 0.56 with the retrains (disattenuated ~0.46-0.70), per-task delta SD 33pp vs 15-17pp, with swings of +73, +64, +62, -60, -38,
     -31pp on individual tasks, and its typing-forgiven gain collapses to +2.0pp (typing fails 0.1/row). Its profile is highly reliable (split-half 0.93). Its update norm is
     ~26x the low-lr adapters' (mean ||dW||_F 0.53 vs 0.02 per layer). The high-lr regime leaves the seed-invariant solution and lands in a different basin with over-optimization.
 F6. Six measurement-integrity failures where a component kept emitting well-formed numbers after it stopped measuring: forgeable verdict sentinel (candidate prints "__PASS__"),
     verdict readable from shared namespace (candidate reads _NONCE; closed by an AST-level harness_smells check), interpreter-version-dependent ground truth (18/310 completions
     flip between Python 3.11 and 3.14), saturated benchmark, dataset gate that stopped parsing, analysis script pooling a reference arm across two instruments.
     NEW candidate 7th: training_args.bin records seed=42 (did not govern init), gradient_checkpointing=False (it is active), warmup_steps=0 beside warmup_ratio=0.1, and
     optim=adamw_bnb_8bit whose block-quantized update is not Adam in one block (see F10).
 F7. Pair-primary DPO: 66% of task attempts yield no training row; 16.9% of generations reach one. The repo now records an immutable per-candidate TRACE from which SFT/KTO/DPO
     views are derived — but no trace has been populated yet (data/trace.jsonl does not exist).
 F8. The verifier "seam": the only domain-specific component is the correctness check; a second domain (SQL via SQLite authorizer) was built to demonstrate it.
 F9. Training corpus: 13 tasks (effective 9.93) but 767 distinct (chosen, rejected) contrast structures over 918 pairs.
 F10. NEW — optimizer anomaly in the one adapter on this machine (poscontrol, adamw_bnb_8bit): 170 elements of layers.1.mlp.down_proj.lora_A exceed the Adam worst-case
     displacement bound (3.16·Σlr) by up to 3x, ALL inside the 256-aligned column window [2304,2559], which contains column 2427 — reported in the super-weight literature as
     Llama-3-8B's most important weight coordinate (layers.1.mlp.down_proj[788,2427]; citation must be verified). Hypothesis: bitsandbytes' blockwise (blocksize 256) 8-bit
     optimizer-state quantization lets one massive-activation column set the block absmax so its 255 neighbours' second moments underflow and their steps blow past lr.
     Not yet ablated (adamw_torch vs adamw_bnb_8bit at a fixed seed would settle it in ~25 min).

ASSETS ON THIS MACHINE: data/ruler_noise.jsonl (334 replicate rows, every row with per-task, per-draw binary outcomes and a typing-NameError flag, for all arms listed above);
dpo_adapter_poscontrol (the only adapter weights here; plus its GGUF and a 50,000x-amplified liveness-control GGUF served in Ollama); the three retrain training logs;
the 918-pair corpus with chosen/rejected code and rejected_error tracebacks; failures.jsonl with 1,576 raw failing candidates; screen_results.jsonl with the 78 screened
AceCode task payloads (5-21 asserts each); a working train/export/eval stack. NOT here: the original adapter, the three retrain adapters, AceCode-89K parquet, KodCode.
train_native.py exposes --lr --epochs --max-steps --out but NOT --seed/--rank/--optim (easy to add). export_adapter.py's amplified-adapter liveness control works by
scaling lora_B by 50,000 and demanding a visible output change.

WHAT THE AUTHOR WANTS: to step back from incremental measurement of one adapter and find a theoretically interesting, untouched research gap that these findings
and this (small) resource budget position them to attack — something a careful reviewer would say they did not know.
