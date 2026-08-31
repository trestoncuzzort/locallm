"""t.verifiers.spark — the third kernel: GNATprove (SPARK 2014, Why3 + Z3).

Verdicts are classified from TEXT plus the kernel's own machine-written audit
(the per-unit .spark JSON), because gnatprove was MEASURED (2026-08-31, FSF
16.1.0-1, confirmed on x86_64-linux) to exit 0 for a full proof, for an
unproved postcondition, for a file that does not even parse, AND — Wave-1
audit, 2026-08-31 — for eight files where the proof obligation was justified,
skipped, or never generated at all:
    any "error:" line                 -> MALFORMED (checked BEFORE medium/high;
                                          a broken file can produce both)
    any "medium:" or "high:" line     -> REFUTED
    wall backstop                     -> TIMEOUT
    exit 0                            -> VERIFIED only if the .spark audit
                                          shows the obligations were DISCHARGED
                                          (see _classify_audit below); zero
                                          checks generated is not a pass.
    none of the above                 -> TOOL_ERROR

POSITIVE EVIDENCE (the contract): exit 0 under --quiet was MEASURED to be
what pragma SPARK_Mode (Off), pragma/aspect Import, and pragma Annotate
(GNATprove, Skip_Proof|Skip_Flow_And_Proof|False_Positive|Intentional, ...)
all produce — with zero checks proved. So VERIFIED additionally requires,
from gnatprove's own gnatprove/*.spark JSON in the scratch dir (written by
the tool, not printable or suppressible by the source, unlike stdout):
  * >= 1 proof entry with severity "info" (a check actually proved), of
    which >= 1 is rule VC_POSTCONDITION (every t lowering puts a Post on F);
  * no proof entry justified or unproved (annot_kind / severity != "info":
    MEASURED shape of Annotate False_Positive/Intentional under --quiet —
    the medium entry stays in the JSON while stdout goes silent);
  * empty pragma_assume / skip_proof / skip_flow_proof lists (MEASURED:
    Skip_Proof fills skip_proof while printing nothing);
  * every entity in the "spark" map analyzed "all" (MEASURED: an Import'd or
    SPARK_Mode-Off body leaves "spec" or an empty map — the theorem's body
    was never in the proof's scope).

Budget: --steps, gnatprove's explicitly machine-independent deterministic
bound. Prover pinned to the bundled Z3 with --prover=z3. Vacuity analogue:
`pragma Assume`, SPARK_Mode Off, Import, and GNATprove justification
annotations prove or excuse anything — t never emits them; the adapter rules
VACUOUS on sight (BANNED below), and the audit requirements above are the
guarantee when a ban token is missed. The ban scan runs on _active_code():
comments, string literals and character literals stripped (a commented
"pragma Assume" is inert — Wave-1 probe p12 measured the unstripped scan
overfiring VACUOUS on an honest proof) and unicode homoglyphs folded to
ASCII (probe p11; GNAT itself rejects non-ASCII program text with "error:
illegal character", so folding cannot excuse real code).

Assertion_Policy (Ignore) needs no ban: MEASURED (p06/p07) — gnatprove
proves the ignored assertions anyway and still reports "medium:".

gnatprove requires a project; each verify runs in a scratch dir with a
two-line .gpr beside a copy of the source. The hash in the Result is the
SOURCE file's, so witnesses bind to t's artifact, not the scaffolding.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path

from . import Outcome, Result, safe_text, sha256_file
from .discover import find, missing

GNATPROVE = find("T_GNATPROVE", ['gnatprove'], [".local/gnatprove/**/bin/gnatprove", ".alire/**/bin/gnatprove"])
_GNATPROVE_WHY = missing("spark", "T_GNATPROVE", ['gnatprove'], [".local/gnatprove/**/bin/gnatprove", ".alire/**/bin/gnatprove"])
DEFAULT_STEPS = 20_000
WALL_S = 180

# Pragma AND aspect forms of every accepted-without-proof mechanism (Wave-1:
# pragma SPARK_Mode (Off) / pragma Import (C, ...) evaded the aspect-only
# ban; Import => True reordered after Post, and bare `Import` in a comma
# aspect list, evaded `with Import`). \bImport(?:_\w+)?\b needs no context:
# the word in active code is the aspect, the pragma, or GNAT's
# Import_Function/Import_Procedure variants; pragma Interface is the Ada 83
# synonym. GNATprove-comma catches pragma Annotate AND Annotate => (...) for
# the justify/skip families without caring which syntax carried it.
BANNED = re.compile(
    r"pragma\s+Assume\b"
    r"|SPARK_Mode\s*(?:=>|\()\s*Off\b"
    r"|\bImport(?:_\w+)?\b"
    r"|pragma\s+Interface(?:_Name)?\b"
    r"|GNATprove\s*,\s*(?:False_Positive|Intentional|Skip_Proof"
    r"|Skip_Flow_And_Proof)\b",
    re.IGNORECASE)

# Confusable-to-ASCII fold for the ban scan (probe p11: Cyrillic А in
# "pragma Аssume"). NFKC first (fullwidth/compatibility forms), then the
# common Cyrillic/Greek lookalikes of the letters our ban tokens use.
_HOMOGLYPHS = str.maketrans(
    "АВЕКМНОРСТУХЅІЈабвеорсухіјѕԛԝ"
    "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧοικρτυσνε",
    "ABEKMHOPCTYXSIJabveopcyxijsqw"
    "ABEZHIKMNOPTYXoikptusve")

# One leftmost-first pass: a string opened in a comment is not a string, a
# "--" inside a string or character literal is not a comment. [^"\n] keeps
# an unterminated literal from swallowing lines (fail-closed: leftovers can
# only over-match the ban, never under-match it).
_INERT = re.compile(r"'[^'\n]'|\"(?:[^\"\n]|\"\")*\"|--[^\n]*")

GPR = "project T_Work is\n   for Source_Dirs use (\".\");\nend T_Work;\n"


def _active_code(raw: str) -> str:
    folded = unicodedata.normalize("NFKC", raw).translate(_HOMOGLYPHS)
    return _INERT.sub(" ", folded)


def _read_audit(work: Path) -> tuple[dict | None, str]:
    """Summarize gnatprove/*.spark. (None, why) when the audit is absent or
    unreadable — that is TOOL_ERROR, never a pass: the kernel's own record
    is the only acceptable positive evidence."""
    gdir = work / "gnatprove"
    files = sorted(gdir.glob("*.spark")) if gdir.is_dir() else []
    if not files:
        return None, "gnatprove wrote no .spark audit"
    a = {"proved": 0, "post_proved": 0, "flagged": 0, "justified": 0,
         "skips": 0, "assumes": 0, "entities": {}}
    for f in files:
        try:
            d = json.loads(f.read_bytes().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError) as e:
            return None, f"unreadable audit {f.name}: {e}"
        a["assumes"] += len(d.get("pragma_assume", []))
        a["skips"] += (len(d.get("skip_proof", []))
                       + len(d.get("skip_flow_proof", [])))
        for entry in d.get("proof", []):
            if "annot_kind" in entry or entry.get("severity") != "info":
                a["flagged"] += 1
                a["justified"] += 1 if "annot_kind" in entry else 0
            else:
                a["proved"] += 1
                if entry.get("rule") == "VC_POSTCONDITION":
                    a["post_proved"] += 1
        for entry in d.get("flow", []):
            # honest flow entries are "info" (plus library "warning"s in
            # warn_error, not here); a justified flow check carries
            # annot_kind exactly like a justified proof check.
            if "annot_kind" in entry \
                    or entry.get("severity") not in ("info", "warning"):
                a["flagged"] += 1
        for k, v in (d.get("spark") or {}).items():
            a["entities"][f"{f.stem}:{k.strip()}"] = v
    return a, ""


def _classify_audit(a: dict) -> tuple[str, str]:
    """Exit-0, no-diagnostics runs land here; the audit decides. Returns
    (outcome, reason)."""
    if a["assumes"] or a["skips"] or a["flagged"]:
        return Outcome.VACUOUS, (
            f"accepted without discharging: {a['assumes']} pragma_assume, "
            f"{a['skips']} skipped, {a['flagged']} justified/unproved "
            f"check(s) in the .spark audit")
    if a["proved"] == 0:
        return Outcome.MALFORMED, (
            "zero checks proved (audit shows no proof obligations were "
            "generated — SPARK_Mode Off / Import / empty unit shape)")
    if not a["entities"] or any(v != "all" for v in a["entities"].values()):
        return Outcome.MALFORMED, (
            f"body not fully analyzed: entities {a['entities']} "
            f"(an entity below \"all\" has code outside the proof's scope)")
    if a["post_proved"] == 0:
        return Outcome.MALFORMED, (
            "no VC_POSTCONDITION proved — the artifact's theorem (the Post "
            "on F) was never discharged")
    return Outcome.VERIFIED, ""


def version() -> str:
    if not GNATPROVE:
        raise SystemExit(_GNATPROVE_WHY)
    p = subprocess.run([str(GNATPROVE), "--version"],
                       capture_output=True, text=True)
    first = p.stdout.strip().splitlines()
    return "gnatprove " + " / ".join(first[:2])


def verify(path: Path, budget: int = DEFAULT_STEPS) -> Result:
    src_hash = sha256_file(path)
    src_text = safe_text(path)
    banned = [m.group(0) for m in BANNED.finditer(_active_code(src_text))]
    t0 = time.monotonic()
    m = re.search(r"package\s+(\w+)", src_text)
    unit = (m.group(1).lower() if m else "t_unit") + ".ads"
    with tempfile.TemporaryDirectory(prefix="t-spark-") as td:
        work = Path(td)
        (work / "t_work.gpr").write_text(GPR, encoding="utf-8")
        # GNAT's naming convention demands file name == unit name; deriving it
        # here keeps harness filenames free (twins live in *.twin.ads outside).
        (work / unit).write_text(src_text, encoding="utf-8")
        try:
            p = subprocess.run(
                [str(GNATPROVE), "-P", "t_work.gpr", "--steps", str(budget),
                 "--prover=z3", "--quiet"],
                capture_output=True, text=True, timeout=WALL_S, cwd=work)
        except subprocess.TimeoutExpired:
            return Result("spark", version(), src_hash, Outcome.TIMEOUT,
                          wall_ms=int((time.monotonic() - t0) * 1000),
                          budget=f"steps={budget}", error="wall backstop fired")
        audit, audit_why = _read_audit(work)   # before the scratch dir dies
    wall = int((time.monotonic() - t0) * 1000)
    out = p.stdout + p.stderr
    why = ""
    if banned:
        outcome = Outcome.VACUOUS
    elif re.search(r"^.*\berror\b", out, re.MULTILINE):
        outcome = Outcome.MALFORMED
    elif re.search(r"^\s*\S+:\d+:\d+: (medium|high):", out, re.MULTILINE) \
            or "medium:" in out or "high:" in out:
        outcome = Outcome.REFUTED
    elif p.returncode == 0:
        if audit is None:
            outcome, why = Outcome.TOOL_ERROR, audit_why
        else:
            outcome, why = _classify_audit(audit)
    else:
        outcome = Outcome.TOOL_ERROR
    extras = {"banned_tokens": banned[:5]}
    if audit is not None:
        extras["audit"] = {k: audit[k] for k in
                           ("proved", "post_proved", "flagged", "justified",
                            "skips", "assumes")}
        extras["audit"]["entities"] = audit["entities"]
    return Result("spark", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"steps={budget}",
                  error=why if why else
                  ("" if outcome != Outcome.TOOL_ERROR else out[-400:]),
                  extras=extras)
