"""fielddiff.py <A> <B> [--to N]: per prefix and field, how many trace lines differ and the first tick (address fields of
LE lines dropped). Lines are matched by order within (prefix, tick)."""
import re, sys, collections
def load(p, to):
    d = collections.defaultdict(list)
    for l in open(p, encoding='latin-1'):
        m = re.match(r'(L[TEFUL]) t=(\d+) ', l)
        if not m or int(m.group(2)) > to: continue
        kv = dict(x.split('=', 1) for x in l.split()[1:] if '=' in x)
        if m.group(1) == 'LE': kv.pop('a', None); kv.pop('vt', None)
        d[(m.group(1), int(m.group(2)))].append(kv)
    return d
to = int(sys.argv[sys.argv.index('--to') + 1]) if '--to' in sys.argv else 10**9
A, B = load(sys.argv[1], to), load(sys.argv[2], to)
cnt = collections.Counter(); first = {}; bebits = set()
for k in sorted(set(A) | set(B), key=lambda x: x[1]):
    a, b = A.get(k, []), B.get(k, [])
    if len(a) != len(b): cnt[(k[0], '#lines')] += 1; first.setdefault((k[0], '#lines'), k[1])
    for x, y in zip(a, b):
        for f in set(x) | set(y):
            if x.get(f) != y.get(f):
                cnt[(k[0], f)] += 1; first.setdefault((k[0], f), k[1])
                if f == 'be' and x.get(f) and y.get(f):
                    bebits.add(hex(int(x[f], 16) ^ int(y[f], 16)))
for (p, f), n in sorted(cnt.items(), key=lambda z: first[z[0]]):
    print('%s %-6s lines %6d first t=%d' % (p, f, n, first[(p, f)]))
if not cnt: print('IDENTICAL')
if bebits: print('be bits that differ:', sorted(bebits))
