"""data.py — a dependency-free tokenizer built from YOUR corpus, plus batching.

Char-level: the vocabulary is exactly the set of characters in your text, so there
is no external tokenizer, no downloads, nothing proprietary. You own the whole stack.
"""
from __future__ import annotations

import hashlib
import json
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

    # First-fit-decreasing toward the target. Naive "add documents until the
    # target is passed" looks fine until one document is larger than the whole
    # target, at which point it lands in validation and takes 90% of the corpus
    # with it. Packing largest-first, and only accepting a document that still
    # fits, keeps validation at or just under the requested size.
    # Sort by (-length, hash) so it is deterministic and independent of file order.
    docs.sort(key=lambda kv: (-len(kv[1]), kv[0]))

    val, train, acc = [], [], 0
    for _, d in docs:
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
            self.train = torch.tensor(tokenizer.encode(train_text), dtype=torch.long)
            self.val = torch.tensor(tokenizer.encode(val_text), dtype=torch.long)
        else:
            data = torch.tensor(tokenizer.encode(text), dtype=torch.long)
            n = int(len(data) * (1 - val_frac))
            self.train, self.val = data[:n], data[n:]
        self.device = device

    def get_batch(self, split: str, batch_size: int, block_size: int):
        d = self.train if split == "train" else self.val
        ix = torch.randint(len(d) - block_size, (batch_size,))
        x = torch.stack([d[i:i + block_size] for i in ix])
        y = torch.stack([d[i + 1:i + 1 + block_size] for i in ix])
        return x.to(self.device), y.to(self.device)
