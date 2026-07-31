"""verify_claims.py — check this README's factual claims against the repo.

    python verify_claims.py

Every empirical claim in the README that CAN be settled by a machine is settled
here, against the artifacts shipped beside it, and the script exits non-zero if
one has drifted. A README is a set of promises; this is the mechanism that keeps
them true rather than asking a reader to trust them.

WHAT IT CANNOT CHECK, which is the honest half:

  - Claims resting on `data/eval_history.jsonl`. That file is NOT published, so
    the 57-run saturation and standard-deviation figures cannot be reproduced
    from this repo by a reader. The README marks them as such. They are reported
    from a local artifact and you are being asked to take them on trust; this
    script will not pretend otherwise.
  - Anything needing a GPU, Ollama, or a training run.
  - Whether the pipeline is a GOOD idea. Not falsifiable, not touched.
  - It is a FIXED LIST of checks, not a general fact-checker. A newly written
    sentence is not caught automatically. Flashlight, not fence.

Layout note: published, this sits next to README.md. In the source repo the same
file is `verify_dpo_claims.py` beside `publish/dpo_README.md`. It finds whichever
is present so one implementation serves both.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
# SOURCE layout FIRST. Getting this order wrong is not academic: in the source
# repo, HERE/README.md is a DIFFERENT project's readme, and the first run of this
# script cheerfully checked the DPO claims against it and reported failures that
# were really "that text is not in this file". Publish-layout detection has to be
# the fallback, not the default.
for _c in (HERE / "publish" / "dpo_README.md", HERE / "README.md"):
    if _c.exists():
        README_PATH = _c
        break
else:                                                    # pragma: no cover
    print("cannot find the README to check"); sys.exit(2)
README = README_PATH.read_text(encoding="utf-8")
# Markdown wraps prose, so a claim can straddle a line break -- "an 8-second"
# ending one line and "timeout" starting the next. Matching against the raw text
# made this script report a MISSING claim that was plainly on the page. Prose
# checks use the flattened copy.
FLAT = re.sub(r"\s+", " ", README)
DATA = HERE / "data"

RESULTS: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "", ok_detail: str = "") -> None:
    """`detail` describes the failure, `ok_detail` the pass. Never print a
    failure message beside a passing mark."""
    RESULTS.append((ok, name, ok_detail if ok else detail))


def _json(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ---------------------------------------------------------------------------
def check_gate_numbers():
    """'1,269 unique pairs, 0 violations, 2,190 rows across ... (1,234) ... (918)
    ... (38)' — all of it from the published receipt."""
    r = _json("dataset_verification.json")
    if r is None:
        return check("gate receipt is published", False, "data/dataset_verification.json missing")
    want = {
        "unique pairs": (r["total_pairs"], r"\*\*([\d,]+) unique pairs"),
        "violations": (r["violations"], r"unique pairs, (\d+) violations"),
        "rows total": (r["total_rows_across_files"], r"covering ([\d,]+) rows"),
        "dpo_pairs.jsonl": (r["files"]["dpo_pairs.jsonl"]["pairs"], r"`dpo_pairs\.jsonl` \(([\d,]+)\)"),
        "capped": (r["files"]["dpo_pairs_capped.jsonl"]["pairs"], r"`dpo_pairs_capped\.jsonl` \(([\d,]+)"),
        "repair": (r["files"]["repair_pairs.jsonl"]["pairs"], r"`repair_pairs\.jsonl` \(([\d,]+)\)"),
    }
    bad = []
    for label, (actual, pat) in want.items():
        m = re.search(pat, README)
        if not m:
            bad.append(f"{label}: claim not found in README")
        elif int(m.group(1).replace(",", "")) != actual:
            bad.append(f"{label}: README {m.group(1)} vs receipt {actual}")
    check("gate numbers match the published receipt", not bad, "; ".join(bad),
          f"{len(want)} figures verified against dataset_verification.json")

    check("the receipt really records zero violations",
          r["violations"] == 0 and all(f["violations"] == 0 for f in r["files"].values()),
          f"receipt reports violations: {r['violations']}",
          "0 violations across every file in the receipt")


def check_receipt_pins_the_verifier():
    """The gate section claims editing a dataset stops training. Since the
    interpreter can change what 'verified' MEANS without touching a byte of data,
    the receipt must pin that too, and the README must say so."""
    r = _json("dataset_verification.json")
    if r is None:
        return
    v = r.get("verifier") or {}
    check("the receipt pins the verifier, not only the data",
          bool(v) and any(k.endswith(".py") for k in v),
          f"receipt verifier entry: {v}",
          f"pins {', '.join(sorted(v))}")
    # A word is not a disclosure. The first version of this check passed merely
    # because "interpreter" appeared in an unrelated sentence about
    # PYTHONOPTIMIZE -- a green mark earned for the wrong reason, which is worse
    # than a red one. It now requires language that actually describes the pin.
    discloses = re.search(
        r"(pins?|pinned|records?) (the )?(python )?(interpreter|version)"
        r"|interpreter (is )?(pinned|recorded)", FLAT, re.I)
    check("the README discloses that the interpreter is pinned",
          bool(discloses) and "interpreter" in v,
          "the receipt pins an interpreter but the README never says so -- a "
          "reader cannot know that re-verification is interpreter-specific"
          if "interpreter" in v else "receipt does not pin an interpreter",
          "README describes the pin and the receipt carries it")


