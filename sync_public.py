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
    "studio.py", "leakage.py", "exp_lr_width.py", "prereg_lr_width.json",
    "exp_lr_width_result.json", "README.md", ".gitattributes",
]

# Anything internal. Word-boundary matched so ordinary English ("endpoint")
# cannot trip it, which a naive substring scan does.
FORBIDDEN = [
    r"council", r"moonwalker", r"starter[- ]kit", r"asshole", r"proprietor",
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
