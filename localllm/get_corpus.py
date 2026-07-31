#!/usr/bin/env python3
"""get_corpus.py — fetch text that a SMALL model can actually learn to write.

THE PROBLEM THIS FIXES. The shipped corpus.txt was 549,023 characters of this
repository's own Python source: 13 files, 97 distinct characters, one narrow
domain. A 3.18M-parameter character model trained on that can only ever produce
something that looks like Python and is not Python. No architecture change fixes
a corpus that small and that narrow - it was a benchmark fixture, not training
data, and it made the whole tool look like a toy.

WHAT TO TRAIN A SMALL MODEL ON, and why this is not a guess. Eldan & Li (2023),
"TinyStories: How Small Can Language Models Be and Still Speak Coherent English?"
(arXiv 2305.07759) built a corpus of simple short stories using only words a
3-4 year old knows, specifically to show that models of 1M-33M parameters produce
FLUENT, COHERENT English when the text is simple enough. This project's models
are 3.18M (Medium) and 18.9M (Large). That is the exact range the paper is about,
which makes TinyStories the single highest-leverage change available here.

HOW MUCH TO DOWNLOAD, computed rather than guessed. Training reads
    steps x batch_size x block_size
characters in total. The GUI's "Normal" preset on Medium is 44,100 steps at
32 x 128, which is ~181 million characters. Anything past that is never seen even
once in a single pass. The full TinyStories train file is 1.92 GB, so the default
here takes the first 200 MB at a story boundary: enough that nothing repeats,
without a two-gigabyte download that cannot be reached. Ask for more with --mb if
you intend to train for much longer.

VOCABULARY IS CAPACITY. In a character model every distinct character costs an
embedding row and an output column, and rare glyphs cannot be learned from a
handful of examples. Raw web-ish text carries smart quotes, em dashes and stray
accents that add vocabulary and teach nothing, so by default the text is folded
to plain ASCII with a small explicit mapping. That is a real quality lever, not
tidiness: it moves capacity from glyphs nobody needs to letters everybody does.

    python get_corpus.py stories            # simple English, best for small models
    python get_corpus.py books              # public-domain classics, richer prose
    python get_corpus.py stories --mb 500   # more, if you will train longer

Nothing here downloads WEIGHTS. The model is always built from random init on
this machine; this fetches plain text only, and every source is public domain or
openly licensed.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "corpora"
UA = {"User-Agent": "Mozilla/5.0 (localllm get_corpus.py)"}

# Characters that carry no information a character model needs, mapped to the
# plain equivalent. Everything not in the surviving set is dropped.
FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "―": "-", "−": "-",
    "…": "...", " ": " ", "•": "*", "·": "*",
    "′": "'", "″": '"', "﻿": "",
}

SOURCES = {
    "stories": dict(
        urls=["https://huggingface.co/datasets/roneneldan/TinyStories/"
              "resolve/main/TinyStories-train.txt"],
        default_mb=200,
        sep="",
        what="TinyStories (Eldan & Li 2023, arXiv 2305.07759) - short stories "
             "written with a small vocabulary, built so that models of 1M-33M "
             "parameters can speak coherent English. CDLA-Sharing-1.0.",
        best_for="Simple, fluent English sentences. The best choice for a small "
                 "model, and the only one likely to produce genuinely readable "
                 "output at 3M parameters."),
    "books": dict(
        # Public-domain classics from Project Gutenberg. A fixed, named list, so
        # what you trained on is reproducible rather than "whatever was popular".
        urls=[f"https://www.gutenberg.org/cache/epub/{i}/pg{i}.txt" for i in
              (11, 1342, 84, 1661, 74, 2701, 98, 345, 1080, 5200,
               76, 2542, 174, 43, 1400, 120, 16, 35, 36, 219)],
        default_mb=0,          # take all of them; the whole set is ~40 MB
        sep="\n\n",
        what="20 public-domain books from Project Gutenberg (Alice, Pride and "
             "Prejudice, Frankenstein, Sherlock Holmes, Moby Dick, Dracula, "
             "Great Expectations, Ulysses and more).",
        best_for="Richer, more varied prose. Harder for a small model - expect "
                 "convincing-looking sentences that wander. Better once you "
                 "train Large for a while."),
}


def fold_to_ascii(text: str) -> str:
    for bad, good in FOLD.items():
        text = text.replace(bad, good)
    # Decompose accents (café -> cafe) rather than dropping the whole word.
    text = unicodedata.normalize("NFKD", text)
    keep = []
    for ch in text:
        if ch in "\n\t" or (32 <= ord(ch) < 127):
            keep.append(ch)
        elif ch.isspace():
            keep.append(" ")
    return "".join(keep)


def strip_gutenberg(text: str) -> str:
    """Drop the licence header and footer, which are identical in every book.

    Left in, they are the single most repeated passage in the corpus and the
    model would learn to recite Project Gutenberg's terms of use, which is a
    real failure mode and an easy one to avoid.
    """
    start = text.find("*** START OF")
    if start != -1:
        start = text.find("\n", start)
        text = text[start + 1:]
    end = text.find("*** END OF")
    if end != -1:
        text = text[:end]
    return text.strip()


def download(url: str, dest: Path, limit_bytes: int) -> Path:
    """Stream to disk, stopping at limit_bytes (0 = no limit). Resumable-ish:
    an already-complete cached file is reused rather than fetched again."""
    if dest.exists() and dest.stat().st_size > 0:
        if not limit_bytes or dest.stat().st_size >= limit_bytes * 0.98:
            print(f"  cached  {dest.name}  ({dest.stat().st_size / 1e6:.1f} MB)")
            return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    # Generous, because on some links the TLS handshake to the file host takes
    # minutes while the transfer itself then runs at several MB/s. Measured on
    # this machine: 169s to connect to huggingface.co, then 4.36 MB/s. A 60s
    # timeout kills the download during the handshake and looks like "no
    # internet", which is the wrong diagnosis and the wrong fix.
    with urllib.request.urlopen(req, timeout=420) as r, tmp.open("wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        target = min(total, limit_bytes) if (total and limit_bytes) else (limit_bytes or total)
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            if limit_bytes and got + len(chunk) > limit_bytes:
                chunk = chunk[:limit_bytes - got]
            f.write(chunk)
            got += len(chunk)
            if target:
                pct = 100 * got / target
                speed = got / max(time.time() - t0, 1e-9) / 1e6
                print(f"\r  {dest.name}: {got/1e6:8.1f} / {target/1e6:.1f} MB "
                      f"({pct:5.1f}%)  {speed:5.1f} MB/s", end="", flush=True)
            if limit_bytes and got >= limit_bytes:
                break
    print()
    tmp.replace(dest)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Download text worth training a small model on.")
    ap.add_argument("source", choices=sorted(SOURCES), nargs="?", default="stories")
    ap.add_argument("--mb", type=int, default=None,
                    help="how many megabytes to keep (0 = everything available)")
    ap.add_argument("--out", default=str(HERE / "corpus.txt"))
    ap.add_argument("--keep-unicode", action="store_true",
                    help="do NOT fold to ASCII (bigger vocabulary, worse model)")
    ap.add_argument("--list", action="store_true", help="describe the sources and exit")
    args = ap.parse_args()

    if args.list:
        for name, s in SOURCES.items():
            print(f"\n{name}\n  {s['what']}\n  Best for: {s['best_for']}")
        return

    src = SOURCES[args.source]
    mb = src["default_mb"] if args.mb is None else args.mb
    limit = mb * 1_000_000
    CACHE.mkdir(exist_ok=True)

    print(f"source : {args.source}")
    print(f"         {src['what']}")
    print(f"target : {'everything available' if not limit else f'{mb} MB'}")
    print()

    parts, per_url_limit = [], (limit // len(src["urls"]) if limit else 0)
    for url in src["urls"]:
        name = url.rstrip("/").split("/")[-1]
        try:
            p = download(url, CACHE / name,
                         limit if len(src["urls"]) == 1 else per_url_limit)
        except Exception as e:                       # noqa: BLE001
            print(f"  SKIPPED {name}: {e.__class__.__name__}: {e}")
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        if "gutenberg" in url:
            raw = strip_gutenberg(raw)
        parts.append(raw)

    if not parts:
        raise SystemExit("nothing downloaded - check your internet connection")

    text = src["sep"].join(parts)
    before_vocab = len(set(text))
    if not args.keep_unicode:
        text = fold_to_ascii(text)

    # Never cut mid-word: back up to the last blank line so the final document
    # ends where a document actually ends.
    if limit and len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        text = text[:cut if cut > limit // 2 else limit]

    out = Path(args.out)
    if out.exists():
        backup = out.with_suffix(".previous.txt")
        shutil.copy2(out, backup)
        print(f"\nkept your old corpus as {backup.name}")
    out.write_text(text, encoding="utf-8")

    vocab = sorted(set(text))
    print(f"\nwrote {out}")
    print(f"  {len(text):,} characters")
    print(f"  {len(vocab)} distinct characters (was {before_vocab} before folding)")
    print(f"  vocabulary: {''.join(c for c in vocab if c.isprintable())[:96]}")
    reads = 44100 * 32 * 128
    print(f"\nThe GUI's Normal preset reads about {reads/1e6:.0f}M characters while "
          f"training,\nso this corpus is seen about {len(text)/reads:.2f} times in a "
          f"full run.")
    if len(text) < reads * 0.2:
        print("  NOTE: that is several passes over the same text, which invites "
              "memorising.\n  Consider --mb larger.")


if __name__ == "__main__":
    main()
