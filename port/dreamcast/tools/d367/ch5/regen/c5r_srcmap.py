import json, sys, os, collections, re
S = os.path.dirname(os.path.abspath(__file__))
EV = r'C:\Flycast-Evidence\re4-dreamcast\ch5found-20261016'
cache = {}
def stage(run):
    if run not in cache:
        p = os.path.join(EV, run, 'stage.json')
        cache[run] = json.load(open(p))['fixture']['replace'] if os.path.exists(p) else None
    return cache[run]
out = []
c = collections.Counter()
for line in open(os.path.join(S, 'missing.tsv')):
    path, size, sha, run = line.rstrip('\n').split('\t')
    r = stage(run)
    src = '?norun' if r is None else r.get(path, '?nokey')
    if not isinstance(src, str): src = json.dumps(src)
    out.append((path, size, sha, run, src))
    k = re.sub(r'/(r3[0-9a-f]{2})(?=/|$)', '/<room>', src)
    k = '/'.join(k.split('/')[:8])
    c[(path.split('/')[0] + '/' + path.split('/')[1] if path.startswith('dc/') else path.split('/')[0], k)] += 1
with open(os.path.join(S, 'missing-src.tsv'), 'w') as f:
    for o in out: f.write('\t'.join(o) + '\n')
for (a, k), v in sorted(c.items(), key=lambda x: -x[1]): print(v, a, k)
