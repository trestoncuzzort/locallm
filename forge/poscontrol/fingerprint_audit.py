import json, collections

ROWS = [json.loads(l) for l in
        open("data/ruler_noise.jsonl", encoding="utf-8") if l.strip()]

SUFFIXES = ("-rep", "-rep1", "-rep2", "-null-rep")
seen = collections.OrderedDict()
for r in ROWS:
    m = r["model"]
    if not m.endswith(SUFFIXES):
        continue
    v = r.get("verifier") or {}
    key = (m,
           str(v.get("forge.py", "?"))[:12],
           str(v.get("screen_tasks.py", "?"))[:12],
           str(v.get("task_bank.py", "?"))[:12],
           str(v.get("data/screen_results.jsonl", "?"))[:12],
           str(v.get("version", "?")))
    ent = seen.setdefault(key, [0, None, None])
    ent[0] += 1
    ts = r.get("ts")
    if ent[1] is None:
        ent[1] = ts
    ent[2] = ts

hdr = "%-24s%-14s%-14s%-14s%-14s%-9s%-5s%s" % (
    "model", "forge", "screen_tasks", "task_bank", "screen_res", "py", "n", "window")
print(hdr)
for k, (n, t0, t1) in seen.items():
    print("%-24s%-14s%-14s%-14s%-14s%-9s%-5d%s -> %s"
          % (k[0], k[1], k[2], k[3], k[4], k[5], n, t0, t1))
