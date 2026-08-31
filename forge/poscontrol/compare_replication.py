"""compare_replication.py — the original measurement against its replication.

Reads data/ruler_noise.jsonl and partitions it into four arms:

    ORIGINAL   llama3-forged            trained, 2026-08-02, author's machine
               llama3-forged-null       null,    2026-08-02, author's machine
    REPLICATION llama3-forged-rep       trained, 2026-08-04, this machine
               llama3-forged-null-rep   null,    2026-08-04, this machine

The two pairs are NOT pooled. They were produced by different verifier states on
different hardware, and pooling them is the exact defect this project already
found in analyze_run1.py (which groups by model name alone and thereby mixes two
samplers and two verifier states inside the base arm). Each pair is analysed on
its own terms; only the two RESULTS are compared.

What replication can and cannot settle here: both pairs measure the SAME two
served artifacts (the adapter GGUF hash is identical on both machines), so this
is a replication of the MEASUREMENT, not of the training. Agreement therefore
speaks to the stability of the instrument, not to training-seed variance -- which
remains zero in both pairs, one checkpoint per arm.

Welch's t implemented locally (no scipy in this venv): regularised incomplete
beta by Lentz continued fraction, with self-checks against known critical values.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "ruler_noise.jsonl"

# The ORIGINAL arms are read from the author's delivered transfer package, not
# from the repo's data file. Two reasons, both load-bearing. (1) The repo file on
# this branch predates his eecdb2e commit and carries only 5 of the 40 null-arm
# replicates; reading it here silently compares against a 5-row null and produces
# a confident wrong answer -- which is exactly what happened on the first run of
# this script. (2) The replication is appending to the repo file WHILE it runs, so
# merging his rows into it mid-run would race the writer. His delivered bytes stay
# untouched as evidence; ours accumulate in the repo; neither is edited to suit
# the other. Override with SRLM_ORIG_ROWS if the package moves.
ORIG_ROWS = Path(os.environ.get(
    "SRLM_ORIG_ROWS",
    r"C:\Users\t\AppData\Local\Temp\claude"
    r"\C--Users-t-source-project"
    r"\496ed0c0-fccf-4e48-bbaa-c663c1320a63\scratchpad\adapter-transfer"
    r"\data\ruler_noise.jsonl"))

ORIG = ("llama3-forged", "llama3-forged-null")
REP = ("llama3-forged-rep", "llama3-forged-null-rep")


# ---------------------------------------------------------------- statistics
def _betacf(a: float, b: float, x: float) -> float:
    TINY, EPS, ITMAX = 1e-300, 3e-16, 400
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < TINY:
        d = TINY
    d = 1.0 / d
    h = d
    for m in range(1, ITMAX + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def t_sf2(t: float, df: float) -> float:
    """Two-sided survival function for Student's t."""
    return betai(df / 2.0, 0.5, df / (df + t * t))


def t_crit(df: float, p: float = 0.975) -> float:
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if 1.0 - t_sf2(mid, df) / 2.0 < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _selfcheck() -> None:
    checks = [(t_crit(10), 2.228, 2e-3), (t_crit(78), 1.991, 2e-3),
              (t_sf2(2.0, 30), 0.0546, 2e-3)]
    for got, want, tol in checks:
        assert abs(got - want) < tol, f"t-impl selfcheck failed: {got} vs {want}"


def mean_sd(v):
    n = len(v)
    m = sum(v) / n
    s = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else 0.0
    return n, m, s


def welch(a, b):
    na, ma, sa = mean_sd(a)
    nb, mb, sb = mean_sd(b)
    va, vb = sa * sa / na, sb * sb / nb
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va * va / (na - 1) + vb * vb / (nb - 1))
    t = (ma - mb) / se
    tc = t_crit(df)
    return dict(diff=ma - mb, se=se, t=t, df=df, p=t_sf2(t, df),
                lo=(ma - mb) - tc * se, hi=(ma - mb) + tc * se)


# ---------------------------------------------------------------- load
def _read(path: Path, arms: dict) -> int:
    n = 0
    if not path.exists():
        return 0
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        arms[r.get("model")].append(r)
        n += 1
    return n


