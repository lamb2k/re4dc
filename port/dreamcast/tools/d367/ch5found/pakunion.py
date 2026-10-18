"""pakunion.py <out.pak> <winner.pak> <other.pak>: a RE4PAK1 v1 pack holding every key of both; on a shared key the
smaller payload is kept (the VQ one; ties: the winner) (lane ch5found16: the island disc's st3 VQ pak wins over test 15's; test 15-only keys ride along).
Layout as the source packs: index at 0x800 sorted by key, data from the next 2 KiB boundary, each entry 2 KiB aligned."""
import struct, sys, zlib
def rd(p):
    b = open(p, 'rb').read(); magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
    assert magic == b'RE4PAK1\x00' and ver == 1
    return {(c, f): b[o:o + n] for c, f, o, n in (struct.unpack_from('<4I', b, ioff + 16 * i) for i in range(count))}
out, win, oth = sys.argv[1:4]
w = rd(win); o = rd(oth)
m = dict(o); diff = sum(1 for k in w if k in o and o[k] != w[k])
# A shared key whose bytes differ keeps the smaller payload (the VQ encoding, whichever pack made it).
for k, v in w.items():
    if k not in o or len(v) <= len(o[k]): m[k] = v
keys = sorted(m)
al = lambda x: (x + 2047) & ~2047
ioff = 0x800; doff = al(ioff + 16 * len(keys))
idx = []; data = bytearray(); pos = doff
for k in keys:
    v = m[k]; idx.append(struct.pack('<4I', k[0], k[1], pos, len(v)))
    data += v; pad = al(pos + len(v)) - (pos + len(v)); data += b'\0' * pad; pos += len(v) + pad
hdr = struct.pack('<8s5I', b'RE4PAK1\x00', 1, len(keys), ioff, doff, 0)  # crc set below
blob = hdr + b'\0' * (ioff - len(hdr)) + b''.join(idx)
blob += b'\0' * (doff - len(blob)) + bytes(data)
blob = blob[:24] + struct.pack('<I', zlib.crc32(blob[ioff:doff])) + blob[28:]  # texpack.verify: crc32 of the padded index sectors
blob = blob[:28] + struct.pack('<I', zlib.crc32(blob[ioff:doff])) + blob[32:]  # texpack.verify: crc32 of the padded index sectors
open(out, 'wb').write(blob)
print(out, 'keys', len(keys), 'winner', len(w), 'other', len(o), 'shared', sum(1 for k in w if k in o), 'shared_differ', diff, 'bytes', len(blob))
