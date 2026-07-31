"""The text-handling half of get_corpus.py, checked without touching the network.

The download itself is proven by running it; these are the transformations that
decide what the model actually sees, and they are the ones that quietly ruin a
corpus if they are wrong.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import get_corpus  # noqa: E402


def test_smart_punctuation_becomes_plain_ascii():
    """Every one of these is a distinct character to a character model: an
    embedding row and an output column spent on a curly quote."""
    dirty = "“Don’t,” she said—then left… café"
    clean = get_corpus.fold_to_ascii(dirty)
    assert clean == '"Don\'t," she said-then left... cafe', repr(clean)
    assert all(ord(c) < 127 for c in clean)


def test_folding_actually_shrinks_the_vocabulary():
    dirty = "".join(chr(c) for c in range(32, 700))
    before, after = len(set(dirty)), len(set(get_corpus.fold_to_ascii(dirty)))
    assert after < before, (before, after)
    assert after <= 96, f"ASCII printable + whitespace is 96 or fewer, got {after}"


def test_accents_are_decomposed_not_deleted():
    """cafe is a word; caf is not. Dropping the whole character loses the word."""
    assert get_corpus.fold_to_ascii("naïve résumé") == "naive resume"


def test_newlines_and_tabs_survive():
    """Paragraph structure is signal - it is how the model learns where a story
    ends."""
    assert get_corpus.fold_to_ascii("a\n\nb\tc") == "a\n\nb\tc"


def test_gutenberg_licence_block_is_stripped():
    """Left in, the licence is the single most repeated passage in the corpus and
    the model learns to recite it."""
    body = "Real story text here.\nMore of it.\n"
    raw = ("The Project Gutenberg eBook of Something\nlots of header\n"
           "*** START OF THE PROJECT GUTENBERG EBOOK SOMETHING ***\n"
           + body +
           "*** END OF THE PROJECT GUTENBERG EBOOK SOMETHING ***\n"
           "licence terms that must not be learned\n")
    out = get_corpus.strip_gutenberg(raw)
    assert out == body.strip(), repr(out)
    assert "licence terms" not in out
    assert "START OF" not in out


def test_stripping_a_file_with_no_markers_keeps_it():
    assert get_corpus.strip_gutenberg("just text") == "just text"


def test_every_source_is_described_and_reachable_by_name():
    for name, s in get_corpus.SOURCES.items():
        assert s["urls"], f"{name} has no urls"
        assert s["what"] and s["best_for"], f"{name} is undescribed"
        for u in s["urls"]:
            assert u.startswith("https://"), f"{name}: {u} is not https"


def test_the_recommended_source_is_the_one_built_for_small_models():
    """Not a preference: TinyStories exists specifically to show 1M-33M models
    can speak coherent English, and this project's models are 3M-19M."""
    s = get_corpus.SOURCES["stories"]
    assert "TinyStories" in s["what"]
    assert "2305.07759" in s["what"], "the citation for the claim is missing"


def test_the_default_size_is_justified_by_what_training_actually_reads():
    """44,100 steps x 32 x 128 = ~181M characters. A default far below that means
    repeats; far above means bytes that are never read."""
    reads = 44100 * 32 * 128
    default_chars = get_corpus.SOURCES["stories"]["default_mb"] * 1_000_000
    assert 0.5 * reads <= default_chars <= 2 * reads, (default_chars, reads)


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails.append(name); print(f"FAIL {name}: {e}")
    print(f"\n{len(fails)} failed")
    raise SystemExit(1 if fails else 0)
