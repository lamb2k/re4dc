"""pakadd.py <out.pak> <in.pak> <key.re4tex>...: a RE4PAK1 v1 pack = <in.pak> plus loose .re4tex packages (named
<crc>-<fnv>.re4tex; a key already in the pack is replaced). Same layout as pakunion.py: index at 0x800 sorted by key,
data from the next 2 KiB boundary, each entry 2 KiB aligned, CRC32 of the padded index sectors at header offset 24."""
import struct, sys, zlib, os
def rd(p):
    b = open(p, 'rb').read(); magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
    assert magic == b'RE4PAK1\x00' and ver == 1
    return {(c, f): b[o:o + n] for c, f, o, n in (struct.unpack_from('<4I', b, ioff + 16 * i) for i in range(count))}
out, src, adds = sys.argv[1], sys.argv[2], sys.argv[3:]
m = rd(src); n0 = len(m); rep = 0
for a in adds:
    c, f = (int(x, 16) for x in os.path.basename(a).split('.')[0].split('-'))
    rep += (c, f) in m; m[(c, f)] = open(a, 'rb').read()
keys = sorted(m)
al = lambda x: (x + 2047) & ~2047
ioff = 0x800; doff = al(ioff + 16 * len(keys))
idx = []; data = bytearray(); pos = doff
for k in keys:
    v = m[k]; idx.append(struct.pack('<4I', k[0], k[1], pos, len(v)))
    data += v; pad = al(pos + len(v)) - (pos + len(v)); data += b'\0' * pad; pos += len(v) + pad
hdr = struct.pack('<8s5I', b'RE4PAK1\x00', 1, len(keys), ioff, doff, 0)
blob = hdr + b'\0' * (ioff - len(hdr)) + b''.join(idx)
blob += b'\0' * (doff - len(blob)) + bytes(data)
blob = blob[:24] + struct.pack('<I', zlib.crc32(blob[ioff:doff])) + blob[28:]
open(out, 'wb').write(blob)
print(out, 'keys', n0, '->', len(keys), 'replaced', rep, 'bytes', len(blob))
