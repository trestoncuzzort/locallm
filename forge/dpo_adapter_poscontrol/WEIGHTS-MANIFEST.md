# dpo_adapter_poscontrol — excluded binaries (sha256, from the 2026-08-22 repo audit)

The adapter weights are gitignored (over GitHub's 100MB limit for the safetensors; regenerable
from the fixed seed once `--seed` lands, and the GGUF is served in Ollama as `llama3-forged-poscontrol`).
Provenance is pinned here so a fresh clone can verify a re-exported copy.

| file | bytes | sha256 |
|---|---|---|
| adapter_model.safetensors | 167832240 | 3115603c7872ba673faf7ca551f5de772553142fe12b1fd77e8cf3c016547235 |
| export/adapter.gguf | 83917280 | 2cf7e8ccd6f7c130e12610b39f57846f6ec371fa9345af68fedf81d83f64735d |
| export/adapter_amplified.gguf (lora_B x50000 liveness control) | 83916832 | 4baabc002c277021707ebfaa8d6f34ec2a913e60486bff6a524c37a62e3a35c9 |
| export/amplified/adapter_model.safetensors | ~167M | 3f8b12fca6d0fd80da95ed4afdc05d29bb5dabd1f5139ab6f9be0cbd90b37170 |

Recipe: lr 2e-4, 3 epochs, beta 0.1, rpo_alpha 1.0, 918 pairs (data/prereg_positive_control.json).