def check_rpo_alpha_table():
    """The loss/nll_loss table and the arithmetic under it."""
    r = _json("smoke_rpo_alpha_result.json")
    if r is None:
        return check("rpo_alpha artifact is published", False,
                     "data/smoke_rpo_alpha_result.json missing")
    blob = json.dumps(r)
    nums = re.findall(r"\| `1\.0` \| ([\d.]+) \| \*\*([\d.]+)\*\* \|", README)
    unset = re.search(r"\| unset \| ([\d.]+) \|", README)
    if not nums or not unset:
        return check("rpo_alpha table found in README", False, "table not matched")
    loss_on, nll = (float(x) for x in nums[0])
    loss_off = float(unset.group(1))
    present = [v for v in (loss_on, nll, loss_off)
               if re.search(rf"{re.escape(f'{v}')}", blob)]
    check("rpo_alpha table numbers appear in the artifact",
          len(present) == 3,
          f"only {len(present)}/3 of {loss_on}, {nll}, {loss_off} found in the artifact",
          "all three figures found in smoke_rpo_alpha_result.json")
    # The README does its own arithmetic in the prose; check the prose is right.
    m = re.search(r"`([\d.]+) \+ ([\d.]+) = ([\d.]+)` against an observed `([\d.]+)`", README)
    if m:
        a, b, claimed_sum, observed = (float(x) for x in m.groups())
        check("the README's own arithmetic is correct",
              abs((a + b) - claimed_sum) < 5e-4,
              f"{a} + {b} = {a + b}, README says {claimed_sum}",
              f"{a} + {b} = {claimed_sum}, and the observed value is {observed}")


def check_export_acceptance():
    r = _json("export_acceptance_result.json")
    if r is None:
        return check("export acceptance artifact is published", False,
                     "data/export_acceptance_result.json missing")
    blob = json.dumps(r).lower()
    check("the 50,000x adapter-is-live control is in the artifact",
          "50000" in blob.replace(",", "") or "50_000" in blob,
          f"no 50,000x scaling recorded in the artifact",
          "the amplification control is recorded")


def check_code_claims():
    """Claims about the code, checked against the code."""
    forge_src = (HERE / "forge.py").read_text(encoding="utf-8")
    check("EMIT_CONCISENESS is really False",
          re.search(r"EMIT_CONCISENESS\s*=\s*False", forge_src) is not None,
          "EMIT_CONCISENESS is not False in forge.py",
          "length-preference pairs are disabled in forge.py")
    m = re.search(r"CAND_TIMEOUT\s*=\s*(\d+)", forge_src)
    claimed = re.search(r"(\d+)-second timeout", FLAT)
    check("the quoted candidate timeout matches the code",
          bool(m and claimed and int(m.group(1)) == int(claimed.group(1))),
          f"code={m.group(1) if m else '?'}s, README={claimed.group(1) if claimed else '?'}s",
          f"both say {m.group(1)}s" if m else "")
    check("candidates really run under `python -I`",
          '"-I"' in forge_src or "'-I'" in forge_src,
          "no -I flag found in forge.py's subprocess call",
          "forge.py launches the harness with -I")

    gate_src = (HERE / "dataset_gate.py").read_text(encoding="utf-8")
    bypass = re.search(r"--force|--skip-gate|SKIP_GATE|--no-verify", gate_src)
    check("'there is no bypass flag' is true of dataset_gate.py", not bypass,
          f"found what looks like a bypass: {bypass.group(0) if bypass else ''}",
          "no bypass flag in dataset_gate.py")


def check_unverifiable_claims_are_marked():
    """The 57-run figures rest on data/eval_history.jsonl, which is NOT
    published. A reader cannot reproduce them. The README must say so rather
    than presenting them like the gate numbers, which ARE reproducible."""
    cites_57 = re.search(r"57\s+logged runs|over those 57", README)
    if not cites_57:
        return check("eval_history claims present", True, "", "no 57-run claim made")
    # "Does it ship?" is a question about the WHITELIST, not about whether the
    # file happens to sit on this disk. Checking the filesystem in the source
    # repo answers "yes" for every unpublished artifact in data/ -- which is the
    # exact opposite of the truth, and is what this check exists to catch.
    shipped = (DATA / "eval_history.jsonl").exists()
    if (HERE / "sync_public.py").exists():
        try:
            sys.path.insert(0, str(HERE))
            import sync_public
            shipped = any(dest.endswith("eval_history.jsonl")
                          for dest in sync_public.DPO_PUBLISH.values())
        except Exception:
            pass                       # fall back to the filesystem answer
    marked = re.search(r"not (?:published|shipped|included)|cannot be reproduced"
                       r"|not reproducible from this repo", README, re.I)
    check("claims resting on unpublished artifacts are labelled as such",
          shipped or bool(marked),
          "the README quotes 57-run figures from data/eval_history.jsonl, which "
          "is not published, without saying it is unreproducible here",
          "eval_history.jsonl ships" if shipped else
          "the README marks these figures as not reproducible from this repo")


# ---------------------------------------------------------------------------
def main() -> int:
    for fn in (check_gate_numbers, check_receipt_pins_the_verifier,
               check_rpo_alpha_table, check_export_acceptance,
               check_code_claims, check_unverifiable_claims_are_marked):
        try:
            fn()
        except Exception as e:
            check(fn.__name__, False, f"check itself errored: {e!r}")

    width = max(len(n) for _, n, _ in RESULTS)
    failed = sum(not ok for ok, _, _ in RESULTS)
    for ok, name, detail in RESULTS:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name.ljust(width)}  {detail}")
    print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} README claims verified"
          + ("" if not failed else f", {failed} FAILED"))
    print(f"checked against: {README_PATH.name}")
    print("Scope: a fixed list. Claims needing a GPU, Ollama, a training run, or "
          "the unpublished eval_history.jsonl are NOT checked here.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
