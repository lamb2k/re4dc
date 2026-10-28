import sys
from pathlib import Path
T = Path("/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367/test12fx")
sys.path.insert(0, str(T))
import fx_ps2_pack as F

IN = Path("/root/work/lanes/cast-ps2-25/_s/r21/fx/in")
out, want = Path(sys.argv[1]), sys.argv[2]
gc_ids, gc_tpls = F.gc_eff_tables(IN, ["core.das"], "etc/core.das")
hit = None
for ctx, ids in gc_ids.items():
    for n, tid in enumerate(ids):
        ks = [k for k, w, h in gc_tpls.get("%s/tpl%d" % (ctx, n), [])]
        if want in ks:
            hit = (ctx, tid, n)
            print("GC", ctx, hex(tid), "tpl", n, "frames", len(ks), ks)
blob = (IN / "Core.dat").read_bytes()
ps2_effs = {}
for k, (ty, s0, s1) in enumerate(F.dat_entries(blob)):
    if ty == "EFF":
        try:
            ps2_effs[k] = F.ps2_eff_textures(blob[s0:s1])
        except Exception as ex:
            print("skip", k, ex)
ctx, tid, n = hit
ent = dict(F.pair_effs({ctx: gc_ids[ctx]}, ps2_effs))[ctx]
print("PS2 EFF entry", ent, "has id", ent is not None and tid in ps2_effs.get(ent, {}))
rows = F.convert_set(ctx, [tid], {"%s/tpl0" % ctx: gc_tpls["%s/tpl%d" % (ctx, n)]},
                     ps2_effs.get(ent, {}) if ent is not None else {}, "Core.dat:%s" % ent, out, {})
print(rows)
