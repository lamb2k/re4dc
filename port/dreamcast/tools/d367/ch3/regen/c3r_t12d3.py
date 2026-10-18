"""c3r_t12d3.py TOOLS T121PAK NEWTEXDIR OUT OLDPAK...: newtex keys also present (same bytes) in older paks are the likely
2 kept keys; try every pair among them (size filtered) against 43be4b59."""
import hashlib, itertools, os, sys
T, src, nt, out = sys.argv[1:5]; olds = sys.argv[5:]
sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
import texpack
from vq_pak import read_pak
p = read_pak(open(src, 'rb').read())
newk = [tuple(int(x, 16) for x in f[:-7].split('-')) for f in os.listdir(nt) if f.endswith('.re4tex')]
hits = {}
for o in olds:
    q = read_pak(open(o, 'rb').read())
    for k in newk:
        if k in q: hits.setdefault(k, []).append((os.path.basename(o), q[k] == p[k]))
for k, v in hits.items(): print('%08x-%08x' % k, len(p[k]), v)
cand = sorted(hits)
base = {k: v for k, v in p.items() if k not in set(newk)}
pad = lambda n: (n + 2047) // 2048 * 2048
for a, b in itertools.combinations(cand, 2):
    if pad(len(p[a])) + pad(len(p[b])) != 40960: continue
    q = dict(base); q[a] = p[a]; q[b] = p[b]
    bb, _ = texpack.build(q); h = hashlib.sha256(bb).hexdigest()
    print('try', a, b, h[:8])
    if h.startswith('43be4b59'): open(out, 'wb').write(bb); print('HIT'); break
# also: maybe a single key of padded size 40960
for a in cand:
    if pad(len(p[a])) == 40960:
        q = dict(base); q[a] = p[a]; bb, _ = texpack.build(q); h = hashlib.sha256(bb).hexdigest(); print('try1', a, h[:8])
        if h.startswith('43be4b59'): open(out, 'wb').write(bb); print('HIT'); break
