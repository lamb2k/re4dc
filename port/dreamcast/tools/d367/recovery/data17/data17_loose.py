#!/usr/bin/env python3
"""data17_loose.py <tools dir> <payload tree> <ch2 tex.pak> <pak17 tex.pak> <out dir> <data json>...
Candidate pak17 loose set = payload tree's loose dc/tex + the data sets' loose dc/tex (replace entries and 'tex' dirs).
Classifies like disc_pack.py and compares with pak17's added keys. Writes candidate loose-keys.txt / base.json."""
import hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import tex_merge  # noqa: E402

tools, tree, ch2p, p17p, out = sys.argv[1:6]
datas = sys.argv[6:]
NAME = re.compile(r'^dc/tex/[0-9a-f]/([0-9a-f]{8}-[0-9a-f]{8})\.re4tex$')
TN = re.compile(r'^([0-9a-f]{8}-[0-9a-f]{8})\.re4tex$')
sec = lambda n: (n + 2047) // 2048 * 2048
loose = {}
for p in sorted((Path(tree) / 'dc' / 'tex').rglob('*.re4tex')):
    d = 'dc/tex/' + p.relative_to(Path(tree) / 'dc' / 'tex').as_posix()
    if NAME.match(d):
        loose[d] = str(p)
nbase = len(loose)
staged = {}
for dj in datas:
    rep = json.load(open(dj))['replace']
    for k, v in rep.items():
        if k == 'tex':
            for t in (v if isinstance(v, list) else [v]):
                for p in sorted(Path(t).rglob('*.re4tex')):
                    if TN.match(p.name.lower()):
                        staged['dc/tex/%s/%s' % (p.name[0].lower(), p.name.lower())] = str(p)
        elif isinstance(v, str) and NAME.match(k):
            staged[k] = v
loose.update(staged)
ch2, p17 = tex_merge.read(ch2p), tex_merge.read(p17p)
added = {k for k in p17 if k not in ch2}
cls = {}
mism, extra = [], []
rows = []
for d, s in sorted(loose.items()):
    k = tuple(int(x, 16) for x in NAME.match(d).group(1).split('-'))
    b = Path(s).read_bytes()
    if k in ch2:
        c = 'in-pak-same' if ch2[k] == b else 'in-pak-other'
    else:
        c = 'added'
        if k not in added: extra.append(d)
        elif p17[k] != b: mism.append(d)
    x = cls.setdefault(c, [0, 0]); x[0] += 1; x[1] += sec(len(b))
    rows.append((d, hashlib.sha256(b).hexdigest()))
seen = {tuple(int(x, 16) for x in NAME.match(d).group(1).split('-')) for d, _ in rows}
print('base loose', nbase, 'staged', len(staged), 'total', len(loose), 'disc bytes', sum(v[1] for v in cls.values()))
for c, v in sorted(cls.items()): print(' ', c, v)
print('added keys in pak17', len(added), 'covered', len(added & seen), 'loose not in pak17', len(extra),
      'added-class bytes differ (VQ expected 241)', len(mism))
Path(out).mkdir(parents=True, exist_ok=True)
(Path(out) / 'loose-keys.txt').write_text(''.join(d + '\n' for d, _ in rows))
(Path(out) / 'base.json').write_text(json.dumps(dict(
    pak=hashlib.sha256(open(ch2p, 'rb').read()).hexdigest(), out=hashlib.sha256(open(p17p, 'rb').read()).hexdigest(),
    loose={d: h for d, h in rows}), indent=1) + '\n')
