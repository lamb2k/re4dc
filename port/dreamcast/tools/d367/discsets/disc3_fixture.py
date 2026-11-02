#!/usr/bin/env python3
"""disc3_fixture.py D1TREE ISLANDTREE WORKDIR  (lane world-ch5, 2026-11-02; the island twin of castle31/castle_fixture.py)
Writes WORKDIR/island-fixture.json for discsets/mkdisc3.py: the island content (ISLANDTREE, discsets/d3-content.sh)
laid over the current Disc 1 (release) candidate tree.
- every ISLANDTREE file the Disc 1 tree lacks is added;
- island-owned files win where both have them: room files named r3xx, st3/, rel/st3_*, the island enemy archives,
  dc/native/r3xx, the stream file (island entries), bio4midi.dat (island BGM0 tracks), the island resident.bin;
- dc/tex.pak = pak_keep.py: Disc 1's pack unchanged (its winner on every shared key) + the island-only keys;
- every other shared file keeps the Disc 1 (newer) copy (Leon, Ashley, weapons, merchant, ss, font, ...)."""
import json, os, re, struct, subprocess, sys

d1, it, work = sys.argv[1:4]
os.makedirs(work, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
ISLAND_EM = 'em1d|em1e|em1f|em32|em36|em39|em3a|em3d'
OWN = re.compile(r'(^|/)(r3[0-3][0-9a-f])[^/]*$|^st3/|^rel/st3_|^dc/native/r3[0-3][0-9a-f]/|^em/(%s)\.(drs|das)$|'
                 r'^bgm/aica_str\.dat$|^bgm/bio4midi\.dat$|^dc/resident\.bin$' % ISLAND_EM)


def files(r):
    out = {}
    for d, _, fs in os.walk(r):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, r)] = os.path.getsize(p)
    return out


A, C = files(d1), files(it)
rep, rem = {}, []
for k in sorted(C):
    if k in ('dc/tex.pak', 'SHA256SUMS'):
        continue
    if k not in A or OWN.search(k):
        rep[k] = os.path.join(it, k)
pak = os.path.join(work, 'tex.pak')
subprocess.check_call([sys.executable, os.path.join(HERE, '..', 'castle31', 'pak_keep.py'), pak,
                       os.path.join(d1, 'dc/tex.pak'), os.path.join(it, 'dc/tex.pak')])
rep['dc/tex.pak'] = pak
b = open(pak, 'rb').read(); _, _, cnt, ioff, _ = struct.unpack_from('<8s4I', b, 0)
inpak = {'%08x-%08x' % struct.unpack_from('<2I', b, ioff + 16 * i) for i in range(cnt)}
loose = [k for k in rep if k.startswith('dc/tex/') and os.path.basename(k)[:17] in inpak]
for k in loose:  # the loader reads the pack first: a loose key the pack holds is disc space only
    del rep[k]
print(f'loose keys dropped (in pack) {len(loose)}')
json.dump({'replace': rep, 'remove': rem,
           'provenance': {'d1': d1, 'island': it, 'tool': 'discsets/disc3_fixture.py'}},
          open(os.path.join(work, 'island-fixture.json'), 'w'), indent=1)
print(f'FIXTURE replace {len(rep)} remove {len(rem)}')
