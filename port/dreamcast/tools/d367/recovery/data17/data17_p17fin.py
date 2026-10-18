#!/usr/bin/env python3
"""data17_p17fin.py <tools dir> <cand dir> <ch2-data.json> <ch2 tex.pak> <pak17 tex.pak> <payload tree> <cast16-data.json>
Adds ch2's 23 unrecovered loose paths (provenance.missing) to the candidate loose-keys.txt; writes vq-keys.txt
(added keys whose pak17 bytes differ from the loose source)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import tex_merge  # noqa: E402
cand, c2j, ch2p, p17p, tree, c16j = sys.argv[2:8]
lk = Path(cand) / 'loose-keys.txt'
paths = [l.strip() for l in open(lk) if l.strip()]
miss = json.load(open(c2j))['provenance']['missing']
allp = sorted(set(paths) | set(miss))
lk.write_text(''.join(p + '\n' for p in allp))
print('loose-keys', len(paths), '+', len(set(miss) - set(paths)), '=', len(allp))
ch2, p17 = tex_merge.read(ch2p), tex_merge.read(p17p)
base = json.load(open(Path(cand) / 'base.json'))
src = {}
for p in sorted((Path(tree) / 'dc' / 'tex').rglob('*.re4tex')):
    src['dc/tex/' + p.relative_to(Path(tree) / 'dc' / 'tex').as_posix()] = p
NAME = re.compile(r'([0-9a-f]{8})-([0-9a-f]{8})\.re4tex$')
for j in (c2j, c16j):
    for k, v in json.load(open(j))['replace'].items():
        if k == 'tex':
            for t in (v if isinstance(v, list) else [v]):
                for p in Path(t).rglob('*.re4tex'):
                    src['dc/tex/%s/%s' % (p.name[0].lower(), p.name.lower())] = p
        elif isinstance(v, str) and k.startswith('dc/tex/'):
            src[k] = Path(v)
vq = []
for d in base['loose']:
    m = NAME.search(d); key = (int(m.group(1), 16), int(m.group(2), 16))
    if key not in ch2 and p17[key] != src[d].read_bytes():
        vq.append(m.group(0)[:-7])
(Path(cand) / 'vq-keys.txt').write_text(''.join(k + '\n' for k in sorted(vq)))
print('vq-keys', len(vq))
