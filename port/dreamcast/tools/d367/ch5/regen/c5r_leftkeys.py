import os, sys, hashlib
L = '/root/probe/lanes-20261018/ch5regen'
found = set(l.split('\t')[0] for l in open(L + '/found.tsv'))
idx = {}
for d in sys.argv[2:]:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.re4tex'): idx.setdefault(f[:-7], os.path.join(root, f))
for line in open(sys.argv[1]):
    p, size, sha, run, src = line.rstrip('\n').split('\t')
    if p in found or not p.endswith('.re4tex'): continue
    k = os.path.basename(p)[:-7]
    f = idx.get(k)
    info = ''
    if f:
        b = open(f, 'rb').read(); info = '%s size %d (target %s)' % (f.replace(L, ''), len(b), size)
    print(k, src.split('/')[-2] if 'loose' in src else src.replace('/root/', '')[:60], info)
