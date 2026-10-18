"""pakmatch.py NEED.json OUTDIR LISTFILE: for every path in LISTFILE (tex*.pak, GD track03.iso/.bin, disc.bin), find the
NEED files by sha256: RE4PAK1 entries (key crc-fnv -> dc/tex/<c>/<crc>-<fnv>.re4tex, bytes verbatim), and loose files
inside ISO9660 images (2048 or raw 2352 sectors, base LBA 0 or 45000), including tex.pak files inside them.
Matches are written to OUTDIR/<disc path>; OUTDIR/pakmatch.json maps disc path -> source."""
import hashlib, json, os, struct, sys
need = json.load(open(sys.argv[1]))['need']; out = sys.argv[2]
want = {}
for k, v in need.items(): want.setdefault(v['sha256'], []).append(k)
sizes = {v['size'] for v in need.values()}
got = {}
pj = os.path.join(out, 'pakmatch.json')
if os.path.exists(pj): got = json.load(open(pj))

def take(b, src):
    if len(b) not in sizes: return
    h = hashlib.sha256(b).hexdigest()
    for k in want.get(h, []):
        if k not in got:
            got[k] = src; q = os.path.join(out, k); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(b)

def pak(blob, src):
    if blob[:8] != b'RE4PAK1\x00': return 0
    n = struct.unpack_from('<I', blob, 12)[0]
    for i in range(n):
        c, f, o, s = struct.unpack_from('<4I', blob, 2048 + 16 * i)
        take(blob[o:o + s], src + '#%08x-%08x' % (c, f))
    return n

class Img:
    def __init__(self, p):
        self.f = open(p, 'rb'); self.raw = None; self.base = None
        for raw in (2048, 2352):
            for base in (0, 45000):
                pvd = self.sec(16 + base, 1, raw, base)
                if pvd[1:6] == b'CD001':
                    self.raw, self.base = raw, base; return
    def sec(self, lba, n, raw=None, base=None):
        raw = raw or self.raw; base = self.base if base is None else base
        if raw == 2048:
            self.f.seek((lba - base) * 2048); return self.f.read(n * 2048)
        b = bytearray()
        for i in range(n):
            self.f.seek((lba - base + i) * 2352 + 16); b += self.f.read(2048)
        return bytes(b)
    def read(self, lba, size):
        return self.sec(lba, (size + 2047) // 2048)[:size]

def iso(p):
    im = Img(p)
    if im.raw is None: print('  not iso9660', p); return
    pvd = im.sec(16 + im.base, 1)
    rl, rs = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
    def walk(lba, size, path):
        data = im.read(lba, size); i = 0
        while i < len(data):
            n = data[i]
            if n == 0: i = (i // 2048 + 1) * 2048; continue
            el, sz = struct.unpack_from('<I', data, i + 2)[0], struct.unpack_from('<I', data, i + 10)[0]
            fl = data[i + 25]; nl = data[i + 32]; name = data[i + 33:i + 33 + nl].decode('latin1').split(';')[0]
            i += n
            if name in ('\x00', '\x01'): continue
            q = path + '/' + name if path else name
            if fl & 2: walk(el, sz, q)
            elif name.lower().startswith('tex') and name.lower().endswith('.pak'):
                pak(im.read(el, sz), p + '!' + q)
            elif sz in sizes:
                take(im.read(el, sz), p + '!' + q)
    walk(rl, rs, '')

for p in [l.strip() for l in open(sys.argv[3]) if l.strip()]:
    before = len(got)
    try:
        if p.lower().endswith('.pak'): pak(open(p, 'rb').read(), p)
        else: iso(p)
    except Exception as e: print('  error', p, e)
    print(len(got) - before, p)
    json.dump(got, open(pj, 'w'), indent=0)
print('matched', len(got), 'of', len(need))
