# srlm-forge Council — Full Transcript, Activation #8

2026-07-26 ~08:10. Manually convened by the proprietor — the executor's `§19 EXECUTOR LOG` explicitly handed back one open decision ("that is the next decision, not a thing I will quietly pick") without rewriting the DIRECTIVE block, so the automated watcher did not fire on its own.

---

## 1. The decision, as framed

Track A's `train_native.py` merge step (line ~138) calls `merge_and_unload()` directly on the 4-bit (NF4) model and mislabels the output "merged fp16" for GGUF export — the export cannot work as written (the artifact is still 4-bit bitsandbytes params, not fp16). Two fixes on the table:

- **(A)** §14's original mandate: reload the base model fresh in bf16, attach the trained adapter, merge, save.
- **(B)** §18's alternative, surfaced from prior art but never validated on this project: skip merging entirely — convert the LoRA adapter to a GGUF adapter via llama.cpp's `convert_lora_to_gguf.py`, apply it at inference time via Ollama's `ADAPTER` Modelfile directive against the untouched base GGUF.

**New fact reframing the round** (orchestrator, pre-round verification): Option (A) may not physically fit — Llama-3-8B is 8,030,261,248 params; in bf16 that's ~16 GB of weights alone on a 16 GB RTX 4080, before adapter/activations/overhead. Nobody had checked this before §14 mandated Option (A).

---

## 2. The five style advisors — raw responses (banked, new PhD-facing format)

### Contrarian

> **THESIS:** Both paths fail unvalidated assumptions; Option B's failure is silent and lethal, while Option A's is visible and survivable — but the real move is testing B cheaply before choosing either.
>
> - Option A's VRAM math is broken as specified (16.06 GB into 16 GB card, negative headroom); "proven in papers" means A100s, not this card.
> - Option A failure is visible (OOM, then pivot to CPU offload). Option B failure is invisible — if `convert_lora_to_gguf.py` silently produces wrong tensors, the model *runs* but inference is corrupted, shipping a quietly-wrong null-baseline.
> - `[VERIFY]` bitsandbytes adapters carry quantization state that regular LoRA doesn't.
>
> **Direct answer:** Test Option B for $0 first — take the trained LoRA sitting idle now, run `convert_lora_to_gguf.py`, load as Ollama ADAPTER, run one inference. Pass/fail. If it works, ship B. If it fails, execute A with CPU offloading as a known cost.

*(The PhD found: no trained adapter exists — this test as proposed cannot run. Also found the quantization-state claim false by direct inspection.)*

### First Principles

> **THESIS:** The VRAM discovery reframes this as choosing between two unvalidated paths on this hardware; Option A's defect is worse because it's a silent constraint violation requiring workarounds, while Option B is a testable hypothesis.
>
> - The merge is not the goal — inference parity is the goal; Option B exists precisely because llama.cpp knows how to apply LoRA without merging.
> - Option A was mandated on an untested assumption (fits in 16GB) that turns out false. CPU offloading turns Option A into "a much slower, more complex baseline that no longer proves what it was meant to prove."
> - We're comparing two unproven paths on this card, not proven vs. unproven.
>
> **Direct answer:** Spend 30 minutes validating Option B first (run inference, compare outputs to the in-memory trained model). Merge bug stays parked until then.

*(The PhD found: "compare to the in-memory trained model" also assumes a trained model exists — same false premise.)*

### Expansionist

> **THESIS:** Option B isn't a workaround for a VRAM problem — it's the architecturally superior path that solves this AND unlocks cheaper iteration on every future model this project trains.
>
> - Option A's "proven in literature" only holds with CPU offload on this card — a permanent tax on every future merge.
> - Option B's risk is testable in hours (pass/fail on inference correctness).
> - Immutable GGUF base + swappable adapter is architecturally cleaner (audit, version, rollback). If it validates, this becomes the project's standing export pattern, including for models too large to ever bf16-reload.
>
> **Direct answer:** validate B — if it works you've discovered the project's whole future training-export pattern, not just fixed one bug.

### Outsider

> **THESIS:** the executor's refusal to deploy unvalidated adapter merging is sound instinct, but it's obscuring that NEITHER option has been tested on this hardware — deferring empirical work that belongs to the executor, not the council.
>
> - Option A is "never tested on this card's VRAM constraints" just as much as Option B is "never tested on this project's adapter." Symmetric unknowns.
> - The current baseline is already broken, so Option B "can't be worse than that."
> - `[VERIFY]` worse-failure-mode claim: B's opaque inference corruption vs. A's immediate OOM/hang — this is the one dissent from the round's majority.
>
> **Direct answer:** discover whether Option A works on this hardware first (20 min test); ship A with documented CPU-offload fallback if needed, because B's silent-failure risk outweighs the cost of testing A.

