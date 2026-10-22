#!/usr/bin/env python3
"""lane mipmap22 B2: rekey world sidecars to the texconv22 add-on keys, refresh their physical certificates and add
the 6 bind rows (sorted) to scoped_representations.inc. Args: <manifest> <addon inc> <world tree dc/native> <rect21 dir>"""
import json, re, struct, sys, zlib
from pathlib import Path

man, addinc, wdir, rdir = map(Path, sys.argv[1:5])
m = json.load(open(man))
pairs = [(e['pack_key_1760'], e['addon_key']) for e in m['held23'] if e.get('addon_key')]
assert len(pairs) == 6, pairs
def kb(k):
    c, f = (int(x, 16) for x in k.split('-'))
    return struct.pack('<II', c, f)
def fnv(b):
    h = 2166136261
    for x in b: h = ((h ^ x) * 16777619) & 0xffffffff
    return h
certp = rdir / 'provenance_certificates.inc'
certs = certp.read_text()
hits = {}
for w in sorted(wdir.glob('*/ps2-world.r4pw')):
    room = w.parent.name
    b = bytearray(w.read_bytes()); n = 0
    for old, new in pairs:
        o, nw = kb(old), kb(new); c = b.count(o)
        if c: b[:] = b.replace(o, nw); n += c; hits.setdefault(room, []).append((old, new, c))
    if not n: continue
    oldcrc = struct.unpack_from('<I', b, 20)[0]; oldfnv = fnv(w.read_bytes())
    struct.pack_into('<I', b, 20, zlib.crc32(bytes(b[32:])) & 0xffffffff)
    newcrc = struct.unpack_from('<I', b, 20)[0]; newfnv = fnv(bytes(b))
    roomno = int(room[1:], 16)
    pat = re.compile(r'^\{0x%xU,.*$' % roomno, re.M)
    row = pat.search(certs); assert row, room
    r = row.group(0)
    assert ('0x%08xU' % oldcrc) in r and ('0x%08xU' % oldfnv) in r, (room, r, hex(oldcrc), hex(oldfnv))
    r2 = r.replace('0x%08xU' % oldcrc, '0x%08xU' % newcrc).replace('0x%08xU' % oldfnv, '0x%08xU' % newfnv)
    certs = certs.replace(r, r2)
    w.unlink(); w.write_bytes(bytes(b))
certp.write_text(certs)
inc = rdir / 'scoped_representations.inc'
rows = [l for l in inc.read_text().splitlines() if l.startswith('{')]
head = [l for l in inc.read_text().splitlines() if not l.startswith('{')]
add = [l for l in addinc.read_text().splitlines() if l.startswith('{')]
key = lambda l: tuple(int(x, 16) for x in re.match(r'\{0x([0-9a-f]+)U,0x([0-9a-f]+)U', l).groups())
allr = sorted(rows + add, key=key)
assert len({key(l) for l in allr}) == len(allr) == len(rows) + 6
inc.write_text('\n'.join(head + allr) + '\n')
h = rdir / 'world_rect_bind.h'
h.write_text(h.read_text().replace('qualified_count==792U', 'qualified_count==%dU' % len(allr)))
print(json.dumps(dict(rows=len(allr), hits=hits)))
