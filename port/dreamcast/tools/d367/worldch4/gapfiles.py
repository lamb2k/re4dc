#!/usr/bin/env python3
"""gapfiles.py D1TREE CASTLETREE STORE ROOM...   (WSL; lane world-ch4, 2026-11-02)
For each chapter 4 room: the GameCube disc files named after the room outside st*/ (event data evd/, event/, sound,
movies ...) that none of the Disc 1 tree, the castle content tree and this lane's data set STORE carries under the same
path (or the same stem in dc/movie for a movie the port plays). These are the files a Disc 2 room still lacks; each is
reviewed (the PS2 may stream it as a movie under ROUTE_MOVIES_CH4)."""
import os, re, sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[2])]
from assetpipe.rooms import GcIso  # noqa: E402

GC_ISO = '/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
d1, ct, store = (Path(x) for x in sys.argv[1:4])
rooms = sys.argv[4:]
g = GcIso(GC_ISO)
trees = (d1, ct, store)
movies = {p.stem.lower() for t in trees if (t / 'dc/movie').is_dir() for p in (t / 'dc/movie').iterdir()}
have = lambda k: any((t / k).exists() for t in trees)
tot = 0
for r in rooms:
    miss, ok = [], 0
    for k in sorted(g.files):
        kl = k.lower()
        if not re.search(r'(^|/)%s' % r, kl) or kl.split('/')[0].startswith('st'):
            continue
        if have(kl) or Path(kl).stem in movies:
            ok += 1; continue
        miss.append('%s(%d)' % (kl, g.files[k][1]))
    tot += len(miss)
    print(r, 'present', ok, 'missing', len(miss), ' '.join(miss))
print('TOTAL missing', tot)
