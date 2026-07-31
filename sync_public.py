#!/usr/bin/env python3
"""sync_public.py — publish the PRODUCT to the public GitHub repo, and nothing else.

Standing rule (proprietor, 2026-07-26): commit to GitHub after every iteration.
That rule plus a source repo containing the council channel and method-kit
pointers is a leak waiting to happen, so this script is the only sanctioned path
and it REFUSES rather than trusting anyone to remember.

    python sync_public.py                 # sync, commit, push
    python sync_public.py -m "message"    # with a commit message
    python sync_public.py --check         # scan + diff only, never writes or pushes
    python sync_public.py --no-push       # commit locally, don't push

Two hard guarantees:
  1. WHITELIST ONLY. Files not in PUBLISH are never copied. There is no
     "sync everything" mode and no glob over the repo root.
  2. FORBIDDEN-TERM ABORT. If any file about to be published mentions the
     council, the method kit, or this project's internals, the script STOPS and
     publishes nothing. It does not silently scrub, because silent scrubbing
     mangles meaning and hides the mistake.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "localllm"
REMOTE = "https://github.com/jonhhjackson-a11y/locallm"
CLONE = HERE.parent / "_locallm_publish"       # sibling of the repo, never inside it
CHANNEL = HERE / "instructions.txt"
STATE = HERE / "council" / "publish_state.json"
# The detector tests import torch; the system Python here is 3.14 and has none.
TEST_PYTHON = HERE / ".venv-train" / "Scripts" / "python.exe"

# The product. Anything not listed here does not get published, ever.
PUBLISH = [
    "model.py", "data.py", "train.py", "generate.py", "make_corpus.py",
    "studio.py", "leakage.py", "bench_device.py", "test_detectors.py",
    # checkpoint.py is REQUIRED, not optional: generate.py and studio.py both
    # import it, so omitting it publishes a repo whose two entry points fail on
    # `import checkpoint`. It exists because the GUI could previously only sample
    # a model it had trained in the same session (nothing loaded ckpt.pt), and
    # the fix had to live in one place rather than being copied into both callers.
    "checkpoint.py", "test_checkpoint.py", "test_ingest.py",
    # verify_claims.py re-derives the README's factual claims from the repo.
    # It has to SHIP: a claim-checker that only the author can run is a
    # promise, and the point of it is that a reader can settle the claims
    # without trusting anyone.
    "verify_claims.py",
    "runlog.py", "start_studio.py",
    "exp_lr_width.py",
    "prereg_lr_width.json", "exp_lr_width_result.json",
    "prereg_lr_width_fast.json", "exp_lr_width_result_fast.json",
    "README.md", "LICENSE", ".gitattributes", "requirements.txt",
    "Train My AI.bat", "training_data/README.txt",
]

# Files a published script may legitimately reference without shipping: things
# the user generates locally.
GENERATED_LOCALLY = {"corpus.txt", "ckpt.pt", "tokenizer.json",
                     "exp_lr_width_result_quick.json",
                     "bench_device_result.json",
                     "runs.jsonl", "training_data"}

# Anything internal. Word-boundary matched so ordinary English ("endpoint")
# cannot trip it, which a naive substring scan does.
FORBIDDEN = [
    # Third-party / family proprietary software and its author. These must never
    # leave this machine. Local files may mention them freely; this list is what
    # guarantees the PUBLIC repo cannot.
    r"moonwalker", r"starter[- ]kit", r"cuzzort", r"moonwalker[- ]?seat",
    r"council", r"asshole", r"proprietor",
    r"executor", r"srlm", r"directive", r"instructions\.txt", r"dpo_pairs",
    r"the phd", r"contrarian", r"expansionist", r"§",
]
PATTERN = re.compile("|".join(rf"\b{t}\b" if t[0].isalpha() else t
                              for t in FORBIDDEN), re.IGNORECASE)

# The ONE deliberate exception, and it is deliberately narrow. `cuzzort` is on the
# forbidden list because it is the method kit's author attribution, which must
# never ship. But the proprietor is also the copyright holder of THIS product and
# asked (2026-07-28) for an MIT licence in his own name — publishing your own name
# on your own licence is the opposite of a leak.
#
# So: the surname is allowed ONLY on a copyright line. Not anywhere else, not in
# any other file, and every other forbidden term still aborts even on these lines.
# A blanket "skip LICENSE" rule would have let the whole list through in that file.
ALLOW_COPYRIGHT_NAME = re.compile(
    r"^\s*(#\s*)?(MIT\b.*)?Copyright \(c\) \d{4} Treston Malachi Cuzzort\.?\s*$",
    re.IGNORECASE)
# The README states the licence in prose rather than as a bare copyright line.
ALLOW_LICENCE_PROSE = re.compile(
    r"^\s*MIT\s*.\s*see \[LICENSE\]\(LICENSE\)\. Copyright \(c\) \d{4} "
    r"Treston Malachi Cuzzort\.\s*$", re.IGNORECASE)


# --- SECOND PUBLISHED TRACK: the DPO pipeline, into dpo/ --------------------
# Published 2026-07-28 by proprietor decision. Mapping is {source -> path under
# dpo/} so the public README can be a separate file from this repo's own.
DPO_SRC = HERE
DPO_DEST = "dpo"
DPO_PUBLISH = {
    "publish/dpo_README.md": "README.md",
    "forge.py": "forge.py",
    "verify_dataset.py": "verify_dataset.py",
    "test_gate_coverage.py": "test_gate_coverage.py",
    "dataset_gate.py": "dataset_gate.py",
    "clean_dataset.py": "clean_dataset.py",
    "build_training_set.py": "build_training_set.py",
    "train_native.py": "train_native.py",
    "train_dpo.py": "train_dpo.py",
    "export_adapter.py": "export_adapter.py",
    "eval.py": "eval.py",
    "repair.py": "repair.py",
    "measure.py": "measure.py",
    "config.py": "config.py",
    # The claim-checker ships under the name the published layout expects.
    "verify_dpo_claims.py": "verify_claims.py",
    "data/dpo_pairs.jsonl": "data/dpo_pairs.jsonl",
    "data/dpo_pairs_capped.jsonl": "data/dpo_pairs_capped.jsonl",
    "data/repair_pairs.jsonl": "data/repair_pairs.jsonl",
    "data/known_hard.json": "data/known_hard.json",
    "data/dataset_verification.json": "data/dataset_verification.json",
    "data/smoke_rpo_alpha_result.json": "data/smoke_rpo_alpha_result.json",
    "data/export_acceptance_result.json": "data/export_acceptance_result.json",
}

# The DPO track carries a DIFFERENT forbidden list, and the difference is the
# whole point. `srlm` and `dpo_pairs` are forbidden in the product track because
# mentioning them there would leak the existence of this pipeline; here they ARE
# the product, so they are fine. Everything belonging to the family's licensed
# method still aborts, because that is what must never ship — and it would leak
# without ever printing its own name, which is why the seat vocabulary is listed.
DPO_FORBIDDEN = [
    r"moonwalker", r"starter[- ]kit", r"cuzzort", r"moonwalker[- ]?seat",
    r"council", r"asshole", r"proprietor", r"executor", r"directive",
    r"instructions\.txt", r"the phd", r"contrarian", r"expansionist", r"§",
]
DPO_PATTERN = re.compile("|".join(rf"\b{t}\b" if t[0].isalpha() else t
                                  for t in DPO_FORBIDDEN), re.IGNORECASE)


def _permitted_copyright_line(line: str, match: str) -> bool:
    """True only for the copyright-holder's own name on a copyright line."""
    if match.lower() != "cuzzort":
        return False
    return bool(ALLOW_COPYRIGHT_NAME.match(line) or ALLOW_LICENCE_PROSE.match(line))


