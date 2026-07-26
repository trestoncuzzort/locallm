"""data.py — a dependency-free tokenizer built from YOUR corpus, plus batching.

Char-level: the vocabulary is exactly the set of characters in your text, so there
is no external tokenizer, no downloads, nothing proprietary. You own the whole stack.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import torch

DOC_MARKER = "\n\n# file: "


def documents(text: str) -> list[str]:
    """Split a corpus into documents.

    Uses make_corpus.py's `# file:` markers when present, otherwise falls back to
    blank-line-separated blocks so arbitrary user text is still grouped rather
    than sliced mid-sentence.
    """
    if DOC_MARKER in text:
        head, *rest = text.split(DOC_MARKER)
        docs = ([head] if head.strip() else []) + ["# file: " + r for r in rest]
    else:
        docs = text.split("\n\n")
    return [d for d in docs if d.strip()]


def group_split(text: str, val_frac: float = 0.1, seed: int = 1337) -> tuple[str, str]:
    """Split by whole document, never mid-document, after removing duplicates.

    The naive alternative is to cut the corpus at 90% of its length. That splits
    in the middle of a document and, worse, lets duplicated material sit on both
    sides of the split, so validation measures memorisation instead of
    generalisation. See leakage.py, which will tell you how bad it is.

    Assignment is by hash of the document text, so it is deterministic, and two
    identical documents always land on the same side even if de-duplication is
    skipped.
    """
    seen, docs = set(), []
    for d in documents(text):
        key = hashlib.sha1(d.encode("utf-8")).hexdigest()
        if key in seen:
            continue          # exact duplicate: keep one copy, in one split
        seen.add(key)
        docs.append((key, d))

    total = sum(len(d) for _, d in docs)
    target = total * val_frac

    # Two passes, both bounded by the target.
    #
    # Pass 1 walks the documents in a SEED-SHUFFLED order and takes any that
    # still fit. That is what makes `seed` real: a different seed produces a
    # genuinely different validation set, which is the only way to measure how
    # much of a result is split-induced rather than model-induced.
    #
    # Pass 2 fills the leftover gap smallest-first. Without it, one early large
    # document can consume the budget and leave validation far short of target.
    # Never "add until the target is passed": one document bigger than the whole
    # target would land in validation and take most of the corpus with it.
    rng = random.Random(seed)
    order = list(docs)
    rng.shuffle(order)

    val, acc, leftover = [], 0, []
    for key, d in order:
        if acc + len(d) <= target:
            val.append(d)
            acc += len(d)
        else:
            leftover.append((key, d))

    train = []
    for key, d in sorted(leftover, key=lambda kv: len(kv[1])):
        if acc + len(d) <= target:
            val.append(d)
            acc += len(d)
        else:
            train.append(d)

    if not train:                            # tiny corpora: never empty the train side
        train, val = val, []
    return "\n\n".join(train), "\n\n".join(val)


def split_health(text: str, val_frac: float = 0.1, seed: int = 1337) -> dict:
    """Can this corpus actually support the requested split?

    A document-level split cannot hit 10% if the corpus is three documents, or
    if one document is most of the text. Rather than silently returning a wildly
    wrong ratio, report what was actually achieved so the caller can say so.
    """
    train_text, val_text = group_split(text, val_frac, seed)
    total = len(train_text) + len(val_text)
    achieved = len(val_text) / max(total, 1)
    docs = documents(text)
    largest = max((len(d) for d in docs), default=0)
    return {
        "documents": len(docs),
        "requested_val_frac": val_frac,
        "achieved_val_frac": achieved,
        "largest_doc_frac": largest / max(len(text), 1),
        # Achieving less than half the requested validation size means the
        # document sizes, not the setting, are in charge.
        "ok": achieved >= val_frac * 0.5 and len(val_text) > 0,
    }


class CharTokenizer:
    def __init__(self, chars):
        self.chars = list(chars)
        self.stoi = {c: i for i, c in enumerate(self.chars)}
        self.itos = {i: c for i, c in enumerate(self.chars)}

    @property
    def vocab_size(self) -> int:
        return len(self.chars)

    @classmethod
    def from_text(cls, text: str) -> "CharTokenizer":
        return cls(sorted(set(text)))

    def encode(self, s: str):
        return [self.stoi[c] for c in s if c in self.stoi]

    def decode(self, ids) -> str:
        return "".join(self.itos[int(i)] for i in ids)

    def save(self, path):
        Path(path).write_text(json.dumps(self.chars, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "CharTokenizer":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))


class Corpus:
    """Holds train/val splits as token tensors and serves random batches."""

    def __init__(self, text: str, tokenizer: CharTokenizer, device: str,
                 val_frac: float = 0.1, grouped: bool = True, seed: int = 1337):
        """grouped=True splits by whole document and de-duplicates first, so
        validation text cannot also be training text. grouped=False reproduces
        the naive positional cut; it is kept only so leakage.py can show what
        that costs, and it should not be used for real comparisons."""
        if grouped:
            train_text, val_text = group_split(text, val_frac, seed)
            train_ids = torch.tensor(tokenizer.encode(train_text), dtype=torch.int32)
            val_ids = torch.tensor(tokenizer.encode(val_text), dtype=torch.int32)
        else:
            data = torch.tensor(tokenizer.encode(text), dtype=torch.int32)
            n = int(len(data) * (1 - val_frac))
            train_ids, val_ids = data[:n], data[n:]

        self.device = device
        # Keep the corpus resident on the training device. Batches are then cut
        # on-device with one vectorised gather instead of a Python loop plus a
        # host-to-device copy per step, which is the dominant cost at these
        # model sizes: the GPU finishes a 3M-parameter step long before Python
        # can assemble the next batch. int32 halves the residency of int64 and
        # costs one cheap cast per batch (nn.Embedding needs int64 indices).
        self.train = self._place(train_ids)
        self.val = self._place(val_ids)

    def _place(self, t: torch.Tensor) -> torch.Tensor:
        """Move the corpus to the device, falling back to host memory if it
        does not fit. A corpus large enough to fill VRAM should not cost you
        the ability to train on it."""
        if self.device == "cpu":
            return t
        try:
            return t.to(self.device)
        except (torch.cuda.OutOfMemoryError, RuntimeError):
            return t

    def get_batch(self, split: str, batch_size: int, block_size: int,
                  generator: torch.Generator | None = None):
        """One vectorised gather, on whichever device the corpus lives on.

        Pass `generator` to draw from a dedicated RNG stream rather than the
        global one, so that evaluating cannot perturb the training sequence.
        """
        d = self.train if split == "train" else self.val
        hi = len(d) - block_size
        if hi < 1:
            raise ValueError(
                f"{split} split holds {len(d)} tokens but block_size is "
                f"{block_size}. Use a bigger corpus or a smaller context window.")
        ix = torch.randint(hi, (batch_size,), device=d.device, generator=generator)
        window = ix[:, None] + torch.arange(block_size + 1, device=d.device)
        chunk = d[window].long()
        # .contiguous(): these are strided views of one gather, and the loss
        # reshapes targets with .view(), which rejects a non-contiguous tensor.
        x, y = chunk[:, :-1].contiguous(), chunk[:, 1:].contiguous()
        if x.device.type != self.device:
            x, y = x.to(self.device), y.to(self.device)
        return x, y
