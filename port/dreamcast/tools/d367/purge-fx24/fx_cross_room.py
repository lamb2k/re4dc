#!/usr/bin/env python3
"""fx_cross_room.py: a GameCube room effect id paired with the same flipbook in ANOTHER PS2 room file (lane purge-fx24).

  fx_cross_room.py check <gc iso> <ps2 dat> <out.png>         compare + contact sheet (GC row over PS2 row)
  fx_cross_room.py pack  <gc iso> <ps2 dat> <in tex.pak> <out dir>   tex.pak with the GC keys as the PS2 pictures

Pairs (PAIRS): r117 GC st1/r117 EFF 0x86 (the church candle flames, 8 x 64x128 frames) <- PS2 r10e.dat EFF #7 0x86:
the PS2 r117.dat has no 0x86 (ps2lib effects-tex NONE) but the PS2 church draws the candles; fx_ps2_pack.py lib pairs
a room only with its own .dat, so this takes the picture from r10e (coordinator decision 10-24). Conversion is
fx_ps2_pack.convert_set (PAL4 ARGB4444, one 16-colour palette per id, cover flags), packed under the GC keys.
Writes <out>/dc/tex.pak, pak-derived.json (base/out sha256, changed keys), report.json.
"""
import hashlib, json, os, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'vram'))
sys.path.insert(0, str(HERE.parent / 'test12fx'))
sys.path.insert(0, str(HERE.parent.parent))
import fx_ps2_pack as F  # noqa: E402
import fx_ps2_sheet as SH  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

# (room, GC room file, GC EFF id, PS2 member, PS2 EFF entry[, PS2 EFF id when it differs from the GC id])
# r202 (lane castle-ps2-26 10-26): the castle candle flames, GC EFF 0x85 (8 x 64x128 frames, st2/r202 EFF #7 tpl1); the
# PS2 r202.dat EFF #7 has no textures (the PS2 castle rooms' EFFs are empty; BIO4DAT scan), the same candle flipbook as
# r117 -> PS2 r10e.dat EFF #7 0x86.
# PS2 EFF entry may be 'N/etXX.eff': member etXX.eff of the PS2 .dat's ETM entry N (an etc effect file); the GC side then
# takes the id from the GC ETM member of the same name (lane fxproof26 10-26).
# r100 (lane fxproof26 10-26): the window-break glass crack, GC ETM et00.eff id 0x14 (one 196x196 picture; key 212e55c1,
# shared by r101 / r105 / r107 et00.eff and r102 et2c.eff) <- PS2 r100.dat ETM (entry 9) et00.eff 0x14 (128x128, the same
# picture by content, d 8.2; the PS2 et00.eff / et2c.eff keep EST5 drawing 0x14, only the 0xd1 shard records are gone).
# r206 (lane fxproof26 10-26): the castle candle glow, GC st2/r206 EFF #7 0xe6 (64x128) <- PS2 r50c.dat EFF #7 0xe6 (the
# same picture, d 4.1); the PS2 r206 SST1-5 records draw that glow with Core 0xe9 (r206's PS2 EFF has no textures).
PAIRS = [('r117', 'st1/r117.das', 0x86, 'r10e.dat', 7),
         ('r202', 'st2/r202.das', 0x85, 'r10e.dat', 7, 0x86),
         ('r100', 'st1/r100.das', 0x14, 'r100.dat', '9/et00.eff'),
         ('r206', 'st2/r206.das', 0xe6, 'r50c.dat', 7)]
if os.environ.get('FXX_ROOMS'):
    PAIRS = [p for p in PAIRS if p[0] in os.environ['FXX_ROOMS'].split(',')]
WORK = Path(os.environ.get('FXX_WORK', '/root/work/lanes/purge-fx24-scratch/xroom'))


def gc_side(iso, rel, gid, member=None):
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / Path(rel).name
    p.write_bytes(GcIso(iso).read('S' + rel[1:]))   # the debug disc names the folder St1
    pics = SH.gc_pictures([(rel, p)])
    ids, tpls = F.gc_eff_tables(p.parent, [p.name], rel)
    for ctx, l in ids.items():
        if member and not ctx.endswith('/' + member):
            continue
        if gid in l:
            n = l.index(gid)
            return ctx, l, tpls, pics.get('%s/tpl%d' % (ctx, n), [])
    raise SystemExit('GC %s has no EFF id %#x' % (rel, gid))


