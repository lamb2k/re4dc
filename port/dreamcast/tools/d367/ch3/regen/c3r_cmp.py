"""c3r_cmp.py DIR...: compare *.re4tex (recursive) against srcmap (missing) and all chosen lane targets."""
import hashlib, json, os, sys, glob
S = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(os.path.join(S, 'srcmap.json')))
want = {}
for p, v in m.items(): want.setdefault(v['sha256'], []).append(p)
alltgt = json.load(open(os.path.join(S, 'alltargets.json'))) if os.path.exists(os.path.join(S, 'alltargets.json')) else {}
allsha = {v for v in alltgt.values()}
for d in sys.argv[1:]:
    fs = [f for f in glob.glob(os.path.join(d, '**', '*'), recursive=True) if os.path.isfile(f) and not f.endswith(('.log', 'manifest', '.json'))]
    hit = miss_t = anyt = 0; byname = 0
    for f in fs:
        h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
        if h in want: hit += 1
        if h in allsha: anyt += 1
        k = os.path.basename(f)
        cand = [p for p in m if p.endswith('/' + k)]
        if cand: byname += 1
        if cand and h not in want: miss_t += 1
    print(d, 'files', len(fs), 'missing-sha hits', hit, 'any-target hits', anyt, 'name in missing', byname, 'name-but-sha-differs', miss_t)
