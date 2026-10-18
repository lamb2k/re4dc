"""ch5regen: extract DC/TEX.PAK from a raw GD track03.bin (2352-byte sectors, LBA base 45000) and report the given keys.
usage: c5r_rawpak.py <track03.bin> <out.pak> <key>..."""
import struct, sys, hashlib
src, out = sys.argv[1:3]
keys = sys.argv[3:]
f = open(src, 'rb')


def sect(lba, n=1):
    b = bytearray()
    for i in range(n):
        f.seek((lba - 45000 + i) * 2352 + 16); b += f.read(2048)
    return bytes(b)


pvd = sect(45016)
assert pvd[1:6] == b'CD001', pvd[:8]
ext, size = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]


def find(ext, size, comps):
    data = sect(ext, (size + 2047) // 2048)
    o = 0
    while o < len(data):
        l = data[o]
        if not l:
            o = (o // 2048 + 1) * 2048; continue
        e, s = struct.unpack_from('<I', data, o + 2)[0], struct.unpack_from('<I', data, o + 10)[0]
        nl = data[o + 32]; name = data[o + 33:o + 33 + nl].decode('latin1').split(';')[0].upper()
        if name == comps[0]:
            return (e, s) if len(comps) == 1 else find(e, s, comps[1:])
        o += l
    raise FileNotFoundError(comps)


e, s = find(ext, size, ['DC', 'TEX.PAK'])
with open(out, 'wb') as w:
    left = s; lba = e
    while left > 0:
        n = min(left, 2048 * 512)
        w.write(sect(lba, (n + 2047) // 2048)[:n]); lba += (n + 2047) // 2048; left -= n
pak = open(out, 'rb').read()
print(out, len(pak), hashlib.sha256(pak).hexdigest()[:8])
cnt, io, do = struct.unpack_from('<III', pak, 12)
idx = {}
for i in range(cnt):
    a, b, o, sz = struct.unpack_from('<IIII', pak, io + 16 * i)
    idx['%08x-%08x' % (a, b)] = (o, sz)
print('entries', cnt)
for k in keys:
    print(k, idx.get(k))
