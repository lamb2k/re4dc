#!/usr/bin/env python3
"""Check cast16-ch4 / ch4found cast targets against files found under given roots (by basename for re4tex, by
reg-<room>/package path for registries). usage: c4r-c16chk.py <missing-src.tsv> <root>..."""
import hashlib, os, sys, glob
rows = []
for l in open(sys.argv[1]):
    p, s, k, src = l.rstrip('\n').split('\t')
    if 'cast16data-ch4' in src or '/ch4found/cast/' in src:
        rows.append((p, s, src))
found = {}
for root in sys.argv[2:]:
    for f in glob.glob(root + '/**/*.re4tex', recursive=True) + glob.glob(root + '/**/registry.re4nmr', recursive=True):
        found.setdefault(os.path.basename(f) if f.endswith('.re4tex') else f, []).append(f)
ok = bad = miss = 0
for p, s, src in sorted(rows):
    if p.endswith('.re4tex'):
        cands = found.get(os.path.basename(p), [])
    else:
        room = p.split('/')[2]
        cands = [f for k, v in found.items() if k.endswith('/package/%s/registry.re4nmr' % room) for f in v]
    hs = {f: hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in cands}
    hit = [f for f, h in hs.items() if h == s]
    if hit: ok += 1; print('EXACT', p, hit[0])
    elif cands: bad += 1; print('DIFF ', p, s[:8], ' '.join('%s=%s' % (f, h[:8]) for f, h in hs.items()))
    else: miss += 1; print('MISS ', p)
print('exact', ok, 'diff', bad, 'missing', miss, 'of', len(rows))
