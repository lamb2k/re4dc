"""phases.py TICKS.tsv [console_pt.json key]: model per-phase ms, mirroring tick_log.cpp, next to the console PT means."""
import csv, sys, json, collections, os
NAMES = ['CamCtrl.Check', 'ScenarioMove', 'EmMgr.move', 'Player', 'ObjMgr.move', 'CameraMove', 'EspMove', 'LightMove',
         'TaskScheduler', 'EspTrans', 'ShadowTrans', 'MirrorTrans', 'ClothTrans', 'objTrans', 'SndWatcher']
MHZ = 200.0

def model(path):
    fr = collections.defaultdict(dict)
    for r in csv.DictReader(open(path), delimiter='\t'):
        fr[r['trace']][int(r['idx'])] = (float(r['first']), float(r['last']), int(r['n']), float(r['frame_cycles']))
    rows = []
    for tr, d in sorted(fr.items()):
        if 32 not in d or 4 not in d or 0 not in d:
            rows.append(dict(trace=os.path.basename(tr), note='incomplete', keys=sorted(d))); continue
        z = d[32][1]                      # last zero_tick store of the frame
        st = {k: v[1] - z for k, v in d.items() if k < 32}
        r = dict(trace=os.path.basename(tr), frame_ms=d[0][3] / MHZ / 1000, zero_at=z / MHZ / 1000)
        r['total'] = st[0]; r['setup'] = st[4]; r['cpu'] = st.get(2); r['end'] = st.get(1); r['remain'] = st.get(3)
        prev = st[4]
        for i, n in enumerate(NAMES):
            k = 5 + i
            if k in st:
                r[n] = st[k] - prev; prev = st[k]
        if 13 in st and 23 in st:  # TaskScheduler idx 13, SndWatcher idx 19
            pass
        it, isnd = 5 + NAMES.index('TaskScheduler'), 5 + NAMES.index('SndWatcher')
        if it in st and isnd in st:
            r['logic'] = st[it] - st[4]; r['trans'] = st[isnd] - st[it]; r['post'] = st[2] - st[isnd] if 2 in st else None
        for k, v in list(r.items()):
            if isinstance(v, float) and k not in ('frame_ms', 'zero_at'):
                r[k] = v / MHZ / 1000      # cycles -> ms
        rows.append(r)
    return rows

rows = model(sys.argv[1])
good = [r for r in rows if 'note' not in r]
print('frames', len(rows), 'complete', len(good))
for r in rows:
    if 'note' in r:
        print(' ', r['trace'], r['note'], r['keys'])
keys = ['total', 'setup', 'logic', 'trans', 'post', 'cpu', 'remain'] + NAMES
avg = {k: sum(r[k] for r in good if r.get(k) is not None) / max(1, sum(1 for r in good if r.get(k) is not None)) for k in keys}
print('per-frame totals (ms):', ' '.join('%.1f' % r['total'] for r in good))
con = None
if len(sys.argv) > 2:
    con = json.load(open(sys.argv[2]))[sys.argv[3]]
print('%-14s %8s %8s %6s' % ('phase', 'model', 'console', 'c/m'))
for k in keys:
    c = con.get(k) / 1000 if con and con.get(k) is not None else None
    print('%-14s %8.2f %8s %6s' % (k, avg[k], '%.2f' % c if c is not None else '-', '%.2f' % (c / avg[k]) if c and avg[k] else '-'))
json.dump(dict(avg=avg, rows=rows), open(sys.argv[1] + '.phases.json', 'w'), indent=1)
