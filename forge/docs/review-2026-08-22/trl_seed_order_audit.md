# TRL Seeding-Order Audit

| tag | release date | trainer | line get_peft_model | line super.__init__ | order | permalink |
|---|---|---|---|---|---|---|
| v0.7.0 | 2023-08-30 | dpo_trainer.py | 114 | 180 | peft-first | https://github.com/huggingface/trl/blob/v0.7.0/trl/trainer/dpo_trainer.py |
| v0.7.0 | 2023-08-30 | sft_trainer.py | 150 | 212 | peft-first | https://github.com/huggingface/trl/blob/v0.7.0/trl/trainer/sft_trainer.py |
| v0.8.6 | 2024-04-22 | dpo_trainer.py | 251 | 383 | peft-first | https://github.com/huggingface/trl/blob/v0.8.6/trl/trainer/dpo_trainer.py |
| v0.8.6 | 2024-04-22 | sft_trainer.py | 228 | 323 | peft-first | https://github.com/huggingface/trl/blob/v0.8.6/trl/trainer/sft_trainer.py |
| v0.9.6 | 2024-07-08 | dpo_trainer.py | 290 | 535 | peft-first | https://github.com/huggingface/trl/blob/v0.9.6/trl/trainer/dpo_trainer.py |
| v0.9.6 | 2024-07-08 | sft_trainer.py | 263 | 413 | peft-first | https://github.com/huggingface/trl/blob/v0.9.6/trl/trainer/sft_trainer.py |
| v0.11.4 | 2024-10-15 | dpo_trainer.py | 556 | 822 | peft-first | https://github.com/huggingface/trl/blob/v0.11.4/trl/trainer/dpo_trainer.py |
| v0.11.4 | 2024-10-15 | sft_trainer.py | 266 | 401 | peft-first | https://github.com/huggingface/trl/blob/v0.11.4/trl/trainer/sft_trainer.py |
| v0.12.2 | 2024-12-06 | dpo_trainer.py | 376 | 640 | peft-first | https://github.com/huggingface/trl/blob/v0.12.2/trl/trainer/dpo_trainer.py |
| v0.12.2 | 2024-12-06 | sft_trainer.py | 283 | 408 | peft-first | https://github.com/huggingface/trl/blob/v0.12.2/trl/trainer/sft_trainer.py |
| v0.13.0 | 2024-12-16 | dpo_trainer.py | 318 | 487 | peft-first | https://github.com/huggingface/trl/blob/v0.13.0/trl/trainer/dpo_trainer.py |
| v0.13.0 | 2024-12-16 | sft_trainer.py | 224 | 307 | peft-first | https://github.com/huggingface/trl/blob/v0.13.0/trl/trainer/sft_trainer.py |
| v0.15.2 | 2025-02-25 | dpo_trainer.py | 324 | 470 | peft-first | https://github.com/huggingface/trl/blob/v0.15.2/trl/trainer/dpo_trainer.py |
| v0.15.2 | 2025-02-25 | sft_trainer.py | 318 | 232 | seed-first | https://github.com/huggingface/trl/blob/v0.15.2/trl/trainer/sft_trainer.py |
| v0.15.2 | 2025-02-25 | grpo_trainer.py | 247 | 330 | peft-first | https://github.com/huggingface/trl/blob/v0.15.2/trl/trainer/grpo_trainer.py |
| v0.17.0 | 2025-04-25 | dpo_trainer.py | 321 | 467 | peft-first | https://github.com/huggingface/trl/blob/v0.17.0/trl/trainer/dpo_trainer.py |
| v0.17.0 | 2025-04-25 | sft_trainer.py | 439 | 358 | seed-first | https://github.com/huggingface/trl/blob/v0.17.0/trl/trainer/sft_trainer.py |
| v0.17.0 | 2025-04-25 | grpo_trainer.py | 411 | 184 | seed-first | https://github.com/huggingface/trl/blob/v0.17.0/trl/trainer/grpo_trainer.py |
| v0.19.0 | 2025-06-21 | dpo_trainer.py | 573 | 441 | seed-first | https://github.com/huggingface/trl/blob/v0.19.0/trl/trainer/dpo_trainer.py |
| v0.19.0 | 2025-06-21 | sft_trainer.py | 585 | 498 | seed-first | https://github.com/huggingface/trl/blob/v0.19.0/trl/trainer/sft_trainer.py |
| v0.19.0 | 2025-06-21 | grpo_trainer.py | 442 | 552 | peft-first | https://github.com/huggingface/trl/blob/v0.19.0/trl/trainer/grpo_trainer.py |
| v0.21.0 | 2025-08-05 | dpo_trainer.py | 585 | 453 | seed-first | https://github.com/huggingface/trl/blob/v0.21.0/trl/trainer/dpo_trainer.py |
| v0.21.0 | 2025-08-05 | sft_trainer.py | 623 | 544 | seed-first | https://github.com/huggingface/trl/blob/v0.21.0/trl/trainer/sft_trainer.py |
| v0.21.0 | 2025-08-05 | grpo_trainer.py | 553 | 692 | peft-first | https://github.com/huggingface/trl/blob/v0.21.0/trl/trainer/grpo_trainer.py |
| main | N/A | dpo_trainer.py | 652 | 888 | peft-first | https://github.com/huggingface/trl/blob/main/trl/trainer/dpo_trainer.py |
| main | N/A | sft_trainer.py | 1119 | 1350 | peft-first | https://github.com/huggingface/trl/blob/main/trl/trainer/sft_trainer.py |
| main | N/A | grpo_trainer.py | 447 | 949 | peft-first | https://github.com/huggingface/trl/blob/main/trl/trainer/grpo_trainer.py |

Note: `transformers` `Trainer.__init__` calls `set_seed` on line 424 (at v4.46.3) and line 408 (at main). Because `super().__init__` invokes `Trainer.__init__`, any `peft-first` trainer invokes `get_peft_model` prior to `set_seed(args.seed)` running, resulting in an unseeded `lora_A` initialization.

## Community Reports
I searched GitHub issues and PRs in `huggingface/trl` and `huggingface/peft`, as well as the web, using the following exact queries:
- `site:github.com/huggingface/trl "get_peft_model" "set_seed"`
- `site:github.com/huggingface/peft "get_peft_model" "set_seed"`
- `site:github.com/huggingface/trl "lora_A" "seed"`
- `site:github.com/huggingface/trl "get_peft_model" "reproducib"`

**None found** reporting this exact library defect (that `TRL`'s internal classes call them in the wrong order, causing `lora_A` to be unseeded by `training_args.seed`). The search hits show users and developers sporadically recommending manual workarounds in their own scripts (e.g., calling `set_seed(training_args.seed)` manually *before* passing the model to a TRL trainer), but there is no issue tracking the internal bug that the trainers themselves enforce a `peft-first` sequence out-of-the-box in their `__init__` methods.
