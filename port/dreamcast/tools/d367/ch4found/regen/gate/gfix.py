# ch4regen gate fixtures ("recovered-data gate, ch1-2 at current versions", coordinator option b, 2026-10-18).
# Per ch4 room: the room's recorded ch4found fixture (latest run on tex.pak 5ed4ba5a, else latest run), with
#  - ch1-2 keys -> ch2data-20261018 / cast16data-20261016 (current gated versions; ch22-era versions dropped),
#  - ch4 keys -> the byte-exact ch4regen set (tex.pak 5ed4ba5a, resident 9419a6b6, aica-c4c em banks),
#  - other lost paths -> sha-resolved copies (gate-resolve.json), else dropped (logged),
#  - dc/warp.txt -> a git warp (tools/d367/ch4found/warps) when the room has one, else a walk warp rebuilt from the
#    recorded run's 'warp: start' line (flagged),
#  - dc/*.ovl -> arm c4hmW.
import json, glob, os, re, sys
E = '/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016'
L = '/root/probe/lanes-20261018/ch4regen'
OUT = L + '/gatefix2'
C = '/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018'
CAND = '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs/candidate-routec4hmW'
GW = L + '/tree/port/dreamcast/tools/d367/ch4found/warps'
ROOMS = 'r206 r210 r222 r201 r219 r211 r216 r212 r213 r214 r217 r218 r215 r229 r221 r22b r220 r223 r224 r21d r225 r21b r226 r227 r228 r22a'.split()
ch2 = json.load(open('/root/re4data/private/ch2data-20261018/ch2-data.json')) if os.path.exists('/root/re4data/private/ch2data-20261018/ch2-data.json') else json.load(open('/mnt/c/Game Dev/Emulators/re4-assets-private/ch2data-20261018/ch2-data.json'))
c16 = json.load(open('/root/re4data/private/cast16data-20261016/cast16-data.json'))
cur = dict(ch2['replace']); cur.update(c16['replace'])
CH4LANES = ('ch4found', 'cast16data-ch4', 'ch3found', 'lanes-20261015/castle', 'codex-ps2-castle', 'lanes-20261015/ps2cast', 'cast16')
res = json.load(open(L + '/gatefix/resolve.json'))
mine = {'dc/tex.pak': C + '/texpak/dc/tex.pak', 'dc/resident.bin': C + '/vram/dc/resident.bin'}
for f in glob.glob(C + '/aica-c4c/em/*.drs'): mine['em/' + os.path.basename(f)] = f
os.makedirs(OUT, exist_ok=True)
summary = {}
for r in ROOMS:
    runs = [os.path.dirname(p) for p in glob.glob(E + '/h-*c4*/scenarios/cx-%s-*/payload-manifest.json' % r)]
    fin = [s for s in runs if '5ed4ba5a' in open(s + '/payload-manifest.json').read()]
    src = max(fin or runs, key=lambda s: os.path.getmtime(s + '/stage.json'))
    fx = json.load(open(src + '/stage.json'))['fixture']
    rep, log = {}, {'ch2cur': 0, 'mine': 0, 'kept': 0, 'resolved': 0, 'dropped': []}
    for k, p in fx['replace'].items():
        if k.startswith('dc/') and k.endswith('.ovl') and '/' not in k[3:]: continue
        if k == 'dc/warp.txt': continue
        if k in mine: rep[k] = mine[k]; log['mine'] += 1; continue
        if k in cur and not any(x in p for x in CH4LANES): rep[k] = cur[k]; log['ch2cur'] += 1; continue
        if os.path.exists(p): rep[k] = p; log['kept'] += 1; continue
        if res.get(p): rep[k] = res[p]; log['resolved'] += 1; continue
        if k in cur: rep[k] = cur[k]; log['ch2cur'] += 1; continue
        log['dropped'].append(k)
    for f in glob.glob(CAND + '/*.ovl'): rep['dc/' + os.path.basename(f)] = f
    gw = None
    for pre in ('draw-', 'cov-', 'cast-', 'ce-', 'cen-', 'dec-', 'p-'):
        if os.path.exists('%s/%s%s.txt' % (GW, pre, r)): gw = '%s/%s%s.txt' % (GW, pre, r); break
    if not gw:
        txt = open(src + '/capture/run-output.txt', encoding='latin1').read()
        m = re.search(r'warp: start room=(\w+) next_room=\w+ pos=(-?\d+),(-?\d+),(-?\d+) ang=(-?\d+)/1000', txt)
        gw = '%s/%s/walk-%s.txt' % (OUT, r, r); os.makedirs(os.path.dirname(gw), exist_ok=True)
        open(gw, 'w').write('name rg-%s-walk\n# ch4regen: walk warp rebuilt from %s (warp: start line); Codex walk warp lost\n'
                            'room 0x%s\npos %s %s %s\nang %.4f\ninv default\nact 360 fwd 12\ndump\n'
                            % (r, os.path.relpath(src, E), m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5)) / 1000))
        log['warp'] = 'rebuilt'
    else:
        log['warp'] = os.path.basename(gw)
    rep['dc/warp.txt'] = gw
    out = dict(fx); out['replace'] = rep
    out['remove'] = sorted(set(fx.get('remove', [])) - set(rep) - set(ch2.get('unremove', [])))
    prov = dict(fx.get('provenance', {}))
    prov['ch4regen_gate'] = {'label': 'recovered-data gate, ch1-2 at current versions', 'source_run': os.path.relpath(src, E),
                             'counts': {k: (len(v) if isinstance(v, list) else v) for k, v in log.items()}, 'dropped': log['dropped']}
    if 'fixture_arm' in prov: prov['fixture_arm'] = dict(prov['fixture_arm'], arm='c4hmW', candidate_dir=CAND)
    out['provenance'] = prov
    os.makedirs('%s/%s' % (OUT, r), exist_ok=True)
    json.dump(out, open('%s/%s/cx-%s-rg.armed.json' % (OUT, r, r), 'w'), indent=1, sort_keys=True)
    print(r, os.path.relpath(src, E), {k: (len(v) if isinstance(v, list) else v) for k, v in log.items()}, log['dropped'][:6])
