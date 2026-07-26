#!/usr/bin/env python3
"""train_native.py — Windows-native QLoRA DPO, no Unsloth (avoids triton/xformers).

Runs in .venv-train (Python 3.11 + torch cu121). Model-agnostic: base model, LoRA
targets, and seq length come from config.py ($SRLM_MODEL / $SRLM_HF_BASE).

Run 1 discipline (council §12): DPO on the verified frontier pairs only; the 38
repair pairs are EXCLUDED by default (single variable). Pass --include-repair to add.

    .venv-train\\Scripts\\python train_native.py            # frontier pairs only
    .venv-train\\Scripts\\python train_native.py --include-repair

Output: dpo_adapter_native/  (LoRA adapter + merged fp16 for GGUF export).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import config

HERE = Path(__file__).parent
M = config.MODEL


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-repair", action="store_true",
                    help="also train on data/repair_pairs.jsonl (default: off)")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--max-steps", type=int, default=-1,
                    help="cap optimizer steps (smoke test); -1 = full epochs")
    ap.add_argument("--limit", type=int, default=0,
                    help="use only first N pairs (smoke test); 0 = all")
    ap.add_argument("--lr", type=float, default=8e-6)
    ap.add_argument("--out", default=str(HERE / "dpo_adapter_native"))
    ap.add_argument("--merge", action="store_true",
                    help="also write a merged fp16 model for GGUF export")
    args = ap.parse_args()

    if not M.trainable:
        raise SystemExit(f"No HF base for '{M.ollama_tag}'; set SRLM_HF_BASE.")

    import torch
    from datasets import load_dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, prepare_model_for_kbit_training
    from trl import DPOConfig, DPOTrainer

    print(f"[train] base={M.hf_base} targets={M.target_modules} "
          f"cuda={torch.cuda.is_available()} "
          f"gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU!'}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA not available in venv — check the torch cu121 install.")

    tok = AutoTokenizer.from_pretrained(M.hf_base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # The unsloth *-bnb-4bit repos are standard bitsandbytes NF4 checkpoints;
    # transformers loads them directly (quant config is embedded).
    model = AutoModelForCausalLM.from_pretrained(
        M.hf_base, device_map={"": 0}, torch_dtype=torch.bfloat16)
    model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    peft_cfg = LoraConfig(
        r=16, lora_alpha=16, lora_dropout=0.0, bias="none",
        target_modules=M.target_modules, task_type="CAUSAL_LM")

    files = [str(HERE / "data" / "dpo_pairs.jsonl")]
    rp = HERE / "data" / "repair_pairs.jsonl"
    if args.include_repair and rp.exists():
        files.append(str(rp))
    ds = load_dataset("json", data_files=files, split="train")
    keep = {"prompt", "chosen", "rejected"}
    ds = ds.remove_columns([c for c in ds.column_names if c not in keep])
    if args.limit:
        ds = ds.select(range(min(args.limit, len(ds))))
    # Wrap the prompt in this model's own chat template (correct across models).
    if getattr(tok, "chat_template", None):
        ds = ds.map(lambda ex: {"prompt": tok.apply_chat_template(
            [{"role": "user", "content": ex["prompt"]}],
            tokenize=False, add_generation_prompt=True)})
    print(f"[train] {len(ds)} pairs from {[Path(f).name for f in files]}")

    cfg = DPOConfig(
        output_dir=args.out,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,          # effective batch 16
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.lr,
        beta=0.1,
        warmup_ratio=0.1,
        bf16=True,
        optim="paged_adamw_8bit",
        logging_steps=5,
        save_strategy="no",
        max_length=M.max_seq,
        max_prompt_length=M.max_seq // 2,
        report_to="none",
    )
    trainer = DPOTrainer(model=model, args=cfg, train_dataset=ds,
                         processing_class=tok, peft_config=peft_cfg)
    trainer.train()
    trainer.save_model(args.out)
    print(f"[train] adapter saved to {args.out}")

    if args.merge:
        merged = Path(args.out).with_name(Path(args.out).name + "_merged16")
        m = trainer.model.merge_and_unload()
        m.save_pretrained(str(merged), safe_serialization=True)
        tok.save_pretrained(str(merged))
        print(f"[train] merged fp16 -> {merged}  (for convert_hf_to_gguf.py)")

    # Record what ran, for the executor log / prereg trail.
    (Path(args.out) / "run_meta.json").write_text(json.dumps({
        "base": M.hf_base, "ollama_tag": M.ollama_tag, "pairs": len(ds),
        "include_repair": args.include_repair, "epochs": args.epochs,
        "lr": args.lr, "beta": 0.1, "targets": M.target_modules,
    }, indent=2))


if __name__ == "__main__":
    main()
