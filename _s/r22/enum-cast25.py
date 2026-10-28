"""Enumerate GC core.das EFF #16 / #25 ids: GC keys, PS2 counterpart, rooms whose resident list holds a key, fx lib coverage."""
import glob, json, os, sys
from pathlib import Path
D = Path("/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367")
sys.path.insert(0, str(D / "test12fx"))
import fx_ps2_pack as F
IN = Path("/root/work/lanes/cast-ps2-25/_s/r22/in")
gc_ids, gc_tpls = F.gc_eff_tables(IN, ["core.das"], "etc/core.das")
print("ctxs", {k: len(v) for k, v in gc_ids.items()})
blob = (IN / "Core.dat").read_bytes()
ps2 = {}
for k, (ty, s0, s1) in enumerate(F.dat_entries(blob)):
    if ty == "EFF":
        try:
            ps2[k] = F.ps2_eff_textures(blob[s0:s1])
        except Exception as ex:
            print("ps2 skip", k, ex)
rooms = {}
for f in glob.glob(str(D / "vram/resident/*.tsv")) + glob.glob(str(D / "vram/resident/*/*.tsv")):
    r = Path(f).stem
    for l in open(f):
        k = l.split("\t")[0].strip()
        rooms.setdefault(k, set()).add(r)
out = []
for ctx in sorted(gc_ids):
    if ctx == "etc/core.das:0#1":
        continue
    ent = dict(F.pair_effs({ctx: gc_ids[ctx]}, ps2))[ctx]
    for n, tid in enumerate(gc_ids[ctx]):
        keys = [k for k, w, h in gc_tpls.get("%s/tpl%d" % (ctx, n), [])]
        sz = [(w, h) for k, w, h in gc_tpls.get("%s/tpl%d" % (ctx, n), [])][:1]
        rs = sorted(set().union(*[rooms.get(k, set()) for k in keys])) if keys else []
        pp = ps2.get(ent, {}).get(tid) if ent is not None else None
        conv = pp is not None and all(p is not None for p in pp)
        out.append(dict(ctx=ctx, id=tid, ps2_ent=ent, ps2=pp is not None, convertible=conv, frames=len(keys), size=sz, rooms=rs, keys=keys))
        print(ctx, hex(tid), "ps2" if pp is not None else "NOPS2", "conv" if conv else "-", len(keys), sz, ",".join(rs))
json.dump(out, open(sys.argv[1], "w"), indent=1)
