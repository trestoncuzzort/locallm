# Ubuntu bootstrap — srlm-forge on ubuntu-box

Written 2026-08-25 from the macOS side. Read this before running anything.
Paste it to the Claude instance on that machine as its first message.

## Machine etiquette comes first

`ubuntu-box` is shared with two PhD students (two PhD students). Written policy from
the machine's owner: **PhD experiments always take priority over undergraduate experiments.**
Before starting GPU work, check whether the card is busy:

    nvidia-smi

If someone is training, do CPU-only work and come back. Any GPU job you do start must be
interruptible: checkpoint often, write artifacts atomically (temp file + `os.replace`), and
be able to stop between replicates without leaving a half-written row. A truncated row that
later gets hashed as evidence is the exact failure mode this project studies.

## Step 1 — hardware, CONFIRMED 2026-08-25 (no longer an open question)

    $ nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
    NVIDIA RTX 6000 Ada Generation, 49140 MiB, 595.71.05   x4

**Four** RTX 6000 Ada cards, 48 GB each, ~192 GB total, driver 595.71.05.
Architecture is **Ada Lovelace, sm_89** — NOT Blackwell. An earlier note in this project said
GDDR7/Blackwell; that was wrong and is corrected here. Consequences:

- PyTorch **cu121 or cu124** both work. cu128 is unnecessary.
- `bitsandbytes` 8-bit optimizers are fully supported on sm_89, so the F2 optimizer ablation
  can run here as written.
- Four cards means contention is **per-GPU, not whole-box**. Pick a free one instead of waiting:

        CUDA_VISIBLE_DEVICES=2 .venv-train/bin/python train_native.py ...

  `train_native.py:141` hardcodes `device_map={"": 0}`, pinning physical GPU 0 — the card most
  likely to be contended, and the one a desktop session already touches. Either override it with
  `CUDA_VISIBLE_DEVICES` (which remaps the visible device to index 0) or make the device
  configurable. Do not silently train on whichever card someone else is using.

`CLAUDE.md` pins Ollama to `cuda_v12` because `cuda_v13` crashed on driver 591.86. That is a
**Windows** driver number; this box runs 595.71.05 on Linux. Re-derive that pin here rather than
carrying it over.

## Step 2 — get the repo by CLONE, never by copy

    gh auth login          # or set up a PAT; the repo is private
    git clone https://github.com/jonhhjackson-a11y/srlm-forge.git
    cd srlm-forge
    git checkout tool/test-run-dashboard

**Why clone and not rsync/scp/USB:** 243 of 251 committed blobs are already pure LF and all 251
index entries are mode 100644, so a clone lands clean. A file copy from the Windows or macOS
tree brings CRLF line endings and 0700 permissions with it, which breaks shebangs
(`bad interpreter: /usr/bin/env python3^M`) and poisons the file hashes the dataset gate
compares. One operational rule neutralises four separate portability findings.

Verify you got LF:

    git ls-files --eol forge.py data/dpo_pairs_capped.jsonl

## Step 3 — Python 3.12.10, exactly

The dataset gate compares the interpreter string by **exact equality**
(`dataset_gate.require_verified`, `if recorded != current`), and the committed receipt records
`python 3.12.10`. Ubuntu 24.04 ships **3.12.3**, which will FAIL the gate on a micro-version
mismatch. Get the exact build:

    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv python install 3.12.10
    uv venv --python 3.12.10 .venv-train
    .venv-train/bin/python -V        # must print 3.12.10

## Step 4 — the two blockers that stop `import forge` dead

These are confirmed, with file:line. Fix them before anything else runs.

1. **`dataset_gate.py:116`** hardcodes the Windows venv layout:
   `_VENV_PY = HERE / ".venv-train" / "Scripts" / "python.exe"`.
   On POSIX the interpreter is `.venv-train/bin/python`. `verify_py()` has NO fallback and
   raises SystemExit. `forge.py:130` calls it at MODULE scope (`VERIFY_PY = dataset_gate.verify_py()`),
   so this fires during `import forge`, before argparse, before `--help`. **19 tracked modules
   import forge** and all of them die. Same hardcoding appears at `venv_guard.py:35`,
   `export_adapter.py:53`, `sync_public.py:40`, `poscontrol/run_interleaved.py:31`,
   `tests/test_verifier_pin.py:39`, `tests/test_replicate_provenance.py:76`.
   Fix once, in one place, platform-aware; delete the copies.

2. **`dataset_gate.py:157-166`** — `interpreter_fingerprint()` catches `OSError` and also falls
   through on non-zero exit, recording the literal `python unknown`. That sentinel is a CONSTANT:
   two hosts with different interpreters both record it and **compare equal**, so the gate passes
   having established nothing. This is documented in the paper as Measurement-Integrity Failure 8.
   Make an unanswerable interpreter **fatal**, not silent.

## Step 5 — line endings, with a receipt

