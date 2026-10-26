#!/usr/bin/env python3
"""props_inventory.py: per-room inventory of every room-archive model (room BINs + ETM etc models) in a composed
native room archive (lane props-ps2-26, 2026-10-26).

  props_inventory.py --fixture pkg.json [--rooms r100,r101,...] --out inv.json [--tsv inv.tsv]

For each model: its source in the composed archive (GC = le_mirror(GC BIN) byte for byte; PS2 = equals ps2_objects'
rebuild from the PS2 BIN of the same object (plain or --uv-fold); EMPTY = the emptied form (world-owned / placeholder);
OTHER = changed by another set), whether the PS2 room .dat has a counterpart (ETM: same name; room BIN: the same
archive index holding a BIN whose bounds overlap the GC model's), its triangle counts (GC, PS2 raw) and whether a
Dreamcast reduction (mesh_lod) was applied (props26 stores carry 'lod' in their reports; older sets never did).
"""
import argparse
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]
import ps2_objects as po  # noqa: E402
import ps2_bin as pb  # noqa: E402
import room_smd as rs  # noqa: E402


def bounds(pts):
    return [min(p[a] for p in pts) for a in range(3)], [max(p[a] for p in pts) for a in range(3)]


def gc_bounds(gbin):
    m = po.GcModel(gbin)
    pts = [m.p(r[0]) for p in m.parts for t in p['tris'] for r in t]
    return bounds(pts) if pts else None


def ps2_bounds(pbin):
    pm = pb.parse_bin(pbin)
    pts = [c['p'] for t, cs in pb.triangles(pm) for c in cs]
    return (bounds(pts), sum(1 for _ in pb.triangles(pm))) if pts else (None, 0)


def overlap(a, b):
    """bounds overlap fraction (min over axes of intersection / smaller extent); 1.0 = one box inside the other"""
    if not a or not b:
        return 0.0
    f = 1.0
    for i in range(3):
        lo, hi = max(a[0][i], b[0][i]), min(a[1][i], b[1][i])
        ext = max(1e-3, min(a[1][i] - a[0][i], b[1][i] - b[0][i]))
        f = min(f, max(0.0, hi - lo) / ext if ext > 1e-2 else (1.0 if hi >= lo - 1 else 0.0))
    return f


def classify(cur, gbin, pbin, label):
    cur = cur.rstrip(b'\0')
    if cur == po.to_le(gbin, label).rstrip(b'\0'):
        return 'GC', None
    try:
        if cur == po.to_le(po.rebuild(gbin, None, lambda m: [], allow_empty=True)[0], label).rstrip(b'\0'):
            return 'EMPTY', None
    except Exception:
        pass
    if pbin is not None:
        po.LOD = False   # older sets converted without the reduction step
        for fold in (False, True):
            po.UV_FOLD = fold
            try:
                new, st = po.rebuild(gbin, pbin, tex_map=po.TEX_MAPS.get(label.lower()))
            except Exception:
                continue
            finally:
                po.UV_FOLD = False
            if cur == po.to_le(new, label).rstrip(b'\0'):
                return 'PS2', dict(out_tris=st['out_tris'], uv_fold=fold)
    return 'OTHER', None


