"""c3r_isox.py TRACK03.ISO OUT PATH: extract one ISO9660 file (case-insensitive) from a 2048-byte-sector track03.iso (LBA base 45000)."""
import struct, sys
trk, out, want = sys.argv[1], sys.argv[2], sys.argv[3].upper().split('/')
f = open(trk, 'rb'); BASE = 45000
def sec(lba, n=1):
    b = bytearray()
    for i in range(n):
        f.seek((lba - BASE + i) * 2048); b += f.read(2048)
    return bytes(b)
pvd = sec(BASE + 16)
rl, rs = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
def find(lba, size, name):
    d = sec(lba, (size + 2047) // 2048); i = 0
    while i < len(d):
        n = d[i]
        if n == 0: i = (i // 2048 + 1) * 2048; continue
        el, sz = struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0]
        nl = d[i + 32]; nm = d[i + 33:i + 33 + nl].decode('latin1').split(';')[0].upper()
        if nm == name: return el, sz
        i += n
    raise SystemExit('not found ' + name)
lba, size = rl, rs
for p in want: lba, size = find(lba, size, p)
with open(out, 'wb') as o:
    left = size; l = lba
    while left > 0:
        n = min(left, 2048 * 512); o.write(sec(l, (n + 2047) // 2048)[:n]); left -= n; l += 512
print(out, size)
