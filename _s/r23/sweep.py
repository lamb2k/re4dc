import sys, types, hashlib, json, os, csv
sys.modules["numpy"] = types.ModuleType("numpy")
sys.path.insert(0, "/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367/charbake")
import cb_tex as cb
PAK = "/root/re4data/private/fxc26b-20261026/dc/tex.pak"
LIB = "/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/effects-tex/common/"
G = "/root/rr/work/1026-1350-f82f262c/gca/provenance/"
P = json.load(open(G + "proofs.json"))
rows = P if isinstance(P, list) else next(v for v in P.values() if isinstance(v, list))
prov = {x["id"]: x["provenance"] for x in rows if x.get("kind") == "texture"}
for r in csv.reader(open(G + "unknown-rows.tsv"), delimiter="\t"):
    if len(r) > 1 and r[0] == "texture":
        prov.setdefault(r[1], "unknown")
idx = cb.pak_index(PAK)
lib_rows = {l.split("\t")[2]: l.split("\t") for l in open("/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/INDEX.tsv") if l.startswith("effects-tex\tcommon\t")}
out, todo = [], []
for e in json.load(open("enum.json")):
    for n, k in enumerate(e["keys"]):
        p = prov.get(k, "notincatalog")
        if p == "ps2":
            continue
        inpak = cb.parse_key(k) in idx
        a = hashlib.sha256(cb.pak_get(PAK, cb.parse_key(k))).hexdigest() if inpak else None
        f = LIB + k + ".re4tex"
        b = hashlib.sha256(open(f, "rb").read()).hexdigest() if os.path.exists(f) else None
        st = "LIBMATCH" if a and a == b else ("NOTPAK" if not inpak else "GC")
        gid = "%s:0x%02x" % (e["ctx"], e["id"])
        out.append((st, gid, n, k, p, a, b, len(e["rooms"]), e["rooms"]))
        if st == "GC":
            todo.append((gid, k, e["rooms"]))
import collections
c = collections.Counter((o[0], o[4]) for o in out)
print(c)
for o in out:
    if o[0] != "LIBMATCH":
        print(o[0], o[1], o[2], o[3], o[4], o[7], ",".join(o[8][:8]))
json.dump(out, open("sweep.json", "w"), indent=0)
