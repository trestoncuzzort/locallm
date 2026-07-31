"""start_studio.py — the double-click entry point.

Rebuilds the corpus from training_data/ if you have put anything there, then
opens the studio. This is what the Desktop shortcut runs.

Kept deliberately small and defensive: it is the one file a non-technical user
ends up depending on, so every failure here has to explain itself rather than
vanish into a console that closes instantly.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
DATA = HERE / "training_data"
CORPUS = HERE / "corpus.txt"

from make_corpus import is_trainable_file  # noqa: E402


def user_files() -> list[Path]:
    """Every file here that a character model can actually read.

    This used to filter on a hardcoded {".txt", ".md", ".py"}. That made the
    double-click path — the one for people who never open a terminal — silently
    ignore a folder full of .csv, .jsonl or .log files and then announce there
    was nothing to train on. The decision now comes from make_corpus, is made on
    CONTENT rather than extension, and lives in exactly one place.
    """
    if not DATA.is_dir():
        return []
    return [p for p in sorted(DATA.rglob("*"))
            if is_trainable_file(p)[0] and p.name.lower() != "readme.txt"]


def main() -> int:
    py = sys.executable
    files = user_files()

    if files:
        total = sum(p.stat().st_size for p in files)
        print(f"Found {len(files)} file(s) in training_data ({total:,} bytes).")
        print("Rebuilding the corpus from your text...\n")
        r = subprocess.run([py, str(HERE / "make_corpus.py"),
                            "--src", str(DATA), "--out", str(CORPUS)],
                           cwd=HERE)
        if r.returncode != 0:
            print("\nCould not build a corpus from training_data.")
            print("The studio will open with whatever corpus was there before.")
    elif CORPUS.is_file():
        print("training_data is empty, so the existing corpus will be used.")
        print(f"To train on your own writing, put .txt/.md/.py files in:\n  {DATA}\n")
    else:
        print("No training data and no corpus yet.")
        print(f"Put some .txt/.md/.py files in:\n  {DATA}\nthen run this again.")
        input("\nPress Enter to close...")
        return 1

    if CORPUS.is_file():
        try:
            sys.path.insert(0, str(HERE))
            from data import documents, split_health
            text = CORPUS.read_text(encoding="utf-8", errors="ignore")
            docs = len(documents(text))
            h = split_health(text)
            print(f"corpus: {len(text):,} characters, {docs} document(s), "
                  f"{len(set(text))} distinct characters")
            if h["val_chars"] == 0 or h["achieved_val_frac"] < h["achievable_val_frac"]:
                print(f"  NOTE: {h['unique_documents']} unique document(s), largest is "
                      f"{h['largest_unique_doc_frac']:.0%} of them. Validation loss")
                print("  will not mean much until there are more, smaller files.")
                print("  Judge runs on TRAINING loss for now.")
        except Exception:                        # noqa: BLE001
            pass                                 # never block the studio on a summary

    print("\nOpening the studio...")
    subprocess.Popen([py.replace("python.exe", "pythonw.exe"),
                      str(HERE / "studio.py")], cwd=HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
