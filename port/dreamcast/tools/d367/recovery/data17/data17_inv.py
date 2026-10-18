#!/usr/bin/env python3
"""data17_inv.py <t11-fix.py> <payload root> <data line name>: per data set of the line, file presence on WSL and
whether the 16.4 payload carries the same disc path with the same bytes."""
import hashlib, importlib.util, json, os, sys
from pathlib import Path
tf, proot, line = sys.argv[1:4]
spec = importlib.util.spec_from_file_location('t11', tf)
m = importlib.util.module_from_spec(spec)
sys.argv = [tf]
spec.loader.exec_module(m)
names = getattr(m, line).split(',')
man = json.load(open(Path(proot) / 'MANIFEST-disc.json'))
if 'files' in man: man = man['files']
low = {k.lower(): v for k, v in man.items()}
H = {}
def sha(p):
    if p not in H: H[p] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return H[p]
for n in names:
    d = m.DATA.get(n)
    if d is None:
        print('%-12s NOT DEFINED' % n); continue
    tot = have = same = 0; miss = []; dirs = []
    for k, v in d.items():
        if k in ('ovl',):
            continue
        if k == 'tex':
            for t in (v if isinstance(v, list) else [v]):
                dirs.append((t, os.path.isdir(t)))
            continue
        if not isinstance(v, str):
            continue
        tot += 1
        if os.path.exists(v):
            have += 1
            e = low.get(k.lower())
            if e and os.path.getsize(v) < 400 << 20 and e.get('sha256') == sha(v): same += 1
        else:
            miss.append((k, v))
    pm = sum(1 for k, _ in miss if k.lower() in low)
    print('%-12s files %4d present %4d (=16.4 payload bytes %4d) missing %4d (path on 16.4 disc %4d) texdirs %s' % (
        n, tot, have, same, len(miss), pm, ' '.join('%s:%s' % (('ok' if ok else 'MISSING'), t) for t, ok in dirs)[:300]))
    for k, v in miss[:3]:
        print('     missing e.g. %s <- %s' % (k, v))
