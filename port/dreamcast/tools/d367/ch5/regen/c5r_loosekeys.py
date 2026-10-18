import os, sys, collections
L = '/root/probe/lanes-20261018/ch5regen'
have = {}
for root, _, files in os.walk(L):
    if '/tools/.git' in root or '/game-' in root and '/.git' in root: continue
    for f in files:
        if f.endswith('.re4tex'): have.setdefault(f[:-7], []).append(os.path.join(root, f))
c = collections.Counter(); rows = []
for line in open(sys.argv[1]):
    p, size, sha, run, src = line.rstrip('\n').split('\t')
    if 'st3-pak-loose' not in src: continue
    k = os.path.basename(p)[:-7]
    where = have.get(k, [])
    tag = 'nokey' if not where else ('/'.join(where[0].split('/')[5:7]))
    c[tag] += 1; rows.append((k, size, tag))
for k, v in c.most_common(): print(v, k)
for r in rows[:15]: print(*r)
