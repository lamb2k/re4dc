#!/usr/bin/env python3
"""Stage verified cast files by target sha: <out>/<group>/<disc path>; writes SHA256SUMS + MANIFEST.tsv.
usage: c4r-c16stage.py <missing-src.tsv> <out> <root>..."""
import hashlib, os, sys, glob, shutil
out = sys.argv[2]
want = {}
for l in open(sys.argv[1]):
    p, s, k, src = l.rstrip('\n').split('\t')
    if 'cast16data-ch4' in src or '/ch4found/cast/' in src:
        g = 'cast16data-ch4' if 'cast16data-ch4' in src else 'ch4found-cast'
        want.setdefault(s, []).append((g, p, src))
have = {}
for root in sys.argv[3:]:
    for f in glob.glob(root + '/**/*.re4tex', recursive=True) + glob.glob(root + '/**/registry.re4nmr', recursive=True):
        h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
        if h in want: have.setdefault(h, f)
sums = []; man = []
for s, rows in want.items():
    for g, p, src in rows:
        if s not in have: man.append((g, p, s, 'MISSING', src)); continue
        d = os.path.join(out, g, p); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copyfile(have[s], d)
        sums.append('%s  %s/%s' % (s, g, p)); man.append((g, p, s, have[s], src))
open(os.path.join(out, 'SHA256SUMS'), 'w').write('\n'.join(sorted(sums)) + '\n')
with open(os.path.join(out, 'MANIFEST.tsv'), 'w') as f:
    for r in sorted(man): f.write('\t'.join(r) + '\n')
print('staged', len(sums), 'missing', sum(1 for r in man if r[3] == 'MISSING'))
