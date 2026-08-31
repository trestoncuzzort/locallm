#!/usr/bin/env python3
"""config.py — one place that makes srlm-forge model-agnostic.

The pipeline touches a model through TWO different identifiers:
  - an OLLAMA TAG for generation/eval/repair (e.g. "qwen2.5:7b-instruct-q4_K_M")
  - an HF BASE for training via Unsloth        (e.g. "unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
plus per-architecture LoRA target modules. This module resolves all of it from a
single source so you can point the whole pipeline at any model without editing code.

Pick a model, in priority order:
  1. env  SRLM_MODEL=<ollama tag>          (generation/eval side)
     env  SRLM_HF_BASE=<hf repo or path>   (training side; needed for unknown models)
     env  SRLM_TARGET_MODULES=q_proj,...   (optional LoRA target override)
  2. the built-in registry (known families get HF base + targets automatically)
  3. for an unknown tag, the architecture is auto-detected from Ollama /api/show so
     generation/eval Just Work; training then only needs SRLM_HF_BASE.

Inspect what will be used:   python config.py
List the known registry:     python config.py --list
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests

OLLAMA_URL = os.environ.get("SRLM_OLLAMA_URL", "http://localhost:11434")
DEFAULT_TAG = "llama3:8b-instruct-q4_K_M"

# LoRA target modules by architecture.
_ATTN_MLP = ["q_proj", "k_proj", "v_proj", "o_proj",
             "gate_proj", "up_proj", "down_proj"]          # llama/mistral/qwen/gemma
_PHI3 = ["qkv_proj", "o_proj", "gate_up_proj", "down_proj"]  # fused projections

_ARCH_MODS = {
    "llama": _ATTN_MLP, "mistral": _ATTN_MLP, "qwen2": _ATTN_MLP,
    "qwen3": _ATTN_MLP, "gemma": _ATTN_MLP, "gemma2": _ATTN_MLP,
    "gemma3": _ATTN_MLP, "phi3": _PHI3,
}

# Known models: match by Ollama-tag prefix -> (HF base for Unsloth, target modules).
# hf bases are Unsloth 4-bit repos that fit a 16 GB card for QLoRA.
_REGISTRY: dict[str, tuple[str, list[str]]] = {
    "llama3.1":  ("unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit", _ATTN_MLP),
    "llama3.2":  ("unsloth/Llama-3.2-3B-Instruct-bnb-4bit", _ATTN_MLP),
    "llama3":    ("unsloth/llama-3-8b-Instruct-bnb-4bit", _ATTN_MLP),
    "qwen2.5":   ("unsloth/Qwen2.5-7B-Instruct-bnb-4bit", _ATTN_MLP),
    "qwen3":     ("unsloth/Qwen3-8B-bnb-4bit", _ATTN_MLP),
    "mistral":   ("unsloth/mistral-7b-instruct-v0.3-bnb-4bit", _ATTN_MLP),
    "gemma2":    ("unsloth/gemma-2-9b-it-bnb-4bit", _ATTN_MLP),
    "gemma3":    ("unsloth/gemma-3-4b-it-bnb-4bit", _ATTN_MLP),
    "phi3":      ("unsloth/Phi-3-mini-4k-instruct-bnb-4bit", _PHI3),
    "codellama": ("unsloth/codellama-7b-Instruct-bnb-4bit", _ATTN_MLP),
}


@dataclass
class ModelConfig:
    ollama_tag: str                 # generation / eval / repair (via Ollama)
    hf_base: str | None             # training base (via Unsloth); None = must be set
    target_modules: list[str] = field(default_factory=lambda: list(_ATTN_MLP))
    max_seq: int = 2048
    load_in_4bit: bool = True
    source: str = "registry"        # how this config was resolved (for logging)

    @property
    def trainable(self) -> bool:
        return bool(self.hf_base)


def _detect_arch(tag: str) -> str | None:
    """Best-effort architecture from Ollama /api/show (so unknown tags still work
    for generation and get sane LoRA targets)."""
    try:
        r = requests.post(f"{OLLAMA_URL}/api/show", json={"name": tag}, timeout=5)
        r.raise_for_status()
        info = r.json()
        arch = (info.get("model_info", {}) or {}).get("general.architecture")
        return arch or (info.get("details", {}) or {}).get("family")
    except requests.RequestException:
        return None


def resolve() -> ModelConfig:
    tag = os.environ.get("SRLM_MODEL", DEFAULT_TAG)
    hf_env = os.environ.get("SRLM_HF_BASE")
    tm_env = os.environ.get("SRLM_TARGET_MODULES")
    tmods = [m.strip() for m in tm_env.split(",")] if tm_env else None

    hf_base, reg_mods, source = None, None, "custom-env"
    low = tag.lower()
    for key, (base, mods) in _REGISTRY.items():
        if low.startswith(key):
            hf_base, reg_mods, source = base, mods, f"registry:{key}"
            break
    else:
        arch = _detect_arch(tag)
        if arch:
            reg_mods = _ARCH_MODS.get(arch.lower(), _ATTN_MLP)
            source = f"autodetect:{arch}"

    return ModelConfig(
        ollama_tag=tag,
        hf_base=hf_env or hf_base,          # env wins; else registry; else None
        target_modules=tmods or reg_mods or list(_ATTN_MLP),
        max_seq=int(os.environ.get("SRLM_MAX_SEQ", "2048")),
        source=source if not hf_env else f"{source}+env-hf",
    )


# Resolved once at import; the rest of the pipeline reads these.
MODEL = resolve()
MODEL_NAME = MODEL.ollama_tag        # back-compat alias used across the pipeline


def _cli() -> None:
    import sys
    if "--list" in sys.argv:
        print("known model families (match by ollama-tag prefix):")
        for k, (base, _) in _REGISTRY.items():
            print(f"  {k:12} -> {base}")
        return
    m = MODEL
    print("resolved active model config")
    print(f"  ollama_tag     : {m.ollama_tag}")
    print(f"  hf_base        : {m.hf_base or '(unset — export SRLM_HF_BASE to train)'}")
    print(f"  target_modules : {m.target_modules}")
    print(f"  max_seq        : {m.max_seq}")
    print(f"  trainable      : {m.trainable}")
    print(f"  resolved via   : {m.source}")
    print(f"  ollama url     : {OLLAMA_URL}")
    print("\nchange model:  SRLM_MODEL=<ollama-tag>  (+ SRLM_HF_BASE=<repo> if unknown)")


if __name__ == "__main__":
    _cli()
