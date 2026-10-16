"""summ.py <scenario dir>...: per-room heap 4 / VRAM / KOS / fps / AICA / alive numbers from a Flycast run-output.txt."""
import re, sys, json, os
for sd in sys.argv[1:]:
    p = os.path.join(sd, 'capture', 'run-output.txt')
    t = open(p, encoding='latin-1').read().split('\n')
    rooms = {}
    cur = None
    for l in t:
        m = re.search(r'room lifecycle: phase=enter room=(\w+) generation=\d+ frames=\d+ heap4=\S+ size=(\d+) free=(\d+)', l)
        if m:
            cur = m.group(1); r = rooms.setdefault(cur, dict(h4size=int(m.group(2)), h4entry=int(m.group(3)), h4min=None, h4minlarge=None,
                vram=None, gaps=None, kosmin=None, fps=[], aica_nofit=0, alive=None, ovl=[], kos_entry=None)); continue
        if cur is None: continue
        r = rooms[cur]
        m = re.search(r'room lifecycle: phase=enter vram_free=\d+ kos_free=(\d+)', l)
        if m: r['kos_entry'] = int(m.group(1))
        m = re.search(r'heap4 water: room \w+ free (\d+) largest (\d+)', l)
        if m:
            f, g = int(m.group(1)), int(m.group(2))
            if r['h4min'] is None or f < r['h4min']: r['h4min'] = f; r['h4minlarge'] = g
        m = re.search(r'vram room: r=(\w+) .*', l)
        if m and m.group(1) == cur: r['vram'] = l[l.index('pinned'):][:220]
        m = re.search(r'vram gaps: r=(\w+) .*kos=(\d+)', l)
        if m and m.group(1) == cur:
            r['gaps'] = l[l.index('refusals'):][:200]
            k = int(m.group(2)); r['kosmin'] = k if r['kosmin'] is None else min(r['kosmin'], k)
        m = re.search(r'page=FPS ([\d.]+)', l)
        if m: r['fps'].append(float(m.group(1)))
        if 'does not fit' in l and l.startswith('aica'): r['aica_nofit'] += 1
        m = re.search(r'alivecap: peak (\d+) room (\w+)', l)
        if m: r['alive'] = int(m.group(1))
        m = re.search(r'route overlay: (\w+) load \d+ (\d+) B .* heap(\d)', l)
        if m: r['ovl'].append('%s %s B heap%s' % m.groups())
    for k, r in rooms.items():
        f = r.pop('fps'); r['fps_last5'] = f[-5:]
    print(os.path.basename(sd.rstrip('/')), json.dumps(rooms, indent=1))
