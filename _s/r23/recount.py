import json, re, glob, os
P = json.load(open("prov/proofs.json"))
rows = P if isinstance(P, list) else next(v for v in P.values() if isinstance(v, list))
now = {(x["kind"], x["sha256"]): x["provenance"] for x in rows}
import sys; EV = sys.argv[1]
for d in sorted(glob.glob(EV + "gca-*")):
    f = d + "/run-output.txt"
    if not os.path.exists(f):
        continue
    per = {}
    for l in open(f, errors="replace"):
        m = re.match(r"GC-ASSET v=2 room=(\w+) .*kind=(\S+) id=(\S+) sha256=(\S+) provenance=(\S+)", l)
        if m and m.group(5) in ("gc", "unknown"):
            b, a = per.setdefault(m.group(1), (set(), set()))
            key = (m.group(2), m.group(3))
            b.add(key)
            kk = m.group(2) if m.group(2) != "texture" else "texture"
            if now.get((kk, m.group(4)), m.group(5)) != "ps2":
                a.add(key)
    for room, (b, a) in sorted(per.items()):
        print("%-10s room %-5s before %3d  after %3d  cleared: %s" % (os.path.basename(d), room, len(b), len(a), " ".join(sorted(k[1] for k in b - a))[:400]))
