"""poscontrol_verdict.py — the decision-rule script for data/prereg_positive_control.json.

Applies the prereg's fixed-in-advance rule (Welch's t-test, two-sided, alpha=.05,
on run-level pass@1) to the two arms named in that prereg. Success iff p<.05 AND
observed effect (positive_control - null) >= +5.00pp. Reuses the same ms()/welch()
math as control_verdict.py rather than importing it, because that script is a
hardcoded historical record of the Aug 4/5 analysis and is not meant to be reused
as a library for a different day's arms.

Run: .venv-train\\Scripts\\python.exe poscontrol\\poscontrol_verdict.py
"""
import json
import math
import collections
from pathlib import Path

PREREG = json.loads(Path("data/prereg_positive_control.json").read_text(encoding="utf-8"))
POS_ARM = PREREG["arms"]["positive_control"]
NULL_ARM = PREREG["arms"]["null"]
THRESHOLD_PP = 5.00
ALPHA = 0.05

ROWS = [json.loads(l) for l in
        open("data/ruler_noise.jsonl", encoding="utf-8") if l.strip()]

arms = collections.defaultdict(list)
win = {}
for r in ROWS:
    m = r.get("model")
    if m in (POS_ARM, NULL_ARM):
        arms[m].append(r["aggregate"]["pass@1"])
        ts = r.get("ts")
        win.setdefault(m, [ts, ts])
        win[m][1] = ts


def ms(v):
    n = len(v)
    m = sum(v) / n
    s = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else 0.0
    return n, m, s


def welch(a, b):
    na, ma, sa = ms(a)
    nb, mb, sb = ms(b)
    va, vb = sa * sa / na, sb * sb / nb
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va * va / (na - 1) + vb * vb / (nb - 1))
    t = (ma - mb) / se
    # Regularized incomplete beta via Lentz continued fraction, same approach
    # the paper's own Appendix A implementation used, so p-values here are
    # computed the same way rather than eyeballed against a table.
    p = _t_two_sided_p(t, df)
    return (ma - mb), se, t, df, p


def _betacf(a, b, x, itmax=200, eps=3e-12):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                   + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_two_sided_p(t, df):
    x = df / (df + t * t)
    return _betai(df / 2.0, 0.5, x)


print("%-28s%5s%9s%9s   %s" % ("arm", "n", "mean", "sd", "window"))
for m in (POS_ARM, NULL_ARM):
    if m in arms:
        n, mu, sd = ms(arms[m])
        print("%-28s%5d%9.4f%9.4f   %s -> %s"
              % (m, n, mu, sd, win[m][0], win[m][1]))
    else:
        print("%-28s  NO ROWS YET" % m)

print()
print("=== PREREG DECISION RULE (data/prereg_positive_control.json) ===")
print(f"  success iff p < {ALPHA} AND effect >= +{THRESHOLD_PP:.2f}pp")

if POS_ARM in arms and NULL_ARM in arms:
    n_pos = len(arms[POS_ARM])
    n_null = len(arms[NULL_ARM])
    diff, se, t, df, p = welch(arms[POS_ARM], arms[NULL_ARM])
    pp = diff * 100
    sig = p < ALPHA
    big = pp >= THRESHOLD_PP
    verdict = "SUCCESS" if (sig and big) else "NOT SUCCESS"
    print(f"  n = {n_pos}/{n_null} (positive_control/null)")
    if n_pos < 40 or n_null < 40:
        print("  ** FEWER THAN 40 REPLICATES PER ARM ** -- this is a peek, not the "
              "fixed-N result. Do not treat this verdict as final until both arms "
              "reach 40.")
    print(f"  effect (pos - null) = {pp:+.3f}pp   SE={se*100:.3f}pp   "
          f"t({df:.1f})={t:.3f}   p={p:.4g}")
    print(f"  significant (p<{ALPHA})?  {sig}")
    print(f"  effect >= {THRESHOLD_PP}pp?   {big}")
    print(f"  VERDICT: {verdict}")
else:
    print("  Not enough data yet -- one or both arms have zero rows in "
          "data/ruler_noise.jsonl.")
