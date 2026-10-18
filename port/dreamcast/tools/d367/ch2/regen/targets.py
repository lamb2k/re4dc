"""targets.py: the ch2 data set's per-file target shas, from surviving staged-run evidence (stage.json fixture map +
payload-manifest.json shas). Picks the newest run whose fixture maps files from ch2data-20261016 (and cast16data)."""
import json, os, glob, sys, collections
roots = [r'C:\Flycast-Evidence\re4-dreamcast\ch2code-20261016', r'C:\Flycast-Evidence\re4-dreamcast\cast16-20261016']
best = []
for root in roots:
    for st in glob.glob(os.path.join(root, '*', 'stage.json')):
        try:
            s = json.load(open(st))
        except Exception:
            continue
        fx = s.get('fixture') or {}
        rep = fx.get('replace') or {}
        n = sum(1 for v in rep.values() if isinstance(v, str) and 'ch2data-20261016' in v)
        c = sum(1 for v in rep.values() if isinstance(v, str) and 'cast16data' in v)
        if n:
            best.append((os.path.getmtime(st), n, c, st))
best.sort()
for b in best[-8:]:
    print(b)
pick = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else best[-1][3]
s = json.load(open(pick)); rep = s['fixture']['replace']
pm = json.load(open(os.path.join(os.path.dirname(pick), 'payload-manifest.json')))
base = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
basesha = collections.defaultdict(list)
for k, v in base.items():
    basesha[v['sha256']].append(k)
out = {}
for k, v in sorted(rep.items()):
    if not isinstance(v, str):
        continue
    if 'ch2data-20261016' in v or 'cast16data' in v:
        m = pm.get(k) or {}
        out[k] = dict(src=v, sha256=m.get('sha256'), size=m.get('size'),
                      on_base_same_path=(base.get(k, {}).get('sha256') == m.get('sha256')),
                      on_base_any=basesha.get(m.get('sha256'), [])[:2])
json.dump(dict(stage=pick, files=out), open('targets.json', 'w'), indent=1)
cnt = collections.Counter()
for k, v in out.items():
    top = '/'.join(k.split('/')[:2]) if not k.startswith('dc/tex/') else 'dc/tex'
    cnt[(top, 'base' if v['on_base_any'] else 'need')] += 1
for k, v in sorted(cnt.items()):
    print(k, v)
print('total', len(out), 'need', sum(1 for v in out.values() if not v['on_base_any']))
