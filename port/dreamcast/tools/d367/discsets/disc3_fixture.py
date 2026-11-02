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
ISLAND_EM = 'em1d|em1e|em1f|em32|em36|em39|em3a|em3d|em31|pl0e'
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
# D3_DATA (recipe.conf; lane world-ch5): Disc 3 only t11-fix DATA sets, in order, over the island content. Whole-file
# keys only (e.g. assets-dc dcf3isl: the island loose pictures in Dreamcast form); other key kinds are refused.
D3 = [x for x in os.environ.get('D3_DATA', '').split(',') if x]
if D3:
    import importlib.util
    _sp = importlib.util.spec_from_file_location('t11fix', os.path.join(HERE, '..', 'test11', 't11-fix.py'))
    t11 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(t11)
    for x in D3:
        if x not in t11.DATA:
            raise SystemExit('disc3_fixture: D3_DATA set %s is not in t11-fix DATA (store missing?)' % x)
        nk = 0
        for k, v in t11.DATA[x].items():
            if k in ('graft', 'tex', 'remove', 'dc/tex.pak') or not isinstance(v, str):
                raise SystemExit('disc3_fixture: D3_DATA set %s key %s is not a whole-file key' % (x, k))
            rep[k] = v; nk += 1
        print('D3_DATA %s: %d files' % (x, nk))
pak = os.path.join(work, 'tex.pak')
subprocess.check_call([sys.executable, os.path.join(HERE, '..', 'castle31', 'pak_keep.py'), pak,
                       os.path.join(d1, 'dc/tex.pak'), os.path.join(it, 'dc/tex.pak')])
# Village / castle-only pack keys (listed only by r1xx / r2xx room resident lists, never by r000, an island room or the
# island tree) are dead weight on Disc 3: drop them (D3_PAK_PRUNE=0 keeps the composed pack).
if os.environ.get('D3_PAK_PRUNE', '1') == '1':
    import glob, zlib
    lists = {}
    for t in glob.glob(os.path.join(HERE, '..', 'vram', 'resident', '**', 'r*.tsv'), recursive=True):
        room = os.path.basename(t)[:4]
        for ln in open(t).read().splitlines()[1:]:
            if ln.strip():
                lists.setdefault(ln.split('\t')[0], set()).add(room)
    island_keys = {os.path.basename(k)[:17] for k in C if k.startswith('dc/tex/')}
    def dead(key):
        rooms = lists.get(key)
        if not rooms or key in island_keys:
            return False
        return all(re.match(r'r[12][0-9a-f]{2}$', r) and r != 'r22c' for r in rooms)
    b = open(pak, 'rb').read(); magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
    m = {}
    for i in range(count):
        c, f, o, n = struct.unpack_from('<4I', b, ioff + 16 * i); m[(c, f)] = b[o:o + n]
    drop_keys = [k for k in m if dead('%08x-%08x' % k)]
    dropped = sum(len(m[k]) for k in drop_keys)
    for k in drop_keys:
        del m[k]
    keys = sorted(m); al = lambda x: (x + 2047) & ~2047
    ioff = 0x800; doff = al(ioff + 16 * len(keys)); idx = []; data = bytearray(); pos = doff
    for k in keys:
        v = m[k]; idx.append(struct.pack('<4I', k[0], k[1], pos, len(v)))
        data += v; pad = al(pos + len(v)) - (pos + len(v)); data += b'\x00' * pad; pos += len(v) + pad
    blob = struct.pack('<8s5I', b'RE4PAK1\x00', 1, len(keys), ioff, doff, 0)
    blob = blob + b'\x00' * (ioff - len(blob)) + b''.join(idx)
    blob += b'\x00' * (doff - len(blob)) + bytes(data)
    crc = struct.pack('<I', zlib.crc32(blob[ioff:doff])); blob = blob[:24] + crc + crc + blob[32:]   # as pak_keep.py
    pak = os.path.join(work, 'tex-d3.pak'); open(pak, 'wb').write(blob)
    print(f'pak prune: {len(drop_keys)} village/castle-only keys, {dropped} bytes')
rep['dc/tex.pak'] = pak
# dc/resident.bin = Disc 1's current resident.bin (newer core / shared records) + the island room lists
# (vram/resident/r3*.tsv), via water/water_resident.py pack (base + lists union); the 10-18 island18 copy is older.
res = os.path.join(work, 'resident-d3.bin')
import glob as _g
subprocess.check_call([sys.executable, os.path.join(HERE, '..', 'water', 'water_resident.py'), 'pack',
                       os.path.join(d1, 'dc/resident.bin'), res] +
                      sorted(_g.glob(os.path.join(HERE, '..', 'vram', 'resident', 'r3*.tsv'))))
rep['dc/resident.bin'] = res
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
