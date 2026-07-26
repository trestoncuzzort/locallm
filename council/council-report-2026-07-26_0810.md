# srlm-forge Council — Report

**Activation #8** · 2026-07-26 ~08:10 · manually convened (not DIRECTIVE-triggered — the executor's §19 log handed back one specific open decision rather than rewriting the DIRECTIVE)
**Scope:** `train_native.py`, `config.py`, on-disk model configs, plus live experiments run by The PhD on this machine this session.

## The question

Track A's merge step is broken: `train_native.py` calls `merge_and_unload()` directly on the 4-bit model and mislabels the output "merged fp16" — it can't actually export. Two fixes were on the table: (A) the original council mandate — reload the base in bf16 and merge properly; (B) an untested alternative from round 7 — skip merging, convert the LoRA to a GGUF adapter and apply it at inference via Ollama's `ADAPTER` directive. The executor refused to pick either unilaterally on unvalidated prior art and handed the decision to the council.

## Key numbers

- Llama-3-8B in bf16: **14.96 GiB** of weights alone. Measured free VRAM on this machine: **14.69 GiB**. Gap: **-0.27 GiB**, before adapter/activations/merge overhead.
- CUDA system-memory fallback is **ON** on this driver (591.86): a 22 GiB allocation on a 15.99 GiB card did not error — it silently spilled to host RAM.
- Option B validated end-to-end: real throwaway smoke adapter (2 steps, 22.6s) → converted → loaded into Ollama → coherent inference. A 50,000x adapter-scale control confirmed the adapter is genuinely applied (output degenerated to garbage), not silently ignored.

## The chairman's verdict

**Where the council agrees:** four of five style advisors independently proposed testing Option B before committing to either path — real convergence, not vote-counting.

**Corrections that changed the round:** three of five style advisors proposed testing Option B against "the trained LoRA sitting idle now" — no such adapter exists (zero gradient steps have been taken on Track A). The PhD caught this and substituted a real throwaway smoke adapter. The Contrarian's claimed mechanism for why Option B was dangerous ("bitsandbytes adapters carry quantization state") was directly disproved by tensor inspection. The round's own reframing arithmetic (16.06 GB into 16 GB) mixed decimal GB against GiB — the PhD corrected the units; the conclusion survived, the number as first stated didn't.

**The one real disagreement:** the Outsider dissented from the four-advisor majority, arguing Option A's failure (OOM) would be safe and visible while Option B's would be silent and dangerous. Both halves inverted under direct measurement — Option B failed loudly on its first real attempt (a named exception in ~10 seconds), and Option A doesn't OOM on this hardware at all; it silently spills into host RAM.

**The recommendation:** Adopt Option B outright. It's not merely preferred — Option A is dead on three independent grounds (doesn't fit measured VRAM, can't even be attempted as specified because the only local Llama-3 weights are pre-quantized and true bf16 requires a gated, undownloaded repo, and is documented-lossy even when it works). Delete the `--merge` path rather than leave it as latent, mislabeled dead code.

## The one thing to do first

Before run 1: verify tokenizer/vocab identity between the training base (`unsloth/llama-3-8b-Instruct-bnb-4bit`) and the inference base (Ollama's `llama3:8b-instruct-q4_K_M`) — the one seam in this round's validation that wasn't checked. Cheap (hash comparison + a logits spot check), and it's the one place a quiet error could still enter.

## Advisor alignment map

| Seat | Position this round |
|---|---|
| **The PhD** (leads, + inherited audit duty) | Ran the actual experiments. Option B validated end-to-end; Option A dead on 3 grounds. Corrected 3 advisors' false "trained adapter exists" assumption and the Contrarian's disproved mechanism claim. |
| Contrarian | Wanted Option B tested first, but via a nonexistent trained adapter; central risk claim (quantization state in adapters) was tested and found false. |
| First Principles | Reframed the goal as "inference parity," not "merging" — correctly identified Option B addresses the actual goal more directly. |
| Expansionist | Option B as the project's standing pattern for all future models, not just a workaround — survived the round intact. |
| Outsider | Lone dissent (test A first) — refuted by measurement (A doesn't fail loudly here; B does, safely). Correctly noted neither option had been tested yet. |
| Pragmatist | Proposed a VRAM dry-run probe — found unsound on this specific machine due to the sysmem-fallback discovery; would report a false "fits." |

Full record: `council-transcript-2026-07-26_0810.md`.
