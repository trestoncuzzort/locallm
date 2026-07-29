"""Pins the training-input seam: what the trainer sees == what the sampler saw.

THE CLASS THIS CLOSES. Council section 62 finding 2 found that train_native.py
optimised a prompt with no system turn, against targets whose code fences had
been stripped, while forge.Actor.generate sampled every pair WITH the system
turn and eval.py scored WITH it. Nothing in the repo could see it, because
dataset_gate.load_verified certifies that chosen passes the tests and rejected
fails - which is true of stripped code. The gate certifies SEMANTICS; nothing
certified FORMAT.

These tests certify format. They use a recording stand-in for the tokenizer, so
they run on plain python with no transformers, no model download, no GPU.

SCOPE, stated because it is the weak part: this pins the two specific mismatches
that were found - the missing system turn and the stripped fences. It does not
verify that every future field of the sampling payload is mirrored in training.
A third divergence introduced later is NOT caught automatically. Enumerated, not
swept.
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import train_native
import forge


class RecordingTokenizer:
    """Stands in for a HF tokenizer; records the messages it was handed."""
    chat_template = "recording-stub"

    def __init__(self):
        self.messages = None

    def apply_chat_template(self, messages, tokenize=False,
                            add_generation_prompt=False):
        self.messages = messages
        return "".join(f"<|{m['role']}|>{m['content']}" for m in messages)


def test_training_prompt_carries_the_system_turn():
    tok = RecordingTokenizer()
    train_native.build_training_prompt(tok, "Write `foo(x)`.")
    roles = [m["role"] for m in tok.messages]
    assert "system" in roles, (
        f"training prompt has no system turn (roles={roles}); the sampler sent "
        f"one with every pair and eval.py sends one when scoring")


def test_training_system_message_is_the_sampling_system_message():
    tok = RecordingTokenizer()
    train_native.build_training_prompt(tok, "Write `foo(x)`.")
    sys_msg = next(m["content"] for m in tok.messages if m["role"] == "system")
    assert sys_msg == forge.ACTOR_SYSTEM, (
        "training system turn differs from forge.ACTOR_SYSTEM; the trainer and "
        "the sampler must agree byte for byte, not merely both have one")


def test_user_turn_is_the_task_prompt():
    tok = RecordingTokenizer()
    train_native.build_training_prompt(tok, "Write `foo(x)`.")
    user = next(m["content"] for m in tok.messages if m["role"] == "user")
    assert user == "Write `foo(x)`."


def test_target_is_fenced_not_bare_source():
    legacy = {"chosen": "def foo(x):\n    return x"}
    out = train_native.training_target(legacy, "chosen")
    assert out.lstrip().startswith("```"), (
        "DPO target is bare source, but ACTOR_SYSTEM instructs the policy to "
        "emit a ```python fenced block, so bare source is off-manifold")
    assert "def foo(x):" in out


def test_target_prefers_the_verbatim_completion_when_present():
    row = {"chosen": "def foo(x):\n    return x",
           "chosen_raw": "```python\ndef foo(x):\n    return x\n```"}
    assert train_native.training_target(row, "chosen") == row["chosen_raw"], (
        "when forge recorded the real emission, training must use it rather "
        "than a reconstruction")


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
