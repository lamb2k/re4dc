#!/usr/bin/env python3
"""Stage ch3's NEED-FROM-CH4-cast16.tsv items we reproduced: <out>/<disc path>, SHA256SUMS, MANIFEST.tsv.
usage: c4r-forch3.py <tsv> <out> <root>..."""
import hashlib, glob, os, shutil, sys
need = [l.rstrip('\n').split('\t') for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
out = sys.argv[2]
have = {}
for root in sys.argv[3:]:
    for f in glob.glob(root + '/**/*.re4tex', recursive=True) + glob.glob(root + '/**/registry.re4nmr', recursive=True):
        have.setdefault(hashlib.sha256(open(f, 'rb').read()).hexdigest(), f)
sums, man = [], []
for r in need:
    p, s = r[0], r[1]
    src = have.get(s)
    man.append('\t'.join([p, s, src or 'MISSING', r[2] if len(r) > 2 else '']))
    if not src: continue
    d = os.path.join(out, p); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copyfile(src, d); sums.append(f'{s}  {p}')
open(out + '/SHA256SUMS', 'w').write('\n'.join(sorted(sums)) + '\n')
open(out + '/MANIFEST.tsv', 'w').write('\n'.join(man) + '\n')
print('staged', len(sums), 'of', len(need))
