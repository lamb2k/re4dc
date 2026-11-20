"""relpos.py <engine trace (T lines)> <reference run-output> --offset N --to M: Leon's displacement from engine tick 0 /
reference tick N against each other (a resume that starts a few units apart: does the motion after it agree?)."""
import struct, sys
def f(h): return struct.unpack('<f', struct.pack('<I', int(h, 16)))[0]
eng, ref = sys.argv[1], sys.argv[2]
off = int(sys.argv[sys.argv.index('--offset') + 1]); to = int(sys.argv[sys.argv.index('--to') + 1])
E, R = {}, {}
for l in open(eng, encoding='latin-1'):
    if l.startswith('T t='):
        d = dict(x.split('=', 1) for x in l.split()[1:] if '=' in x); E[int(d['t'])] = [f(x) for x in d['p'].split(',')]
for l in open(ref, encoding='latin-1'):
    if l.startswith('LT t='):
        d = dict(x.split('=', 1) for x in l.split()[1:] if '=' in x); t = int(d['t']) - off
        if 0 <= t <= to: R.setdefault(t, [f(x) for x in d['p'].split(',')])
ok = n = 0; first = None; worst = 0
for t in range(1, to + 1):
    if t in E and t in R and 0 in E and 0 in R:
        de = [a - b for a, b in zip(E[t], E[0])]; dr = [a - b for a, b in zip(R[t], R[0])]
        d = max(abs(a - b) for a, b in zip(de, dr)); n += 1; worst = max(worst, d)
        if d <= 1: ok += 1
        elif first is None: first = t
print('start apart %.2f units; displacement within 1 unit %d/%d, first over %s, worst %.2f' % (
    max(abs(a - b) for a, b in zip(E[0], R[0])), ok, n, first, worst))
