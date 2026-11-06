#!/usr/bin/env python3
"""room_vram.py <tex-rows.json> <evidence root> [changed-keys.json ...]   (lane assets-dc, 2026-11-02; read only)

Per room: the VRAM line of the rr census run (cg-rXXX/run-output.txt, last "vram room:" line of that room: pinned,
free, largest) and the textures the run loaded there ("native UI: load /cd/dc/tex/.../<key>.re4tex"), joined with the
texaudit.py rows of the disc's dc/tex.pak: loaded bytes, raw 16-bit bytes, minified without mips, and the bytes a
VQ(+mips when square) conversion of the raw ones would save. Optional pak-derived.json files name the keys a batch
changed; their after-sizes come from the batch's report.json next to it.
"""
import json, re, sys, os, glob
rows = {r['key']: r for r in json.load(open(sys.argv[1]))}
root = sys.argv[2]
LOAD = re.compile(r'native UI: load /cd/dc/tex/(?:[0-9a-f]/)?([0-9a-f]{8}-[0-9a-f]{8})\.re4tex')
VR = re.compile(r'vram room: r=([0-9a-f]+) .*?pinned=(\d+) dynamic=(\d+) other=(\d+) free=(\d+) largest=(\d+)')
print('room\tpinned\tfree\tlargest\tkeys\tbytes\traw16\traw16B\tnomip\tsaveB\tfree_after')
for d in sorted(glob.glob(os.path.join(root, 'cg-r*'))):
    room = d.rsplit('-', 1)[1]
    f = os.path.join(d, 'run-output.txt')
    if not os.path.exists(f):
        continue
    keys, last = set(), None
    for line in open(f, errors='replace'):
        m = LOAD.search(line)
        if m: keys.add(m.group(1))
        v = VR.search(line)
        if v and v.group(1) == room[1:]: last = v
    k = [rows[x] for x in keys if x in rows]
    raw = [r for r in k if r['pay'] != 'vq' and r['fmt'] in ('rgb565', 'argb4444', 'argb1555')]
    save = sum(max(0, r['bytes'] - (2048 + (r['w'] * r['h'] // 4) * (4 if r['w'] == r['h'] else 3) // 3)) for r in raw)
    nomip = sum(1 for r in k if not r['mip'])
    if last:
        p, dy, o, fr, lg = (int(last.group(i)) for i in (2, 3, 4, 5, 6))
    else:
        p = fr = lg = -1
    print('%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d' % (room, p, fr, lg, len(k), sum(r['bytes'] for r in k), len(raw),
                                                    sum(r['bytes'] for r in raw), nomip, save, fr + save if fr >= 0 else -1))
