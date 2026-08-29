#!/usr/bin/env python3
"""dafny_verify.py — the Dafny GROUND TRUTH reward, in the shape verify_dataset.py already expects.

forge.verify() executes a candidate against hidden unit tests. This is the same
contract for Dafny, with a stronger oracle: unit tests say "passed these cases",
`dafny verify` says "correct for all inputs". The model still never grades itself.

Stdlib only, on purpose — same reason as dataset_gate.py: this is imported by the
system Python (verify side) and by .venv-train's Python (training side).

WHAT THIS FILE LEARNED FROM dataset_gate.py, AND WHY IT MATTERS MORE HERE
------------------------------------------------------------------------
dataset_gate's central finding is that a receipt must pin THE VERIFIER, not only
the data — section 71's red witness was 310 completions scoring 172 under 3.14 and
154 under 3.11, same bytes. The Dafny analogue of "which Python" is "which Z3, at
what resource limit", and it is a sharper edge for two reasons:

  1. THIS INSTALL SHIPS TWO SOLVERS (z3-4.12.1 and z3-4.14.1). Whichever Dafny
     picks by default is an implicit dependency, so this module PINS it with
     --solver-path and records which one ran. Never inherit the default.
  2. Z3 IS NONDETERMINISTIC. The same file at the same limit can verify on one run
     and time out on the next. `--resource-limit` (rlimit) is a DETERMINISTIC
     budget where wall-clock is not, so rlimit is the primary bound here and the
     wall-clock timeout is only a hang backstop. Use flake_check() before trusting
     any single verdict — the noise-floor discipline the ruler already applies.

THE OUTCOME TAXONOMY IS THE POINT (do not collapse it to a bool)
---------------------------------------------------------------
verify_dataset.py's rule is "chosen must PASS and rejected must FAIL", and its
insight is that a rejected which passes is preference noise pointing the wrong
way. Dafny adds two failure modes that a bool would silently merge into "failed",
and both would poison a preference pair:

  MALFORMED (exit 2) — does not parse or resolve. This is NOT a proof failure.
     A `rejected` that merely fails to parse teaches the model syntax, not proof;
     it is a degenerate pair, the exact analogue of a rejected-that-passes, and
     pair_verdict() refuses it.

  VACUOUS (exit 0, contradictory assumptions) — `ensures true`, or a precondition
     nothing can satisfy, verifies INSTANTLY AND CLEANLY. Measured: exit 0, zero
     errors, indistinguishable from a real proof by exit code alone. This is the
     "passing for the wrong reason" failure relocated from the benchmark to the
     specification, and it is the one a self-improving loop will find on its own,
     because a model rewarded for `dafny verify` exit 0 can always weaken the
     spec instead of proving the theorem. --warn-contradictory-assumptions makes
     it visible; this module makes it a distinct outcome so it can never be
     counted as a win.

EXIT CODES ARE MEASURED, NOT ASSUMED (dafny 4.11.0, this box):
     0 = verified · 2 = parse/resolution error · 4 = verification failed
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCHEMA = 1

# Deterministic default budget. Dafny's own docs call rlimit the deterministic
# alternative to a time limit; this number is the knob a dataset is pinned to, so
# it belongs in the fingerprint and changing it invalidates a receipt.
DEFAULT_RLIMIT = 1_000_000

# Hang backstop ONLY. rlimit is the real bound; if this fires, the run is reported
# TIMEOUT and is never silently folded into "failed to verify".
DEFAULT_WALL_TIMEOUT = 120

DAFNY_HOME = Path(os.environ.get("DAFNY_HOME", Path.home() / ".local" / "dafny"))


class Outcome:
    VERIFIED = "verified"      # exit 0, no vacuity warning — a real proof
    VACUOUS = "vacuous"        # exit 0, but proved under contradictory assumptions
    REFUTED = "refuted"        # exit 4 — the honest "this is wrong"
    MALFORMED = "malformed"    # exit 2 — does not parse/resolve; NOT a proof failure
    TIMEOUT = "timeout"        # wall backstop fired; we do NOT know if it is wrong
    TOOL_ERROR = "tool_error"  # anything else; never counted as evidence


@dataclass
class DafnyResult:
    """Mirrors forge.Result's contract: `ok` is the reward, everything else is why."""
    source_sha256: str
    outcome: str
    ok: bool = False           # True ONLY for Outcome.VERIFIED — vacuous is not a win
    exit_code: int = -1
    wall_ms: int = 0
    rlimit: int = DEFAULT_RLIMIT
    error: str = ""
    timed_out: bool = False
    diagnostics: list = field(default_factory=list)   # parsed --json-output records
    vacuity_warnings: list = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dafny_bin() -> Path:
    exe = DAFNY_HOME / "dafny"
    if exe.exists():
        return exe
    found = shutil.which("dafny")
    if not found:
        raise SystemExit(
            f"GATE: no dafny at {exe} and none on PATH.\n"
            f"  Set DAFNY_HOME, or install: https://github.com/dafny-lang/dafny/releases")
    return Path(found)