def room_rows(room, dar_path, g, iso_ps2, afs):
    dar = Path(dar_path).read_bytes()
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    pay = dar[off:off + size]
    key = next((k for rr, k in g.rooms() if rr == room), None)
    gd = g.read(key)
    if gd[:32] == rs.CONTAINER_MAGIC:
        gd = rs.decode_das(gd)
    ge = rs.tagged_entries(gd, '>')
    le = rs.tagged_entries(pay, '<')
    try:
        pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(iso_ps2, room + '.dat', afs))}
    except Exception:
        pe = {}
    rows = []
    pcache = None
    for i, (tag, s, e) in enumerate(ge):
        t = tag.rstrip(b'\0')
        if t == b'BIN' and i < len(le) and le[i][0].rstrip(b'\0') == b'BIN':
            gbin = gd[s:e]
            try:
                gm = po.GcModel(gbin)
            except Exception as ex:
                rows.append(dict(room=room, kind='room BIN', name=hex(i + 4), source='?', note=str(ex)))
                continue
            gtris = sum(len(p['tris']) for p in gm.parts)
            p = pe.get(i + 4)
            pbin, ptris, ov, parc = None, 0, 0.0, i + 4
            gbd = gc_bounds(gbin)
            if p and p[0] == 'BIN':
                try:
                    pbd, ptris = ps2_bounds(p[1])
                    ov = overlap(gbd, pbd)
                    pbin = p[1] if ov >= 0.5 else None
                except Exception:
                    pbin = None
            if pbin is None and gbd:
                # the PS2 archive may number the object differently: the PS2 BIN whose bounds match both ways best
                best = (0.0, None)
                if pcache is None:
                    pcache = {}
                    for j, (tt, bb) in pe.items():
                        if tt == 'BIN':
                            try:
                                pcache[j] = ps2_bounds(bb)
                            except Exception:
                                pass
                for j, (pbd, pt) in pcache.items():
                    bb = pe[j][1]
                    if not pbd:
                        continue
                    sc = min(overlap(gbd, pbd), min(
                        (min(gbd[1][a] - gbd[0][a], pbd[1][a] - pbd[0][a]) + 1) /
                        (max(gbd[1][a] - gbd[0][a], pbd[1][a] - pbd[0][a]) + 1) for a in range(3)))
                    if sc > best[0]:
                        best = (sc, j, bb, pt)
                if best[0] >= 0.7:
                    parc, pbin, ptris = best[1], best[2], best[3]
                    ov = best[0]
            src, info = classify(pay[le[i][1]:le[i][2]], gbin, pbin, hex(i + 4))
            rows.append(dict(room=room, kind='room BIN', name=hex(i + 4), source=src, gc_tris=gtris,
                             ps2=('yes (arc %s)' % hex(parc)) if pbin is not None else ('no' if not p or p[0] != 'BIN' else 'no (bounds %.2f)' % ov),
                             ps2_arc=hex(parc) if pbin is not None else None,
                             ps2_tris=ptris if pbin is not None else None, out_tris=(info or {}).get('out_tris'),
                             uv_fold=(info or {}).get('uv_fold')))
        if t == b'ETM':
            gb = gd[s:e]
            li = next((j for j, (lt, a, z) in enumerate(le) if lt.rstrip(b'\0') == b'ETM'), None)
            lb = pay[le[li][1]:le[li][2]]
            lents = {n: lb[a:z] for n, a, z in po.etm_entries(lb, '<')}
            pbm = next((b for tt, b in pe.values() if tt == 'ETM'), None)
            pents = {n: pbm[a + 0x40:z] for n, a, z in po.etm_entries(pbm, '<')} if pbm else {}
            for n, a, z in po.etm_entries(gb, '>'):
                if not n.lower().endswith('.bin'):
                    continue
                gbin = gb[a + 0x40:z]
                try:
                    gm = po.GcModel(gbin)
                except Exception as ex:
                    rows.append(dict(room=room, kind='etc', name=n, source='?', note=str(ex)))
                    continue
                gtris = sum(len(p['tris']) for p in gm.parts)
                pbin = pents.get(n)
                ptris = None
                if pbin is not None:
                    try:
                        ptris = ps2_bounds(pbin)[1]
                    except Exception:
                        pass
                src, info = classify(lents[n][0x40:], gbin, pbin, n)
                rows.append(dict(room=room, kind='etc', name=n, source=src, gc_tris=gtris,
                                 ps2='yes' if pbin is not None else 'no', ps2_tris=ptris,
                                 out_tris=(info or {}).get('out_tris'), uv_fold=(info or {}).get('uv_fold')))
    return rows


def main():
    import faulthandler
    import os
    if os.environ.get('INV_TRACE'):
        faulthandler.dump_traceback_later(int(os.environ['INV_TRACE']), repeat=True)
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture', required=True)
    ap.add_argument('--rooms')
    ap.add_argument('--out', required=True)
    ap.add_argument('--tsv')
    a = ap.parse_args()
    from assetpipe.rooms import GcIso
    r = json.load(open(a.fixture))['replace']
    rooms = a.rooms.split(',') if a.rooms else sorted(Path(k).stem for k in r if k.startswith('st1/') and k.endswith('.dar'))
    g = GcIso(po.GC_ISO)
    afs = pb.afs_index(po.PS2_ISO)
    rows = []
    for room in rooms:
        rr = room_rows(room, r['st1/%s.dar' % room], g, po.PS2_ISO, afs)
        rows += rr
        c = {}
        for x in rr:
            c[x['source']] = c.get(x['source'], 0) + 1
        print(room, c, flush=True)
    Path(a.out).write_text(json.dumps(rows, indent=1))
    if a.tsv:
        cols = ['room', 'kind', 'name', 'source', 'ps2', 'gc_tris', 'ps2_tris', 'out_tris', 'uv_fold', 'note']
        Path(a.tsv).write_text('\t'.join(cols) + '\n' + ''.join(
            '\t'.join('' if x.get(k) is None else str(x.get(k)) for k in cols) + '\n' for x in rows))


if __name__ == '__main__':
    main()
