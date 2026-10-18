# ch4regen gatefix3: one consistent final-era base for every room = gatefix2 r216 (source run h-c4emW cx-r216-walk-m2,
# the last ch4found run, tex.pak 5ed4ba5a) without its r216-only keys; each room adds its own keys from its gatefix2
# fixture (keys naming the room, evd/ and event/ keys, and dc/tex keys the base lacks) and its own warp.
# Reason: gatefix2 fixtures from older-arm runs mix old dc/mot keys with the final aica-c4c em banks -> r210/r212/r219
# "invalid prepared enemy motion archive" HALT.
import json, os
G2 = '/root/probe/lanes-20261018/ch4regen/gatefix2'; G3 = '/root/probe/lanes-20261018/ch4regen/gatefix3'
base = json.load(open(G2 + '/r216/cx-r216-rg.armed.json'))
brep = {k: v for k, v in base['replace'].items() if 'r216' not in k and k != 'dc/warp.txt'}
ROOMS = 'r206 r210 r222 r201 r219 r211 r216 r212 r213 r214 r217 r218 r215 r229 r221 r22b r220 r223 r224 r21d r225 r21b r226 r227 r228 r22a'.split()
for r in ROOMS:
    fx = json.load(open('%s/%s/cx-%s-rg.armed.json' % (G2, r, r)))
    rep = dict(brep); add = 0
    for k, v in fx['replace'].items():
        if r in k or k.startswith(('evd/', 'event/')) or (k.startswith('dc/tex/') and k not in rep) or k == 'dc/warp.txt':
            if rep.get(k) != v: add += 1
            rep[k] = v
    out = dict(base); out['replace'] = rep
    out['remove'] = sorted(set(base.get('remove', [])) - set(rep))
    prov = dict(fx['provenance']); prov['ch4regen_gate'] = dict(prov['ch4regen_gate'], base='gatefix2 r216 (h-c4emW cx-r216-walk-m2) minus r216 keys', room_keys=add)
    out['provenance'] = prov
    os.makedirs('%s/%s' % (G3, r), exist_ok=True)
    json.dump(out, open('%s/%s/cx-%s-rg3.armed.json' % (G3, r, r), 'w'), indent=1, sort_keys=True)
    print(r, 'room keys', add, 'total', len(rep))
