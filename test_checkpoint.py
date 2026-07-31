"""Can a trained model be sampled after the session that trained it ended?

THE BUG. studio.py assigned `self.model` in exactly one place — the "done"
message at the end of a training run — and created the Sample button with
`state="disabled"`, re-enabling it only from that same handler. Nothing loaded
`<out>/ckpt.pt`. So the model on disk was unreachable from a fresh GUI: the
button stayed greyed, and `_generate` opened with `if self.model is None: return`,
which is silent. Reported as "when I sample the AI it won't talk back after
training."

RED WITNESS (source-level, because Tk needs a window station this shell has not
got — see the pre-fix file in git):
    git show <pre-fix>:localllm/studio.py | grep -A2 "def _generate"
        def _generate(self):
            if self.model is None:
                return
    grep -c "load_checkpoint\|_load_saved" studio.py   ->  0

These tests are the executable half: the load-from-disk path now exists, round
trips, and produces text. They do NOT drive the GUI — they cover the logic the
GUI delegates to, plus source-level assertions that the silent return is gone.
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import checkpoint  # noqa: E402

OUT = HERE / "out_gui"
STUDIO = (HERE / "studio.py").read_text(encoding="utf-8")


def test_checkpoint_exists_needs_both_files():
    assert checkpoint.checkpoint_exists(OUT), f"no trained model in {OUT}"
    assert not checkpoint.checkpoint_exists(HERE / "definitely_not_a_dir")


def test_load_and_sample_round_trips():
    """The capability that did not exist: load a model trained earlier and get
    text out of it."""
    model, tok, cfg = checkpoint.load_checkpoint(OUT)
    assert cfg.vocab_size == len(tok.chars), "tokenizer/model vocab disagree"
    text = checkpoint.sample(model, tok, "def ", tokens=40, temperature=0.8, top_k=40)
    assert isinstance(text, str) and len(text) > 10, f"sampled nothing: {text!r}"
    assert text.startswith("def "), f"prompt not echoed into the sample: {text[:40]!r}"


def test_empty_prompt_still_produces_text():
    """An empty prompt encodes to nothing, and generating from an empty tensor is
    an error rather than an empty answer. Both callers used to handle this with
    their own `or [0]`; now one does."""
    model, tok, _ = checkpoint.load_checkpoint(OUT)
    assert len(checkpoint.sample(model, tok, "", tokens=20)) > 0


def test_prompt_of_unknown_characters_does_not_crash():
    """A char-level tokenizer built from this corpus has ~97 characters. A prompt
    made entirely of characters outside it encodes to nothing — the same empty
    path, reachable from the GUI's prompt box by typing an emoji."""
    model, tok, _ = checkpoint.load_checkpoint(OUT)
    assert len(checkpoint.sample(model, tok, "你好\U0001f600", tokens=20)) > 0


def test_missing_checkpoint_names_the_directory():
    """Failing silently is what caused the report. A missing model must say which
    directory it looked in."""
    try:
        checkpoint.load_checkpoint(HERE / "no_such_out")
    except FileNotFoundError as e:
        assert "no_such_out" in str(e), f"error does not name the directory: {e}"
    else:
        raise AssertionError("loading a missing checkpoint did not raise")


def test_studio_has_no_silent_return_on_missing_model():
    """The exact line that produced the symptom."""
    assert "if self.model is None:\n            return" not in STUDIO, \
        "studio._generate still returns silently when no model is loaded"


def test_studio_can_load_from_disk():
    assert "_load_saved" in STUDIO, "studio has no load-from-disk path"
    assert "checkpoint.load_checkpoint" in STUDIO, \
        "studio does not use the shared loader"


def test_studio_and_cli_share_one_sampler():
    """generate.py and the GUI must not drift apart — the parent repo has paid
    for duplicated helpers before (venv_guard.py)."""
    gen = (HERE / "generate.py").read_text(encoding="utf-8")
    assert "checkpoint.sample" in gen, "generate.py does not use the shared sampler"
    assert "checkpoint.sample" in STUDIO, "studio.py does not use the shared sampler"
    assert "model.generate(idx" not in STUDIO, \
        "studio.py still has its own copy of the sampling loop"


def test_cli_still_works():
    """Regression: the refactor must not break the documented CLI."""
    p = subprocess.run([sys.executable, str(HERE / "generate.py"),
                        "--out", "out_gui", "--prompt", "def ", "--tokens", "30"],
                       capture_output=True, text=True, timeout=600, cwd=str(HERE))
    assert p.returncode == 0, f"generate.py failed: {p.stderr[-400:]}"
    assert len(p.stdout.strip()) > 10, f"generate.py printed nothing: {p.stdout!r}"


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
