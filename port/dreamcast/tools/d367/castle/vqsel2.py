import json, collections
cand = json.load(open('/root/probe/lanes-20261015/castle/vq-c31-cands.json'))
fx = set()
for l in open('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/effects-tex/KEYS.tsv'):
    fx.add(l.split('\t')[0])
sel = [c for c in cand if c[2] >= 64 and c[3] >= 64 and c[0] not in fx]
fxhit = [c[0] for c in cand if c[0] in fx]
print('cands', len(cand), 'fx excluded', len(fxhit), 'selected', len(sel))
before = sum(c[2] * c[3] * 2 for c in sel); after = sum(2048 + c[2] * c[3] // 4 for c in sel)
print('VRAM before %d after %d saves %d' % (before, after, before - after))
per = collections.Counter()
for c in sel:
    for r in c[7]: per[r] += c[2] * c[3] * 2 - (2048 + c[2] * c[3] // 4)
print('per-room saving (if all drawn):', dict(per))
open('/root/probe/lanes-20261015/castle/vq-c31-keys.txt', 'w').write('\n'.join(c[0] for c in sel) + '\n')
print(collections.Counter((c[1], c[4], c[5]) for c in sel))
