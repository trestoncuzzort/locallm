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
                                          (see _classify_audit below) AND the
                                          havoc oracle (below) shows the
                                          postcondition has teeth;
                                          zero checks generated is not a pass.
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

SEMANTIC VACUITY — two kernel-native instruments, neither of them lexical.

(1) gnatprove's own proof warnings, --proof-warnings=on. MEASURED on the
    Wave-2 probes: a contradictory Pre — Pre => Big_Integer'(1) =
    Big_Integer'(2), which discharges a FALSE Post at exit 0 with severity
    "info" — puts a proof entry {rule: VC_INCONSISTENT_PRE, severity:
    "warning", message: "precondition is always False"} in the .spark JSON:
    the kernel itself saying the hypothesis is unsatisfiable, in its own
    machine-written record. The three always-False rules
    (VC_INCONSISTENT_PRE / _POST / _ASSUME) rule VACUOUS. The detection is
    semantic, not syntactic — MEASURED to fire on
    Pre => (X > 0 and then X < 0) as well — and MEASURED to fire on none of
    the 22 honest files (11 real + 11 twin).

    VC_UNREACHABLE_BRANCH and VC_DEAD_CODE are NOT verdicts here, MEASURED:
    VC_UNREACHABLE_BRANCH fires on 7 of the 11 honest real lowerings
    (count_matches, factorial, fib, gcd, linear_search, sum_upto, max's twin)
    because lower_spark.py wraps every Subprogram_Variant as
    (if D >= 0 then D else 0) and the `else 0` branch is provably dead under
    the invariant. Ruling on that rule would fail 7 honest cells. They are
    recorded in extras["proof_warnings"] as evidence and nothing more; the
    vacuous-implication class they would have caught is caught by (2).

(2) The havoc oracle, for the class no warning reports: a postcondition that
    is TRUE of every possible result (Post => True; Post => (if 1 = 2 then
    ...)) is proved honestly by the kernel and looks exactly like a real
    proof. _havoc_source replaces F's expression-function completion with a
    call to an Import'd, contract-free function, so F'Result becomes an
    arbitrary value of the return type, and asks the SAME kernel at the SAME
    --steps budget whether F's postcondition still proves. If it does, the
    contract says nothing about the computed result and the cell is VACUOUS.
    MEASURED: F's VC_POSTCONDITION goes "info" -> "medium" on all 22 honest
    files and stays "info" on all three Wave-2 holes — full separation. The
    oracle runs ONLY when every other gate has already said VERIFIED, so
    refuted twins never pay for it. F's postcondition is identified by
    gnatprove's own entity table (entities[id].name ending in ".F"), not by
    source position.

    The oracle is fail-closed: a source the completion scanner cannot
    rewrite, a havoc run that emits "error:", or a havoc run with no
    VC_POSTCONDITION for F is TOOL_ERROR, never VERIFIED — the adapter may
    not certify what its own instrument could not examine.

Budget: --steps, gnatprove's explicitly machine-independent deterministic
bound; the havoc run reuses it, so "provable against an arbitrary result" is
judged at exactly the standard the real run was judged at. The havoc run's
unproved F postcondition was MEASURED to reach "medium" two ways —
unproved_status "gave_up" (Z3 answered "Unknown (sat)": abs, max, sum_upto)
and "limit" (the 20000 steps ran out: the other 8 tasks) — so a "limit"
result cannot be refused as inconclusive: demanding "gave_up" would turn 8
of the 11 honest cells into TIMEOUT. Both are recorded in extras["f_post"].
Prover pinned to the bundled Z3 with --prover=z3.

`pragma Assume`, SPARK_Mode Off, Import, and GNATprove justification
annotations prove or excuse anything — t never emits them; the adapter rules
VACUOUS on sight (BANNED below). That ban is the
cheap second line, not the guarantee: the guarantee is the audit requirements
plus the two instruments above. The ban scan runs on _active_code():
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

import hashlib
import json
import re
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

# gnatprove's own always-False rules (--list-categories, "Proof warnings
# categories"): the kernel reporting that a hypothesis it was handed cannot
# be satisfied. MEASURED absent from all 22 honest files, present on the
# contradictory-Pre probe.
CONTRADICTORY = frozenset((
    "VC_INCONSISTENT_PRE", "VC_INCONSISTENT_POST", "VC_INCONSISTENT_ASSUME"))
# Same warning family, recorded but NEVER ruled on: MEASURED to fire on 7 of
# 11 honest real lowerings (lower_spark.py's (if D >= 0 then D else 0)
# Subprogram_Variant wrapper makes the `else 0` branch provably dead).
UNREACHABLE = frozenset(("VC_UNREACHABLE_BRANCH", "VC_DEAD_CODE"))

# The havoc oracle's injected function. Contract-free and Import'd, so
# gnatprove has nothing to know about its result but its type. The name is
# suffixed with a digest of the source (probe e4 measured a file that squats
# the fixed name: gnatprove answers "conflicts with declaration at line N",
# which costs the oracle its subject). Predicting the suffix requires a source
# containing its own hash, so squatting it is not an available move.
HAVOC_FN = "T_Vacuity_Havoc"

# lower_spark.py emits F's completion as one signature line ending in `is`
# followed by a parenthesised expression; the W_k helpers put `is` on the
# next line, so both placements are accepted. The declaration is never
# matched: it is followed by `with`, not by `is`.
_F_COMPLETION = re.compile(
    r"^[ \t]*function[ \t]+F[ \t]*(\([^\n]*\))?[ \t]*return[ \t]+(\w+)"
    r"[ \t]*\r?\n?[ \t]*is\b",
    re.MULTILINE)


def _active_code(raw: str) -> str:
    folded = unicodedata.normalize("NFKC", raw).translate(_HOMOGLYPHS)
    return _INERT.sub(" ", folded)


def _end_of_expression(src: str, i: int) -> int:
    """Index just past the `;` closing the expression-function body that
    starts at src[i:]. Parenthesis depth is tracked with string and character
    literals skipped, so a `;` inside them cannot end the body early.
    Returns -1 when the body is unterminated."""
    depth, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n and src[i] != '"':
                i += 1
        elif c == "'" and i + 2 < n and src[i + 2] == "'":
            i += 2                      # character literal, never an attribute
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == ";" and depth <= 0:
            return i + 1
        i += 1
    return -1


def _havoc_source(src: str) -> tuple[str | None, str]:
    """F's completion replaced by a call to an Import'd contract-free
    function, so F'Result is an arbitrary value of the return type. Returns
    (text, "") or (None, why) — and (None, why) is fail-closed at the call
    site, never a pass."""
    fn = (HAVOC_FN + "_"
          + hashlib.sha256(src.encode("utf-8", "replace")).hexdigest()[:12])
    if fn.lower() in src.lower():
        return None, (f"source already declares {fn}; the havoc oracle cannot "
                      f"inject a fresh arbitrary result")
    ms = list(_F_COMPLETION.finditer(src))
    if not ms:
        return None, "no `function F ... is` expression-function completion"
    m = ms[-1]
    end = _end_of_expression(src, m.end())
    if end < 0:
        return None, "F's expression-function body is unterminated"
    plist, rtype = m.group(1) or "", m.group(2)
    body = (f"   function {fn} return {rtype}\n"
            f"   with Import, Global => null;\n\n"
            f"   function F {plist} return {rtype} is\n"
            f"     ({fn});\n")
    return src[:m.start()] + body + src[end:], ""


def _read_audit(work: Path) -> tuple[dict | None, str]:
    """Summarize gnatprove/*.spark. (None, why) when the audit is absent or
    unreadable — that is TOOL_ERROR, never a pass: the kernel's own record
    is the only acceptable positive evidence."""
    gdir = work / "gnatprove"
    files = sorted(gdir.glob("*.spark")) if gdir.is_dir() else []
    if not files:
        return None, "gnatprove wrote no .spark audit"
    a = {"proved": 0, "post_proved": 0, "flagged": 0, "justified": 0,
         "skips": 0, "assumes": 0, "entities": {},
         "contradictory": [], "unreachable": [], "f_post": []}
    for f in files:
        try:
            d = json.loads(f.read_bytes().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError) as e:
            return None, f"unreadable audit {f.name}: {e}"
        a["assumes"] += len(d.get("pragma_assume", []))
        a["skips"] += (len(d.get("skip_proof", []))
                       + len(d.get("skip_flow_proof", [])))
        # gnatprove's entity table: id -> qualified name, its own attribution
        # of every check to a subprogram (measured key "entities").
        names = {str(k).strip(): (v or {}).get("name", "")
                 for k, v in (d.get("entities") or {}).items()}
        for entry in d.get("proof", []):
            rule = entry.get("rule", "")
            if rule in CONTRADICTORY:
                a["contradictory"].append(
                    f"{rule} at {entry.get('file')}:{entry.get('line')}")
                continue      # a warning, not an obligation: never counted
            if rule in UNREACHABLE:
                a["unreachable"].append(
                    f"{rule} at {entry.get('file')}:{entry.get('line')}")
                continue      # measured on honest lowerings; evidence only
            owner = names.get(str(entry.get("entity")).strip(), "")
            if rule == "VC_POSTCONDITION" \
                    and owner.rsplit(".", 1)[-1] == "F":
                # severity + why it went unproved; "limit" (steps exhausted)
                # vs "gave_up" (countermodel) is the kernel's own distinction,
                # kept as evidence — see the havoc-budget note in the header.
                a["f_post"].append(
                    f"{entry.get('severity')}/"
                    f"{(entry.get('unproved_status') or {}).get('status')}")
            if "annot_kind" in entry or entry.get("severity") != "info":
                a["flagged"] += 1
                a["justified"] += 1 if "annot_kind" in entry else 0
            else:
                a["proved"] += 1
                if rule == "VC_POSTCONDITION":
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
    (outcome, reason). VERIFIED here is provisional — verify() must still
    clear it through the havoc oracle."""
    if a["contradictory"]:
        return Outcome.VACUOUS, (
            "gnatprove --proof-warnings reports an unsatisfiable hypothesis: "
            + "; ".join(a["contradictory"][:4]))
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


def _run(src_text: str, unit: str, budget: int, warnings: bool):
    """One gnatprove run over src_text in a fresh scratch dir. Returns
    (proc | None, audit | None, why); proc None means the wall backstop
    fired."""
    with tempfile.TemporaryDirectory(prefix="t-spark-") as td:
        work = Path(td)
        (work / "t_work.gpr").write_text(GPR, encoding="utf-8")
        # GNAT's naming convention demands file name == unit name; deriving it
        # here keeps harness filenames free (twins live in *.twin.ads outside).
        (work / unit).write_text(src_text, encoding="utf-8")
        cmd = [str(GNATPROVE), "-P", "t_work.gpr", "--steps", str(budget),
               "--prover=z3", "--quiet"]
        if warnings:
            cmd.append("--proof-warnings=on")
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=WALL_S, cwd=work)
        except subprocess.TimeoutExpired:
            return None, None, "wall backstop fired"
        audit, why = _read_audit(work)   # before the scratch dir dies
    return p, audit, why


def _havoc_verdict(src_text: str, unit: str, budget: int) -> tuple[str, str]:
    """The weak-spec oracle. VERIFIED only when F's postcondition FAILS
    against an arbitrary result; VACUOUS when it still proves; TOOL_ERROR
    when the oracle could not be applied — never a pass on ignorance."""
    hv, why = _havoc_source(src_text)
    if hv is None:
        return Outcome.TOOL_ERROR, f"havoc oracle not applicable: {why}"
    p, audit, awhy = _run(hv, unit, budget, warnings=False)
    if p is None:
        return Outcome.TIMEOUT, "havoc oracle: wall backstop fired"
    out = p.stdout + p.stderr
    if re.search(r"^.*\berror\b", out, re.MULTILINE):
        return Outcome.TOOL_ERROR, (
            "havoc oracle rejected by gnatprove: " + out[-300:])
    if audit is None:
        return Outcome.TOOL_ERROR, f"havoc oracle: {awhy}"
    if not audit["f_post"]:
        return Outcome.TOOL_ERROR, (
            "havoc oracle produced no VC_POSTCONDITION for F; the contract "
            "was not examined against an arbitrary result")
    if all(s.startswith("info") for s in audit["f_post"]):
        return Outcome.VACUOUS, (
            "content-free contract: F's postcondition still proves when the "
            f"body is replaced by an arbitrary (Import'd) {HAVOC_FN} result, "
            "so it constrains nothing the body computes")
    return Outcome.VERIFIED, ""


def version() -> str:
    if not GNATPROVE:
        raise SystemExit(_GNATPROVE_WHY)
    p = subprocess.run([str(GNATPROVE), "--version"],
                       capture_output=True, text=True)
    first = p.stdout.strip().splitlines()
    return "gnatprove " + " / ".join(first[:2])


def verify(path: Path, budget: int = DEFAULT_STEPS) -> Result:
    if not GNATPROVE:
        raise SystemExit(_GNATPROVE_WHY)
    src_hash = sha256_file(path)
    src_text = safe_text(path)
    banned = [m.group(0) for m in BANNED.finditer(_active_code(src_text))]
    t0 = time.monotonic()
    m = re.search(r"package\s+(\w+)", src_text)
    unit = (m.group(1).lower() if m else "t_unit") + ".ads"
    p, audit, audit_why = _run(src_text, unit, budget, warnings=True)
    if p is None:
        return Result("spark", version(), src_hash, Outcome.TIMEOUT,
                      wall_ms=int((time.monotonic() - t0) * 1000),
                      budget=f"steps={budget}", error="wall backstop fired")
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
    havoc_wall = 0
    if outcome == Outcome.VERIFIED:
        # Only a would-be pass pays for the second kernel run: a refuted twin
        # is already answered, and running the oracle on it would buy nothing.
        h0 = time.monotonic()
        outcome, why = _havoc_verdict(src_text, unit, budget)
        havoc_wall = int((time.monotonic() - h0) * 1000)
    wall = int((time.monotonic() - t0) * 1000)
    extras = {"banned_tokens": banned[:5], "havoc_ms": havoc_wall}
    if audit is not None:
        extras["audit"] = {k: audit[k] for k in
                           ("proved", "post_proved", "flagged", "justified",
                            "skips", "assumes")}
        extras["audit"]["entities"] = audit["entities"]
        extras["proof_warnings"] = (audit["contradictory"]
                                    + audit["unreachable"])[:5]
        extras["f_post"] = audit["f_post"]
    return Result("spark", version(), src_hash, outcome,
                  ok=outcome == Outcome.VERIFIED, exit_code=p.returncode,
                  wall_ms=wall, budget=f"steps={budget}",
                  error=why if why else
                  ("" if outcome != Outcome.TOOL_ERROR else out[-400:]),
                  extras=extras)
