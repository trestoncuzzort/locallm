"""Can this train on ANYTHING you have, or only on the three file types we guessed?

THE BUG. `start_studio.py` — the double-click path, the one aimed at people who
never open a terminal — filtered on a hardcoded `EXTS = {".txt", ".md", ".py"}`.
Drop a folder of `.csv`, `.jsonl` or `.log` into `training_data/` and it saw none
of them, then reported there was nothing to train on. That is the whole industrial
and commercial case silently excluded by a set literal.

RED WITNESS (five real files: sensor.csv, events.jsonl, run.log, notes.txt,
blob.bin), against the old rule:
    blob.bin      accepted=False
    events.jsonl  accepted=False      <- text, wrongly refused
    notes.txt     accepted=True
    run.log       accepted=False      <- text, wrongly refused
    sensor.csv    accepted=False      <- text, wrongly refused
Only 1 of 4 text files got in.

WHAT THIS FILE IS ALLOWED TO CLAIM, narrowed after review.
The claim shipped as "acceptance is decided on CONTENT" and that over-reaches.
`BINARY_EXTS` short-circuits on the file's NAME at is_trainable_file():87,
before a single byte is read, so a .bin holding pure text is still refused for
being called .bin. That check is deliberate — it is there to avoid reading
large media off disk — but it means the honest claim is narrower:

    AN UNKNOWN EXTENSION IS NEVER REFUSED FOR BEING UNKNOWN, AND THE DECISION
    LIVES IN EXACTLY ONE PLACE.

That is the claim these tests pin, and it is the one the industrial case needed
(.csv, .jsonl, .log, .tsv, no extension at all). The old wording is deleted
rather than softened.

SECOND RED WITNESS — the probe window.
`is_trainable_file` decides a whole-file property from the first 8192 bytes,
and that produced two separate refusals of ordinary text:

  1. A boundary that splits a multi-byte character made the probe undecodable
     while the file was valid UTF-8 throughout. 200 synthetic files per script,
     lengths 9-40 kB, alignment randomised:
         CJK (3-byte)      refused 100.0%  ->  0.0%
         Cyrillic (2-byte) refused  45.5%  ->  0.0%
         EU accented       refused  18.0%  ->  0.0%
         pure ASCII        refused   0.0%  ->  0.0%
     End to end, a 400-line Japanese machine log: refused as "content is not
     text (binary or undecodable)" before, ingested after.
  2. A NUL byte PAST the probe window passed the gate and reached the corpus.
     Same run: 3 NUL characters in the corpus before, 0 after, and the file is
     now reported as "content is not text past the first 8 kB".
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_corpus import (is_trainable_file, looks_like_text,  # noqa: E402
                         text_is_readable, trim_to_char_boundary)

SAMPLES = {
    "sensor.csv":   b"ts,machine,temp_c,status\n2026-07-30,PUMP-01,88.4,ALARM\n",
    "events.jsonl": b'{"ts":"2026-07-30","unit":"PUMP-01","event":"overtemp"}\n',
    "run.log":      b"[00:02:00] WARN PUMP-01 temperature 88.4C exceeds 85.0C\n",
    "readings.tsv": b"ts\tmachine\ttemp\n2026-07-30\tPUMP-01\t88.4\n",
    "config.yaml":  b"threshold_c: 85.0\nunits:\n  - PUMP-01\n",
    "query.sql":    b"SELECT unit, MAX(temp_c) FROM readings GROUP BY unit;\n",
    "notes.txt":    b"ordinary prose\n",
    "NOEXTENSION":  b"a file with no extension at all, still plain text\n",
}
BINARIES = {
    "blob.bin":   b"\x00\x01\x02BINARY\xff\xfe",
    "model.pt":   b"PK\x03\x04\x00\x00garbage",
    "photo.png":  b"\x89PNG\r\n\x1a\n\x00\x00\x00",
    "nul.dat":    b"looks texty until\x00 the NUL byte",   # unknown extension
}


def _write(tmp, name, data):
    p = pathlib.Path(tmp) / name
    p.write_bytes(data)
    return p


def test_text_files_are_accepted_whatever_they_are_called():
    """The industrial case: csv, jsonl, log, tsv, yaml, sql, and no extension."""
    with tempfile.TemporaryDirectory() as tmp:
        refused = []
        for name, data in SAMPLES.items():
            ok, why = is_trainable_file(_write(tmp, name, data))
            if not ok:
                refused.append(f"{name} ({why})")
        assert not refused, f"text files wrongly refused: {refused}"


def test_binaries_are_refused_on_content_not_just_extension():
    with tempfile.TemporaryDirectory() as tmp:
        admitted = []
        for name, data in BINARIES.items():
            ok, _ = is_trainable_file(_write(tmp, name, data))
            if ok:
                admitted.append(name)
        assert not admitted, f"binary files wrongly admitted: {admitted}"


def test_unknown_extension_binary_is_caught_by_its_bytes():
    """nul.dat is the case extension-filtering cannot get right in either
    direction: an unknown extension carrying a NUL byte. It must be refused
    because of what is inside it."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "nul.dat", BINARIES["nul.dat"])
        ok, why = is_trainable_file(p)
        assert not ok, "a NUL-bearing file was accepted as text"
        assert "not text" in why, f"refused for the wrong reason: {why}"