def load():
    """Replication arms from the repo file; ORIGINAL arms from the delivered
    package. Each source contributes only its own arm names, so a row can never
    be counted twice even if both files happen to carry the same model tag."""
    rep_arms: dict = defaultdict(list)
    orig_arms: dict = defaultdict(list)
    n_repo = _read(OUT, rep_arms)
    n_orig = _read(ORIG_ROWS, orig_arms)
    arms: dict = defaultdict(list)
    for m in REP:
        arms[m] = rep_arms.get(m, [])
    for m in ORIG:
        arms[m] = orig_arms.get(m, [])
    print(f"[load] repo rows: {n_repo} ({OUT})")
    print(f"[load] delivered rows: {n_orig} ({ORIG_ROWS.name})")
    return arms


def fingerprint_of(rows) -> str:
    keys = set()
    for r in rows:
        keys |= set((r.get("verifier") or {}).keys())
    hashed = sorted(k for k in keys if k.endswith((".py", ".jsonl")))
    return ",".join(hashed) if hashed else "(interpreter only — no source hashes)"


def report_pair(label, trained_rows, null_rows):
    tp = [r["aggregate"]["pass@1"] for r in trained_rows]
    np_ = [r["aggregate"]["pass@1"] for r in null_rows]
    nt, mt, st = mean_sd(tp)
    nn, mn, sn = mean_sd(np_)
    w = welch(tp, np_)
    print(f"\n=== {label} ===")
    print(f"  trained  n={nt:3d}  M={mt:.4f}  SD={st:.4f}")
    print(f"  null     n={nn:3d}  M={mn:.4f}  SD={sn:.4f}")
    print(f"  diff = {w['diff']*100:+.3f} pp   SE={w['se']*100:.3f} pp")
    print(f"  t({w['df']:.1f}) = {w['t']:.4f}   p = {w['p']:.4f}")
    print(f"  95% CI [{w['lo']*100:+.3f}, {w['hi']*100:+.3f}] pp")
    print(f"  verifier provenance recorded: {fingerprint_of(trained_rows + null_rows)}")
    ts = sorted(r.get("ts", "") for r in trained_rows + null_rows if r.get("ts"))
    if ts:
        print(f"  window: {ts[0]} -> {ts[-1]}")
    return dict(mt=mt, st=st, mn=mn, sn=sn, w=w, tp=tp, np=np_)


def main() -> int:
    _selfcheck()
    arms = load()
    have_orig = all(len(arms.get(m, [])) for m in ORIG)
    have_rep = all(len(arms.get(m, [])) for m in REP)
    if not have_orig:
        print("original arms not present; nothing to compare")
        return 1

    o = report_pair("ORIGINAL (2026-08-02, author's machine)",
                    arms[ORIG[0]], arms[ORIG[1]])
    if not have_rep:
        print("\nreplication arms not present yet")
        return 0
    r = report_pair("REPLICATION (2026-08-04, this machine, interleaved)",
                    arms[REP[0]], arms[REP[1]])

    print("\n=== REPLICATION VERDICT ===")
    print(f"  original   effect: {o['w']['diff']*100:+.3f} pp  "
          f"CI [{o['w']['lo']*100:+.3f}, {o['w']['hi']*100:+.3f}]")
    print(f"  replication effect: {r['w']['diff']*100:+.3f} pp  "
          f"CI [{r['w']['lo']*100:+.3f}, {r['w']['hi']*100:+.3f}]")
    same_sign = (o['w']['diff'] >= 0) == (r['w']['diff'] >= 0)
    in_ci = o['w']['lo'] <= r['w']['diff'] <= o['w']['hi']
    print(f"  same sign: {same_sign}")
    print(f"  replication point estimate inside original's 95% CI: {in_ci}")
    print(f"  both nulls (p>=.05): "
          f"{o['w']['p'] >= .05 and r['w']['p'] >= .05}")

    # Cross-run stability of the SAME served artifact: trained-vs-trained and
    # null-vs-null across machines. This is the between-session variance term the
    # original analysis has no estimate for.
    wt = welch(r['tp'], o['tp'])
    wn = welch(r['np'], o['np'])
    print("\n=== CROSS-RUN (same artifact, different session/machine) ===")
    print(f"  trained rep - trained orig: {wt['diff']*100:+.3f} pp  "
          f"p={wt['p']:.4f}  CI [{wt['lo']*100:+.3f}, {wt['hi']*100:+.3f}]")
    print(f"  null    rep - null    orig: {wn['diff']*100:+.3f} pp  "
          f"p={wn['p']:.4f}  CI [{wn['lo']*100:+.3f}, {wn['hi']*100:+.3f}]")
    print("  (a large shift here with a small within-session effect is the "
          "signature of session variance dominating the quantity under test)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
