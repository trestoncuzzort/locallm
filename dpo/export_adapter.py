#!/usr/bin/env python3
"""export_adapter.py — put a trained LoRA adapter in front of the UNTOUCHED base.

train_native.py has always pointed here and this file did not exist, so a trained
adapter had no documented way into Ollama. This is that path.

NOTHING IS EVER MERGED. The 4-bit merge round-trip (dequantize -> add -> requantize)
was deleted from train_native.py deliberately and is not reintroduced here.
Instead llama.cpp converts the PEFT adapter to GGUF and Ollama's ADAPTER instruction
applies it at inference against the base GGUF, which is never rewritten.

    python export_adapter.py --adapter smoke_adapter_qwen05b \
        --base-tag qwen2.5:0.5b-instruct --name forged-qwen05b --verify

WHAT --verify CHECKS (the acceptance test):
  1. conversion exits 0 AND the GGUF carries the same tensor count as the adapter
  2. `ollama create` succeeds for both the adapted model and the null baseline
  3. a coherent-output spot check on the adapted model
  4. THE ADAPTER-IS-LIVE CONTROL. An adapter can be silently ignored — a wrong
     path, an unsupported architecture, an instruction that parsed but did nothing —
     and every check above still passes. So we build a THIRD model from the same
     adapter with its LoRA B matrices scaled by a large factor and confirm its
     output changes. If a 50,000x amplification leaves output byte-identical to
     the null baseline, the adapter is not being applied and the export is a lie.

ON THE PASS CRITERION FOR CHECK 4, deliberately: it gates on "the amplified
output is not byte-identical to the null output" — a bright line, not a tuned
similarity threshold. This project has repeatedly shipped guards whose own
threshold was invented and passed while the thing they guarded was broken; a
number like "similarity < 0.8" here would be exactly that mistake. Similarity
ratios ARE reported, as evidence to read, but nothing keys off them.

THE NULL BASELINE is the same Modelfile with the ADAPTER line removed. That is
what an efficacy run compares against, so that "the adapter did something" cannot
be confounded with "the export path did something".
"""
from __future__ import annotations

import argparse
import difflib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The converter needs torch + gguf, which live in the training venv, not in the
# system Python this script may be launched with. Same lesson as sync_public.py:
# choose the interpreter, do not inherit it.
VENV_PY = HERE / ".venv-train" / "Scripts" / "python.exe"
LLAMA_CPP = Path(__import__("os").environ.get("SRLM_LLAMA_CPP", r"C:\Users\t\llama.cpp"))
OLLAMA_URL = "http://localhost:11434"
AMPLIFY = 50_000.0

SPOT_PROMPT = "Write a Python function that returns the sum of a list of numbers."


def _reexec_in_venv_if_needed() -> None:
    """This script needs torch/gguf/safetensors, which live in .venv-train, but it
    is natural to launch it with the system Python like every other script here.
    Rather than fail on an import three steps in, hand off to the right
    interpreter immediately. Same lesson as sync_public.py's test gate."""
    try:
        import gguf, safetensors, torch  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    me = Path(__file__).resolve()
    if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
        r = subprocess.run([str(VENV_PY), str(me), *sys.argv[1:]])
        sys.exit(r.returncode)
    raise SystemExit(
        "export_adapter.py needs torch, gguf and safetensors.\n"
        f"  expected interpreter: {VENV_PY}\n"
        "  install into that venv:  .venv-train\\Scripts\\python -m pip install gguf")


def safe(s: str) -> str:
    """Console-safe echo. A degenerate adapter emits whatever it likes — CJK
    punctuation, control bytes — and the Windows console is cp1252, so printing
    raw model output crashes the run that was about to report the finding. The
    full text always goes to the JSON report; only this echo is sanitised."""
    enc = sys.stdout.encoding or "utf-8"
    return s.encode(enc, errors="replace").decode(enc, errors="replace")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def generate(model: str, prompt: str, timeout: int = 180) -> str:
    """One deterministic completion, so reruns are comparable."""
    import urllib.request
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0, "seed": 1337, "num_predict": 120},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["response"]