*(The PhD's verdict: this dissent loses — both halves of the asymmetry it rests on inverted under direct measurement. See §4 below.)*

### Pragmatist

> **THESIS:** Option A's VRAM infeasibility can be verified in under 2 minutes; that test is cheaper than gambling on unvalidated B.
>
> - Negative headroom already at weights-alone.
> - Option A's failure mode (needs CPU offload) is a documented, local Monday-morning fix; Option B's failure makes the entire export pipeline untrusted "at baseline, forever."
> - Proposed test: `device_map="auto"` dry-run load with `torch.cuda.mem_get_info()` before/after.
>
> **Direct answer:** run the 2-minute VRAM probe first; that result determines whether you need Option A + offload engineering, or can rule A out immediately.

*(The PhD found this probe unsound on this machine — see §4, sysmem fallback makes it report a false "fits.")*

---

## 3. The PhD — closing pass (full)

*(Reproduced in full; every claim below is either independently re-derived or a live, executed probe on this machine this session. Repo left untouched — `git status` clean throughout; all artifacts written to scratch; reserved `dpo_adapter_native` path never touched.)*

### Corrections to the round

**C1 — No trained adapter exists.** Verified three ways (no `dpo_adapter_native*` directory, no PEFT artifacts anywhere in the repo tree, only base-model cache entries exist). The Contrarian's "take the trained LoRA sitting idle now" is false, and it contaminates First Principles' and the Expansionist's proposals too — three of five seats built their test proposal on a nonexistent artifact.

**C2 — The Contrarian's stated mechanism for Option B's danger is false, disproved directly.** Claim: "bitsandbytes adapters carry quantization state that regular LoRA doesn't." Trained a real QLoRA adapter against the NF4 base and inspected it: 448 tensors, every one `torch.float32`, zero quantization-state tensors (no `absmax`, `quant_map`, `quant_state`, `nested`), no quantization keys in `adapter_config.json`. NF4 state lives in the frozen base, never written into the adapter. This was load-bearing under the Contrarian's "silent and lethal" thesis and does not hold.

**C3 — Units error in the round's reframing fact.** "16.06 GB into a 16 GB card = -0.06 GB" mixes decimal GB against a GiB-labelled card. Corrected: bf16 weights are 14.96 GiB, card is 15.99 GiB → +1.03 GiB nominal headroom, not negative. The conclusion (won't fit) survives via a different route (see independently-measured free VRAM below), but the number as first stated is wrong and shouldn't be quoted that way.

**C4 — The most consequential correction: Option A's failure mode on this machine is silent, not visible.** Every seat that preferred testing A first did so believing "A fails loudly (OOM), B fails silently." Tested directly: NVIDIA's CUDA system-memory fallback is ON on driver 591.86 — allocated 22 GiB on a 15.99 GiB card before it raised anything. Over-budget models here do not OOM; they spill to host RAM over PCIe and keep running, slowly and silently. The asymmetry the round assumed is not real.

**C5 — Option A as mandated is unbuildable today, not just tight.** `config.py` sets the training base to a pre-quantized NF4 checkpoint — the only Llama-3 weights on this machine. §14 said "reload the base fresh in bf16." You cannot: reloading that repo in bf16 yields dequantized-NF4 weights, not true bf16. Genuine bf16 requires `meta-llama/Meta-Llama-3-8B-Instruct`, which is gated (license acceptance required) and not downloaded (~16 GB). Nobody costed this.

**C6 — The Pragmatist's proposed probe is unsound on this machine**, per C4: a `device_map="auto"` + `mem_get_info()` dry-run will report a successful fit while silently offloading/spilling. It cannot answer the question it was proposed to answer.

**C7 — Minor:** the merge bug is now at `train_native.py:138`, not `:113`. Also, `--merge` is opt-in and defaults off, so the bug is currently latent, not actively blocking anything today.

### Independently verified VRAM arithmetic

Derived from the on-disk `config.json` (not a memorized spec): 8,030,261,248 total params (exactly matches the public spec) → bf16 = 14.96 GiB, NF4+double-quant = 4.11 GiB. Measured free VRAM with the desktop running: 14.69 GiB.

**Verdict: 14.96 GiB weights vs. 14.69 GiB free = -0.27 GiB — before optimizer, adapter, activations, or merge dequant buffers.** Option A does not fit. Per C4, it will not *say* so — it will silently degrade instead.

### Research: `convert_lora_to_gguf.py` vs. QLoRA/bnb-4bit

