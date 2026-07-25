# srlm-forge

A failure-driven self-rewarding loop that trains a local model to fix its own
mistakes. The model proposes; **unit tests decide**; preferences are learned
from the verdict. No ungrounded self-judging, so it improves instead of drifting.

## The loop

```
forge.py                          train_dpo.py
--------                          ------------
actor  -> K candidates
verify -> unit tests = reward -->  DPO on (prompt, chosen, rejected)
pair   -> chosen vs rejected  -->  QLoRA adapter -> GGUF
fails  -> failures.jsonl                |
   ^                                    v
   +------ better actor <-- ollama create llama3-forged
```

`failures.jsonl` is the point: the tasks no candidate could solve are the
curriculum for the next round and the seed for training from scratch on
current failures.

## What you need to make it run

1. **Ollama up with a model** (not currently reachable on this box):
   ```
   ollama serve            # if not already running
   ollama pull llama3:8b-instruct-q4_K_M
   ```
2. **Generate data** (works on the system Python 3.14; only needs `requests`):
   ```
   python forge.py
   ```
   → `data/dpo_pairs.jsonl` and `data/failures.jsonl`
3. **Train** — in a *separate* Python 3.10–3.12 env with CUDA torch (the
   system 3.14 can't run Unsloth/torch). See the header of `train_dpo.py`.

## VRAM budget (16 GB card)

- Generation: only the 4-bit actor is resident (~5–6 GB for an 8B). `keep_alive`
  keeps it warm between tasks and releases it on exit.
- Training: 8B QLoRA fits in ~10–12 GB. Lower `MAX_SEQ` or batch if you OOM.

## Safety notes (read before scaling)

- `forge.py` executes model-generated code in an isolated subprocess (`python -I`,
  timeout) with a coarse banned-op filter. That is **defense-in-depth, not a real
  sandbox.** For untrusted or large runs, execute inside a container or a
  throwaway VM.
- Tasks are pure-function coding problems on purpose: the reward is objective and
  the blast radius is small. Keep new tasks in that shape and the loop stays sound.
