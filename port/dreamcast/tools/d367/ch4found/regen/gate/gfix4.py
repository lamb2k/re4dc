# ch4regen gatefix4 = gatefix3 + em/pl11.drs (Ashley) at the ch4found recorded version: ch2data's current pl11.drs
# halts the c4hmW arm in the Ashley rooms (r210 r212 r219: "invalid prepared enemy motion archive" right after em/pl11.drs).
import json, os, glob
E = '/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016'
L = '/root/probe/lanes-20261018/ch4regen'
st = json.load(open(E + '/h-c4emW/scenarios/cx-r216-walk-m2/stage.json'))
p = st['fixture']['replace']['em/pl11.drs']
res = json.load(open(L + '/gatefix/resolve.json'))
q = p if os.path.exists(p) else res.get(p)
print('recorded pl11', p, '->', q)
assert q
for f in sorted(glob.glob(L + '/gatefix3/*/cx-*-rg3.armed.json')):
    d = json.load(open(f)); r = f.split('/')[-2]
    d['replace']['em/pl11.drs'] = q
    d['provenance']['ch4regen_gate']['pl11'] = 'recorded ch4found version (ch2data pl11 halts c4hmW)'
    os.makedirs('%s/gatefix4/%s' % (L, r), exist_ok=True)
    json.dump(d, open('%s/gatefix4/%s/cx-%s-rg4.armed.json' % (L, r, r), 'w'), indent=1, sort_keys=True)
print('ok')
