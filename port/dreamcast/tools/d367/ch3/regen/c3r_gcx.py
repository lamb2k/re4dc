"""c3r_gcx.py ISO OUTDIR PATH...: extract GC FST files (case-insensitive path match) to OUTDIR/<lowercase path>."""
import os, struct, sys
iso, out = sys.argv[1], sys.argv[2]
want = {p.lower() for p in sys.argv[3:]}
f = open(iso, 'rb')
f.seek(0x424); fst_off, fst_sz = struct.unpack('>II', f.read(8))
f.seek(fst_off); fst = f.read(fst_sz)
n = struct.unpack('>I', fst[8:12])[0]
strs = fst[n * 12:]
def name(o): return strs[o:strs.index(b'\0', o)].decode('latin1')
paths = {}
def walk(start, end, prefix):
    i = start
    while i < end:
        w0, a, b = struct.unpack('>III', fst[i * 12:i * 12 + 12])
        nm = name(w0 & 0xffffff)
        if w0 >> 24:
            walk(i + 1, b, prefix + nm + '/'); i = b
        else:
            paths[(prefix + nm).lower()] = (a, b); i += 1
walk(1, n, '')
if not want:
    for k in sorted(paths): print(k, paths[k][1])
for p in sorted(want):
    if p not in paths:
        print('MISSING', p); continue
    a, b = paths[p]; f.seek(a); d = f.read(b)
    q = os.path.join(out, p); os.makedirs(os.path.dirname(q), exist_ok=True)
    open(q, 'wb').write(d); print('ok', p, b)
