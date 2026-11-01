#!/usr/bin/env python3
"""castle_fixture.py D1TREE CASTLETREE WORKDIR  (lane castle31, 2026-10-26)
Writes WORKDIR/castle-fixture.json for discsets/mkdisc2.py: the castle content of a qualified Disc 2 tree
(CASTLETREE, e.g. the recovered J tree) laid over the current Disc 1 (release) tree.
- every CASTLETREE file the Disc 1 tree lacks is added;
- castle-owned files win where both have them: room files named r2xx, the stream file (castle entries), Ashley pl01.drs,
  the castle resident.bin;
- dc/tex.pak = pak_keep.py: Disc 1's pack unchanged (its winner on every shared key) + the castle-only keys;
- every other shared file keeps the Disc 1 (newer) copy."""
import json, os, re, subprocess, sys

d1, ct, work = sys.argv[1:4]
os.makedirs(work, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
OWN = re.compile(r'(^|/)(r2[0-9a-f]{2})[^/]*$|^dc/native/r2[0-9a-f]{2}/|^bgm/aica_str\.dat$|^em/pl01\.drs$|^dc/resident\.bin$')
# D1_ROOMS (lane castle-disc2-26): rooms whose Disc 1 files win although they are r2xx (r200: the castle gate is also the
# 2-3 end room of Disc 1, whose release package carries the PS2 cast; the castle21 J copy drew an em12 Ganado on the GC
# path, CAST-GC r200 1143 frames). Default r200; D1_ROOMS= (empty) restores the castle31 rule.
D1 = [r for r in os.environ.get('D1_ROOMS', 'r200').split() if r]
D1RE = re.compile(r'(^|/)(%s)([^0-9a-f/][^/]*)?$|^dc/native/(%s)/' % ('|'.join(D1), '|'.join(D1))) if D1 else None


def files(r):
    out = {}
    for d, _, fs in os.walk(r):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, r)] = os.path.getsize(p)
    return out


A, C = files(d1), files(ct)
rep, rem = {}, []
for k in sorted(C):
    if k == 'dc/tex.pak':
        continue
    if k in A and D1RE and D1RE.search(k):
        continue
    if k not in A or OWN.search(k):
        rep[k] = os.path.join(ct, k)
pak = os.path.join(work, 'tex.pak')
subprocess.check_call([sys.executable, os.path.join(HERE, 'pak_keep.py'), pak,
                       os.path.join(d1, 'dc/tex.pak'), os.path.join(ct, 'dc/tex.pak')])
rep['dc/tex.pak'] = pak
import struct
b = open(pak, 'rb').read(); _, _, cnt, ioff, _ = struct.unpack_from('<8s4I', b, 0)
inpak = {'%08x-%08x' % struct.unpack_from('<2I', b, ioff + 16 * i) for i in range(cnt)}
loose = [k for k in rep if k.startswith('dc/tex/') and os.path.basename(k)[:17] in inpak]
for k in loose:  # a loose key the pack already holds is never read (the loader reads the pack first): disc space only
    del rep[k]
print(f'loose keys dropped (in pack) {len(loose)}')
for k in A:  # castle GC fallback meshes the castle tree dropped (rooms that have their PS2 world)
    if re.match(r'^dc/native/r2[0-9a-f]{2}/MAINSCENARIO\.re4mesh$', k) and k not in C:
        rem.append(k)
json.dump({'replace': rep, 'remove': rem,
           'provenance': {'d1': d1, 'castle': ct, 'tool': 'castle31/castle_fixture.py'}},
          open(os.path.join(work, 'castle-fixture.json'), 'w'), indent=1)
print(f'FIXTURE replace {len(rep)} remove {len(rem)}')
