# TRL seeding-order audit — PARTIAL (byte-level, execution order inside __init__)

Session cd70aff0, workflow wf_d02411b3-eb8, stopped 2026-08-22 ~17:15 to free the lab PC for the manuscript pass; 45 agent results cached, resumable with resumeFromRunId.
Question: does the trainer reach get_peft_model (lora_A kaiming init on the global RNG) BEFORE transformers.Trainer.__init__ runs set_seed(args.seed)?

Antigravity's earlier table marked several rows 'seed-first' from FILE line order; those are artifacts (e.g. v0.21.0 DPOTrainer.__init__ calls self._prepare_peft_model at line 317 before super().__init__ at 453; the helper at 543 calls get_peft_model at 585 => peft-first).

Tags discovered: v0.7.11, v0.8.6, v0.9.6, v0.10.1, v0.11.4, v0.12.2, v0.13.0, v0.14.0, v0.15.2, v0.16.1, v0.17.0, v0.18.2, v0.19.1, v0.20.0, v0.21.0, v0.22.2, v0.23.1, v0.24.0, v0.25.1, v0.26.2, v0.27.2, v0.28.0, v0.29.1, v1.0.0, v1.1.0, v1.2.0, v1.3.0, v1.4.0, v1.5.1, v1.6.0, v1.7.1, v1.8.0, v1.9.2, v1.10.0  (method: GitHub REST API: curl -sL "https://api.github.com/repos/huggingface/trl/tags?per_page=100&page=N" for N=1..4 (page 1 returned all 94 tags; pages 2-4 returned empty arrays, so no rate-limit fallback wa)

| tag | trainer | PEFT wrap line (via) | Trainer.__init__ line | explicit seed before wrap | ORDER | verifier |
|---|---|---|---|---|---|---|
| trl-v0.22.2-peft-vs-seed-order | dpo | 324 (helper DPOTrainer._prepare_peft_model (def at line 547); ins) | 460 | none | **peft-first** |  |
| trl-v0.22.2-peft-vs-seed-order | sft | 694 (helper trl.models.utils.prepare_peft_model (imported at sft_) | 822 | none | **peft-first** |  |
| trl-v0.22.2-peft-vs-seed-order | grpo | 264 (helper trl.models.utils.prepare_peft_model (imported at grpo) | 402 | none | **peft-first** |  |
| v0.10.1 | dpo | 567 (direct) | 833 | none | **peft-first** |  |
| v0.10.1 | sft | 266 (direct) | 412 | none | **peft-first** |  |
| v0.10.1 | grpo | file absent | | | n/a | |
| v0.10.1 | dpo | 567 (direct) | 833 | none | **peft-first** |  |
| v0.10.1 | sft | 266 (direct) | 412 | none | **peft-first** |  |
| v0.10.1 | grpo | file absent | | | n/a | |
| v0.11.4 | dpo | 556 (direct) | 822 | none | **peft-first** |  |
| v0.11.4 | sft | 266 (direct (two branches of one if/else: line 266 for sharded-QL) | 401 | none | **peft-first** |  |
| v0.11.4 | grpo | file absent | | | n/a | |
| v0.12.2 | dpo | 376 (direct) | 640 | none | **peft-first** |  |
| v0.12.2 | sft | 285 (direct) | 408 | none | **peft-first** |  |
| v0.12.2 | grpo | file absent | | | n/a | |
| v0.13.0 | dpo | 318 (direct) | 487 | none | **peft-first** |  |
| v0.13.0 | sft | 226 (direct) | 307 | none | **peft-first** |  |
| v0.13.0 | grpo | file absent | | | n/a | |
| v0.14.0 | dpo | 323 (direct) | 469 | none | **peft-first** |  |
| v0.14.0 | sft | 224 (direct) | 307 | none | **peft-first** |  |
| v0.14.0 | grpo | 198 (direct) | 269 | none | **peft-first** |  |
| v0.15.2 | dpo | 324 (direct) | 470 | none | **peft-first** |  |
| v0.15.2 | sft | 183 (_prepare_peft_model (defined line 279); inside it get_peft_m) | 232 | none | **peft-first** |  |
| v0.15.2 | grpo | 247 (direct) | 330 | none | **peft-first** |  |
| v0.15.2 | dpo | 324 (direct) | 470 | none | **peft-first** |  |
| v0.15.2 | sft | 183 (_prepare_peft_model (defined at 279); inside it get_peft_mod) | 232 | none | **peft-first** |  |
| v0.15.2 | grpo | 247 (direct) | 330 | none | **peft-first** |  |
| v0.16.1 | dpo | 321 (direct) | 467 | none | **peft-first** |  |
| v0.16.1 | sft | 281 (_prepare_peft_model (defined at line 363, below __init__); g) | 321 | none | **peft-first** |  |
| v0.16.1 | grpo | 308 (direct) | 413 | none | **peft-first** |  |
| v0.16.1 | dpo | 321 (direct) | 467 | none | **peft-first** |  |
| v0.16.1 | sft | 281 (_prepare_peft_model (defined at 363); inside helper: 402 'mo) | 321 | none | **peft-first** |  |
| v0.16.1 | grpo | 308 (direct) | 413 | none | **peft-first** |  |
| v0.17.0 | dpo | 321 (direct) | 467 | none | **peft-first** |  |
| v0.17.0 | sft | 274 (_prepare_peft_model (defined at line 400, below __init__); i) | 358 | none | **peft-first** |  |
| v0.17.0 | grpo | 411 (direct) | 565 | none | **peft-first** |  |
| v0.17.0 | dpo | 321 (direct) | 467 | none | **peft-first** |  |
| v0.17.0 | sft | 274 (_prepare_peft_model (defined at 400); get_peft_model called ) | 358 | none | **peft-first** |  |
| v0.17.0 | grpo | 411 (direct) | 565 | none | **peft-first** |  |
| v0.18.2 | dpo | 317 (direct) | 463 | none | **peft-first** |  |
| v0.18.2 | sft | 291 (_prepare_peft_model (defined at line 433, below __init__); i) | 385 | none | **peft-first** |  |
| v0.18.2 | grpo | 433 (direct) | 543 | none | **peft-first** |  |
| v0.18.2 | dpo | 317 (direct) | 463 | none | **peft-first** |  |
| v0.18.2 | sft | 291 (_prepare_peft_model (defined L433, below __init__); inside i) | 385 | none | **peft-first** |  |
| v0.18.2 | grpo | 433 (direct) | 543 | none | **peft-first** |  |
| v0.19.1 | dpo | 306 (_prepare_peft_model (defined at line 531, below __init__); i) | 441 | none | **peft-first** |  |
| v0.19.1 | sft | 397 (_prepare_peft_model (defined at line 554, below __init__); i) | 506 | none | **peft-first** |  |
| v0.19.1 | grpo | 443 (direct) | 553 | none | **peft-first** |  |
| v0.19.1 | dpo | 306 (_prepare_peft_model (def at 531); get_peft_model called at l) | 441 | none | **peft-first** |  |
| v0.19.1 | sft | 397 (_prepare_peft_model (def at 554); get_peft_model called at l) | 506 | none | **peft-first** |  |
| v0.19.1 | grpo | 443 (direct) | 553 | none | **peft-first** |  |
| v0.20.0 | dpo | 317 (_prepare_peft_model (defined at 543); inside helper line 585) | 453 | none | **peft-first** |  |
| v0.20.0 | sft | 434 (_prepare_peft_model (defined at 591); inside helper line 624) | 543 | none | **peft-first** |  |
| v0.20.0 | grpo | 580 (direct) | 719 | none | **peft-first** |  |
| v0.21.0 | dpo | 317 (_prepare_peft_model (def at line 543); inside helper: 555: `) | 453 | none | **peft-first** |  |
| v0.21.0 | sft | 434 (_prepare_peft_model (def at line 592); inside helper: 617: `) | 544 | none | **peft-first** |  |
| v0.21.0 | grpo | 553 (direct) | 692 | none | **peft-first** |  |
| v0.21.0 | dpo | 317 (_prepare_peft_model (defined L543); inside helper: L585 `   ) | 453 | none | **peft-first** |  |
| v0.21.0 | sft | 434 (_prepare_peft_model (defined L592); inside helper: L623 `   ) | 544 | none | **peft-first** |  |
| v0.21.0 | grpo | 553 (direct) | 692 | none | **peft-first** |  |
| v0.22.2 | dpo | 324 (_prepare_peft_model (same file, def at 547); inside it line ) | 460 | none | **peft-first** |  |
| v0.22.2 | sft | 694 (prepare_peft_model imported at line 55 `from ..models import) | 822 | none | **peft-first** |  |
| v0.22.2 | grpo | 264 (prepare_peft_model imported at line 56 `from ..models import) | 402 | none | **peft-first** |  |
| v0.23.1 | dpo | 320 (_prepare_peft_model (defined at line 543 in trl/trainer/dpo_) | 456 | none | **peft-first** |  |
| v0.23.1 | sft | 731 (prepare_peft_model from trl/models/utils.py (imported at sft) | 869 | none | **peft-first** |  |
| v0.23.1 | grpo | 262 (prepare_peft_model from trl/models/utils.py (imported at grp) | 402 | none | **peft-first** |  |
| v0.24.0 | dpo | 350 (helper DPOTrainer._prepare_peft_model (def at line 565 of tr) | 486 | none | **peft-first** |  |
| v0.24.0 | sft | 697 (helper prepare_peft_model imported from ..models (sft_traine) | 844 | none | **peft-first** |  |
| v0.24.0 | grpo | 272 (helper prepare_peft_model imported from ..models (grpo_train) | 408 | none | **peft-first** |  |
| v0.25.1 | dpo | 354 (_prepare_peft_model (defined at dpo_trainer.py:569 `def _pre) | 490 | none | **peft-first** |  |
| v0.25.1 | sft | 697 (prepare_peft_model (imported at sft_trainer.py:51 `from ..mo) | 844 | none | **peft-first** |  |
| v0.25.1 | grpo | 296 (prepare_peft_model (imported at grpo_trainer.py:62 `from ..m) | 446 | none | **peft-first** |  |
| v0.26.2 | dpo | 354 (_prepare_peft_model (defined at 553, called from __init__ at) | 490 | none | **peft-first** |  |
| v0.26.2 | sft | 703 (direct) | 871 | none | **peft-first** |  |
| v0.26.2 | grpo | 319 (direct) | 503 | none | **peft-first** |  |
| v0.27.2 | dpo | 364 (_prepare_peft_model (defined at line 555, `def _prepare_peft) | 492 | none | **peft-first** |  |
| v0.27.2 | sft | 725 (direct) | 883 | none | **peft-first** |  |
| v0.27.2 | grpo | 344 (direct) | 534 | none | **peft-first** |  |
| v0.28.0 | dpo | 380 (_prepare_peft_model (defined at 579); get_peft_model called ) | 516 | none | **peft-first** |  |
| v0.28.0 | sft | 725 (direct) | 909 | none | **peft-first** |  |
| v0.28.0 | grpo | 331 (direct) | 544 | none | **peft-first** |  |
| v0.29.1 | dpo | 557 (direct) | 683 | none | **peft-first** |  |
| v0.29.1 | sft | 752 (direct) | 936 | none | **peft-first** |  |
| v0.29.1 | grpo | 351 (direct) | 599 | none | **peft-first** |  |
| v0.7.11 | dpo | 247 (direct) | 379 | none | **peft-first** |  |
| v0.7.11 | sft | 212 (direct) | 299 | none | **peft-first** |  |
| v0.7.11 | grpo | file absent | | | n/a | |
| v0.8.6 | dpo | 251 (direct) | 383 | none | **peft-first** |  |
| v0.8.6 | sft | 228 (direct) | 323 | none | **peft-first** |  |
| v0.8.6 | grpo | file absent | | | n/a | |
| v0.9.6 | dpo | 290 (direct) | 535 | none | **peft-first** |  |
| v0.9.6 | sft | 265 (direct) | 413 | none | **peft-first** |  |
| v0.9.6 | grpo | file absent | | | n/a | |
| v0.9.6 | dpo | 290 (direct) | 535 | none | **peft-first** |  |
| v0.9.6 | sft | 263 (direct) | 413 | none | **peft-first** |  |
| v0.9.6 | grpo | file absent | | | n/a | |
| v1.0.0 | dpo | 593 (direct) | 729 | none | **peft-first** |  |
| v1.0.0 | sft | 791 (direct) | 983 | none | **peft-first** |  |
| v1.0.0 | grpo | 347 (direct) | 609 | none | **peft-first** |  |
| v1.1.0 | dpo | 589 (direct) | 725 | none | **peft-first** |  |
| v1.1.0 | sft | 791 (direct) | 990 | none | **peft-first** |  |
| v1.1.0 | grpo | 355 (direct) | 626 | none | **peft-first** |  |
| v1.2.0 | dpo | 589 (direct) | 725 | none | **peft-first** |  |
| v1.2.0 | sft | 791 (direct) | 990 | none | **peft-first** |  |
| v1.2.0 | grpo | 367 (direct) | 635 | none | **peft-first** |  |
| v1.3.0 | dpo | 589 (direct) | 725 | none | **peft-first** |  |
| v1.3.0 | sft | 791 (direct) | 990 | none | **peft-first** |  |
| v1.3.0 | grpo | 365 (direct) | 632 | none | **peft-first** |  |
| v1.4.0 | dpo | 590 (direct) | 738 | none | **peft-first** |  |
| v1.4.0 | sft | 1059 (direct) | 1286 | none | **peft-first** |  |
| v1.4.0 | grpo | 366 (direct) | 643 | none | **peft-first** |  |
| v1.5.1 | dpo | 590 (direct) | 738 | none | **peft-first** |  |
| v1.5.1 | sft | 1065 (direct) | 1292 | none | **peft-first** |  |
| v1.5.1 | grpo | 366 (direct) | 643 | none | **peft-first** |  |
| v1.6.0 | dpo | 589 (direct) | 744 | none | **peft-first** |  |
| v1.6.0 | sft | 1091 (direct) | 1327 | none | **peft-first** |  |
| v1.6.0 | grpo | 366 (direct) | 644 | none | **peft-first** |  |

Rows: 108 from 39 tags traced; 5 verifier re-derivations (5 agree).

## Verifier evidence
- v0.7.11/trl/trainer/dpo_trainer.py::DPOTrainer: agree -> peft-first. Independent trace of fetched bytes (1250 lines). __init__ spans 142-419.

142:    def __init__(
211:        elif is_peft_available() and peft_config is not None:
213:            if isinstance(model, PeftModel):
234:                model = prepare_model_for_kbit_training(model, **preprare_model_kwargs)
241:                    def make_inputs_require_grad(module, input, output):   [nested def at 20-
- v0.7.11/SFTTrainer (trl/trainer/sft_trainer.py): agree -> peft-first. Fetched https://raw.githubusercontent.com/huggingface/trl/v0.7.11/trl/trainer/sft_trainer.py (519 lines, sha256 8139b63bffbb6786dff7cd1d6520bfa127437fb1936c2b4b66bca53e327ea447). Execution trace inside __init__:
123:    def __init__(
165:            model = AutoModelForCausalLM.from_pretrained(model, **model_init_kwargs)
172:        if is_peft_available() and peft_config is not None:
179:         
- v0.24.0/DPOTrainer (trl/trainer/dpo_trainer.py): agree -> peft-first. Fetched https://raw.githubusercontent.com/huggingface/trl/v0.24.0/trl/trainer/dpo_trainer.py (2004 lines, sha256 54161b42470b7bc333da3da2a84e86c7da1eb95946992d022dd91ea22fd4fe52). Independent trace of EXECUTION order inside __init__:

187:class DPOTrainer(BaseTrainer):
269:    def __init__(

PEFT wrap call (8-space indent = unconditional __init__ body level; the ONLY self.*() call between lines 26
- v0.24.0/GRPOTrainer (trl/trainer/grpo_trainer.py): agree -> peft-first. Independently fetched https://raw.githubusercontent.com/huggingface/trl/v0.24.0/trl/trainer/grpo_trainer.py (1843 lines, sha256 bb6905182acf2ec426f1dc9ffc37e5210d58ee47d2764f7cf12dbb90a4a28954) and trl/models/utils.py (563 lines), trl/models/__init__.py, trl/trainer/base_trainer.py.

grpo_trainer.py imports:
29: from accelerate.utils import broadcast_object_list, gather, gather_object, is_peft_mod
- v0.24.0/SFTTrainer (trl/trainer/sft_trainer.py): agree -> peft-first. Fetched from raw.githubusercontent.com/huggingface/trl/v0.24.0 (sft_trainer.py md5 b4e50e365128a6410359a2e5ae7f603d; models/utils.py md5 21ec84dfe1b138c2347d548052221d21).

sft_trainer.py:
50: from ..models import clone_chat_template, get_act_offloading_ctx_manager, prepare_peft_model
481: class SFTTrainer(BaseTrainer):
575:     def __init__(
603:         if isinstance(model, str):
604:           