`.gitattributes` currently contains only `data/*.jsonl merge=union`. There is no `text`/`eol`
policy, so each clone's line endings depend on that machine's `core.autocrlf`. This is open
residual R-1 / M3, and the repo's own rule is **red witness before any fix, receipt after**.
The red witnesses are already captured at `docs/port-2026-08-24/RED-WITNESS-{A,B,C}.txt` — read
them rather than re-deriving.

The published digests are **CRLF-dialect**: six of the seven recorded in
`data/dataset_verification.json` equal `sha256(committed blob converted to CRLF)`. Do not
"fix" this by renormalising and regenerating — that silently invalidates every hash printed in
the paper. The intended repair is to hash a **declared canonical form** so the already-published
values stay valid. Decide this deliberately; it is a paper-visible change.

Also note: `git add --renormalize .` fixes only the INDEX. The worktree stays CRLF and the gate
hashes worktree bytes. Getting LF onto disk needs
`git ls-files -z | xargs -0 touch` and then `git checkout -- .`.

## Step 6 — the receipt is stale, independently of all the above

`data/dataset_verification.json` records `forge.py 13d52d9c…`, which matches **no** encoding of
the committed file at the revision the receipt itself was committed at. It is the hash of that
file as it stood 19 days earlier (`c0ffaa5`, 2026-08-03, vs the receipt's `f755dea`, 2026-08-22).
The verifier was deliberately changed and disclosed; the receipt was never regenerated. So the
gate refuses on Windows too — this is not something the port caused.

Regenerate the receipt **on this machine, under 3.12.10**, once steps 3-5 are done:

    .venv-train/bin/python verify_dataset.py

Quote its output. Do not summarise it, and do not claim the dataset is clean unless that run
just enforced it — repo rule, `CLAUDE.md`.

## Step 7 — dependencies

`requirements.txt` lists 11 bare names with no pins. Split it: the analysis/measurement scripts
need only `numpy`/`pyarrow`/`safetensors`/`huggingface_hub` and must import with **no torch
present**; training needs the CUDA lane from step 1. `unsloth` and `bitsandbytes` are the two
that will fight you — `bitsandbytes` is a hard requirement of `train_native.py:140-141,189` and
is **not declared in requirements.txt** at all.

## What NOT to do

- Do not `git commit` the line-ending change together with anything else. One atomic commit,
  two attribute paths, zero content files.
- Do not raise the batch size because 48-96 GB of VRAM is available. Effective batch size must
  stay identical to the original runs or the retrain is a different experiment wearing the same
  name.
- Do not run `overnight.ps1` logic by hand; it is PowerShell and has no Linux equivalent yet.
  Anything it drives needs writing fresh, with a clean-stop path (SIGTERM / a `council/STOP` file).
- Do not touch `poscontrol/retrain.log` or `retrain2.log`. They are CRLF in history AND cited as
  evidence in the manuscript (the 11 logged learning rates). Pin them `-text`.
- Do not push to `main`. Branch first — repo rule.

## Where the context lives

- `CLAUDE.md` — the rules that govern this repo. Read it first.
- `docs/port-2026-08-24/` — the three captured red witnesses.
- `docs/revision-2026-08-25/` — manuscript v4 through v9, each frozen with a revision note.
- `docs/review-2026-08-22/verification_report.md` — the referee findings and what is still unverified.
- `OPEN-ITEMS.md`, `HANDOFF-2026-08-22.md` — prior state. NOTE: the handoff's M2 recovery pointer
  says "the 4080 machine"; that is WRONG. The delivered 130-row file was on a machine whose user
  is `t` (`C:\Users\t\source\srlm-forge\`).

## Appendix: is someone else using the box?

`nvidia-smi` lists GPU processes by PID but not by owner, so it alone does not answer
"is one of the PhD students on this?". Cross-reference the PIDs against their owners:

    # who owns each GPU process
    nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader | \
      while IFS=, read -r pid mem; do
        pid=$(echo "$pid" | tr -d ' ')
        printf "%-10s %-12s %s\n" "$(ps -o user= -p "$pid" 2>/dev/null)" "$mem" \
          "$(ps -o comm= -p "$pid" 2>/dev/null)"
      done

Empty output means no compute processes are on the card.

    nvidia-smi                 # full view: memory used, utilisation %, process table
    who                        # who is logged in, on what tty/display, since when
    w                          # same plus what each session is running, and load average
    uptime                     # load average alone: >60 means the 60 cores are busy
    loginctl list-sessions     # systemd sessions, including RDP

Read the result with judgement, not just presence/absence:

- **GPU memory allocated but 0% utilisation** usually means a job is between phases,
  loading a checkpoint, or paused at a breakpoint. It is still someone's job. Do not
  start on the assumption that idle means free.
- **A logged-in user with no GPU process** may be about to start one. If `who` shows a
  PhD student active, ask before launching a long run.
- **Nobody logged in and no compute apps** is the only clear all-clear.

Policy reminder: PhD experiments take priority. If they need the card while your job is
running, stop it. That is why every GPU job here must checkpoint and be resumable — see
the etiquette section at the top of this file.
