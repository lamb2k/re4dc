"""pakbase.py <out.pak> <base.pak> <extra.pak> [<key.re4tex>...]: a RE4PAK1 v1 pack = every entry of <base.pak> (it wins
on shared keys), the keys of <extra.pak> that <base.pak> lacks, then loose .re4tex packages (named <crc>-<fnv>.re4tex;
they replace). Layout as pakadd.py / pakunion.py (index at 0x800 sorted by key, 2 KiB aligned data, CRC at +24).
lane ch5found16 2026-10-17: the island pak on the test 17 pak (vram101) instead of the older test 15 base."""
import os
import struct
import sys
import zlib


def rd(p):
    b = open(p, 'rb').read()
    magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
    assert magic == b'RE4PAK1\x00' and ver == 1, p
    return {(c, f): b[o:o + n] for c, f, o, n in (struct.unpack_from('<4I', b, ioff + 16 * i) for i in range(count))}


out, base, extra, adds = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
m = rd(base)
nb = len(m)
e = rd(extra)
shared = sum(1 for k in e if k in m)
differ = sum(1 for k in e if k in m and m[k] != e[k])
for k, v in e.items():
    m.setdefault(k, v)
ne = len(m) - nb
rep = 0
for a in adds:
    c, f = (int(x, 16) for x in os.path.basename(a).split('.')[0].split('-'))
    rep += (c, f) in m
    m[(c, f)] = open(a, 'rb').read()
keys = sorted(m)
al = lambda x: (x + 2047) & ~2047
ioff = 0x800
doff = al(ioff + 16 * len(keys))
idx = []
data = bytearray()
pos = doff
for k in keys:
    v = m[k]
    idx.append(struct.pack('<4I', k[0], k[1], pos, len(v)))
    data += v
    pad = al(pos + len(v)) - (pos + len(v))
    data += b'\0' * pad
    pos += len(v) + pad
hdr = struct.pack('<8s5I', b'RE4PAK1\x00', 1, len(keys), ioff, doff, 0)
blob = hdr + b'\0' * (ioff - len(hdr)) + b''.join(idx)
blob += b'\0' * (doff - len(blob)) + bytes(data)
blob = blob[:24] + struct.pack('<I', zlib.crc32(blob[ioff:doff])) + blob[28:]
open(out, 'wb').write(blob)
print(out, 'base', nb, '+ extra-only', ne, '(shared', shared, 'of which differing', differ, ') + loose', len(adds),
      'replaced', rep, '=', len(keys), 'keys', len(blob), 'bytes, index crc %08x' % zlib.crc32(blob[ioff:doff]))
