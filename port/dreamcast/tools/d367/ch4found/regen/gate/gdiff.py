# ch4regen: payload differences new gate run vs recorded source run (em/, dc/native, st2, dc/mot, tex.pak), Windows python
import json, sys
H = 'C:/Flycast-Evidence/re4-dreamcast/ch4regen-20261018/h-rg4/scenarios'
E = 'C:/Flycast-Evidence/re4-dreamcast/ch4found-20261016'
for r in sys.argv[1:]:
    n = json.load(open('%s/cx-%s-walk-g5/payload-manifest.json' % (H, r)))
    fx = json.load(open('//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch4regen/gatefix2/%s/cx-%s-rg.armed.json' % (r, r)))
    o = json.load(open(E + '/' + fx['provenance']['ch4regen_gate']['source_run'] + '/payload-manifest.json'))
    d = [k for k in sorted(set(n) | set(o)) if n.get(k, {}).get('sha256') != o.get(k, {}).get('sha256')]
    cls = {}
    for k in d: cls.setdefault(k.split('/')[0] + '/' + (k.split('/')[1] if k.startswith('dc/') else ''), []).append(k)
    print(r, len(d), {c: len(v) for c, v in cls.items()})
    print('   ', [k for k in d if not k.startswith('dc/tex/') and not k.startswith('dc/mot/') and not k.endswith('.ovl')][:40])
