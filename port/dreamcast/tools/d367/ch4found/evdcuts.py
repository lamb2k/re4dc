#!/usr/bin/env python3
# evdcuts.py <ps2 evd>... : per camera cut, the PS2 fcv maxFrame (first u16) and the movie picture the cut starts at
# (docs/ROUTE_CUTSCENES.md: cut k starts at sum over j<k of (maxFrame_j + 1)). The PS2 evd ends with a file table of
# 0x40-byte rows: name (0x30), u32 offset, u32 size.
import re, struct, sys, json, os
for p in sys.argv[1:]:
    b = open(p, 'rb').read()
    rows = {}
    for m in re.finditer(rb'event/[^\0]*?/cam/cam_s\w+?_(\d{3})\.fcv\0', b):
        s = m.start()
        off, size = struct.unpack_from('<II', b, s + 0x30)
        if 0 < off < len(b) and 0 < size <= len(b) - off and off % 16 == 0:
            rows[int(m.group(1))] = (off, size, struct.unpack_from('<H', b, off)[0])
    start = 0; out = []
    for k in sorted(rows):
        off, size, mf = rows[k]
        out.append((k, mf, start)); start += mf + 1
    man = os.path.join(os.path.dirname(p), 'manifest.json')
    frames = json.load(open(man))['frames'] if os.path.exists(man) else None
    print(os.path.basename(p), 'cuts', len(out), 'sum', start, 'movie frames', frames)
    for k, mf, st in out:
        print('  cut 0x%02x maxFrame %d starts at picture %d' % (k, mf, st))
