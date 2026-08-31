### Bibliographic line
Aleksandr Nikolich, Igor Kiselev, Vladimir Platonov, Karina Romanova, "Weight-Space Geometry of Offline Reasoning Training", arXiv:2606.23740v1 (21 Jun 2026), cs.LG.

### Setup
*   **Base model**: Qwen3-4B-Instruct
*   **LoRA**: attention-only
*   **Losses**: SFT, RFT, DFT, RIFT, Offline GRPO, DPO
*   **Datasets**: DeepScaleR prompts (~40k verified math), teacher DeepSeek-V4-Flash, K=4 CoT completions/prompt, binary math-verify reward. DPO uses ~1.8K pairs; others ~75K rows.
*   **Seeds**: 42, 123
*   **Learning rates**: 5e-7 to 5e-5 for SFT/RFT/etc., DPO uses 10x smaller learning rate.
*   **ΔW cosine**: Global/per-layer cosine `⟨ΔW^(m), ΔW^(m')⟩ / (||ΔW^(m)|| ||ΔW^(m')||)` where `ΔW = (α/r)BA`.
*   **Linear mode connectivity**: Masked-answer cross-entropy on GSM8K along `α ΔW^(m) + (1-α) ΔW^(m')`.

### Section 3.4 "Seed and learning-rate sensitivity"
> The colinearity above is at a *single* seed, conflating loss agreement with shared-init agreement. We disentangle by training each loss at two seeds (42, 123) and three LRs (5x10^-7..-5); ΔW = (α/r)BA is gauge-invariant, so its cosine is genuine.
> 
> **Seed rotates ΔW more than the loss — but only on the input side.** At a fixed seed SFT–RFT are colinear (cosine 0.996, angle 3.7°), yet the *same loss at two seeds* has cosine only 0.07 (5x10^-7)–0.36 (5x10^-5). Cause: LoRA’s random A init — across seeds the top-1 *output* direction u1 still agrees at 0.99 while the *input* direction v1 agrees at 0.07 (median top-8 angle 26° vs. 76° for unrelated runs). Functionally the seeds are the *same* solution: interpolating their deltas shows no barrier (midpoint +0.004). So the cross-method colinearity is partly shared-init, but convergence onto a common output subspace is seed-robust (Figure 2).
> 
> **Learning rate changes direction, not just magnitude.** A 10x LR step rotates ΔW (cosine ≈ 0.55) and grows its norm only ~3x — not a pure rescaling, which sharpens the caveat on the 10x-smaller-LR DPO comparison.
> 
> **Online GRPO is far more orthogonal than offline GRPO.** We also train *online* GRPO under the same LoRA recipe (on-policy rollouts, group-relative advantage, math_verify reward; 600 steps, 8 generations/prompt, lr 5x10^-6, seed 42) — the comparison the original protocol could not produce. The resulting update is almost entirely orthogonal to the SFT/RFT cluster: cosine 0.025 to SFT and 0.024 to RFT, with an orthogonal fraction of 0.998 off the SFT direction (Figure 1), versus 0.67 for *offline* GRPO (§3.2). Its Frobenius norm is ~10x smaller than SFT’s at the same LR (0.30 vs. 2.84), echoing the small-norm regime of DPO. On-policy sampling thus moves the update off the shared SFT subspace far more than the offline group-relative loss does, indicating that the SFT/offline-RL directional convergence is partly a consequence of training on the *same fixed rollouts*: replacing them with on-policy samples largely breaks it.

#### Figure 2 caption
> **Figure 2**: **Seed and learning-rate sensitivity (SFT, Qwen3-4B).** *Left:* across two seeds the output direction u1 stays aligned (~0.99) while the input direction v1 and full cosine are low at small LR and rise with LR; dashed shows SFT–RFT at a fixed seed. *Middle:* a 10x LR step rotates ΔW (cosine ≈ 0.55) and grows its norm sub-linearly — LR is not a pure rescaling. *Right:* interpolating the two seeds’ deltas shows no loss barrier — different weights, same basin.

### What they did NOT measure
*   (i) per-task or per-item behavioral agreement between seeds (not aggregate accuracy, not loss along an interpolation path): not reported
*   (ii) any reliability correction (split-half, disattenuation, test-retest): not reported
*   (iii) execution-verified code tasks with hidden unit tests: not reported
*   (iv) displacement of lora_A from its initialization (fraction still inside the init box): not reported
*   (v) an analytic expectation for the cross-seed cosine (r/d_in, 1/sqrt(r*fan_in), or similar): not reported
*   (vi) per-module differences in cross-seed cosine (attention q/k/v/o vs MLP down_proj): not reported
*   (vii) whether their lora_A init was seeded, and by which call: not reported

### Library mentions
The paper does not mention `trl`, `peft`, `set_seed`, or `get_peft_model` anywhere.
