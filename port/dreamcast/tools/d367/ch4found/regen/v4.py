#!/usr/bin/env python3
"""Check ch4 missing targets at their recorded source paths. usage: c4r-v4.py <missing-src.tsv> [substring filter]"""
import hashlib, os, sys, collections
flt = sys.argv[2] if len(sys.argv) > 2 else ''
c = collections.defaultdict(collections.Counter)
bad = []
for l in open(sys.argv[1]):
    p, s, k, src = l.rstrip('\n').split('\t')
    if flt not in src:
        continue
    q = src.split('/')
    grp = '/'.join(q[3:6])
    if not os.path.exists(src):
        r = 'absent'
    else:
        r = 'exact' if hashlib.sha256(open(src, 'rb').read()).hexdigest() == s else 'diff'
    c[grp][r] += 1
    if r != 'exact':
        bad.append((r, p, src))
for g in sorted(c):
    print(g, dict(c[g]))
print('TOTAL', dict(sum(c.values(), collections.Counter())))
for b in bad[:int(os.environ.get('SHOWBAD', '0'))]:
    print(*b)
