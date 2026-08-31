import json, math, collections

ROWS = [json.loads(l) for l in
        open("data/ruler_noise.jsonl", encoding="utf-8") if l.strip()]

ORDER = ["llama3-forged-null-rep", "ctl-null", "ctl-null3",
         "llama3-forged-rep", "ctl-his",
         "llama3-forged-rep1", "llama3-forged-rep2", "llama3-forged-rep3"]
LABEL = {
    "llama3-forged-null-rep": "null        (Aug 4)",
    "ctl-null":               "null        (Aug 5 a)",
    "ctl-null3":              "null        (Aug 5 b)",
    "llama3-forged-rep":      "HIS adapter (Aug 4)",
    "ctl-his":                "HIS adapter (Aug 5)",
    "llama3-forged-rep1":     "retrain 1   (Aug 5)",
    "llama3-forged-rep2":     "retrain 2   (Aug 5)",
    "llama3-forged-rep3":     "retrain 3   (Aug 5)",
}

arms = collections.defaultdict(list)
for r in ROWS:
    if r["model"] in LABEL:
        arms[r["model"]].append(r["aggregate"]["pass@1"])


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


print("%-24s%5s%9s%9s" % ("arm", "n", "mean", "sd"))
for m in ORDER:
    if m in arms:
        n, mu, sd = ms(arms[m])
        print("%-24s%5d%9.4f%9.4f" % (LABEL[m], n, mu, sd))

nulls = arms["llama3-forged-null-rep"] + arms["ctl-null"] + arms["ctl-null3"]
n, mu, sd = ms(nulls)
print()
print("pooled null (n=%d): mean=%.4f sd=%.4f" % (n, mu, sd))
print("  null spread across three sessions: %.4f / %.4f / %.4f"
      % (ms(arms["llama3-forged-null-rep"])[1], ms(arms["ctl-null"])[1],
         ms(arms["ctl-null3"])[1]))

print()
print("=== EACH ADAPTER vs POOLED NULL ===")
for m in ("llama3-forged-rep", "ctl-his",
          "llama3-forged-rep1", "llama3-forged-rep2", "llama3-forged-rep3"):
    if m in arms:
        d, se, t, df = welch(arms[m], nulls)
        print("  %-22s %+7.3f pp  SE=%.3f  t(%.1f)=%6.2f"
              % (LABEL[m], d * 100, se * 100, df, t))

print()
print("=== THE THREE RETRAINS vs EACH OTHER ===")
reps = [("llama3-forged-rep1", "llama3-forged-rep2"),
        ("llama3-forged-rep1", "llama3-forged-rep3"),
        ("llama3-forged-rep2", "llama3-forged-rep3")]
for a, b in reps:
    if a in arms and b in arms:
        d, se, t, df = welch(arms[a], arms[b])
        print("  %s - %s : %+7.3f pp  t(%.1f)=%5.2f"
              % (LABEL[a].split("(")[0].strip(), LABEL[b].split("(")[0].strip(),
                 d * 100, df, t))
