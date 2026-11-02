#!/usr/bin/env python3
"""mkwarps.py   (lane world-ch4, 2026-11-02; test tooling): writes warps/<room>.txt (one DBG_WARP entry preset per chapter 4
room: Leon at the destination of the route door that enters the room, the room's chapter, god, census) and
routes/ch4-<N>.txt (the room / door chain of each sub-chapter from its start to its chapter end, with each door's area
centre to walk into), from doors-ch4.tsv (doors.py) and the CASTLE-ROUTE-20261015.md room order."""
import csv
from pathlib import Path

H = Path(__file__).resolve().parent
CH = {10: '4-1', 11: '4-2', 12: '4-3', 13: '4-4'}
# Route order per sub-chapter (CASTLE-ROUTE-20261015.md; chapter ends from SceSetChapterEnd: r22b 4-1, r21d 4-2, r225 4-3,
# r22a 4-4). Backtracking legs (r210 -> r222 -> r210, r211 hub, r214 <-> r217) are kept as the route walks them.
ROUTE = {
    10: ['r206', 'r210', 'r222', 'r210', 'r201', 'r219', 'r211', 'r216', 'r211', 'r212', 'r211', 'r213', 'r214', 'r217', 'r214',
         'r218', 'r215', 'r229', 'r221', 'r22b'],
    11: ['r22b', 'r220', 'r223', 'r224', 'r21d'],
    12: ['r21d', 'r225', 'r21b', 'r225'],
    13: ['r225', 'r226', 'r227', 'r228', 'r22a', 'r300'],
}
EXTRA = {'r21a': ('r225', 12), 'r22c': ('r211', 10)}
doors = list(csv.DictReader(open(H / 'doors-ch4.tsv'), delimiter='\t'))


def door(a, b):
    c = [d for d in doors if d['room'] == a and d['dst_room'] == b]
    return c[0] if c else None


(H / 'warps').mkdir(exist_ok=True); (H / 'routes').mkdir(exist_ok=True)
entry = {}
for ch, rs in ROUTE.items():
    for a, b in zip(rs, rs[1:]):
        if b not in entry and b != 'r300':
            entry[b] = (a, ch)
for r, v in EXTRA.items():
    entry[r] = v
for r, (a, ch) in sorted(entry.items()):
    d = door(a, r)
    lines = ['name w4-%s' % r, '# lane world-ch4: %s entry from %s (door %s), chapter %s' % (r, a, d['no'] if d else '?', CH[ch]),
             'room 0x%s' % r[1:], 'chapter %d' % ch, 'god']
    if d:
        lines += ['pos %s %s %s' % (d['dst_x'], d['dst_y'], d['dst_z']), 'ang %s' % d['dst_ang']]
    lines += ['alivelog 300', 'census 400', 'dump']
    (H / 'warps' / ('%s.txt' % r)).write_text('\n'.join(lines) + '\n')
for ch, rs in ROUTE.items():
    out = ['# chapter %s route (lane world-ch4): room, then the door area to walk into (centre x z) and where it leads' % CH[ch],
           '# start save: chapter %s start (%s); end: SceSetChapterEnd in %s' % (CH[ch], rs[0], rs[-1] if rs[-1] != 'r300' else 'r22a')]
    for a, b in zip(rs, rs[1:]):
        d = door(a, b)
        if d:
            out.append('%s door %s centre %s %s -> %s at %s %s %s ang %s%s' % (a, d['no'], d['cx'], d['cz'], b, d['dst_x'], d['dst_y'],
                       d['dst_z'], d['dst_ang'], ' LOCK %s flag %s' % (d['lock'], d['lockflag']) if d['lock'] != '0' else ''))
        else:
            out.append('%s -> %s: no AEV door (scripted transition: event / jump / lift)' % (a, b))
    (H / 'routes' / ('ch4-%s.txt' % CH[ch])).write_text('\n'.join(out) + '\n')
print('warps', len(entry), 'routes', len(ROUTE))
