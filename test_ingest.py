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
Only 1 of 4 text files got in, and the binary was excluded for the wrong reason:
its extension, not its bytes.

The rule is now content-based and lives in one place. These tests pin that: text
gets in whatever it is called, binary stays out whatever it is called, and the two
callers cannot drift apart again.
"""
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_corpus import is_trainable_file, looks_like_text  # noqa: E402

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


def test_the_two_callers_share_one_rule():
    """start_studio.py must not regrow its own extension list."""
    src = (HERE / "start_studio.py").read_text(encoding="utf-8")
    assert "is_trainable_file" in src, "start_studio does not use the shared rule"
    assert 'EXTS = {".txt"' not in src, \
        "start_studio has its own hardcoded extension set again"


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
