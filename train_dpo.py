#!/usr/bin/env python3
"""
train_dpo.py : QLoRA DPO training on forge-generated preference pairs.

RUN THIS IN A SEPARATE ENV. Unsloth + torch need Python 3.10-3.12 and a CUDA
build of torch. The system default here is Python 3.14, which the ML stack does
not support yet. Create an isolated interpreter, e.g.:

    py -3.12 -m venv .venv-train
    .venv-train\\Scripts\\activate
    pip install "unsloth[cu121] @ git+https://github.com/unslothai/unsloth.git" trl

VRAM: an 8B model in 4-bit QLoRA trains inside ~10-12 GB, leaving headroom
under a 16 GB card. Drop max_seq_length or per_device_batch if you OOM.
"""

from pathlib import Path

DATA = Path(__file__).with_name("data") / "dpo_pairs.jsonl"
OUT = Path(__file__).with_name("dpo_adapter")
BASE_MODEL = "unsloth/llama-3-8b-Instruct-bnb-4bit"
MAX_SEQ = 2048


def main() -> None:
    from datasets import load_dataset
    from unsloth import FastLanguageModel, PatchDPOTrainer
    PatchDPOTrainer()  # must run before importing the trainer
    from trl import DPOConfig, DPOTrainer

    model, tokenizer = FastLanguageModel.from_pretrained(
        BASE_MODEL, max_seq_length=MAX_SEQ, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
    )

    # forge emits {prompt, chosen, rejected} -> exactly TRL's DPO schema.
    ds = load_dataset("json", data_files=str(DATA), split="train")

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
        max_length=MAX_SEQ,
        max_prompt_length=MAX_SEQ // 2,
    )
    trainer.train()

    # Export to GGUF so the improved model goes straight back into Ollama,
    # closing the loop: forge -> train -> better actor -> forge.
    model.save_pretrained_gguf(str(OUT), tokenizer, quantization_method="q4_k_m")
    print(f"adapter + GGUF written to {OUT}")
    print("Then: ollama create llama3-forged -f <Modelfile pointing at the gguf>")


if __name__ == "__main__":
    if not DATA.exists():
        raise SystemExit(f"no preference data at {DATA}; run forge.py first")
    main()
