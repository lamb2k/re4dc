#!/usr/bin/env python3
"""lsroom.py <room>...: GC vs PS2 BIN / ETM inventory per room (lane purge-props24)."""
import struct
import sys
T = '/root/work/lanes/purge-props24/port/dreamcast/tools'
sys.path[:0] = [T, T + '/../../../tools']
import ps2_objects as po  # noqa
import ps2_bin as pb  # noqa
import room_smd as rs  # noqa
from assetpipe.rooms import GcIso  # noqa

g = GcIso(po.GC_ISO)
idx = pb.afs_index(po.PS2_ISO)
rooms = dict((r, k) for r, k in g.rooms())
for room in sys.argv[1:]:
    gd = g.read(rooms[room])
    if gd[:32] == rs.CONTAINER_MAGIC:
        gd = rs.decode_das(gd)
    ge = rs.tagged_entries(gd, '>')
    pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(po.PS2_ISO, room + '.dat', idx))}
    print('== %s' % room)
    for i, (t, s, e) in enumerate(ge):
        tag = t.rstrip(b'\0').decode()
        a = i + 4
        p = pe.get(a)
        if tag == 'BIN':
            print('  BIN 0x%x gc %d ps2 %s %s' % (a, e - s, p[0] if p else '-', len(p[1]) if p else ''))
        if tag == 'ETM':
            gn = [n for n, _, _ in po.etm_entries(gd[s:e], '>')]
            pbm = next((b for tt, b in pe.values() if tt == 'ETM'), b'')
            pn = [n for n, _, _ in po.etm_entries(pbm, '<')] if pbm else []
            print('  ETM gc: %s' % ' '.join(n for n in gn if n.lower().endswith('.bin')))
            print('  ETM ps2-missing: %s' % ' '.join(n for n in gn if n.lower().endswith('.bin') and n not in pn))