def adapter_tensor_count(adapter_dir: Path) -> int:
    from safetensors import safe_open
    with safe_open(adapter_dir / "adapter_model.safetensors", framework="pt") as f:
        return len(list(f.keys()))


def gguf_tensor_count(path: Path) -> int:
    import gguf
    return len(gguf.GGUFReader(str(path)).tensors)


def convert(adapter_dir: Path, out: Path, base_hf: str | None) -> subprocess.CompletedProcess:
    script = LLAMA_CPP / "convert_lora_to_gguf.py"
    if not script.exists():
        raise SystemExit(
            f"llama.cpp converter not found at {script}.\n"
            f"  git clone --depth 1 https://github.com/ggml-org/llama.cpp\n"
            f"  or set SRLM_LLAMA_CPP=<path to llama.cpp>")
    py = VENV_PY if VENV_PY.exists() else Path(sys.executable)
    cmd = [str(py), str(script), str(adapter_dir), "--outfile", str(out),
           "--outtype", "f16"]
    # The converter's two base flags are NOT interchangeable: --base takes a
    # local directory it opens as a path, --base-model-id takes a hub repo id.
    # Passing a repo id to --base makes it look for "Qwen\Qwen2.5-0.5B-Instruct\
    # config.json" on disk and fail. Pick by what the adapter config actually holds.
    if base_hf:
        cmd += (["--base", base_hf] if Path(base_hf).is_dir()
                else ["--base-model-id", base_hf])
    return run(cmd)


def amplified_copy(adapter_dir: Path, dest: Path, factor: float) -> Path:
    """Same adapter with lora_B scaled. B is the zero-initialised side, so scaling
    it scales the whole delta without touching A's geometry."""
    import torch
    from safetensors.torch import load_file, save_file
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in ("adapter_config.json",):
        shutil.copy2(adapter_dir / name, dest / name)
    tensors = load_file(str(adapter_dir / "adapter_model.safetensors"))
    scaled = {k: (v.to(torch.float32) * factor if "lora_B" in k else v.to(torch.float32))
              for k, v in tensors.items()}
    save_file(scaled, str(dest / "adapter_model.safetensors"))
    return dest


