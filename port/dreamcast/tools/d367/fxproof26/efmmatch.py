"""efmmatch.py: content-match the EFM_PS2_CUT effect models against every PS2 efm model (lane fxproof26).

For each eff_sys.cpp kEfmPs2Cut row, the GameCube model (ps2_items.room_assets / core_assets, GC side) is compared by
geometry with every efm model of every PS2 EFF: each room .dat EFF entry, each ETM *.eff member, Core.dat EFF entries
(BIO4DAT.AFS). Geometry key: triangle vertex positions rounded to q=0.5 (ps2_items.same_geometry), score = share of
the GC triangles found in the PS2 model; also triangle counts and bounding boxes.
"""
import sys, struct
sys.path.insert(0, '/root/work/lanes/fxproof26')
T = '/root/work/lanes/fxproof26/wt/port/dreamcast/tools'
sys.path[:0] = [T]
import ps2_items as PI  # noqa
po, pb = PI.po, PI.pb

CUT = [('r101', 0x02, 1), ('r106', 0x5a, 1), ('r10a', 0x7b, 1), ('r10b', 0x7b, 1), ('r10b', 0x7c, 1),
       ('r119', 0x14, 1), ('r119', 0x16, 1), ('r119', 0x17, 1), ('r11a', 0x0f, 2), ('core', 0x3e, 0)]


def gc_tris(gc):
    m = po.GcModel(gc)
    return [tuple(m.p(r[0]) for r in t) for p in m.parts for t in p['tris']]


def ps2_tris(b):
    return [tuple(c['p'] for c in cs) for t, cs in pb.triangles(pb.parse_bin(b))]


def desc(tris, q=0.5):
    keys = set(tuple(sorted(tuple(round(x / q) for x in v) for v in t)) for t in tris)
    pts = [v for t in tris for v in t]
    if not pts:
        return keys, None
    bb = tuple(round(max(p[i] for p in pts) - min(p[i] for p in pts), 1) for i in range(3))
    return keys, bb


def ps2_models(src):
    out = []
    for name in sorted(k for k in src.ix if k.lower().endswith('.dat')):
        try:
            p = pb.afs_read(src.ps2_iso, name, src.ix)
            ents = pb.dat_entries(p)
        except Exception:
            continue
        for i, t, bb in ents:
            bodies = []
            if t == 'EFF':
                bodies.append(('#%d:EFF' % i, bb))
            if t == 'ETM':
                try:
                    for nm, s2, e2 in po.etm_entries(bb, '<'):
                        if nm.endswith('.eff'):
                            bodies.append(('#%d:ETM/%s' % (i, nm), bb[s2 + 0x40:e2]))
                except Exception:
                    pass
            for loc, body in bodies:
                try:
                    efm = PI.eff_efm(body, '<')
                except Exception:
                    continue
                for idv, mo, to in efm:
                    try:
                        tr = ps2_tris(body[mo:to])
                    except Exception:
                        continue
                    out.append(('%s %s efm%#x @%#x' % (name, loc, idv, mo), idv, tr))
    return out


def main():
    src = PI.Sources()
    gcm = {}
    for room, idv, kind in CUT:
        al = PI.core_assets(src) if room == 'core' else PI.room_assets(src, room)
        for cls, name, loc, gb, gt, pb_, pt_ in al:
            if cls == 'breakables' and loc['id'] == idv and (
                    (kind == 0 and loc['kind'] == 'CORE') or (kind == 1 and loc['kind'] == 'EFF') or
                    (kind == 2 and loc['kind'] == 'ETM')):
                gcm[(room, idv, name)] = (gc_tris(gb), pb_ is not None)
    print('gc models', len(gcm), [(k, len(v[0]), v[1]) for k, v in gcm.items()])
    pm = [(n, i, t, desc(t)) for n, i, t in ps2_models(src)]
    print('ps2 efm models', len(pm))
    for k, (tris, has) in sorted(gcm.items()):
        gk, gbb = desc(tris)
        res = []
        for n, i, t, (pk, pbb) in pm:
            if not pk:
                continue
            sc = len(gk & pk) / max(1, len(gk))
            res.append((sc, -abs(len(t) - len(tris)), n, len(t), pbb))
        res.sort(reverse=True)
        print('GC %s %s efm%#x tris=%d bbox=%s same-id-PS2=%s' % (k[0], k[2], k[1], len(tris), gbb, has))
        for sc, _, n, nt, pbb in res[:4]:
            print('   %.3f  %s tris=%d bbox=%s' % (sc, n, nt, pbb))
        # bbox-only nearest (scale/offset differences defeat the position key)
        near = sorted(pm, key=lambda x: (abs(len(x[2]) - len(tris)) / max(1, len(tris)) +
                                         (sum(abs(a - b) for a, b in zip(x[3][1], gbb)) / max(1, sum(gbb)) if x[3][1] and gbb else 9)))
        for n, i, t, (pk, pbb) in near[:3]:
            print('   ~bbox %s tris=%d bbox=%s' % (n, len(t), pbb))


if __name__ == '__main__':
    main()
