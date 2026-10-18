"""Map each missing target to the fixture source path recorded in the chosen run's stage.json."""
import collections, json, sqlite3, sys, os
S = os.path.dirname(os.path.abspath(__file__))
miss = json.load(open(os.path.join(S, 'missing.json')))
db = sqlite3.connect('file:C:/Game Dev/Emulators/re4dc-recovery/harvest.db?mode=ro', uri=True)
ROOTS = {'castle-20261015': r'C:\Flycast-Evidence\re4-dreamcast\castle-20261015',
         'ch3found-20261016': r'C:\Flycast-Evidence\re4-dreamcast\ch3found-20261016'}
out = {}
for lane, m in miss.items():
    runs = collections.defaultdict(list)
    chosen = dict(db.execute('select path, run from targets where lane=? and chosen=1', (lane,)).fetchall())
    for p in m:
        runs[chosen[p]].append(p)
    for run, ps in runs.items():
        cands = [os.path.join(ROOTS[lane], run, 'stage.json'), os.path.join(ROOTS[lane], run.replace('\\', os.sep), 'stage.json')]
        st = None
        for c in cands:
            if os.path.exists(c):
                st = json.load(open(c)); break
        rep = (st or {}).get('fixture', {}).get('replace', {}) if st else {}
        for p in ps:
            v = rep.get(p)
            src = v if isinstance(v, str) else (json.dumps(v) if v else None)
            out.setdefault(p, {}).update(lane_run=f'{lane}:{run}', src=src, **m[p])
json.dump(out, open(os.path.join(S, 'srcmap.json'), 'w'), indent=0)
c = collections.Counter()
for p, v in out.items():
    s = v['src'] or 'NO-FIXTURE-ENTRY'
    c['/'.join(s.split('/')[:6])] += 1
for k, n in c.most_common(): print(n, k)
