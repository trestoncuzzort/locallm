#!/usr/bin/env python3
"""check_overrides.py — every override must name a page that exists.

    python3 tup/check_overrides.py

An override is matched to a page BY FILENAME, so a page number that shifts —
inserting chapter 8's Python moved every later page by one — silently
unhooks its override. The build then runs the raw book page, which is exactly
what the override existed to prevent, and nothing says a word. That is the
same silent-drop class as the dropped Python page and the eaten ORDER list,
so it gets the same treatment: a check that fails loudly.

Exits nonzero if any override does not correspond to a page in some chapter's
ORDER, and prints the pages it looked at so a rename is one edit away.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE / "book"
OVERRIDES = HERE / "overrides"


def main() -> int:
    pages: dict[str, list[str]] = {}
    for order in sorted(BOOK.glob("ch*/ORDER")):
        ch = order.parent.name
        for line in order.read_text().split():
            pages.setdefault(line, []).append(ch)

    bad, ok = [], []
    for ov in sorted(OVERRIDES.rglob("*.sh")):
        rel = ov.relative_to(OVERRIDES)
        scoped = rel.parent.name if rel.parent.name else ""
        chapters = pages.get(ov.name, [])
        if not chapters:
            stem = ov.name.split("-", 1)[-1]
            near = sorted(p for p in pages if p.endswith(stem))
            bad.append((str(rel), near))
        elif len(chapters) > 1 and not scoped:
            # the same page number+name in two chapters is two different
            # builds; a flat override would fire on both
            bad.append((str(rel), [f"AMBIGUOUS across {','.join(chapters)} — "
                                   f"move it into overrides/{chapters[0]}/"]))
        else:
            ok.append((str(rel), ",".join(chapters)))

    for name, ch in ok:
        print(f"  ok   {name:28} -> {ch}")
    for name, near in bad:
        print(f"  FAIL {name:28} -> matches no page"
              + (f"; did you mean {', '.join(near)}?" if near else ""))
    print(f"\n{len(ok)}/{len(ok)+len(bad)} overrides are hooked to a real page")
    if bad:
        print("An unhooked override does not fire, and the raw book page runs "
              "in its place — silently. Rename it to match.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
