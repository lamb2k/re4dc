"""ch5regen: the recorded k9cast.py + k9cat.py edits (cast16 10-17 07:51) on a copy of regcast-st3:
soldr-em1e-06p rooms gain r315 in source.json, ps2-v1/revision-manifest.json and the integration catalog (entry 11).
usage: c5r_k9edit.py <regcast-st3 copy>"""
import json, sys
R = sys.argv[1]
B = R + '/soldr-em1e-06p'
for f in (B + '/source.json', B + '/ps2-v1/revision-manifest.json'):
    t = open(f).read(); d = json.loads(t)

    def fix(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'rooms' and isinstance(v, list) and 'r31d' in v and 'r315' not in v:
                    v.append('r315'); v.sort(); print('rooms', f[-30:], v)
                else:
                    fix(v)
        elif isinstance(o, list):
            for v in o:
                fix(v)
    fix(d)
    json.dump(d, open(f, 'w'), indent=None if not t.startswith('{\n') else 1)
p = R + '/ps2-overlay/integration-bundle/catalog.json'
t = open(p).read(); d = json.loads(t)
# recorded: d[11] (that regcast also held soldr-em1d-12p..15p); here the same entry by name
e = [x for x in d if x.get('name') == 'soldr-em1e-06p'][0]; print(e.get('name'), e['rooms'])
if 'r315' not in e['rooms']:
    e['rooms'] = sorted(e['rooms'] + ['r315'])
open(p, 'w').write(json.dumps(d, indent=1 if t.startswith('[\n') else None))
print(e['rooms'])