def _solver_path() -> Path | None:
    """PIN the solver. Two z3 binaries ship here; inheriting the default makes the
    verdict depend on an unrecorded choice. Highest version wins, and which one it
    was goes in the fingerprint."""
    zdir = DAFNY_HOME / "z3" / "bin"
    if not zdir.is_dir():
        return None
    cands = sorted((p for p in zdir.iterdir() if p.name.startswith("z3-") and os.access(p, os.X_OK)),
                   key=lambda p: [int(x) for x in p.name.split("-")[1].split(".") if x.isdigit()])
    return cands[-1] if cands else None


_FINGERPRINT: dict | None = None


def toolchain_fingerprint(rlimit: int = DEFAULT_RLIMIT) -> dict:
    """What "verified" MEANS, as bytes and versions — the dataset_gate.py rule applied
    to a solver instead of an interpreter. Whole-binary hashes, no hand-picked scope:
    picking "the parts of a solver that matter" is the invented-scope mistake."""
    global _FINGERPRINT
    if _FINGERPRINT is not None and _FINGERPRINT.get("rlimit") == rlimit:
        return _FINGERPRINT
    dbin = _dafny_bin()
    ver = subprocess.run([str(dbin), "--version"], capture_output=True, text=True,
                         timeout=60).stdout.strip()
    fp = {
        "schema": SCHEMA,
        "dafny_version": ver,
        "dafny_bin": str(dbin),
        "dafny_sha256": sha256_file(dbin),
        "rlimit": rlimit,
        # These flags are part of the meaning. --warn-contradictory-assumptions is
        # what makes VACUOUS observable at all; drop it and vacuous proofs silently
        # become VERIFIED, i.e. a passing receipt for a weaker claim.
        "flags": ["--json-output", "--warn-contradictory-assumptions", "--allow-warnings"],
    }
    sp = _solver_path()
    if sp:
        sv = subprocess.run([str(sp), "--version"], capture_output=True, text=True,
                            timeout=60).stdout.strip()
        fp.update(solver_path=str(sp), solver_version=sv, solver_sha256=sha256_file(sp))
    else:
        fp.update(solver_path=None, solver_version="<dafny default — UNPINNED>",
                  solver_sha256=None)
    _FINGERPRINT = fp
    return fp


def _parse_json_lines(stdout: str) -> tuple[list, list]:
    """--json-output emits one JSON object per line. Returns (diagnostics, vacuity)."""
    diags, vac = [], []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "diagnostic":
            continue
        v = obj.get("value", {})
        msg = (v.get("defaultFormatMessage") or "")
        diags.append({
            "severity": v.get("severity"),
            "message": msg,
            "source": v.get("source"),
            "line": (v.get("location", {}).get("range", {}).get("start", {}).get("line")),
            "related": [r.get("defaultFormatMessage", "")
                        for r in (v.get("relatedInformation") or [])],
        })
        if "contradictory" in msg.lower() or "vacuous" in msg.lower():
            vac.append(msg)
    return diags, vac


def verify_source(source: str, rlimit: int = DEFAULT_RLIMIT,
                  wall_timeout: int = DEFAULT_WALL_TIMEOUT) -> DafnyResult:
    """Verify Dafny SOURCE TEXT. The unit of reward."""
    src_hash = sha256_bytes(source.encode("utf-8"))
    with tempfile.TemporaryDirectory(prefix="dfyverify-") as td:
        f = Path(td) / "candidate.dfy"
        f.write_text(source, encoding="utf-8")
        return _run(f, src_hash, rlimit, wall_timeout)


def verify_path(path: str | Path, rlimit: int = DEFAULT_RLIMIT,
                wall_timeout: int = DEFAULT_WALL_TIMEOUT) -> DafnyResult:
    p = Path(path)
    return _run(p, sha256_file(p), rlimit, wall_timeout)