- The converter needs only the base *config*, never base weights (verified from source).
- Contains no bitsandbytes handling because the adapter itself needs none — reads `adapter_model.safetensors` directly, normalizes dtypes.
- PEFT LoRA → GGUF → quantized base is a supported, documented path (HF's GGUF-my-LoRA examples apply converted adapters against Q4_K_M bases — verified via fetched blog post).
- The "LoRA + GPU only for f16 models" error found in some search results is from the pre-refactor `convert-lora-to-ggml.py` (old script) and does not apply to the current `convert_lora_to_gguf.py` — confirmed by running the current path successfully.
- Option A's lossiness is independently documented: merging LoRA into 4-bit gives different generations via rounding error, because the adapter only ever saw dequantized 16-bit weights during training (PEFT #2105, Kaitchup's "Don't Merge Your LoRA Adapter Into a 4-bit LLM" — stronger sources than §14's original PEFT #2321, an unanswered user report).

### Live probes — executed

- **P1/P2 — VRAM allocation + sysmem-fallback test:** allocated real Llama-3-8B tensor shapes in bf16 (reported a suspicious "fit" at exactly 0.00 GiB free — investigated further); then allocated 22 GiB against a 15.99 GiB card — succeeded, confirming fallback is ON (PyTorch's own later error referenced "22.00 GiB is allocated by PyTorch," proving the over-allocation had gone through).
- **P3 — Throwaway smoke adapter:** `--limit 32 --max-steps 2`, output to an explicitly-scratch path, 22.6s, train_loss 1.024. Confirmed real gradient flow (224/224 `lora_B` tensors nonzero after training, ruling out a zero-init no-op). Incidental finding: a `requires_grad=True` warning during training is benign (gradient-checkpointing on frozen embeddings), worth knowing before it alarms someone at run 1.
- **P4 — Adapter inspection:** 448 tensors, all fp32, no quantization state (disproves C2).
- **P5 — Conversion attempt 1 (against the real NF4 base dir): FAILED LOUDLY.** `NotImplementedError: Quant method is not yet supported: 'bitsandbytes'` — the converter choked on the base model's `quantization_config`, not the adapter. A clean, named, immediate exception — not silent corruption, contrary to the round's fear.
- **P6 — Conversion attempt 2 (config-only base dir, quantization_config stripped): SUCCEEDED.** 448 tensors, all preserved.
- **P7 — Ollama end-to-end:** ADAPTER Modelfile against `llama3:8b-instruct-q4_K_M` → `ollama create` succeeded → inference produced coherent, correct Python.
- **P8 — Positive control (the important one):** scaled `lora_B` by 200x first — output unchanged, but measured why (effective ΔW too small at that scale to matter) rather than concluding "ignored." Rescaled to 50,000x — output collapsed into pure garbage. **The adapter is genuinely applied.** Reusable "is the adapter live" detector for future rounds.

### Resolving the Outsider's dissent

**The Outsider loses, on evidence nobody had when the round argued it.** The dissent rested on: A fails visibly (OOM), B fails silently (corrupt inference) → test A first. Both halves inverted under measurement: B failed with a named exception in ~10 seconds on its first real attempt (P5), and silent misapplication is now detectable by the P8 control; A does not fail visibly on this hardware — sysmem fallback (C4) means it silently spills into host RAM instead of erroring. Credit where due: the Outsider was the only seat to note "neither option has been tested on this hardware" — correct, and the right response was to test, which this round did. The four-seat majority ("test B first") wins on the result, though every one of them proposed a test that could not have been run exactly as written (C1).

### Recommendation

**Adopt Option B outright — validated end-to-end on this machine, this session.** Abandon Option A, don't defer it: it needs a gated download that wouldn't fit anyway, would silently degrade rather than fail, and is documented-lossy even when it succeeds.

1. `convert_lora_to_gguf.py`'s `--base` argument must point at a config-only directory with `quantization_config` stripped — the entire difference between the failed and successful conversion attempts.
2. The null baseline becomes strictly cleaner than §14 originally asked for: the same Modelfile with the `ADAPTER` line removed. Same base GGUF, same code path, one-line delta.
3. `train_native.py`'s `--merge` path should be deleted, not fixed — nothing merges under this design; a latent mislabeled path is a trap for a future session.

**Test plan with pass/fail** (Option B acceptance, run before run 1 on the real adapter): conversion exits 0 with matching tensor count; `ollama create` succeeds; one coherent-output spot check passes; the 50,000x-scale adapter-is-live control shows degeneration (mandatory — this is the anti-silent-failure guard); null baseline (Modelfile minus ADAPTER) matches bare `llama3:8b-instruct-q4_K_M` output.

### Residual risks, named so they aren't mistaken for cleared

- The smoke adapter was 2 steps — pipeline validated mechanically, says nothing about training quality or run-1 hyperparameters.
- **`[VERIFY]`, unresolved:** the smoke adapter was trained against `unsloth/llama-3-8b-Instruct-bnb-4bit` but applied to Ollama's `llama3:8b-instruct-q4_K_M` — both descend from the same base but tokenizer/vocab/weight identity between the two quantizations was not verified. The one place a genuinely quiet error could still enter; cheap to check (tokenizer hash comparison + base-only logits spot check), should happen before run 1.
- The llama.cpp working copy used for these probes was a partial clone (hit a Windows filename-length failure on an unrelated subtree); the converter and `gguf-py` ran fine from it, but a clean pinned clone should be vendored properly before this path is load-bearing.

---

## 4. Chairman synthesis

See `COUNCIL RESPONSE §22` in `instructions.txt` (2026-07-26 ~08:10) for the full ranked critique, evidence-read list, leftover risks, "the questions themselves," and the one recommended next prompt. Summary in `council-report-2026-07-26_0810.md`.

---

*Watcher still armed on the DIRECTIVE block (task `bkk3n3jtj`) — fires on the next real DIRECTIVE rewrite. Note: a large new §21 "PROJECT VISION + COMPETITIVE POSITION" section landed in the channel mid-round, separate from this decision — see the proprietor for how to sequence a round on it.*
