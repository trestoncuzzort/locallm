"""make_corpus.py — build a training corpus out of your own files.

Point it at a folder. It concatenates every matching text file into corpus.txt,
which is what train.py and studio.py learn from. Nothing is downloaded and
nothing leaves your machine.

    python make_corpus.py --src "C:/my/writing"
    python make_corpus.py --src ./notes --ext .md .txt
    python make_corpus.py --src . --ext .py            # train on code

Your corpus IS your vocabulary — the tokenizer is built from exactly the
characters in these files (see data.py).
"""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_EXTS = [".txt", ".md", ".py"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".", help="folder to read (recursively)")
    ap.add_argument("--ext", nargs="+", default=DEFAULT_EXTS,
                    help=f"file extensions to include (default: {' '.join(DEFAULT_EXTS)})")
    ap.add_argument("--out", default="corpus.txt")
    ap.add_argument("--min-chars", type=int, default=1,
                    help="skip files shorter than this")
    args = ap.parse_args()

    src = Path(args.src).expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"not a folder: {src}")
    exts = {e if e.startswith(".") else "." + e for e in args.ext}

    parts, skipped = [], 0
    seen: set[str] = set()
    for p in sorted(src.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if any(seg in {".git", "__pycache__", ".venv", "node_modules"}
               for seg in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(text) < args.min_chars:
            continue
        # Exact-duplicate files add nothing but memorisation pressure.
        if text in seen:
            skipped += 1
            continue
        seen.add(text)
        parts.append(f"# file: {p.relative_to(src).as_posix()}\n{text}")

    if not parts:
        raise SystemExit(f"no files matching {sorted(exts)} under {src}")

    out = Path(args.out)
    body = "\n\n".join(parts)
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out}: {len(body):,} chars from {len(parts)} files "
          f"({len(set(body))} distinct characters -> that is your vocab size)")
    if skipped:
        print(f"skipped {skipped} exact-duplicate file(s)")


if __name__ == "__main__":
    main()
