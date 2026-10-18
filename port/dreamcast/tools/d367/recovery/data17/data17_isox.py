#!/usr/bin/env python3
"""data17_isox.py <track03.iso> <out dir> <ISO path>...: extract files from a GD-ROM track03 ISO (LBA base 45000)."""
import os, struct, sys

iso, out, want = sys.argv[1], sys.argv[2], [w.upper() for w in sys.argv[3:]]
f = open(iso, 'rb')
nsec = os.path.getsize(iso) // 2048
f.seek(16 * 2048); pvd = f.read(2048)
assert pvd[1:6] == b'CD001'
root = pvd[156:156 + 34]
rlba = struct.unpack_from('<I', root, 2)[0]
def _ok(b):
    if rlba - b < 0 or rlba - b >= nsec: return False
    f.seek((rlba - b) * 2048); r = f.read(34)
    return r[32] == 1 and r[33] == 0 and struct.unpack_from('<I', r, 2)[0] == rlba
base = 45000 if _ok(45000) else 0
assert _ok(base)


def read(lba, n):
    f.seek((lba - base) * 2048); return f.read(n)


def walk(lba, size, pre, acc):
    d = read(lba, size); o = 0
    while o < len(d):
        L = d[o]
        if L == 0:
            o = (o // 2048 + 1) * 2048; continue
        e_lba, e_sz = struct.unpack_from('<I', d, o + 2)[0], struct.unpack_from('<I', d, o + 10)[0]
        fl = d[o + 25]; nl = d[o + 32]; name = d[o + 33:o + 33 + nl]
        if name not in (b'\x00', b'\x01'):
            nm = name.decode('ascii').split(';')[0]
            p = pre + nm
            if fl & 2: walk(e_lba, e_sz, p + '/', acc)
            else: acc[p.upper()] = (e_lba, e_sz)
        o += L
    return acc


files = walk(rlba, struct.unpack_from('<I', root, 10)[0], '', {})
os.makedirs(out, exist_ok=True)
for w in want:
    lba, sz = files[w]
    dst = os.path.join(out, os.path.basename(w).lower())
    with open(dst, 'wb') as g:
        f.seek((lba - base) * 2048); left = sz
        while left:
            b = f.read(min(left, 1 << 22)); g.write(b); left -= len(b)
    print(w, sz, dst)
