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
# D2_DATA (lane castle-gca-26, 2026-11-01; recipe.conf D2_DATA, default empty = the castle31 fixture unchanged): Disc 2
# data sets of test11/t11-fix.py DATA, in order, over the castle content (never on Disc 1). Keys as t11-fix stages them:
# 'graft' {dest: (source .dar, members)} = graft/dar_graft.py member copy onto the composed castle archive (the .arc
# beside a grafted .dar is rewritten as its type-0 payload, as pmrest25 stages both); 'tex' = loose PS2 picture keys
# (t11-fix texdir); 'remove' = paths off Disc 2; any other key = whole-file replacement.
D2 = [n for n in os.environ.get('D2_DATA', '').split(',') if n]
d2paks = []
if D2:
    import importlib.util, struct as _st
    sys.path[:0] = [os.path.join(HERE, '..', 'graft')]
    import dar_graft
    _sp = importlib.util.spec_from_file_location('t11fix', os.path.join(HERE, '..', 'test11', 't11-fix.py'))
    t11 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(t11)
    gdir = os.path.join(work, 'd2data'); os.makedirs(gdir, exist_ok=True)
    rec = []
    for n in D2:
        if n not in t11.DATA:
            raise SystemExit('castle_fixture: D2_DATA set %s is not in t11-fix DATA (store missing?)' % n)
        for k, v in t11.DATA[n].items():
            if k == 'graft':
                for dest, (src, members) in v.items():
                    cur = rep.get(dest) or os.path.join(d1, dest)
                    comp, sb = open(cur, 'rb').read(), open(src, 'rb').read()
                    res, _r = dar_graft.graft(comp, sb, list(members))
                    bad = dar_graft.verify(comp, res, list(members), sb)
                    if bad:
                        raise SystemExit('castle_fixture: %s graft %s member identity %s' % (n, dest, bad))
                    o = os.path.join(gdir, '%s-%s' % (n, dest.replace('/', '_')))
                    open(o, 'wb').write(res); rep[dest] = o
                    arc = dest[:-4] + '.arc'
                    if dest.endswith('.dar') and (arc in rep or arc in A):
                        _k, size, _d, off = _st.unpack_from('<4I', res, 0x20)
                        oa = o[:-4] + '.arc'; open(oa, 'wb').write(res[off:off + size]); rep[arc] = oa
                    rec.append('%s graft %s %d members' % (n, dest, len(members)))
            elif k == 'tex':
                t11.texdir(v, rep, rec)
            elif k == 'remove':
                for p_ in v:
                    rep.pop(p_, None); rem.append(p_)
            elif k == 'dc/tex.pak':   # pack set: only its pak-derived.json changed/added keys win (keys it did not touch
                d2paks.append((n, v, t11.PAK_DERIVED[n]))   # keep the composed pack's bytes: a newer Disc 1 pack stays)
            else:
                rep[k] = v
                arc = k[:-4] + '.arc'
                if k.endswith('.dar') and (arc in rep or arc in A):  # keep the .arc copy = this .dar's type-0 payload
                    res = open(v, 'rb').read()
                    _k, size, _d, off = _st.unpack_from('<4I', res, 0x20)
                    oa = os.path.join(gdir, '%s-%s' % (n, arc.replace('/', '_')))
                    open(oa, 'wb').write(res[off:off + size]); rep[arc] = oa
    print('D2_DATA %s: %s' % (','.join(D2), '; '.join(rec)))
pak = os.path.join(work, 'tex.pak')
subprocess.check_call([sys.executable, os.path.join(HERE, 'pak_keep.py'), pak,
                       os.path.join(d1, 'dc/tex.pak'), os.path.join(ct, 'dc/tex.pak')])
if d2paks:   # D2_DATA pack sets in order: each set's changed/added keys (pak-derived.json) over the composed pack
    import json as _js, struct as _s2, zlib as _z
    def _rd(p):
        b = open(p, 'rb').read(); magic, ver, count, ioff, doff = _s2.unpack_from('<8s4I', b, 0)
        assert magic == b'RE4PAK1\x00' and ver == 1
        return {(c, f): b[o:o + n] for c, f, o, n in (_s2.unpack_from('<4I', b, ioff + 16 * i) for i in range(count))}
    m = _rd(pak); done = []
    for n, sp, der in d2paks:
        dj = _js.load(open(der)); sk = _rd(sp)
        for key in dj.get('changed', []) + dj.get('added', []):
            kt = tuple(int(x, 16) for x in key.split('-')); m[kt] = sk[kt]; done.append(key)
    keys = sorted(m); al = lambda x: (x + 2047) & ~2047
    ioff = 0x800; doff = al(ioff + 16 * len(keys)); idx = []; data = bytearray(); pos = doff
    for k in keys:
        v = m[k]; idx.append(_s2.pack('<4I', k[0], k[1], pos, len(v)))
        data += v; pad = al(pos + len(v)) - (pos + len(v)); data += b'\x00' * pad; pos += len(v) + pad
    blob = _s2.pack('<8s5I', b'RE4PAK1\x00', 1, len(keys), ioff, doff, 0)
    blob = blob + b'\x00' * (ioff - len(blob)) + b''.join(idx)
    blob += b'\x00' * (doff - len(blob)) + bytes(data)
    crc = _s2.pack('<I', _z.crc32(blob[ioff:doff])); blob = blob[:24] + crc + crc + blob[32:]   # as pak_keep.py
    pak = os.path.join(work, 'tex-d2.pak'); open(pak, 'wb').write(blob)
    print('D2_DATA dc/tex.pak keys %d from %s' % (len(done), ','.join(n for n, _, _ in d2paks)))
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
