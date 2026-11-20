"""draws.py <reference run-output> <engine serial> [--offset 184] [--to 900]: behaviour-generator draws per tick on
both sides (the number of Rnd steps between consecutive LT r= states), and the first tick where the count or the state
differs. A diagnostic for the cause of a divergence (generator state is not a plays-right field)."""
import argparse


def step(r):
    n = ((((r >> 1) + (r >> 8)) & 0xff) << 8) | ((r >> 1) & 0xff)
    m = n & 0xffff
    if m == r:
        m = (n + 0x101) & 0xffff
    return m


def dist(a, b, lim=20000):
    r = a
    for i in range(lim + 1):
        if r == b:
            return i
        r = step(r)
    return None


def lt(path, off):
    d = {}
    for l in open(path, encoding='latin-1'):
        if l.startswith('LT t='):
            kv = dict(x.split('=', 1) for x in l.split()[1:] if '=' in x)
            d.setdefault(int(kv['t']) - off, int(kv['r'], 16))
    return d


ap = argparse.ArgumentParser()
ap.add_argument('ref'); ap.add_argument('eng')
ap.add_argument('--offset', type=int, default=184); ap.add_argument('--eng-offset', type=int, default=0)
ap.add_argument('--to', type=int, default=900)
a = ap.parse_args()
R, E = lt(a.ref, a.offset), lt(a.eng, a.eng_offset)
fs = fc = None
rows = []
for t in range(1, a.to + 1):
    if t not in R or t - 1 not in R or t not in E or t - 1 not in E:
        continue
    rc, ec = dist(R[t - 1], R[t]), dist(E[t - 1], E[t])
    rows.append((t, rc, ec))
    if fs is None and R[t] != E[t]:
        fs = t
    if fc is None and rc != ec:
        fc = t
print('state equal from tick 1 to', (fs - 1) if fs else a.to, '| first state difference', fs,
      '| first count difference', fc)
for t, rc, ec in rows:
    if fc is not None and fc - 3 <= t <= fc + 3:
        print('  tick %d draws ref %s engine %s' % (t, rc, ec))
print('total draws ref %d engine %d' % (sum(r or 0 for _, r, _ in rows), sum(e or 0 for _, _, e in rows)))
