"""estrecs.py: EST/SST sequence records of GC vs PS2 effect blocks (record layout of purge-audit26 ets_ps2_evidence:
set header at +0 (u16 count), records at +0x30 + r*0x12C, byte +1 = record id, byte +2 = texture id). Lane fxproof26.

  estrecs.py etm <room> <member.eff>      GC room ETM member vs PS2 room ETM member
  estrecs.py eff <room> <gc eff#> <ps2 dat entry>
"""
import sys, struct, collections
sys.path.insert(0, '/root/work/lanes/fxproof26')
import efmmatch as M
PI, po, pb = M.PI, M.po, M.pb


def seqrecs(b, en):
    h = struct.unpack_from(en + '12I', b, 0)
    out = []
    for name, lo, do in (('EST', h[2], h[8]), ('SST', h[3], h[9])):
        if not do or not lo:
            continue
        n = struct.unpack_from(en + 'I', b, lo)[0]
        for k in range(n):
            no = struct.unpack_from(en + 'H', b, lo + 4 + 8 * k)[0]   # list entry: EST number (EspGetEstAddr id)
            of = struct.unpack_from(en + 'I', b, do + 4 + 4 * k)[0]
            k = no
            p = do + of
            num = struct.unpack_from(en + 'H', b, p)[0]
            for r in range(min(num, 200)):
                q = p + 0x30 + r * 0x12C
                if q + 0x12C > len(b):
                    break
                out.append((name, k, r, b[q + 1], b[q + 2]))
    return out


def tex_ids(b, en):
    h = struct.unpack_from(en + '12I', b, 0)
    n = struct.unpack_from(en + 'I', b, h[1])[0]
    return [struct.unpack_from(en + 'H', b, h[1] + 4 + 8 * i)[0] for i in range(n)]


def summary(tag, b, en):
    rs_ = seqrecs(b, en)
    sets = collections.OrderedDict()
    for name, k, r, i, t in rs_:
        sets.setdefault((name, k), []).append(None if r is None else (i, t))
    print('%s tex ids %s' % (tag, [hex(x) for x in tex_ids(b, en)]))
    for (name, k), l in sets.items():
        l = [x for x in l if x]
        print('   %s%d n=%d texs=%s' % (name, k, len(l), sorted(set('%#x' % t for _, t in l))))


def main(a):
    src = PI.Sources()
    if a[0] == 'etm':
        room, mem = a[1], a[2]
        g = src.gc_room(room)
        for t, s, e in PI.rs.tagged_entries(g, '>'):
            if t.rstrip(b'\0') == b'ETM':
                for nm, s2, e2 in po.etm_entries(g[s:e], '>'):
                    if nm == mem:
                        summary('GC  %s %s' % (room, mem), g[s:e][s2 + 0x40:e2], '>')
        p = src.ps2_room(room)
        for i, t, bb in pb.dat_entries(p):
            if t == 'ETM':
                for nm, s2, e2 in po.etm_entries(bb, '<'):
                    if nm == mem:
                        summary('PS2 %s.dat #%d %s' % (room, i, mem), bb[s2 + 0x40:e2], '<')
    else:
        room, ge, pe = a[1], int(a[2]), int(a[3])
        g = src.gc_room(room)
        t, s, e = PI.rs.tagged_entries(g, '>')[ge]
        summary('GC  %s arc#%d' % (room, ge), g[s:e], '>')
        for i, t, bb in pb.dat_entries(src.ps2_room(room)):
            if i == pe or (pe < 0 and t == 'EFF'):
                summary('PS2 %s.dat #%d' % (room, i), bb, '<')


if __name__ == '__main__':
    main(sys.argv[1:])
