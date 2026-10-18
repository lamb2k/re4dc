"""cover.py NEED.json OUT.json DIR...: match every needed disc file (sha256) against files under DIR... (WSL).
Writes OUT.json {disc path: source path} for matches; prints coverage by top-level group."""
import hashlib, json, os, sys, collections
need = json.load(open(sys.argv[1]))['need']
want = collections.defaultdict(list)
for k, v in need.items():
    want[v['sha256']].append(k)
found = {}
sizes = {v['size'] for v in need.values()}
for d in sys.argv[3:]:
    for dp, dn, fn in os.walk(d):
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.islink(p) or os.path.getsize(p) > 64 << 20:
                continue
            if os.path.getsize(p) not in sizes:
                continue
            s = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            for k in want.get(s, []):
                found.setdefault(k, p)
json.dump(found, open(sys.argv[2], 'w'), indent=1, sort_keys=True)
g = collections.Counter(); h = collections.Counter()
for k in need:
    top = 'dc/tex' if k.startswith('dc/tex/') else 'dc/mot' if k.startswith('dc/mot/') else k
    (g if k in found else h)[top] += 1
print('matched', len(found), 'of', len(need))
for k in sorted(set(g) | set(h)):
    if h[k]:
        print('  MISSING', k, h[k], 'matched', g[k])