def ps2_side(dat, ent, pname=None):
    """dat: the PS2 member file, or a folder holding it (pname)."""
    b = (Path(dat) / pname if Path(dat).is_dir() else Path(dat)).read_bytes()
    if isinstance(ent, str):   # 'N/etXX.eff': a member of the ETM entry N (header 0x20: u32 size; name 0x20; body)
        n, member = ent.split('/', 1)
        t, o, e = F.dat_entries(b)[int(n)]
        m = b[o:e]
        off = 0x20
        for _ in range(struct.unpack_from('<I', m, 0)[0]):
            size = struct.unpack_from('<I', m, off)[0]
            if m[off + 0x20:off + 0x40].split(b'\0')[0].decode('latin1') == member:
                return F.ps2_eff_textures(m[off + 0x40:off + size])
            if not size:
                break
            off += size
        raise SystemExit('PS2 %s ETM #%s has no %s' % (pname, n, member))
    t, o, e = F.dat_entries(b)[ent]
    return F.ps2_eff_textures(b[o:e])


def member_of(ent):
    return ent.split('/', 1)[1] if isinstance(ent, str) else None


def check(iso, dat, out):
    from PIL import Image
    rep = {}
    for room, rel, gid, pname, ent, *pid in PAIRS:
        ctx, ids, tpls, gp = gc_side(iso, rel, gid, member_of(ent))
        pp = ps2_side(dat, ent, pname).get(pid[0] if pid else gid)
        rep[room] = dict(gc_ctx=ctx, gc_frames=len(gp), gc_size=sorted({(w, h) for _, w, h, _ in gp}),
                         gc_keys=[k for k, _, _, _ in gp], ps2=pname, ps2_frames=len(pp or []),
                         ps2_size=sorted({(q[0], q[1]) for q in pp if q}) if pp else None)
        print(json.dumps(rep[room]))
        n = max(len(gp), len(pp or []))
        sheet = Image.new('RGBA', (128 * n, 256), (0, 0, 0, 255))
        for i, (_, w, h, px) in enumerate(gp):
            sheet.paste(SH.tile(w, h, px), (128 * i, 0))
        for i, q in enumerate(pp or []):
            if q:
                sheet.paste(SH.tile(q[0], q[1], q[2]), (128 * i, 128))
        sheet.save(out if len(PAIRS) == 1 else str(out).replace('.png', '-%s.png' % room))
    return rep


def pack(iso, dat, src, outdir):
    out = Path(outdir)
    pkdir = WORK / 'pkg'
    rows, changed = [], {}
    for room, rel, gid, pname, ent, *pid in PAIRS:
        ctx, ids, tpls, gp = gc_side(iso, rel, gid, member_of(ent))
        ps2 = ps2_side(dat, ent, pname)
        if pid:
            ps2 = {gid: ps2[pid[0]]}
        r = F.convert_set(ctx, [gid], {'%s/tpl0' % ctx: tpls['%s/tpl%d' % (ctx, ids.index(gid))]}, ps2,
                          '%s:%s' % (pname, ent), pkdir, {})
        rows += [dict(r_, room=room) for r_ in r]
    pkgs = F.read_pak(Path(src).read_bytes())
    added = []
    for f in sorted(pkdir.glob('*.re4tex')):
        k = tuple(int(v, 16) for v in f.stem.split('-'))
        if k not in pkgs:
            # pack_add semantics (ch2rooms/pack_add.py): a GC key the base pack does not hold (its picture is still
            # loose / room-side) is added, so the pack, looked up first at run time, draws the PS2 picture.
            added.append(f.stem)
        pkgs[k] = f.read_bytes()
        changed[f.stem] = hashlib.sha256(pkgs[k]).hexdigest()
    (out / 'dc').mkdir(parents=True, exist_ok=True)
    blob, _ = F.texpack.build(pkgs)
    F.texpack.verify(blob)
    (out / 'dc/tex.pak').write_bytes(blob)
    sh = lambda b: hashlib.sha256(b).hexdigest()
    json.dump(dict(base=sh(Path(src).read_bytes()), out=sh(blob), count=len(pkgs), added=sorted(added),
                   changed=sorted(set(changed) - set(added))),
              open(out / 'pak-derived.json', 'w'), indent=1)
    json.dump(dict(rows=rows, packages=changed), open(out / 'report.json', 'w'), indent=1)
    print('pack: %d packages changed, out %s' % (len(changed), sh(blob)))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'check':
        check(a[1], a[2], a[3])
    else:
        pack(a[1], a[2], a[3], a[4])
