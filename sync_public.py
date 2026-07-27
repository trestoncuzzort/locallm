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

# The product. Anything not listed here does not get published, ever.
PUBLISH = [
    "model.py", "data.py", "train.py", "generate.py", "make_corpus.py",
    "studio.py", "leakage.py", "bench_device.py", "test_detectors.py",
    "runlog.py",
    "exp_lr_width.py",
    "prereg_lr_width.json", "exp_lr_width_result.json",
    "prereg_lr_width_fast.json", "exp_lr_width_result_fast.json",
    "README.md", ".gitattributes",
]

# Files a published script may legitimately reference without shipping: things
# the user generates locally.
GENERATED_LOCALLY = {"corpus.txt", "ckpt.pt", "tokenizer.json",
                     "exp_lr_width_result_quick.json",
                     "bench_device_result.json",
                     "runs.jsonl"}

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
            m = PATTERN.search(line)
            if m:
                hits.append((name, i, f"{m.group(0)!r} in: {line.strip()[:90]}"))
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
            if mod not in published and mod not in GENERATED_LOCALLY                     and (SRC / mod).is_file():
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

    print(f"scanning {len(PUBLISH)} publish-listed files for internal references...")
    hits = scan()
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

    print("running the detector tests before publishing...")
    t = subprocess.run([sys.executable, str(SRC / "test_detectors.py")],
                       cwd=SRC, capture_output=True, text=True)
    if t.returncode != 0:
        print("\n!!! ABORT: test_detectors.py FAILED. NOTHING was published.\n")
        print(t.stdout[-2500:] or t.stderr[-2500:])
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
        shutil.copy2(SRC / name, CLONE / name)

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
