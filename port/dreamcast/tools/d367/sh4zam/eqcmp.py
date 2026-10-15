#!/usr/bin/env python3
"""eqcmp.py ctl arm: gameplay-equivalence event lines (kills, cap holds/releases, bell, rooms, movies, events, doors)
with frames, control vs arm."""
import re, sys
E = '/mnt/c/Flycast-Evidence/re4-dreamcast/sh4zam-skin-20261015'
PAT = re.compile(r'(kill target|r101cap|alivecap|ALIVECAP|route movie start|event file: prepare|phase=enter room|'
                 r'door|s30|wave|room clear|cutscene|HALT|FAULT|MISALIGN)', re.I)
SKIP = re.compile(r'doorse|aica|DVD: Read File|door freeze: no texture')
def ev(n):
    out = []
    for l in open(f'{E}/{n}/capture/run-output.txt', encoding='latin-1'):
        if PAT.search(l) and not SKIP.search(l):
            out.append(re.sub(r'm=8c[0-9a-f]+ |wait_us=\d+ |heap=\S+', '', l.strip())[:150])
    return out
a, b = ev(sys.argv[1]), ev(sys.argv[2])
same = a == b
print(f'{sys.argv[1]} vs {sys.argv[2]}: {len(a)} / {len(b)} events, {"IDENTICAL" if same else "DIFFER"}')
if not same:
    import difflib
    for d in list(difflib.unified_diff(a, b, lineterm='', n=0))[:30]:
        print('  ', d)
