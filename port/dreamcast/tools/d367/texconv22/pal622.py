#!/usr/bin/env python3
"""texconv22: sort the 622 Release21 PAL4 palette keys by use (source consumer policy v5 + whole-pack
coverage v9 owner bindings), against the 1760 pack's current state."""
import collections, json, sys
D = sys.argv[1]
inv = json.load(open('/root/work/lanes/texconv22/s/inv1760.json'))
cov = {r['key']: r for r in json.load(open('/root/re4data/private/mipmap21-current-wholepack-policy-v9-20261021/coverage-status.json'))['normal_rows']}
cp = {r['key']: r for r in json.load(open('/root/re4data/private/mipmap21-fx-consumer-policy-v5-20261021/consumer-policy.json'))['rows']}
orig = [k for k in cov if k in cp or (inv[k]['fmt'] == 4)]
assert len(orig) == 622, len(orig)
B = {'world-common-sprite-source-candidate': 'effect (world-placed sprite)', 'hold-custom-or-generator-effect': 'effect (custom/generator)',
     'hold-unresolved-consumer': 'effect (no source record found)', 'hold-screen-or-mixed-effect': 'screen', 'hold-fixed-ID-UI': 'UI/text'}
rows = []
for k in sorted(orig):
    c = cov[k]; i = inv[k]; d = cp[k]['decision'] if k in cp else None
    world = 'native-world' in c['original_owner_categories']; actor = c['separate_actor_candidate'] is not None
    use = 'world surface' if world else 'actor' if actor else B.get(d, 'effect (rectangular frame, no consumer policy)')
    mipped = bool(i['flags'] & 4)
    if use in ('world surface', 'actor'):
        act = 'convert'
    elif mipped:
        act = 'already mipped in 1760 pack'
    elif use in ('UI/text', 'screen'):
        act = 'stay unmipped'
    else:
        act = 'not converted: effect, outside world/actor scope'
    rows.append(dict(key=k, use=use, owners=c['original_owner_categories'], consumer_policy=d, w=i['w'], h=i['h'], fmt=i['fmt'],
                     mipped_1760=mipped, action=act))
s = collections.Counter((r['use'], r['action']) for r in rows)
summary = {'%s | %s' % k: v for k, v in sorted(s.items())}
json.dump(dict(summary=summary, rows=rows), open(D + '/pal622.json', 'w'), indent=1)
for k, v in summary.items(): print(v, k)
