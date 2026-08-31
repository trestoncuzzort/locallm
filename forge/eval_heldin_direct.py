#!/usr/bin/env python3
"""eval_heldin_direct.py — HELD-IN check via transformers+peft, bypassing Ollama.

WHY THIS EXISTS AND WHAT IT IS NOT
----------------------------------
The GGUF export path is blocked: convert_lora_to_gguf.py cannot dequantize a
bitsandbytes base, and every entry in config.py's _REGISTRY is a -bnb-4bit repo.
So the trained adapter cannot currently be served through Ollama at all, and the
Ollama-based scorers cannot see it.

This scores the adapter where it actually lives. It is a DIAGNOSTIC, not the
ruler and not the served artifact:

  - the served artifact would be a merged/requantized GGUF, and merge plus
    requantization can change behaviour (this is exactly the open question the
    sponsor package files under F-22). A number here does not license a claim
    about what Ollama would serve.
  - the tasks are forge.SEED_TASKS, which the adapter trained on. Movement here
    is memorisation-inflated by construction.

THE CONFOUND THIS FILE EXISTS TO AVOID
--------------------------------------
The earlier held-in baseline (0.8308) was produced through Ollama at q4_K_M.
This runs bnb-4bit. Those are DIFFERENT QUANTIZATIONS of the same weights, so
comparing an Ollama base number against a direct adapter number would mix the
quantization delta into the training delta and could invent an effect that is
not there. Therefore BOTH arms run here, through identical code, in one process:

    base (adapter disabled)  vs  base + adapter (adapter enabled)

Only that within-process pair is a legitimate comparison. The Ollama 0.8308 is
carried as a cross-check on the base arm, never as the baseline for the adapter.

Run:  .venv-train/Scripts/python.exe eval_heldin_direct.py
"""
from __future__ import annotations

import json, time, sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

import forge
import eval as ruler

BASE    = "unsloth/llama-3-8b-Instruct-bnb-4bit"
ADAPTER = "dpo_adapter_native"
OUT     = Path(__file__).with_name("data") / "heldin_history.jsonl"
N, TEMP = ruler.N_SAMPLES, ruler.TEMP


def gen(model, tok, prompt: str, temp: float) -> str:
    msgs = [{"role": "system", "content": forge.ACTOR_SYSTEM},
            {"role": "user", "content": prompt}]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                  return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=512, do_sample=temp > 0,
                             temperature=temp if temp > 0 else None,
                             top_p=0.95 if temp > 0 else None,
                             pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][ids.shape[-1]:], skip_special_tokens=True)


def score(model, tok, arm: str) -> dict:
    per_task = []
    for t in forge.SEED_TASKS:
        c = scored = errors = 0
        for i in range(N):
            temp = 0.0 if i == 0 else TEMP      # same policy as eval.py
            try:
                raw = gen(model, tok, t.prompt, temp)
            except Exception as e:              # noqa: BLE001
                errors += 1; print(f"  [{t.tid}] gen error: {e}"); continue
            scored += 1
            if forge.verify(forge.extract_code(raw), t).ok:
                c += 1
        per_task.append({"tid": t.tid, "correct": c, "n": scored,
                         "requested": N, "gen_errors": errors})
        print(f"  {t.tid:18} {''.join('#' if j < c else '.' for j in range(scored))} {c}/{scored}")
    agg = {}
    for k in ruler.KS:
        usable = [p for p in per_task if p["n"] >= k]
        agg[f"pass@{k}"] = round(sum(ruler.pass_at_k(p["n"], p["correct"], k)
                                     for p in usable) / len(usable), 4) if usable else None
    return {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": f"{BASE}+{arm}",
            "task_set": "held_in_direct", "arm": arm, "engine": "transformers+peft bnb-4bit",
            "not_the_served_artifact": True, "n_samples": N, "temp": TEMP,
            "n_tasks": len(forge.SEED_TASKS), "aggregate": agg, "per_task": per_task}


def main() -> None:
    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForCausalLM.from_pretrained(BASE, device_map="cuda:0",
                                                 torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, ADAPTER)
    model.eval()

    results = []
    for arm in ("base", "adapter"):
        if arm == "base":
            model.disable_adapter_layers()
        else:
            model.enable_adapter_layers()
        print(f"\n=== ARM: {arm} ({'adapter OFF' if arm=='base' else 'adapter ON'}) ===")
        r = score(model, tok, arm)
        print(f"  aggregate: {r['aggregate']}")
        results.append(r)

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    b, a = results[0]["aggregate"], results[1]["aggregate"]
    print("\n" + "=" * 60)
    print("HELD-IN, WITHIN-PROCESS, SAME QUANTIZATION (the only valid comparison)")
    for k in ruler.KS:
        key = f"pass@{k}"
        print(f"  {key}: base {b[key]:.4f} -> adapter {a[key]:.4f} "
              f"(delta {a[key]-b[key]:+.4f})")
    print("Memorisation-inflated by construction; not the served artifact.")


if __name__ == "__main__":
    main()
