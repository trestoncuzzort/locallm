#!/usr/bin/env python3
"""
train_dpo.py : QLoRA DPO training on forge-generated preference pairs.

MODEL-AGNOSTIC. The base model, LoRA target modules, and seq length all come from
config.py, which resolves them from $SRLM_MODEL (+ $SRLM_HF_BASE for unknown models).
Point it at any model and this trains that model:

    SRLM_MODEL=qwen2.5:7b-instruct-q4_K_M  python train_dpo.py           # known family
    SRLM_MODEL=my:tag SRLM_HF_BASE=org/Repo-bnb-4bit  python train_dpo.py  # custom

RUN THIS IN A SEPARATE ENV. Unsloth + torch need Python 3.10-3.12 and CUDA torch;
the system default here is 3.14, which the ML stack does not support yet:

    py -3.12 -m venv .venv-train
    .venv-train\\Scripts\\activate
    pip install "unsloth[cu121] @ git+https://github.com/unslothai/unsloth.git" trl

VRAM: a 7-9B model in 4-bit QLoRA trains inside ~10-12 GB under a 16 GB card.
Drop SRLM_MAX_SEQ or per_device_batch if you OOM.
"""

from pathlib import Path

import config
import dataset_gate

HERE = Path(__file__).parent
# Both preference sources: forge's frontier-success pairs + repair's failure-derived.
DATA_FILES = [HERE / "data" / "dpo_pairs.jsonl", HERE / "data" / "repair_pairs.jsonl"]
OUT = HERE / "dpo_adapter"
M = config.MODEL


def main() -> None:
    if not M.trainable:
        raise SystemExit(
            f"No HF training base for ollama tag '{M.ollama_tag}'.\n"
            f"  -> export SRLM_HF_BASE=<hf repo or local path> and retry.\n"
            f"  -> run `python config.py` to inspect the resolved config.")

    # Resolved before the heavy imports so the data gate fails in a second
    # rather than after Unsloth loads a 4-bit model.
    files = [str(p) for p in DATA_FILES if p.exists()]
    if not files:
        raise SystemExit("no preference data; run forge.py / repair.py first")

    # THE GATE — same one train_native.py uses. Both trainers are consumers of
    # the same guarantee, so both go through the same chokepoint; gating only
    # one would leave "verified before training" false via the other path.
    files = dataset_gate.load_verified(files, HERE / "data")

    from datasets import load_dataset
    from unsloth import FastLanguageModel, PatchDPOTrainer
    PatchDPOTrainer()  # must run before importing the trainer
    from trl import DPOConfig, DPOTrainer

    print(f"[train] ollama_tag={M.ollama_tag}  hf_base={M.hf_base}  "
          f"targets={M.target_modules}  (resolved via {M.source})")

    model, tokenizer = FastLanguageModel.from_pretrained(
        M.hf_base, max_seq_length=M.max_seq, load_in_4bit=M.load_in_4bit,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=16, lora_dropout=0.0,
        target_modules=M.target_modules,
        use_gradient_checkpointing="unsloth",
    )

    ds = load_dataset("json", data_files=files, split="train")
    print(f"[train] {len(ds)} preference pairs from {[Path(f).name for f in files]}")

    # Wrap each prompt in THIS model's chat template so training is correct for any
    # architecture; chosen/rejected stay as the raw assistant completions.
    if getattr(tokenizer, "chat_template", None):
        def _templ(ex):
            ex["prompt"] = tokenizer.apply_chat_template(
                [{"role": "user", "content": ex["prompt"]}],
                tokenize=False, add_generation_prompt=True)
            return ex
        ds = ds.map(_templ)

    trainer = DPOTrainer(
        model=model,
        args=DPOConfig(
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            warmup_ratio=0.1,
            num_train_epochs=1,
            learning_rate=5e-6,
            beta=0.1,
            bf16=True,
            optim="adamw_8bit",
            output_dir=str(OUT),
            logging_steps=1,
        ),
        train_dataset=ds,
        tokenizer=tokenizer,
        max_length=M.max_seq,
        max_prompt_length=M.max_seq // 2,
    )
    trainer.train()

    # Export GGUF so the improved model goes straight back into Ollama, closing the
    # loop: forge -> train -> better actor -> forge. Named from the model tag.
    forged = M.ollama_tag.split(":")[0].replace("/", "-") + "-forged"
    model.save_pretrained_gguf(str(OUT), tokenizer, quantization_method="q4_k_m")
    print(f"adapter + GGUF written to {OUT}")
    print(f"Then: ollama create {forged} -f <Modelfile pointing at the gguf>")
    print(f"And measure it:  SRLM_MODEL={forged} python eval.py")


if __name__ == "__main__":
    main()
