"""make_corpus.py — build a demo training corpus from THIS project's own text.

Self-contained: no downloads. Concatenates the hand-written .py sources and the
verified 'chosen' solutions into corpus.txt, so the from-scratch model has real,
local, Python-flavored text to learn. Point train.py at any .txt to use your own.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parts = []

for p in sorted(root.glob("*.py")):
    parts.append(f"# file: {p.name}\n" + p.read_text(encoding="utf-8", errors="ignore"))
for p in sorted((root / "localllm").glob("*.py")):
    if p.name not in ("make_corpus.py",):
        parts.append(f"# file: localllm/{p.name}\n" + p.read_text(encoding="utf-8", errors="ignore"))

dpo = root / "data" / "dpo_pairs.jsonl"
if dpo.exists():
    for line in dpo.open(encoding="utf-8"):
        try:
            parts.append(json.loads(line)["chosen"])
        except (json.JSONDecodeError, KeyError):
            pass

text = "\n\n".join(parts)
out = Path(__file__).with_name("corpus.txt")
out.write_text(text, encoding="utf-8")
print(f"wrote {out.name}: {len(text):,} chars from {len(parts)} sources")
