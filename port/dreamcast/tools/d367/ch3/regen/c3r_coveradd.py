"""c3r_coveradd.py DIR...: (WSL) hash files under DIR (follow symlinks), add uncovered missing.json targets to cover.json."""
import hashlib, json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(S + '/missing.json')); c = json.load(open(S + '/cover.json'))
want = {}
for lane, ms in m.items():
    for p, v in ms.items():
        if lane + '|' + p not in c: want.setdefault(v['sha256'], []).append(lane + '|' + p)
n = 0
for d in sys.argv[1:]:
    for r, _, fs in os.walk(d, followlinks=True):
        for f in fs:
            p = os.path.join(r, f)
            if not os.path.isfile(p) or os.path.getsize(p) > 200 << 20: continue
            h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            for k in want.pop(h, []): c[k] = ['//wsl.localhost/Ubuntu-24.04' + p, 'ch4regen']; n += 1
json.dump(c, open(S + '/cover.json', 'w'), indent=0)
print('added', n, 'still missing', sum(len(v) for v in want.values()))
for v in want.values(): print(' ', v)
