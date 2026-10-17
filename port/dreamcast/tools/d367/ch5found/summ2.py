"""summ2.py <scenario dir>...: round 2 per-run digest (rfp checks + heap 4 / VRAM / KOS + cap 6 + kills + gaps)."""
import re, sys, json, os, collections
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
out = {}
for sd in sys.argv[1:]:
    name = os.path.basename(sd.rstrip('/'))
    p = os.path.join(sd, 'capture', 'run-output.txt')
    if not os.path.exists(p):
        out[name] = 'NO_OUTPUT'; continue
    t = open(p, encoding='latin-1').read().split('\n')
    try: rf = json.load(open(os.path.join(sd, 'rfp-result.json')))
    except Exception: rf = {}
    d = dict(overall=rf.get('overall'), fails=[k for k, v in (rf.get('checks') or {}).items() if v == 'FAIL'],
             rooms=[], h4size=None, h4min=None, vram=None, kosmin=None, fps=[], aica=collections.Counter(), streams=set(),
             peak=0, holds=0, parks=0, releases=0, defers=0, alive_max=0, alive_last=None, kills=0, kill_left=None,
             emerr=set(), evtfail=set(), nmrs=set(), halt=[], gaps=None, leon_gc=0)
    for l in t:
        m = re.search(r'room lifecycle: phase=enter room=(\w+) generation=\d+ frames=\d+ heap4=\S+ size=(\d+) free=(\d+)', l)
        if m: d['rooms'].append(m.group(1)); d['h4size'] = int(m.group(2))
        m = re.search(r'heap4 water: room \w+ free (\d+) largest (\d+)', l)
        if m and (d['h4min'] is None or int(m.group(1)) < d['h4min'][0]): d['h4min'] = (int(m.group(1)), int(m.group(2)))
        m = re.search(r'vram room: r=(\w+) .*', l)
        if m: d['vram'] = re.sub(r'\s+', ' ', l[l.index('pinned'):])[:160]
        m = re.search(r'vram gaps: r=(\w+) .*kos=(\d+)', l)
        if m:
            k = int(m.group(2)); d['kosmin'] = k if d['kosmin'] is None else min(d['kosmin'], k)
            d['gaps'] = re.sub(r' (snd_used|meta)=\d+', '', l[l.index('refusals'):])[:150]
        m = re.search(r'page=FPS ([\d.]+)', l)
        if m: d['fps'].append(float(m.group(1)))
        m = re.search(r'aica: blk (\d+) \((\d+) GC bytes\) does not fit', l)
        if m: d['aica'][m.group(1) + ':' + m.group(2)] += 1
        m = re.search(r'stream sbb=(\w+)( \([^)]*\))? not in aica_str', l)
        if m: d['streams'].add(m.group(1))
        m = re.search(r'alivecap: peak (\d+)', l)
        if m: d['peak'] = max(d['peak'], int(m.group(1)))
        if 'alivecap: hold ' in l: d['holds'] += 1
        if 'alivecap: park ' in l: d['parks'] += 1
        if 'alivecap: release ' in l: d['releases'] += 1
        if 'alivecap: defer send' in l: d['defers'] += 1
        m = re.search(r'warp: alive (\d+) room', l)
        if m: d['alive_max'] = max(d['alive_max'], int(m.group(1))); d['alive_last'] = int(m.group(1))
        if re.search(r'kill 0x\w+ hp<=0', l): d['kills'] += 1
        m = re.search(r'kill repeat (\d+) left', l)
        if m: d['kill_left'] = int(m.group(1))
        m = re.search(r'readEmData\(\): error! (\S+)|Memory allocate failed.*?(em/\S+)', l)
        if m: d['emerr'].add(m.group(1) or m.group(2))
        m = re.search(r'EvtRead\w*: .*?(\w+\.evd)?.*(DC\.setData failed|mem over)', l)
        if m: d['evtfail'].add(l.strip()[:90])
        m = re.search(r'NMRS .*? id=(\w+) .*?plan=G .*?declined=(\d+)', l)
        if m and int(m.group(2)) > 0: d['nmrs'].add(m.group(1))
        if re.search(r'HALT|Coming Soon|module: id \d+ not in the image|Out of memory', l): d['halt'].append(l.strip()[:100])
        if 'LEON-GC' in l and 'FAIL' in l: d['leon_gc'] += 1
    d['fps'] = d['fps'][-3:]
    for k in ('aica',): d[k] = dict(d[k])
    for k in ('streams', 'emerr', 'evtfail', 'nmrs'): d[k] = sorted(d[k])[:6]
    d['halt'] = d['halt'][:3]
    out[name] = d
print(json.dumps(out, indent=1))