def test_looks_like_text_rejects_mojibake():
    """Undecodable bytes must be refused rather than mangled. `errors="ignore"`
    would turn them into junk characters, and in a character-level tokenizer junk
    characters become permanent vocabulary entries."""
    assert not looks_like_text(b"\xff\xfe\xfd\xfc\xfb\xfa")
    assert looks_like_text("temperature 88.4°C — within tolerance\n".encode("utf-8"))


def test_ext_filter_still_narrows_when_asked():
    """Content-based by default, but --ext must still restrict when a user wants
    only one kind of file."""
    with tempfile.TemporaryDirectory() as tmp:
        csv = _write(tmp, "sensor.csv", SAMPLES["sensor.csv"])
        log = _write(tmp, "run.log", SAMPLES["run.log"])
        assert is_trainable_file(csv, {".csv"})[0]
        ok, why = is_trainable_file(log, {".csv"})
        assert not ok and "--ext" in why, f"filter did not apply: {why}"


SCRIPTS = {
    "cjk":      "日本語のログ機械",
    "cyrillic": "привет мир",
    "eu":       "café naïve ",
    "ascii":    "plain ascii logline ",
}


def _straddling(pool: str, target: int = 12000) -> bytes:
    """Valid UTF-8 whose first 8192 bytes are NOT valid UTF-8.

    That is the exact condition the bug needed: the probe boundary falls inside
    a character. Returns b"" for a pool that cannot straddle (pure ASCII never
    can), so the caller can tell "checked and fine" from "not checkable".
    """
    for pad in range(4):
        raw = (" " * pad + (pool * (target // len(pool) + 1))[:target]).encode("utf-8")
        try:
            raw[:8192].decode("utf-8")
        except UnicodeDecodeError:
            return raw
    return b""


def test_multibyte_text_is_not_refused_for_straddling_the_probe_boundary():
    """The bug that refused 100% of CJK text files over 8 kB.

    `test_looks_like_text_rejects_mojibake` could not reach this: it passes a
    40-byte string, far below the 8192-byte probe, so the boundary it would
    have to split does not exist in that fixture.
    """
    with tempfile.TemporaryDirectory() as tmp:
        checked, refused = [], []
        for label, pool in SCRIPTS.items():
            raw = _straddling(pool)
            if not raw:
                continue                    # ASCII cannot straddle; nothing to test
            checked.append(label)
            p = _write(tmp, f"{label}.log", raw)
            ok, why = is_trainable_file(p)
            if not ok:
                refused.append(f"{label} ({why})")
        # Without this the test goes green by checking nothing the day the
        # helper stops producing straddling fixtures.
        assert checked, "no script produced a straddling fixture; the test is inert"
        assert not refused, (
            f"valid UTF-8 refused because the probe cut a character in half: "
            f"{refused} (checked: {checked})")


def test_trim_to_char_boundary_cuts_back_and_only_back():
    ok = "x" * 8191 + "é"
    raw = ok.encode("utf-8")                    # 8193 bytes; probe ends mid-char
    assert trim_to_char_boundary(raw[:8192]) == raw[:8191]
    # A probe that already ends on a boundary must not lose a byte.
    clean = b"x" * 8192
    assert trim_to_char_boundary(clean) == clean
    assert trim_to_char_boundary("é".encode("utf-8")) == "é".encode("utf-8")
    # Genuinely malformed bytes stay in, so the text rule can still refuse them.
    assert trim_to_char_boundary(b"\xff\xfe\xfd") == b"\xff\xfe\xfd"


def test_a_nul_past_the_probe_window_never_reaches_the_corpus():
    """A probe is a SAMPLE. It says nothing about byte 9000.

    In a character model the vocabulary IS the set of characters in the corpus,
    so three stray NULs are three permanent vocabulary entries.

    This runs make_corpus end to end on purpose. Asserting `text_is_readable`
    refuses the string only proves the RULE is right, and the bug was never in
    the rule -- it was that main() never applied it to the whole file. Written
    that way the test passed against the pre-fix code, which is a test that
    cannot fail for the reason it exists.
    """
    body = b"A" * 9000 + b"\x00\x00\x00" + b"B" * 100
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp) / "in"
        src.mkdir()
        (src / "nul_tail.log").write_bytes(body)
        (src / "notes.txt").write_bytes(b"ordinary prose\n")
        # The cheap gate accepts it, and that is what a probe is FOR -- it must
        # not read whole media files off disk to answer a listing question.
        assert is_trainable_file(src / "nul_tail.log")[0], \
            "fixture no longer exercises the probe window; the NUL moved inside it"

        out = pathlib.Path(tmp) / "corpus.txt"
        r = subprocess.run(
            [sys.executable, str(HERE / "make_corpus.py"),
             "--src", str(src), "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8")
        assert out.is_file(), f"make_corpus wrote no corpus: {r.stdout}{r.stderr}"
        corpus = out.read_text(encoding="utf-8")
    assert corpus.count("\x00") == 0, (
        f"{corpus.count(chr(0))} NUL character(s) reached the corpus and would "
        f"become permanent vocabulary entries")
    assert "ordinary prose" in corpus, "the control file did not make it in either"


def test_the_two_callers_share_one_rule():
    """start_studio's double-click path must actually find a .csv.

    This used to assert the string 'EXTS = {".txt"' was absent from the source.
    That is what it was: a search for one exact 15-character spelling. `EXTS = {'.txt'`, `EXTS={".txt"`, `ALLOWED = {...}`
    or a tuple would all have passed it. Behaviour is checked instead.
    """
    import start_studio
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "training_data"
        d.mkdir()
        (d / "sensor.csv").write_bytes(SAMPLES["sensor.csv"])
        (d / "photo.png").write_bytes(BINARIES["photo.png"])
        was = start_studio.DATA
        start_studio.DATA = d
        try:
            found = {p.name for p in start_studio.user_files()}
        finally:
            start_studio.DATA = was
    assert "sensor.csv" in found, f"the double-click path missed a .csv: {found}"
    assert "photo.png" not in found, f"a binary reached the training set: {found}"


def test_the_user_facing_prose_does_not_advertise_the_old_allowlist():
    """User-visible strings are claims too.

    The code will ingest a folder of .csv; the double-click path was still
    telling the user, twice, to supply .txt/.md/.py. A user reading that
    message concludes exactly what they concluded before the fix.

    Limit: this is a search for the one superseded phrasing that was actually
    there. A new way of writing the same wrong instruction is not caught.
    """
    src = (HERE / "start_studio.py").read_text(encoding="utf-8")
    assert ".txt/.md/.py" not in src, \
        "start_studio still tells the user only .txt/.md/.py files are wanted"


def test_corpus_is_not_ingested_into_itself():
    """Accepting files by content means `--src .` reaches corpus.txt. Folding the
    output back into the input doubles every document."""
    src = (HERE / "make_corpus.py").read_text(encoding="utf-8")
    assert "out_path" in src and "p.resolve() == out_path" in src, \
        "make_corpus does not exclude its own output file"


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