def _run(f: Path, src_hash: str, rlimit: int, wall_timeout: int) -> DafnyResult:
    fp = toolchain_fingerprint(rlimit)
    cmd = [fp["dafny_bin"], "verify",
           "--json-output",
           "--resource-limit", str(rlimit),
           # Vacuity must be OBSERVED, not fatal: we want it classified, not turned
           # into a generic non-zero exit that looks like an honest refutation.
           "--warn-contradictory-assumptions", "--allow-warnings"]
    if fp.get("solver_path"):
        cmd += ["--solver-path", fp["solver_path"]]
    cmd.append(str(f))

    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=wall_timeout)
    except subprocess.TimeoutExpired:
        return DafnyResult(source_sha256=src_hash, outcome=Outcome.TIMEOUT, ok=False,
                           wall_ms=int((time.monotonic() - t0) * 1000), rlimit=rlimit,
                           timed_out=True, error=f"wall timeout >{wall_timeout}s")
    wall_ms = int((time.monotonic() - t0) * 1000)
    diags, vac = _parse_json_lines(proc.stdout)

    if proc.returncode == 0:
        outcome = Outcome.VACUOUS if vac else Outcome.VERIFIED
    elif proc.returncode == 4:
        outcome = Outcome.REFUTED
    elif proc.returncode == 2:
        outcome = Outcome.MALFORMED
    else:
        outcome = Outcome.TOOL_ERROR

    err = ""
    if outcome in (Outcome.MALFORMED, Outcome.TOOL_ERROR):
        err = (proc.stderr.strip() or "; ".join(d["message"] for d in diags))[:600]

    return DafnyResult(source_sha256=src_hash, outcome=outcome,
                       ok=(outcome == Outcome.VERIFIED),
                       exit_code=proc.returncode, wall_ms=wall_ms, rlimit=rlimit,
                       error=err, diagnostics=diags, vacuity_warnings=vac)


def flake_check(source: str, n: int = 3, rlimit: int = DEFAULT_RLIMIT) -> dict:
    """Z3 IS NONDETERMINISTIC. Run the same source n times; a stable verdict is one
    that agrees with itself. A dataset built from single runs inherits the flake rate
    as unmeasured label noise — the same reason the ruler's noise floor is measured
    rather than assumed."""
    outs = [verify_source(source, rlimit=rlimit).outcome for _ in range(n)]
    uniq = sorted(set(outs))
    return {"runs": n, "outcomes": outs, "stable": len(uniq) == 1, "distinct": uniq}


def pair_verdict(chosen: str, rejected: str, rlimit: int = DEFAULT_RLIMIT) -> dict:
    """THE GATE, in verify_dataset.py's shape: chosen must pass, rejected must fail —
    with the two Dafny-specific refusals that a bool would hide.

    A pair is USABLE only when:
      chosen   is VERIFIED   (not VACUOUS — a weakened spec is not a proof)
      rejected is REFUTED    (not MALFORMED — "does not parse" is not "is wrong",
                              and training on it teaches syntax, not proof)
    Everything else is degenerate signal and is named, so it can be counted rather
    than silently dropped."""
    c = verify_source(chosen, rlimit=rlimit)
    r = verify_source(rejected, rlimit=rlimit)
    reasons = []
    if c.outcome == Outcome.VACUOUS:
        reasons.append("chosen_vacuous: verified under contradictory assumptions")
    elif c.outcome != Outcome.VERIFIED:
        reasons.append(f"chosen_not_verified: {c.outcome}")
    if r.outcome == Outcome.MALFORMED:
        reasons.append("rejected_malformed: fails to parse/resolve, not a proof failure")
    elif r.outcome == Outcome.VERIFIED:
        reasons.append("rejected_verified: preference noise pointing the wrong way")
    elif r.outcome != Outcome.REFUTED:
        reasons.append(f"rejected_not_refuted: {r.outcome}")
    return {"usable": not reasons, "violations": reasons,
            "chosen": c.to_json(), "rejected": r.to_json()}