def write_modelfile(path: Path, base_tag: str, adapter_gguf: Path | None) -> Path:
    lines = [f"FROM {base_tag}"]
    if adapter_gguf is not None:
        lines.append(f"ADAPTER {adapter_gguf}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def ollama_create(name: str, modelfile: Path) -> subprocess.CompletedProcess:
    return run(["ollama", "create", name, "-f", str(modelfile)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, help="LoRA dir from train_native.py")
    ap.add_argument("--base-tag", required=True, help="Ollama tag of the BASE model")
    ap.add_argument("--name", required=True, help="name for the adapted model")
    ap.add_argument("--outdir", default=None, help="where to put gguf/Modelfiles")
    ap.add_argument("--verify", action="store_true", help="run the 4 acceptance checks")
    args = ap.parse_args()

    adapter = Path(args.adapter).resolve()
    if not (adapter / "adapter_model.safetensors").exists():
        raise SystemExit(f"no adapter_model.safetensors in {adapter}")
    outdir = Path(args.outdir).resolve() if args.outdir else adapter / "export"
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((adapter / "adapter_config.json").read_text())
    base_hf = cfg.get("base_model_name_or_path")
    null_name = f"{args.name}-null"
    report: dict = {"adapter": str(adapter), "base_tag": args.base_tag,
                    "base_hf": base_hf, "model": args.name, "null_model": null_name,
                    "checks": {}}

    # ---- 1. convert -------------------------------------------------------
    gguf_path = outdir / "adapter.gguf"
    print(f"[1/4] converting {adapter.name} -> {gguf_path.name}")
    c = convert(adapter, gguf_path, base_hf)
    if c.returncode != 0 or not gguf_path.exists():
        print(c.stdout[-2000:] or "", c.stderr[-2000:] or "")
        raise SystemExit("conversion FAILED")
    n_ad, n_gg = adapter_tensor_count(adapter), gguf_tensor_count(gguf_path)
    report["checks"]["convert"] = {"exit": c.returncode, "adapter_tensors": n_ad,
                                   "gguf_tensors": n_gg, "match": n_ad == n_gg}
    print(f"      exit 0; tensors adapter={n_ad} gguf={n_gg} "
          f"{'MATCH' if n_ad == n_gg else 'MISMATCH'}")

    # ---- 2. create both models -------------------------------------------
    print(f"[2/4] ollama create {args.name} (+ {null_name}, the null baseline)")
    mf = write_modelfile(outdir / "Modelfile", args.base_tag, gguf_path)
    mf_null = write_modelfile(outdir / "Modelfile.null", args.base_tag, None)
    r1, r2 = ollama_create(args.name, mf), ollama_create(null_name, mf_null)
    report["checks"]["ollama_create"] = {args.name: r1.returncode, null_name: r2.returncode}
    if r1.returncode != 0 or r2.returncode != 0:
        print((r1.stderr or "")[-1500:], (r2.stderr or "")[-1500:])
        raise SystemExit("ollama create FAILED")
    print("      both created")

    if not args.verify:
        print(f"\ndone. run with --verify for the acceptance checks.")
        (outdir / "export_report.json").write_text(json.dumps(report, indent=2))
        return 0

    # ---- 3. spot check ----------------------------------------------------
    print("[3/4] coherent-output spot check")
    out_adapted = generate(args.name, SPOT_PROMPT)
    out_null = generate(null_name, SPOT_PROMPT)
    report["checks"]["spot"] = {"prompt": SPOT_PROMPT,
                               "adapted": out_adapted, "null": out_null}
    print(f"      adapted: {safe(out_adapted[:90])!r}")

    # ---- 4. adapter-is-live control --------------------------------------
    print(f"[4/4] adapter-is-live control (lora_B x {AMPLIFY:,.0f})")
    amp_dir = amplified_copy(adapter, outdir / "amplified", AMPLIFY)
    amp_gguf = outdir / "adapter_amplified.gguf"
    ca = convert(amp_dir, amp_gguf, base_hf)
    if ca.returncode != 0 or not amp_gguf.exists():
        print(ca.stderr[-2000:] or "")
        raise SystemExit("amplified conversion FAILED")
    amp_name = f"{args.name}-amplified"
    mf_amp = write_modelfile(outdir / "Modelfile.amplified", args.base_tag, amp_gguf)
    ra = ollama_create(amp_name, mf_amp)
    if ra.returncode != 0:
        print((ra.stderr or "")[-1500:])
        raise SystemExit("amplified ollama create FAILED")
    out_amp = generate(amp_name, SPOT_PROMPT)

    def sim(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()

    identical = out_amp == out_null
    report["checks"]["adapter_is_live"] = {
        "amplify": AMPLIFY,
        "amplified_output": out_amp[:400],
        "amplified_equals_null": identical,
        "similarity_amplified_vs_null": round(sim(out_amp, out_null), 4),
        "similarity_adapted_vs_null": round(sim(out_adapted, out_null), 4),
        "criterion": "PASS iff amplified output is NOT byte-identical to null. "
                     "Similarities are reported as evidence; nothing keys off them.",
        "passed": not identical,
    }
    print(f"      amplified: {safe(out_amp[:90])!r}")
    print(f"      amplified == null ? {identical}   "
          f"(similarity {sim(out_amp, out_null):.4f}; "
          f"adapted-vs-null {sim(out_adapted, out_null):.4f})")

    all_ok = (n_ad == n_gg) and not identical
    report["verdict"] = "PASS" if all_ok else "FAIL"
    (outdir / "export_report.json").write_text(json.dumps(report, indent=2))
    print(f"\n{'PASS' if all_ok else 'FAIL'} — report: {outdir / 'export_report.json'}")
    print(f"null baseline for efficacy runs: {null_name}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    _reexec_in_venv_if_needed()
    sys.exit(main())
