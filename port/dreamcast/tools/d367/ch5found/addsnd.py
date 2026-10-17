"""addsnd.py <armed.json>...: island sound data on an island fixture: the prebuilt AICA room / enemy banks (snd/aica-c5,
for archives the fixture already stages), the island bio4midi.dat (ROOM_BGM0 #7 / #14) and the ch5 stream file."""
import json, sys, os
W = '/root/probe/lanes-20261016/ch5found/snd'
for f in sys.argv[1:]:
    j = json.load(open(f)); r = j['replace']; n = 0
    for k in list(r):
        if (k.startswith('st3/') and k.endswith('.dar')) or k in ('em/em1d.drs', 'em/em1e.drs', 'em/em1f.drs', 'em/em25.drs'):
            p = '%s/aica-c5/%s' % (W, k)
            if os.path.exists(p): r[k] = p; n += 1
    r['bgm/bio4midi.dat'] = W + '/aica-c5/bgm/bio4midi.dat'
    r['bgm/aica_str.dat'] = W + '/str-c5/bgm/aica_str.dat'
    json.dump(j, open(f, 'w'), indent=1, sort_keys=True)
    print(os.path.basename(f), 'banks', n)
