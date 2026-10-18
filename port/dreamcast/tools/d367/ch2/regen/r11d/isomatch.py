"""isomatch.py NEED.json OUTDIR ISO...: walk ISO9660 GD track images (base LBA 0 or 45000), hash files whose size is
needed, extract sha matches into OUTDIR/<disc path>; print coverage."""
import hashlib, json, os, struct, sys
need = json.load(open(sys.argv[1]))['need']; out = sys.argv[2]
want = {}
for k, v in need.items(): want.setdefault(v['sha256'], []).append(k)
sizes = {v['size'] for v in need.values()}
got = {}
for iso in sys.argv[3:]:
    f = open(iso, 'rb')
    f.seek(16 * 2048); pvd = f.read(2048)
    rl, rs = struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0]
    base = None
    for b in (0, 45000):
        if rl >= b:
            f.seek((rl - b) * 2048); d = f.read(34)
            if d and d[0] >= 34 and struct.unpack_from('<I', d, 2)[0] == rl: base = b; break
    print(iso, 'base', base)
    def walk(lba, size, path):
        f.seek((lba - base) * 2048); data = f.read(size); i = 0
        while i < len(data):
            n = data[i]
            if n == 0: i = (i // 2048 + 1) * 2048; continue
            el, sz = struct.unpack_from('<I', data, i + 2)[0], struct.unpack_from('<I', data, i + 10)[0]
            fl = data[i + 25]; nl = data[i + 32]; name = data[i + 33:i + 33 + nl].decode('latin1').split(';')[0]
            i += n
            if name in ('\x00', '\x01'): continue
            p = path + '/' + name if path else name
            if fl & 2: walk(el, sz, p)
            elif sz in sizes:
                f.seek((el - base) * 2048); b = f.read(sz); h = hashlib.sha256(b).hexdigest()
                for k in want.get(h, []):
                    if k not in got:
                        got[k] = (iso, p); q = os.path.join(out, k); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(b)
    walk(rl, rs, '')
json.dump(got, open(os.path.join(out, 'isomatch.json'), 'w'), indent=1)
import collections
c = collections.Counter(('dc/tex' if k.startswith('dc/tex/') else 'dc/mot' if k.startswith('dc/mot/') else k) for k in got)
print('matched', len(got), 'of', len(need)); print(sorted(c.items()))
