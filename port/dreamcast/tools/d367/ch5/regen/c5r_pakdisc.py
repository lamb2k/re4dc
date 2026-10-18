"""ch5regen: read DC/TEX.PAK out of a cooked GD track03 .iso (LBA base 45000) and match its entries to missing targets.
usage: c5r_pakdisc.py <track03.iso> <missing-src.tsv> <outdir>  -> writes matched entries as <outdir>/<key>.re4tex"""
import hashlib, os, struct, sys
iso, miss, out = sys.argv[1:4]
f = open(iso, 'rb')
def sect(lba, n=1):
    f.seek((lba - 45000 if lba >= 45000 else lba) * 2048); return f.read(n * 2048)
pvd = sect(16)
if pvd[1:6] != b'CD001':
    for base in (45016,):
        pvd = sect(base)
assert pvd[1:6] == b'CD001', pvd[:8]
ext, size = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
def find(ext, size, comps):
    data = sect(ext, (size + 2047) // 2048)
    o = 0
    while o < len(data):
        l = data[o]
        if not l: o = (o // 2048 + 1) * 2048; continue
        e, s = struct.unpack_from('<I', data, o + 2)[0], struct.unpack_from('<I', data, o + 10)[0]
        nl = data[o + 32]; name = data[o + 33:o + 33 + nl].decode('latin1').split(';')[0].upper()
        if name == comps[0]:
            return (e, s) if len(comps) == 1 else find(e, s, comps[1:])
        o += l
    raise FileNotFoundError(comps)
e, s = find(ext, size, ['DC', 'TEX.PAK'])
b = sect(e, (s + 2047) // 2048)[:s]
magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
want = {}
for line in open(miss):
    p, size_, sha, run, src = line.rstrip('\n').split('\t'); want.setdefault(sha, []).append(p)
os.makedirs(out, exist_ok=True)
hit = 0
for i in range(count):
    cc, ff, o, n = struct.unpack_from('<4I', b, ioff + 16 * i)
    blob = b[o:o + n]; h = hashlib.sha256(blob).hexdigest()
    if h in want:
        open(os.path.join(out, '%08x-%08x.re4tex' % (cc, ff)), 'wb').write(blob); hit += 1
print(iso, 'pak bytes', s, 'keys', count, 'matched', hit)
