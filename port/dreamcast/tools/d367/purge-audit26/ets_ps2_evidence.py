"""Per ETS_MATCH=2 drop: PS2 SMD placement at the spot (body) + PS2 room EFF SST/EST record near it (flame)."""
import struct, sys, re
T = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '../..')
sys.path[:0] = [T, T + '/../../../tools']
import ps2_objects as po, ps2_bin as pb, room_smd as rs
G = __import__('os').environ.get('GCARC', '/root/work/lanes/purge-props24-scratch/gcarc')
idx = pb.afs_index(po.PS2_ISO)
src = open(__import__('os').path.join(T, '../../../src/game/EtcModel.cpp')).read()
drops = [(int(a, 16), int(b, 16), int(c, 16)) for a, b, c in re.findall(r'\{0x([0-9a-f]+), 0x([0-9A-F]+), 0x([0-9A-F]+)\},  // r', src)]

def seqrecs(b, en):
    h = struct.unpack_from(en + '12I', b, 0)
    out = []
    for name, do in (('EST', h[8]), ('SST', h[9])):
        if not do: continue
        n = struct.unpack_from(en + 'I', b, do)[0]
        for k, of in enumerate(struct.unpack_from(en + '%dI' % n, b, do + 4)):
            if not of: continue
            p = do + of
            num = struct.unpack_from(en + 'H', b, p)[0]
            for r in range(min(num, 80)):
                q = p + 0x30 + r * 0x12C
                if q + 0x12C > len(b): break
                out.append((name, k, r, b[q + 1], b[q + 2], struct.unpack_from(en + '3f', b, q + 0xC), p - 0 , q))
    return out

rooms = sorted({d[0] for d in drops})
for room in rooms:
    rn = 'r%03x' % room
    gd = open('%s/%s.arc' % (G, rn), 'rb').read()
    gets = {}
    for t, s, e in rs.tagged_entries(gd, '>'):
        tt = t.rstrip(b'\0').decode() if isinstance(t, bytes) else t
        if tt == 'ETS':
            n = struct.unpack_from('>H', gd, s)[0]
            for k in range(n):
                p = s + 16 + k * 40
                ident, slot = struct.unpack_from('>2H', gd, p)
                gets[(ident, slot)] = (struct.unpack_from('>6f', gd, p + 16)[3:6], s, p - s)
    pd = pb.afs_read(po.PS2_ISO, rn + '.dat', idx)
    ents = list(pb.dat_entries(pd))
    smd = [(i, b) for i, t, b in ents if t == 'SMD'][0]
    effs = [(i, b) for i, t, b in ents if t == 'EFF']
    recs = [(i,) + r for i, b in effs for r in seqrecs(b, '<')]
    for (r, ident, no) in [d for d in drops if d[0] == room]:
        if (ident, no) not in gets:
            print('%s et%02x00#%d NOT IN GC ETS' % (rn, ident, no)); continue
        pos, ets_off, rel = gets[(ident, no)]
        sm = None
        for o in range(0, len(smd[1]) - 12, 4):
            x, y, z = struct.unpack_from('<3f', smd[1], o)
            if abs(x - pos[0]) < 60 and abs(y - pos[1]) < 60 and abs(z - pos[2]) < 60:
                sm = (o - 0x10, struct.unpack_from('<H', smd[1], o - 0x10)[0]); break
        fl = [x for x in recs if abs(x[6][0] - pos[0]) < 500 and abs(x[6][2] - pos[2]) < 500 and abs(x[6][1] - pos[1]) < 1500]
        print('%s et%02x00#%d pos %s | GC ETS rec +0x%x | PS2 SMD(dat#%d) %s | PS2 EFF fx %s' % (
            rn, ident, no, tuple(round(v) for v in pos), rel,
            smd[0], ('placement@0x%x bin 0x%x' % sm) if sm else 'NONE',
            ['dat#%d %s%d.%d id%x tex%d @0x%x' % (x[0], x[1], x[2], x[3], x[4], x[5], x[8]) for x in fl[:2]] or 'NONE'))