def directive_sha() -> str:
    """Hash of the DIRECTIVE block, which is what the council actually reads."""
    text = CHANNEL.read_text(encoding="utf-8", errors="ignore")
    try:
        start = text.index("DIRECTIVE (executor -> council")
        end = text.index("\n---", start)
    except ValueError:
        return ""
    return hashlib.sha1(text[start:end].encode("utf-8")).hexdigest()


def run(cmd, cwd, check=True, quiet=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if not quiet and r.stdout.strip():
        print(r.stdout.rstrip())
    if check and r.returncode != 0:
        print(r.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(f"FAILED: {' '.join(cmd)}")
    return r


def scan() -> list[tuple[str, int, str]]:
    """Every forbidden mention in the files we are about to publish."""
    hits = []
    for name in PUBLISH:
        p = SRC / name
        if not p.is_file():
            raise SystemExit(f"ABORT: {name} is on the publish list but missing from {SRC}")
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for m in PATTERN.finditer(line):
                # finditer, not search: a line is only exempt for the copyright
                # name itself. If it ALSO mentions any other forbidden term, that
                # second match still aborts the publish.
                if _permitted_copyright_line(line, m.group(0)):
                    continue
                hits.append((name, i, f"{m.group(0)!r} in: {line.strip()[:90]}"))
    return hits


def scan_dpo() -> list[tuple[str, int, str]]:
    """Same refusal, applied to the DPO track with its own forbidden list."""
    hits = []
    for src in DPO_PUBLISH:
        p = DPO_SRC / src
        if not p.is_file():
            raise SystemExit(f"ABORT: {src} is on the DPO publish list but missing")
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for m in DPO_PATTERN.finditer(line):
                if _permitted_copyright_line(line, m.group(0)):
                    continue
                hits.append((src, i, f"{m.group(0)!r} in: {line.strip()[:90]}"))
    return hits


def dangling_references() -> list[tuple[str, str]]:
    """Find sibling files a published file names but that we do not publish.

    The whitelist is safe against leaking, and silently unsafe against
    OMISSION: adding a feature whose data file is not on the list ships code
    that crashes on a fresh clone. That is exactly how --profile fast went out
    with its preregistration left behind. Catch it here rather than in a bug
    report.
    """
    ref = re.compile(r"[\"']([A-Za-z0-9_.-]+\.(?:json|txt|py))[\"']")
    # Bare imports matter as much as quoted filenames: `import runlog` slipped
    # past the first version of this guard and shipped a module that only
    # existed on the author's disk. A local sibling module that is imported but
    # not published is the same bug as a data file that is named but not
    # published.
    imp = re.compile(r"^\s*(?:import\s+([A-Za-z_][\w]*)|from\s+([A-Za-z_][\w]*)\s+import)",
                     re.MULTILINE)
    published = set(PUBLISH)
    missing = []
    for name in PUBLISH:
        if not name.endswith(".py"):
            continue
        body = (SRC / name).read_text(encoding="utf-8", errors="ignore")
        for a, b in imp.findall(body):
            mod = (a or b) + ".py"
            if (mod not in published and mod not in GENERATED_LOCALLY
                    and (SRC / mod).is_file()):
                missing.append((name, mod))
        for hit in ref.findall(body):
            if hit in published or hit in GENERATED_LOCALLY:
                continue
            if (SRC / hit).is_file():          # exists locally but is not shipped
                missing.append((name, hit))
    return missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", default="")
    ap.add_argument("--check", action="store_true", help="scan and diff only")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    # Publishing without telling the council is how work goes unseen. If the
    # DIRECTIVE has not moved since the last publish, last round's follow-up
    # never happened.
    prev = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {}
    if prev.get("directive_sha") and prev["directive_sha"] == directive_sha():
        print("!" * 68)
        print("WARNING: the DIRECTIVE block has not changed since the last publish")
        print(f"         ({prev.get('commit', '?')}). The council was never told about")
        print("         that work, so it cannot see it. Update the DIRECTIVE at the")
        print("         top of instructions.txt before or right after this push.")
        print("!" * 68)
        print()

    print(f"scanning {len(PUBLISH)} product + {len(DPO_PUBLISH)} DPO files "
          f"for internal references...")
    hits = scan() + scan_dpo()
    if hits:
        print("\n!!! ABORT: internal references found. NOTHING was published.\n")
        for name, ln, detail in hits:
            print(f"  {name}:{ln}  {detail}")
        print("\nRemove these from the product files (the channel is where project")
        print("history belongs), then run again.")
        raise SystemExit(1)
    print("  clean.\n")

    dangling = dangling_references()
    if dangling:
        print("!!! ABORT: a published file references something not on the publish")
        print("    list. It exists here, so it works locally and would crash on a")
        print("    fresh clone. NOTHING was published.\n")
        for src_file, ref in dangling:
            print(f"  {src_file} references {ref}")
        print("\nAdd it to PUBLISH, or to GENERATED_LOCALLY if the user creates it.")
        raise SystemExit(1)

    # The tests import torch, so they must run under the TRAINING venv, not
    # whatever interpreter launched this script. sys.executable here is normally
    # the system Python 3.14, which has no torch — that made the gate abort with
    # ModuleNotFoundError on every publish, blocking the repo for environment
    # reasons rather than test failures. Pick the interpreter deliberately.
    test_py = TEST_PYTHON if TEST_PYTHON.exists() else Path(sys.executable)

    # Gate-coverage runs on the DPO track and needs no torch, so the system
    # interpreter is fine. It fails if any module reads training data without
    # going through dataset_gate.load_verified.
    g = subprocess.run([sys.executable, str(HERE / "test_gate_coverage.py")],
                       cwd=HERE, capture_output=True, text=True)
    print(f"gate coverage: {g.stdout.strip().splitlines()[-1] if g.stdout.strip() else '?'}")
    if g.returncode != 0:
        print("\n!!! ABORT: gate coverage FAILED. NOTHING was published.\n")
        print(g.stdout[-2000:] or g.stderr[-2000:])
        raise SystemExit(1)

    print(f"running the detector tests before publishing...  ({test_py.name})")
    t = subprocess.run([str(test_py), str(SRC / "test_detectors.py")],
                       cwd=SRC, capture_output=True, text=True)
    if t.returncode != 0:
        out = t.stdout[-2500:] or t.stderr[-2500:]
        print("\n!!! ABORT: test_detectors.py FAILED. NOTHING was published.\n")
        if "No module named" in (t.stderr or ""):
            print(f"    This is an ENVIRONMENT failure, not a test failure.\n"
                  f"    Ran under: {test_py}\n"
                  f"    The detector tests need torch. Expected interpreter:\n"
                  f"      {TEST_PYTHON}\n")
        print(out)
        raise SystemExit(1)
    print("  tests pass.\n")

    if not CLONE.exists():
        print(f"cloning {REMOTE} -> {CLONE}")
        run(["git", "clone", REMOTE, str(CLONE)], cwd=HERE.parent)
    else:
        # Always rebase onto the remote first: the repo owner edits on GitHub,
        # and this must never clobber that.
        run(["git", "fetch", "origin", "main"], cwd=CLONE, quiet=True)
        run(["git", "reset", "--hard", "origin/main"], cwd=CLONE, quiet=True)

    for name in PUBLISH:
        dest = CLONE / name
        dest.parent.mkdir(parents=True, exist_ok=True)   # PUBLISH may contain paths
        shutil.copy2(SRC / name, dest)

    for src, rel in DPO_PUBLISH.items():
        dest = CLONE / DPO_DEST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DPO_SRC / src, dest)

    status = run(["git", "status", "--porcelain"], cwd=CLONE, quiet=True).stdout.strip()
    if not status:
        print("no product changes since the last sync. Nothing to commit.")
        return
    print("changes to publish:")
    print(status)

    if args.check:
        print("\n--check: nothing written, nothing pushed.")
        return

    msg = args.message or "sync product from local development"
    run(["git", "add", "-A"], cwd=CLONE, quiet=True)
    run(["git", "commit", "-m", msg], cwd=CLONE, quiet=True)
    print(f"\ncommitted: {msg}")

    if args.no_push:
        print("--no-push: stopping before push.")
        return
    run(["git", "push", "origin", "main"], cwd=CLONE)
    head = run(["git", "log", "--oneline", "-1"], cwd=CLONE, quiet=True).stdout.strip()
    print(f"pushed to {REMOTE}\n  {head}")


if __name__ == "__main__":
    main()
