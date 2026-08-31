#!/usr/bin/env python3
"""extract_book.py — turn the LFS arm64 book into ordered, driver-runnable scripts.

    python3 tup/extract_book.py 5 6 7 8 9 10     # chapters to extract

For every page in each chapter (in TOC order) this writes
tup/book/chNN/MM-<page>.sh containing that page's <pre class="userinput">
blocks, verbatim and in order, with a header naming the page title and URL.
The driver, not this file, decides execution context (lfs user / chroot).

WHAT IS AND IS NOT AUTOMATED, stated plainly:
  - Command blocks are the book's own bytes. Nothing is paraphrased.
  - Package pages (title like "5.5. GCC-15.2.0 - Pass 1") get tarball
    extract/cd/cleanup WRAPPING from the driver, matching the book's standing
    instruction ("for each package: extract, enter, build, delete") which the
    book states once in prose rather than per-page.
  - Blocks that invoke test suites (make check / make -k check / make test)
    are wrapped in a tup_tests guard. Policy ruling 2026-08-31: glibc, gcc,
    binutils suites run; everything else is receipted as SKIPPED, never
    silently dropped.
  - A file in tup/overrides/<page>.sh REPLACES the extracted page entirely.
    That is the only sanctioned way to handle the book's interactive moments
    (root passwd, make menuconfig, GRUB) — an override is a visible, diffable
    decision; an inline edit to book/ would be a silent one. book/ is
    regenerated at will and never hand-edited.
"""
from __future__ import annotations

import html
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/"
HERE = Path(__file__).resolve().parent
BOOK = HERE / "book"

TEST_RE = re.compile(r"\bmake\s+(-k\s+)?(check|test)\b")
# The package is found ANYWHERE in the title ("Linux-6.17.3 API Headers",
# "Libelf from Elfutils-0.193", "GCC-15.2.0 - Pass 2" are all real), names may
# contain hyphens and colons, and the classification is settled by resolving
# against the wget-list's ACTUAL filenames — an unresolved package page gets a
# loud WARNING, never a silent demotion to action-page (the linux-headers
# failure that taught this cost a chain restart).
TITLE_PKG_RE = re.compile(r"([A-Za-z][A-Za-z0-9_+:.-]*?)-(\d[\w.-]*\w)")
NAME_FIXUPS = {"xml::parser": "xml-parser", "flit-core": "flit_core",
               "d-bus": "dbus", "sqlite": "sqlite-autoconf"}


def load_tarballs() -> list[str]:
    txt = fetch(BASE + "wget-list-sysv")
    return [u.rsplit("/", 1)[-1] for u in txt.split() if "/" in u]


def resolve_pkg(title: str, tarballs: list[str]) -> str:
    for m in TITLE_PKG_RE.finditer(title):
        name = NAME_FIXUPS.get(m.group(1).lower(), m.group(1).lower())
        for stem in (f"{name}-{m.group(2)}".lower(),
                     f"{name}{m.group(2)}".lower()):   # tcl8.6.17, expect5.45.4
            for t in tarballs:
                tl = t.lower()
                if tl.startswith((stem + ".tar", stem + ".tgz", stem + "-src")):
                    return t
    return ""


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def toc_pages(chapter: int) -> list[str]:
    """Page filenames for a chapter, in book order, from the master TOC."""
    idx = fetch(BASE + "index.html")
    # Case-SENSITIVE page names exist: the book ships chapter07/Python.html
    # with a capital P, and a lowercase-only class silently dropped it — the
    # temporary Python never got built and glibc's configure failed three
    # chapters later with "critical programs are missing: python". Any class
    # that can silently drop a page is a defect; this one now also COUNTS.
    pat = re.compile(rf'href="(chapter{chapter:02d}/[A-Za-z0-9+.-]+\.html)"')
    seen, out = set(), []
    for m in pat.finditer(idx):
        p = m.group(1)
        if p not in seen and not p.endswith(f"chapter{chapter:02d}.html"):
            seen.add(p)
            out.append(p)
    return out


def extract(page_html: str) -> tuple[str, list[str]]:
    t = re.search(r"<title>\s*(.*?)\s*</title>", page_html, re.S)
    title = html.unescape(re.sub(r"\s+", " ", t.group(1))) if t else "?"
    title = title.replace(" ", " ")
    blocks = [html.unescape(re.sub(r"<[^>]+>", "", b)).strip()
              for b in re.findall(r'<pre class="userinput">(.*?)</pre>',
                                  page_html, re.S)]
    return title, blocks


# Book pages carry DIAGNOSTIC greps — "grep '^FAIL:' $(find -name '*.log')",
# "grep 'Timed out' ...", the toolchain sanity greps in chapters 5 and 6.
# They exist for a human to READ. grep exits 1 when it matches nothing, so
# under `set -e` the good outcome (no failures, no timeouts) aborts the build
# — measured three separate times tonight, on glibc, on binutils, and on the
# chapter-5 sanity checks. They are advisory output, not assertions, so the
# driver prints them and does not gate on them. If a check should GATE, it
# needs an explicit assertion; the book does not provide one, and neither
# does this transformation pretend to.
# `awk` joins `grep` here for the same reason plus one more: gmp's page
# summarises its test log with awk AFTER the test block, so SKIPPING the
# tests leaves the summariser reading a file that was never created
# (measured: "awk: fatal: cannot open file `gmp-check-log`"). A summary of
# output that does not exist is advisory by definition.
DIAG_RE = re.compile(r"^(grep|awk)\b(?!.*\|\|)")


def guard_diagnostics(block: str) -> str:
    out = []
    for line in block.splitlines():
        if DIAG_RE.match(line) and not line.rstrip().endswith("\\"):
            out.append(line + "   || true   # advisory: see extract_book.py")
        else:
            out.append(line)
    return "\n".join(out)


def guard_tests(block: str, pkg: str) -> str:
    if not TEST_RE.search(block):
        return block
    return (f'if tup_tests_enabled "{pkg}"; then\n{block}\n'
            f'else tup_receipt_skip_tests "{pkg}"; fi')


def main() -> int:
    chapters = [int(a) for a in sys.argv[1:]] or [5, 6, 7, 8, 9, 10]
    tarballs = load_tarballs()
    for ch in chapters:
        outdir = BOOK / f"ch{ch:02d}"
        outdir.mkdir(parents=True, exist_ok=True)
        pages = toc_pages(ch)
        manifest = []
        for i, p in enumerate(pages, 1):
            title, blocks = extract(fetch(BASE + p))
            name = Path(p).stem
            tarball = resolve_pkg(title, tarballs)
            if not tarball and TITLE_PKG_RE.search(title):
                print(f"  WARNING ch{ch:02d}/{name}: title names a package "
                      f"but no wget-list tarball resolves: {title!r}")
            body = "\n\n".join(guard_diagnostics(guard_tests(b, name)) for b in blocks)
            script = (f"# {title}\n# {BASE}{p}\n"
                      + (f"# TUP_TARBALL={tarball}\n" if tarball
                         else "# TUP_ACTION_PAGE\n")
                      + "\n" + body + "\n")
            (outdir / f"{i:02d}-{name}.sh").write_text(script, encoding="utf-8")
            manifest.append(f"{i:02d}-{name}.sh")
            print(f"  ch{ch:02d}/{i:02d}-{name}.sh  "
                  f"[{tarball or 'action'}] {len(blocks)} blocks")
        (outdir / "ORDER").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
