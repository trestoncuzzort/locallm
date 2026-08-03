#!/usr/bin/env python3
"""analyze_run1.py — the preregistered comparison, and nothing more than it.

Runs exactly the analysis fixed in data/prereg_track_a_run1.json BEFORE the
first replicate was scored: run-level greedy-free pass@1, Welch on each arm's
OWN standard deviation (never pooled), two-sided, alpha 0.05, fixed N = 40 per
arm.

Welch and not Student's t because pooling assumes the two arms have the same
variance, and the whole question is whether training changed the model -- a
change in spread is a change. Pooling would hide it in the denominator.

A paired per-task comparison is reported SECOND, as a secondary view. Both arms
see the identical frozen task set, so pairing removes between-task difficulty,
which is the largest source of variance here. It is secondary because the
preregistration named the run-level test as primary, and promoting whichever
test gives the better answer after seeing both is the exact move preregistration
exists to prevent.

No scipy on this machine, so the t distribution is implemented here: the
regularised incomplete beta by continued fraction, and the critical value by
bisection on that CDF. Checked against known values in main().
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOISE = HERE / "data" / "ruler_noise.jsonl"
TRAINED, NULL = "llama3-forged", "llama3-forged-null"
BASE = "llama3:8b-instruct-q4_K_M"
MDE_PP = 2.98          # preregistered minimum detectable effect


# --- t distribution, since scipy is not installed -------------------------
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (Lentz's method)."""
    tiny, eps = 1e-30, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < tiny:
            d = tiny
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < tiny:
            d = tiny
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_sf(t: float, df: float) -> float:
    """P(T > t): the upper tail of Student's t."""
    x = df / (df + t * t)
    tail = 0.5 * _betai(df / 2.0, 0.5, x)
    return tail if t > 0 else 1.0 - tail


def t_crit(df: float, alpha: float = 0.05) -> float:
    """Two-sided critical value, by bisection on the CDF."""
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_sf(mid, df) > alpha / 2.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# --- statistics -----------------------------------------------------------
def mean(v: list[float]) -> float:
    return sum(v) / len(v)


def sd(v: list[float]) -> float:
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def welch(a: list[float], b: list[float]) -> dict:
    """Welch's t-test. Each arm keeps its own variance; nothing is pooled."""
    na, nb = len(a), len(b)
    va, vb = sd(a) ** 2, sd(b) ** 2
    se = math.sqrt(va / na + vb / nb)
    diff = mean(a) - mean(b)
    df = (va / na + vb / nb) ** 2 / (
        (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    t = diff / se if se else 0.0
    tc = t_crit(df)
    return {"diff": diff, "se": se, "df": df, "t": t,
            "p": 2.0 * t_sf(abs(t), df),
            "ci": (diff - tc * se, diff + tc * se)}


def paired(a: list[float], b: list[float]) -> dict:
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    se = sd(d) / math.sqrt(n)
    t = mean(d) / se if se else 0.0
    tc = t_crit(n - 1)
    return {"diff": mean(d), "se": se, "df": n - 1, "t": t,
            "p": 2.0 * t_sf(abs(t), n - 1),
            "ci": (mean(d) - tc * se, mean(d) + tc * se)}


def load() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with open(NOISE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                out.setdefault(r.get("model"), []).append(r)
    return out


def rate(row: dict) -> float:
    agg = row["aggregate"]
    return agg["pass@1"] if isinstance(agg, dict) else float(agg)


def main() -> int:
    # Self-check the t implementation before trusting a p-value from it.
    assert abs(t_crit(10) - 2.228) < 0.002, t_crit(10)
    assert abs(t_crit(78) - 1.991) < 0.003, t_crit(78)
    assert abs(2 * t_sf(2.0, 30) - 0.0546) < 0.001, 2 * t_sf(2.0, 30)

    by = load()
    tr = [rate(r) for r in by.get(TRAINED, [])]
    nu = [rate(r) for r in by.get(NULL, [])]
    ba = [rate(r) for r in by.get(BASE, [])]

    print("=" * 66)
    print("  RUN 1 RE-SCORE - the preregistered comparison")
    print("=" * 66)
    print(f"  metric   : greedy-free run-level pass@1")
    print(f"  arms     : trained={len(tr)}  null={len(nu)}   (prereg: 40 each)")
    if len(tr) != 40 or len(nu) != 40:
        print("  !! N does not match the preregistration; reporting anyway.")

    print(f"\n  trained  mean {mean(tr):.4f}   sd {sd(tr):.4f}")
    print(f"  null     mean {mean(nu):.4f}   sd {sd(nu):.4f}")
    if ba:
        print(f"  base     mean {mean(ba):.4f}   sd {sd(ba):.4f}   "
              f"(n={len(ba)}, reference only)")

    w = welch(tr, nu)
    pp = w["diff"] * 100
    print("\n  PRIMARY - Welch, two-sided, unpooled")
    print(f"    difference   {pp:+.2f} pp   (trained minus null)")
    print(f"    95% CI       [{w['ci'][0]*100:+.2f}, {w['ci'][1]*100:+.2f}] pp")
    print(f"    t = {w['t']:.3f}   df = {w['df']:.1f}   p = {w['p']:.4f}")
    print(f"    prereg MDE   {MDE_PP:.2f} pp -> "
          f"{'CLEARS' if abs(pp) >= MDE_PP else 'does NOT clear'}")
    print(f"    at alpha .05 -> "
          f"{'SIGNIFICANT' if w['p'] < 0.05 else 'not significant'}")

    # Secondary: pair by task. Same frozen tasks in both arms.
    # per_task is a LIST of {tid, greedy, sampled}, not a mapping.
    def entries(r):
        pt = r["per_task"]
        return pt if isinstance(pt, list) else [
            dict(v, tid=k) for k, v in pt.items()]

    tasks = sorted({e["tid"] for r in by.get(TRAINED, []) for e in entries(r)})

    def per_task_mean(rows, tid):
        vals = []
        for r in rows:
            for e in entries(r):
                if e.get("tid") != tid:
                    continue
                s = e.get("sampled") or []
                vals.append(sum(s) / len(s) if s else 0.0)
        return mean(vals) if vals else None
    ta = [per_task_mean(by[TRAINED], t) for t in tasks]
    tb = [per_task_mean(by[NULL], t) for t in tasks]
    keep = [(x, y) for x, y in zip(ta, tb) if x is not None and y is not None]
    if len(keep) > 2:
        p = paired([x for x, _ in keep], [y for _, y in keep])
        print(f"\n  SECONDARY - paired by task (n={len(keep)} tasks)")
        print(f"    difference   {p['diff']*100:+.2f} pp")
        print(f"    95% CI       [{p['ci'][0]*100:+.2f}, "
              f"{p['ci'][1]*100:+.2f}] pp")
        print(f"    t = {p['t']:.3f}   df = {p['df']}   p = {p['p']:.4f}")

    print("\n  WHAT THIS CANNOT SHOW: one checkpoint per arm. Zero training-seed")
    print("  variance by construction, so this cannot support a claim about DPO")
    print("  at any k. A look, not a verdict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
