"""c3r_remhit.py DIR...: which remaining.tsv shas exist under DIRs (by sha); prints disc path -> file."""
import hashlib, os, sys
S = os.path.dirname(os.path.abspath(__file__))
rem = {}
for l in open(os.path.join(S, 'remaining.tsv')):
    f = l.rstrip('\n').split('\t')
    if len(f) >= 4: rem.setdefault(f[2], set()).add(f[1]);
sizes = {int(l.split('\t')[3]) for l in open(os.path.join(S, 'remaining.tsv')) if l.strip()}
hits = {}
for d in sys.argv[1:]:
    for root, _, fs in os.walk(d):
        for x in fs:
            p = os.path.join(root, x)
            try:
                if os.path.getsize(p) not in sizes: continue
            except OSError: continue
            h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            if h in rem and h not in hits: hits[h] = p
for h, p in hits.items(): print(sorted(rem[h]), p)
print('hits', len(hits), 'of', len(rem))
