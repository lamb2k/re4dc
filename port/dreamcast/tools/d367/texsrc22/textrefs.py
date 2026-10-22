#!/usr/bin/env python3
"""textrefs.py KEYS.txt OUT.json ROOT... : which text files (tsv/json/inc/txt/py/h/cpp/md under ROOT, < 64 MB)
name each key. Used for the non-GC sources: resident lists, PS2 world/atlas manifests, scoped origins, overlays."""
import json, os, re, sys
keys = {l.strip() for l in open(sys.argv[1]) if l.strip()}
pat = re.compile(r'([0-9a-f]{8})[-_ ]?(?:0x)?([0-9a-f]{8})', re.I)
EXT = ('.tsv', '.json', '.inc', '.txt', '.py', '.h', '.cpp', '.md', '.csv', '.mk', '.sh')
hits = {}
for root in sys.argv[3:]:
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('.git', 'obj', 'objdir')]
        for f in fn:
            if not f.endswith(EXT):
                continue
            p = os.path.join(dp, f)
            try:
                if os.path.getsize(p) > 64 << 20:
                    continue
                t = open(p, errors='ignore').read()
            except OSError:
                continue
            for m in pat.finditer(t):
                k = (m.group(1) + '-' + m.group(2)).lower()
                if k in keys:
                    hits.setdefault(k, set()).add(p)
json.dump({k: sorted(v) for k, v in hits.items()}, open(sys.argv[2], 'w'), indent=0, sort_keys=True)
print('keys with text refs', len(hits))
