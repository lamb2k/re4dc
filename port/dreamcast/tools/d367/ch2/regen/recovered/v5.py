import json, hashlib, os
L = '/root/probe/lanes-20261014/ch22/'
A = L + 'snd/aica-c23/'
d = json.load(open(L + 'fix/route-v4.json'))
rep = d['replace']
def h(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12] if p and os.path.exists(p) else None
take = ['bgm/bio4midi.dat', 'em/em17.drs', 'st1/r11d.dar', 'st1/r11e.dar', 'st1/r10f.dar', 'st1/r11f.dar', 'st2/r200.dar',
        'em/em16.drs', 'em/em35.drs']
for root, _, fs in os.walk(A):
    for f in fs:
        k = os.path.relpath(os.path.join(root, f), A)
        cur = rep.get(k)
        same = h(cur) == h(A + k)
        if k in take:
            print('TAKE', k, h(cur), '->', h(A + k))
            rep[k] = A + k
        elif not same:
            print('KEEP', k, 'route', h(cur), 'aica-c23', h(A + k), (cur or '')[:80])
rep['bgm/aica_str.dat'] = L + 'snd/str-c23/bgm/aica_str.dat'
d['remove'] = [x for x in d['remove'] if x not in rep]
d['provenance']['route-v5'] = ('route-v4 + chapter 2-3 AICA banks (snd/aica-c23: aica_banks.py build, route through r200, '
    'nested freeze title..r103 ; title..r11c) for r11d r11e r10f r11f r200 em16 em35, bio4midi.dat (#6 #8 prebuilt), '
    'em17.drs at the planned 8 kHz (r113 arena), aica_str.dat = --streams ch23')
json.dump(d, open(L + 'fix/route-v5.json', 'w'), indent=1, sort_keys=True)
print('route-v5', len(rep))
