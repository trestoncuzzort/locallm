#!/usr/bin/env python3
"""train_native.py — Windows-native QLoRA DPO, no Unsloth (avoids triton/xformers).

Runs in .venv-train (Python 3.11 + torch cu121). Model-agnostic: base model, LoRA
targets, and seq length come from config.py ($SRLM_MODEL / $SRLM_HF_BASE).

Run 1 discipline: DPO on the verified frontier pairs only; the 38
repair pairs are EXCLUDED by default (single variable). Pass --include-repair to add.

    .venv-train\\Scripts\\python train_native.py            # frontier pairs only
    .venv-train\\Scripts\\python train_native.py --include-repair

Output: dpo_adapter_native/  (LoRA adapter only). Nothing is ever merged: the
adapter is applied at inference via Ollama's ADAPTER instruction against the
untouched base GGUF. See export_adapter.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
import dataset_gate
import forge


def build_training_prompt(tok, prompt_text: str) -> str:
    """Render the training prompt exactly as the sampler and the scorer render it.

    THE SEAM THIS CLOSES (found by an independent review pass; red witness
    recorded in the project log). This function used to build a user-only turn.
    forge.Actor.generate posts
    system=ACTOR_SYSTEM + user when it samples every pair, and eval.py reuses that
    same Actor when it scores. So the trainer was optimising a prompt that was
    missing a header block present at both generation and evaluation - measured at
    47 of 98 prompt tokens for a real pair, nearly half.

    The system turn is not decoration here: ACTOR_SYSTEM is what instructs the
    model to emit a fenced block at all, so dropping it changes what the correct
    output even looks like.
    """
    return tok.apply_chat_template(
        [{"role": "system", "content": forge.ACTOR_SYSTEM},
         {"role": "user", "content": prompt_text}],
        tokenize=False, add_generation_prompt=True)


def training_target(ex: dict, field: str) -> str:
    """The assistant turn to optimise toward, as the policy would have emitted it.

    forge stores `chosen`/`rejected` as extract_code() output - fences stripped -
    because clean_dataset.py:26, verify_dataset.py:82 and both dedup hashes need
    executable source. That is correct for the gates and wrong as a DPO target:
    ACTOR_SYSTEM demands a ```python block, so bare source is a string no policy
    ever emitted.

    Prefers `<field>_raw`, the verbatim completion, when forge recorded it. For
    legacy pairs written before that field existed, re-fences the stored code.
    That is a RECONSTRUCTION, not the original bytes - close, because ACTOR_SYSTEM
    forbids prose, but not identical. Pairs regenerated after this change carry
    the real thing.
    """
    raw = ex.get(f"{field}_raw")
    if raw:
        return raw
    return f"```python\n{ex[field]}\n```"

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
    ap.add_argument("--lr", type=float, default=5e-6,
                    help="from the alignment-handbook zephyr QLoRA-DPO recipe; "
                         "replaces an earlier unsourced 8e-6 default")
    ap.add_argument("--out", default=str(HERE / "dpo_adapter_native"))
    ap.add_argument("--raw-pairs", action="store_true",
                    help="train on the uncapped dpo_pairs.jsonl instead of the "
                         "918-pair capped file (NOT the run-1 configuration)")
    args = ap.parse_args()

    if not M.trainable:
        raise SystemExit(f"No HF base for '{M.ollama_tag}'; set SRLM_HF_BASE.")

    # Run 1 trains from the CAPPED, stratified 918-pair file, not the raw 1,234.
    # The cap takes the top-3 task share from 54.0% to 39.2%. Measured, it is a
    # mild improvement and not a fix: it spends 25.6% of the data to buy 1.06
    # effective tasks (8.86 -> 9.93 by entropy), where 5 new tasks would buy 3.60
    # while adding data. See build_training_set.py. Record its sha256 in the prereg.
    #
    # Resolved BEFORE the heavy imports so the data gate below fails in a second
    # instead of after a 16 GB model load.
    capped = HERE / "data" / "dpo_pairs_capped.jsonl"
    if args.raw_pairs:
        files = [str(HERE / "data" / "dpo_pairs.jsonl")]
        print("[train] WARNING: --raw-pairs — training on the UNCAPPED set. "
              "This is not the run-1 configuration.")
    elif capped.exists():
        files = [str(capped)]
    else:
        raise SystemExit(
            f"Missing {capped.name}. Run: python build_training_set.py\n"
            f"(or pass --raw-pairs to deliberately train on the uncapped set)")
    rp = HERE / "data" / "repair_pairs.jsonl"
    if args.include_repair and rp.exists():
        files.append(str(rp))

    # THE GATE. Every pair in every file about to be trained on must have been
    # re-verified bidirectionally (chosen passes / rejected fails) against the
    # exact bytes on disk. No bypass flag: one would make the guarantee false.
    files = dataset_gate.load_verified(files, HERE / "data")

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
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        target_modules=M.target_modules, task_type="CAUSAL_LM")

    ds = load_dataset("json", data_files=files, split="train")
    # chosen_raw/rejected_raw are the verbatim completions when forge recorded
    # them; they must survive this projection or training_target() can only ever
    # see the fence-stripped fallback.
    keep = {"prompt", "chosen", "rejected", "chosen_raw", "rejected_raw"}
    ds = ds.remove_columns([c for c in ds.column_names if c not in keep])
    if args.limit:
        ds = ds.select(range(min(args.limit, len(ds))))

    n_raw = sum(1 for ex in ds if ex.get("chosen_raw"))
    print(f"[train] {len(ds)} pairs from {[Path(f).name for f in files]}; "
          f"{n_raw} carry verbatim completions, {len(ds) - n_raw} fall back to "
          f"re-fenced source")

    # Render prompt and targets the way the sampler and the scorer render them.
    # See build_training_prompt / training_target for the seam this closes.
    if getattr(tok, "chat_template", None):
        ds = ds.map(lambda ex: {
            "prompt": build_training_prompt(tok, ex["prompt"]),
            "chosen": training_target(ex, "chosen"),
            "rejected": training_target(ex, "rejected"),
        })
        ds = ds.remove_columns([c for c in ds.column_names
                                if c in ("chosen_raw", "rejected_raw")])

    cfg = DPOConfig(
        output_dir=args.out,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,          # effective batch 16
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.lr,
        beta=0.1,
        rpo_alpha=1.0,              # DPO+NLL. Without this the NLL branch in
                                    # TRL 0.12.2's dpo_trainer never executes and
                                    # chosen-likelihood can fall while margin grows
                                    # (Pal 2024, arXiv:2402.13228; Pang 2024, 2404.19733)
        lr_scheduler_type="cosine",  # cosine, not TRL's default linear
        warmup_ratio=0.1,
        bf16=True,
        optim="adamw_bnb_8bit",     # NON-paged (paging never fires under the
                                    # VRAM assert and is the least-tested path here)
        logging_steps=5,
        save_strategy="no",
        max_length=1024,            # 1024/512, not config.max_seq's 2048/1024
        max_prompt_length=512,
        report_to="none",
    )
    trainer = DPOTrainer(model=model, args=cfg, train_dataset=ds,
                         processing_class=tok, peft_config=peft_cfg)
    trainer.train()
    trainer.save_model(args.out)
    print(f"[train] adapter saved to {args.out}")

    # NOTHING IS MERGED. The old --merge path called merge_and_unload() on the
    # 4-bit model and labelled the output "fp16"; it was deleted rather than
    # fixed. Export is: convert_lora_to_gguf.py -> Ollama's ADAPTER
    # instruction, applying the adapter at inference against the untouched base.
    # See export_adapter.py. Do not reintroduce a merge step here.

    # Record what ran, for the preregistration trail.
    (Path(args.out) / "run_meta.json").write_text(json.dumps({
        "base": M.hf_base, "ollama_tag": M.ollama_tag, "pairs": len(ds),
        "include_repair": args.include_repair, "epochs": args.epochs,
        "lr": args.lr, "beta": 0.1, "targets": M.target_modules,
        "rpo_alpha": 1.0, "lr_scheduler_type": "cosine",
        "optim": "adamw_bnb_8bit", "max_length": 1024, "max_prompt_length": 512,
        "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.05,
    }, indent=2))


if __name__ == "__main__":
    main()
