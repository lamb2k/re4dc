"""pak_keep.py <out.pak> <base.pak> <add.pak> (lane castle31 10-26, from ch5found/pakunion.py): every key of <base> with
its bytes unchanged, plus the keys only <add> has. Disc 2 = Disc 1's pack (its winner on every shared key: UI, Leon,
weapons draw the same pictures on both discs) + the castle-only keys. Same layout and CRC as pakunion.py."""
import struct, sys, zlib
def rd(p):
    b = open(p, 'rb').read(); magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
    assert magic == b'RE4PAK1\x00' and ver == 1
    return {(c, f): b[o:o + n] for c, f, o, n in (struct.unpack_from('<4I', b, ioff + 16 * i) for i in range(count))}
out, win, oth = sys.argv[1:4]   # win = base (Disc 1), oth = add (castle)
w = rd(win); o = rd(oth)
m = dict(w)   # w = <base>: kept byte for byte
diff = sum(1 for k in w if k in o and o[k] != w[k])
for k, v in o.items():
    if k not in w: m[k] = v
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
