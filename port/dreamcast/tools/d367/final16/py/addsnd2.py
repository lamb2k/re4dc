"""addsnd2.py <armed.json>... [--snd DIR]: island + final chapter sound data on an r332 fixture (lane final16): the prebuilt
AICA room / enemy banks of snd/aica-f (for archives the fixture already stages: st3/*.dar, the island enemies and
em/em31.drs), the island bio4midi.dat and the ch5 stream file (ch5found16's)."""
import json, sys, os
a = sys.argv[1:]
W = '/root/probe/lanes-20261016/final16/snd/aica-f'
if '--snd' in a:
    i = a.index('--snd'); W = a[i + 1]; del a[i:i + 2]
C5 = '/root/probe/lanes-20261016/ch5found/snd'
for f in a:
    j = json.load(open(f)); r = j['replace']; n = []
    for k in list(r):
        if (k.startswith('st3/') and k.endswith('.dar')) or k in ('em/em1d.drs', 'em/em1e.drs', 'em/em1f.drs', 'em/em25.drs', 'em/em31.drs'):
            p = '%s/%s' % (W, k)
            if os.path.exists(p): r[k] = p; n.append(k)
    r['bgm/bio4midi.dat'] = C5 + '/aica-c5/bgm/bio4midi.dat'
    r['bgm/aica_str.dat'] = '/root/probe/lanes-20261016/final16/snd/str-f/bgm/aica_str.dat'  # ch5f = ch5 + the r332 streams
    json.dump(j, open(f, 'w'), indent=1, sort_keys=True)
    print(os.path.basename(f), 'banks', len(n), [x for x in n if 'r33' in x or 'em31' in x])
