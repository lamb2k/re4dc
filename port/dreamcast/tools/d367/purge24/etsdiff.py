#!/usr/bin/env python3
"""etsdiff.py <gcarc dir> <room>...: etc list (ETS) entries GC has and the PS2 room .dat does not (lane purge-props24).
Matches entries by id and position (2 units tolerance). Prints per room: GC n, PS2 n, dropped (id slot pos), added."""
import struct
import sys
T = '/root/work/lanes/purge-props24/port/dreamcast/tools'
sys.path[:0] = [T, T + '/../../../tools']
import ps2_objects as po  # noqa
import ps2_bin as pb  # noqa
import room_smd as rs  # noqa


def ets(data, en, entries):
    out = []
    for tag, s, e in entries:
        if (tag.rstrip(b'\0') if isinstance(tag, bytes) else tag.encode()) != b'ETS':
            continue
        n = struct.unpack_from(en + 'H', data, s)[0]
        for k in range(n):
            p = s + 16 + k * 40
            ident, slot = struct.unpack_from(en + '2H', data, p)
            f = struct.unpack_from(en + '6f', data, p + 16)
            out.append((ident, slot, f))
    return out


idx = pb.afs_index(po.PS2_ISO)
TAB = []
for room in sys.argv[2:]:
    gd = open('%s/%s.arc' % (sys.argv[1], room), 'rb').read()
    g = ets(gd, '>', rs.tagged_entries(gd, '>'))
    pd = pb.afs_read(po.PS2_ISO, room + '.dat', idx)
    pents = []
    for i, t, b in pb.dat_entries(pd):
        if t == 'ETS':
            n = struct.unpack_from('<I', b, 0)[0]
            for k in range(n):
                q = 16 + 64 * k
                ident, slot = struct.unpack_from('<2H', b, q + 0x30)
                pents.append((ident, slot, struct.unpack_from('<3f', b, q + 0x20)))
    left = list(pents)
    dropped = []
    for ident, slot, f in g:
        m = next((x for x in left if x[0] == ident and all(abs(a - b) < 2 for a, b in zip(x[2][:3], f[3:6]))), None)
        if m is None:
            m = next((x for x in left if x[0] == ident and x[1] == slot), None)
        if m is None:
            dropped.append((ident, slot, f))
        else:
            left.remove(m)
    if '--c' in sys.argv[1:2]:
        pass
    for i, sl, f in dropped:
        TAB.append('    {0x%s, 0x%02X, 0x%04X},  // %s et%02x00' % (room[1:], i, sl, room, i))
    print('%s GC %d PS2 %d dropped %s added %s' % (room, len(g), len(pents),
          ' '.join('et%02x00#%d' % (i, s & 0xff) for i, s, f in dropped) or '-',
          ' '.join('et%02x00#%d' % (i, s & 0xff) for i, s, f in left) or '-'))

for t in TAB:
    print(t)
