PROBE 1 — per-task delta-profile agreement (data/ruler_noise.jsonl, per-task sampled pass rates pooled over replicates, delta = arm − same-session null, 31 tasks):
  Mean delta: rep1 +10.1pp, rep2 +11.4, rep3 +8.8 (orthogonal retrains, lr 5e-6, 1 epoch); original adapter −0.03 (replication machine) / −0.04 (same-session control); positive control (lr 2e-4, 3 epochs) +11.4pp at n=9 (interim look; prereg N=40 fixed).
  Pearson r between delta profiles: rep1–rep2 0.970, rep1–rep3 0.863, rep2–rep3 0.834 (permutation p<1e-4 each).
  Split-half reliability (Spearman-Brown): rep1 0.92, rep2 0.90, rep3 0.69, poscontrol 0.93, original adapter 0.21 (rep session) / 0.52 (control session).
  Disattenuated r (r/sqrt(rel_a*rel_b)): rep1–rep2 1.06, rep1–rep3 1.08, rep2–rep3 1.06 → the three weight-orthogonal adapters are behaviorally INDISTINGUISHABLE at the task level at the instrument's reliability ceiling.
  Original adapter vs retrains: r = −0.10 (p=.70) — its (weakly reliable) profile is UNRELATED to the retrains', not a scaled-down version. Original adapter vs itself across sessions: r=0.47 (p=.004), so its profile is weakly real.
  Positive control vs retrains: r = 0.43/0.42/0.56 (disattenuated ≈0.46–0.70) — same mean gain, DIFFERENT per-task solution: swings of +73, +64, +62, −60, −38, −31pp on individual tasks (per-task delta SD 33pp vs 15–17pp for the retrains). The high-lr/3-epoch run sits in a different behavioral basin with over-optimization on some tasks.
  Gain concentration in retrains: six tasks carry most of it (ace_oss_11023 +43..+55, 17851 +40..+44, 4327 +39..+41, 24748 +33..+39, 23069 +27..+44, 23132 +15..+27); the other 25 tasks move <15pp.

PROBE 2 — did lora_A leave its init? (dpo_adapter_poscontrol/adapter_model.safetensors, 224 layers, r=16, α=32; PEFT inits A ~ kaiming_uniform ⇒ U(−1/√fan_in, +1/√fan_in), B=0)
  Fraction of A entries outside the init bound: mean 4.5% (min 2.6%, max 8.8%). std(A)/std(uniform) = 1.02. Kurtosis 2.05 (uniform 1.80, gaussian 3.00).
  ‖A‖_F mean 2.36; ‖B‖_F mean 0.43; ‖ΔW‖_F mean 0.53 per layer (total 8.69). For comparison the ORIGINAL low-lr adapter had mean ‖ΔW‖_F ≈ 0.020 per layer (replication bundle), i.e. the high-lr adapter's update is ~26× larger.
  ⇒ Even at 40× lr and 3 epochs, A stayed essentially at its random init; the learned update lives in B, so ΔW = B·A0 lies in the random row-space of A0. Two seeds ⇒ two random 16-dim subspaces of a 4096-dim space ⇒ near-orthogonal ΔW (cos≈r/d≈0.004) — exactly the cosine the replication measured. Candidate mechanism: LoRA-with-B=0 at low lr ≈ a random SKETCH of the same full-gradient update; sketches from different seeds are orthogonal but unbiased for the same direction, so behavior concentrates. The original adapter is not on this machine, so its A-distribution and norm could not be checked here.

PROBE 3 — environment: Windows System log shows zero TDR/WHEA/Kernel-Power events in the poscontrol training window (11:29–12:38 on 2026-08-20) and eval window; the machine hard-crashed at 13:32 (Kernel-Power 41) after 9/40 rounds. TdrDelay is still unset (2s default).

PROBE 4 — the 8-bit-optimizer x massive-activation anomaly, verified independently on 2026-08-22 (dpo_adapter_poscontrol + the cached bnb-4bit base, this machine):
  Schedule: 171 steps, 18 warmup, cosine, lr 2e-4 → Σlr = 0.0173; exact-Adam worst-case per-coordinate displacement 3.16·Σlr = 0.0547.
  Scan of all 224 lora_A tensors for elements beyond (init bound + 0.0547): exactly ONE tensor has any — layers.1.mlp.down_proj.lora_A (shape 16 x 14336): 169 elements,
  all in columns [2304, 2558] (93 distinct columns, every one of the 16 rank rows), i.e. exactly the 256-aligned block 9 of the row-major flattened tensor, which is the
  block size of bitsandbytes' 8-bit blockwise optimizer-state quantization. Max |A| = 0.175 at column 2474 (init bound 1/sqrt(14336) = 0.0084, so 21x); mean max|A| per column
  0.058 inside the block vs 0.009 outside. max|B| in this layer = 0.0052 (well inside the bound). Column 2427 itself is NOT an outlier (0.0044).
  Base model (dequantized layers.1.mlp.down_proj, one forward pass on a code prompt): intermediate channel 2427 (the input to down_proj) carries a MASSIVE activation,
  max|x| = 386.5, vs 46.3 for the next channel (198) and a median of 0.013 across the 14336 channels (30,000x). Channel 2427 lies inside [2304,2559]. The third-largest
  weight in down_proj is W[788, 2427] = 0.539 (super-weight-like). Layers 0 and 2 have no comparable channel (max 6.5 and 1.1).
  NOTE: Yu et al. 2024 "The Super Weight in Large Language Models" (arXiv 2411.07191) does NOT list Llama-3-8B (its table covers Llama-1/2, Mistral, OLMo, Phi-3); it does
  state the super weight is always in an early-layer mlp.down_proj and induces a persistent super activation. The [788,2427] coordinate for Llama-3-8B is therefore
  supported by this machine's measurement, not by that citation.
  Mechanism hypothesis (not yet ablated): dL/dA[:, j] scales with x_j, so channel 2427's huge activation makes its optimizer second-moment state dominate the 256-element
  block's absmax; the 255 neighbours' states underflow in the 8-bit dynamic format and their effective step size explodes, while 2427's own entries (the absmax) stay accurate.
  Prediction: retraining with optim=adamw_torch (32-bit states), or adamw_bnb_8bit with min_8bit_size above the LoRA tensor size, removes the block anomaly; channel 198's
  block [0,255] should show a weaker version or none (its within-block dynamic range is ~70x smaller). Cost: ~25 min per arm at 1 epoch (or --max-steps 20, ~10 min).
  Functional materiality (share of ||dW||_F^2 and activation-weighted output energy in the block) was being computed at the time of writing.
  MATERIALITY (computed): the block holds 70.4% of layer-1 down_proj's ||dW||_F^2 (1.8% if uniform) but only 0.94% of the WHOLE adapter's ||dW||_F^2. Activation-weighted on a
  code prompt: the layer's adapter output delta (norm 2.24) is ~entirely channel 2427's contribution (2.53 alone; the block's 255 other columns add ≈0 because their
  activations are ~0.013). The adapter delta at this layer is 0.58% of the base down_proj output. VERDICT: a real optimizer-state defect in weight space (it would corrupt any
  weight-space geometry / norm / intruder-dimension analysis of QLoRA adapters trained with adamw_bnb_8bit on a model with a massive-activation channel), but functionally
  near-inert in THIS adapter. Side observation: because the super activation is prompt-invariant (~386 at channel 2427), the layer-1 down_proj LoRA acts as a learned
  constant offset B·A[:,2427]·386 injected into the residual stream.
