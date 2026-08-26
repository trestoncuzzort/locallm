import json, math, collections

ROWS = [json.loads(l) for l in
        open("data/ruler_noise.jsonl", encoding="utf-8") if l.strip()]

WANT = ("ctl-his", "ctl-null", "llama3-forged-rep", "llama3-forged-null-rep",
        "llama3-forged-rep1", "llama3-forged-rep2")
arms = collections.defaultdict(list)
win = {}
for r in ROWS:
    m = r["model"]
    if m in WANT:
        arms[m].append(r["aggregate"]["pass@1"])
        ts = r.get("ts")
        if m not in win:
            win[m] = [ts, ts]
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
    return (ma - mb), se, ((ma - mb) / se), df


print("%-24s%5s%9s%9s   %s" % ("arm", "n", "mean", "sd", "window"))
for m in WANT:
    if m in arms:
        n, mu, sd = ms(arms[m])
        print("%-24s%5d%9.4f%9.4f   %s -> %s"
              % (m, n, mu, sd, win[m][0], win[m][1]))

print()
print("=== SAME-SESSION CONTROL (today, interleaved) ===")
if "ctl-his" in arms and "ctl-null" in arms:
    d, se, t, df = welch(arms["ctl-his"], arms["ctl-null"])
    print("  his adapter - null : %+.3f pp  SE=%.3f  t(%.1f)=%.3f"
          % (d * 100, se * 100, df, t))
    _, mn, _ = ms(arms["ctl-null"])
    print("  null TODAY  = %.4f" % mn)
    _, myesterday, _ = ms(arms["llama3-forged-null-rep"])
    print("  null YESTERDAY = %.4f   (shift %+.3f pp)"
          % (myesterday, (mn - myesterday) * 100))

print()
print("=== THE QUESTION: are the retrains really above baseline? ===")
if "ctl-null" in arms:
    for rep in ("llama3-forged-rep1", "llama3-forged-rep2"):
        if rep in arms:
            d, se, t, df = welch(arms[rep], arms["ctl-null"])
            print("  %-22s vs null(today): %+.3f pp  SE=%.3f  t(%.1f)=%.3f"
                  % (rep, d * 100, se * 100, df, t))
    if "ctl-his" in arms:
        for rep in ("llama3-forged-rep1", "llama3-forged-rep2"):
            if rep in arms:
                d, se, t, df = welch(arms[rep], arms["ctl-his"])
                print("  %-22s vs HIS(today): %+.3f pp  SE=%.3f  t(%.1f)=%.3f"
                      % (rep, d * 100, se * 100, df, t))
