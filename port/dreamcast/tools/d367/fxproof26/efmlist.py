"""efmlist.py room...: GC vs PS2 efm models of each room EFF / ETM eff (+ core), with triangle count, bbox and the
best cross match by geometry key (any id). Lane fxproof26."""
import sys
sys.path.insert(0, '/root/work/lanes/fxproof26')
import efmmatch as M
PI, po, pb = M.PI, M.po, M.pb


def ps2_room_models(src, room):
    p = src.ps2_room(room) if room != 'core' else src.ps2_core()
    out = []
    for i, t, bb in pb.dat_entries(p):
        bodies = []
        if t == 'EFF':
            bodies.append(('#%d:EFF' % i, bb))
        if t == 'ETM':
            for nm, s2, e2 in po.etm_entries(bb, '<'):
                if nm.endswith('.eff'):
                    bodies.append(('#%d:ETM/%s' % (i, nm), bb[s2 + 0x40:e2]))
        for loc, body in bodies:
            for idv, mo, to in PI.eff_efm(body, '<'):
                tr = M.ps2_tris(body[mo:to])
                out.append((loc, idv, mo, tr, M.desc(tr)))
    return out


def main(rooms):
    src = PI.Sources()
    for room in rooms:
        al = PI.core_assets(src) if room == 'core' else PI.room_assets(src, room)
        pm = ps2_room_models(src, room)
        print('== %s PS2 efm:' % room, ['%s:%#x(%d)' % (l, i, len(t)) for l, i, _, t, _ in pm])
        if room != 'core':
            p = src.ps2_room(room)
            for i, t, bb in pb.dat_entries(p):
                if t == 'ETM':
                    print('   PS2 ETM members:', [nm for nm, _, _ in po.etm_entries(bb, '<')])
            g = src.gc_room(room)
            for t, s, e in PI.rs.tagged_entries(g, '>'):
                if t.rstrip(b'\0') == b'ETM':
                    print('   GC  ETM members:', [nm for nm, _, _ in po.etm_entries(g[s:e], '>')])
        for cls, name, loc, gb, gt, pb_, pt_ in al:
            if cls != 'breakables':
                continue
            tr = M.gc_tris(gb)
            gk, gbb = M.desc(tr)
            best = max(((len(gk & pk) / max(1, len(gk)), l, i) for l, i, _, t, (pk, pbb) in pm), default=None)
            print('  GC %-14s tris=%4d bbox=%-24s samePS2=%s best=%s' % (name, len(tr), gbb, pb_ is not None,
                                                                    '%.2f %s:%#x' % best if best else None))


if __name__ == '__main__':
    main(sys.argv[1:])
