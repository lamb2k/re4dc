# ch4regen gate table: new run (h-rg4) vs the recorded ch4found source run for the same room (Windows python).
import json, glob, os, re
H = 'C:/Flycast-Evidence/re4-dreamcast/ch4regen-20261018/h-rg4/scenarios'
E = 'C:/Flycast-Evidence/re4-dreamcast/ch4found-20261016'
K = ['entry', 'no_fatal', 'short_walk', 'ps2_world_draw', 'tex_check', 'model_source_fallback', 'leon_gc']
ab = lambda v: {'PASS': 'P', 'FAIL': 'F', 'UNPROVEN': 'U'}.get(v, '-')
for s in sorted(glob.glob(H + '/cx-r2*-walk-' + (__import__('sys').argv[1] if len(__import__('sys').argv) > 1 else 'g5'))):
    r = os.path.basename(s).split('-')[1]
    rr = os.path.join(s, 'rfp-result.json')
    if not os.path.exists(rr): print(r, 'NO RESULT'); continue
    d = json.load(open(rr)); c = d.get('checks', {})
    g = json.load(open(s + '/cx-firstpass-check.json')) if os.path.exists(s + '/cx-firstpass-check.json') else {}
    fx = json.load(open('//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch4regen/gatefix2/%s/cx-%s-rg.armed.json' % (r, r)))
    src = fx['provenance']['ch4regen_gate']['source_run']
    o = E + '/' + src + '/rfp-result.json'
    oc = json.load(open(o)).get('checks', {}) if os.path.exists(o) else {}
    fails = [f[:90] for k in ('no_fatal', 'tex_check', 'model_source_fallback') for f in g.get(k, {}).get('failures', [])][:2]
    print('%s new %s | old %s | %s | %s' % (r, ''.join(ab(c.get(k)) for k in K), ''.join(ab(oc.get(k)) for k in K),
                                    'disc-del' if d.get('discs_removed') else 'DISC-LEFT', '; '.join(fails)))
print('columns:', ' '.join(K))
