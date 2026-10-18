"""c3r_t12d2.py TOOLS T121PAK NEWTEXDIR OUT: try keeping 2 of the 295 newtex keys (t12dark said 293 new) whose
built pak size hits 122,920,960; test each candidate pair's sha against 43be4b59."""
import hashlib, itertools, os, sys
T, src, nt, out = sys.argv[1:5]
sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
import texpack
from vq_pak import read_pak
p = read_pak(open(src, 'rb').read())
newk = [tuple(int(x, 16) for x in f[:-7].split('-')) for f in os.listdir(nt) if f.endswith('.re4tex')]
base = {k: v for k, v in p.items() if k not in set(newk)}
pad = lambda n: (n + 2047) // 2048 * 2048
need = 122920960 - 122880000
cand = [(a, b) for a, b in itertools.combinations(newk, 2) if pad(len(p[a])) + pad(len(p[b])) == need]
print('candidate pairs', len(cand))
for a, b in cand[:200]:
    q = dict(base); q[a] = p[a]; q[b] = p[b]
    bb, _ = texpack.build(q)
    h = hashlib.sha256(bb).hexdigest()
    if len(bb) == 122920960 and h.startswith('43be4b59'):
        open(out, 'wb').write(bb); print('HIT', a, b, h[:16]); break
else:
    print('no hit')