# ---------------------------------------------------------------------------
# SPEC STRENGTH — the vacuity that no Dafny flag can catch.
#
# --warn-contradictory-assumptions finds proofs resting on an UNSATISFIABLE
# hypothesis (`requires x > 0 && x < 0`). It does NOT find a spec that is merely
# WEAK. Measured on this box: `method M() returns (r:int) ensures true { r:=0; }`
# verifies at exit 0 with no warning, because the proof is genuinely valid — the
# specification is the useless part, and Dafny has nothing to complain about.
#
# That is the failure a reward-seeking loop converges on. A model paid for exit 0
# can always weaken the `ensures` instead of proving the theorem, and every gate
# above would score it a win.
#
# THE ORACLE IS MUTATION, and it needs no parser for the spec itself: replace the
# body with a HAVOC (`r := *;`, an arbitrary value) and re-verify.
#   still verifies -> the postcondition is satisfied by ANY result -> spec is weak
#   now fails      -> the postcondition actually constrains the result -> adequate
# Measured: `ensures true` havocs to exit 0; a real Max postcondition to exit 4.
#
# ⚠ WHAT THIS DOES NOT COVER, stated so it is not mistaken for more than it is:
#   - Methods with NO out-parameters have nothing to havoc; they are reported
#     "unchecked", never "adequate". Silence is not a pass.
#   - It tests whether the spec constrains the RESULT. It cannot tell you the spec
#     matches the author's INTENT — a strong-but-wrong `ensures` passes this and is
#     still wrong. That gap is what natural-language statements plus I/O examples
#     are for, and it is why the test-case corpora matter here.
#   - Body extraction is best-effort brace matching. It REFUSES rather than guesses:
#     an unparseable method is "unchecked", not "adequate".
# ---------------------------------------------------------------------------

_SPEC_KW = ("requires", "ensures", "modifies", "decreases", "reads", "invariant")


def _find_body(src: str, start: int) -> tuple[int, int] | None:
    """Brace-match the method body beginning at/after `start`. Skips set/map literals
    that appear in spec clauses by checking what follows the matched region."""
    i = start
    n = len(src)
    while i < n:
        if src[i] != "{":
            i += 1
            continue
        depth, j = 0, i
        while j < n:
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            return None
        tail = src[j + 1:].lstrip()
        # If a spec keyword follows, the braces we matched were a literal inside a
        # spec clause, not the body. Keep looking.
        if any(tail.startswith(k) for k in _SPEC_KW):
            i = j + 1
            continue
        return i, j
    return None


def havoc_method(src: str, m):
    """Return src with ONE method's body replaced by havoc assignments, or None."""
    outs = m.group("outs")
    names = []
    for part in outs.split(","):
        part = part.strip()
        if not part:
            continue
        nm = part.split(":")[0].strip()
        if nm.isidentifier():
            names.append(nm)
    if not names:
        return None
    body = _find_body(src, m.end())
    if not body:
        return None
    a, b = body
    return src[:a] + "{ " + " ".join(f"{n} := *;" for n in names) + " }" + src[b + 1:]


def spec_strength(source: str, rlimit: int = DEFAULT_RLIMIT) -> dict:
    """Per-method spec-adequacy. One verification per method, so keep candidates small."""
    import re
    pat = re.compile(
        r"\bmethod\s+(?P<name>\w+)\s*(?:<[^>]*>)?\s*\([^)]*\)\s*"
        r"returns\s*\((?P<outs>[^)]*)\)")
    weak, adequate, unchecked = [], [], []
    for m in pat.finditer(source):
        mutated = havoc_method(source, m)
        if mutated is None:
            unchecked.append(m.group("name"))
            continue
        res = verify_source(mutated, rlimit=rlimit)
        if res.outcome in (Outcome.VERIFIED, Outcome.VACUOUS):
            weak.append(m.group("name"))       # any value satisfies the spec
        elif res.outcome == Outcome.REFUTED:
            adequate.append(m.group("name"))   # the spec caught an arbitrary result
        else:
            unchecked.append(m.group("name"))  # malformed mutation: refuse, do not guess
    return {"weak": weak, "adequate": adequate, "unchecked": unchecked,
            "any_weak": bool(weak),
            "checked": len(weak) + len(adequate)}

def verify_files(paths, rlimit: int = DEFAULT_RLIMIT, workers: int = 8) -> list:
    """Parallel sweep. Shared box — keep `workers` modest; each Dafny run spawns Z3."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda p: (str(p), verify_path(p, rlimit=rlimit)), paths))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Dafny ground-truth verifier for srlm-forge")
    ap.add_argument("paths", nargs="*", help=".dfy files to verify")
    ap.add_argument("--rlimit", type=int, default=DEFAULT_RLIMIT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--fingerprint", action="store_true", help="print the toolchain fingerprint")
    a = ap.parse_args()

    if a.fingerprint or not a.paths:
        print(json.dumps(toolchain_fingerprint(a.rlimit), indent=2))
        if not a.paths:
            raise SystemExit(0)

    tally: dict[str, int] = {}
    for name, res in verify_files(a.paths, rlimit=a.rlimit, workers=a.workers):
        tally[res.outcome] = tally.get(res.outcome, 0) + 1
        print(f"{res.outcome:10s} {res.wall_ms:6d}ms  {name}")
    print("\n" + json.dumps(tally, indent=2))
