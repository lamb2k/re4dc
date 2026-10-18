#!/usr/bin/env python3
"""Which of ch3's NEED-FROM-CH4-cast16.tsv shas exist in our outputs. usage: c4r-ch3need.py <tsv> <root>..."""
import hashlib, glob, sys
need = [l.rstrip('\n').split('\t') for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
have = {}
for root in sys.argv[2:]:
    for f in glob.glob(root + '/**/*.re4tex', recursive=True) + glob.glob(root + '/**/registry.re4nmr', recursive=True):
        have.setdefault(hashlib.sha256(open(f, 'rb').read()).hexdigest(), f)
n = 0
for r in need:
    p, s = r[0], r[1]
    if s in have: n += 1; print('HAVE', p, s[:8], have[s])
    else: print('NO  ', p, s[:8], r[2] if len(r) > 2 else '')
print('have', n, 'of', len(need))
