"""c3r_castleloose.py: loose map for the castle tex chain keys from harvest targets (castle lane) + ch3regen C: out
+ harvest files. Writes castleloose.json {key: wsl path}; reports keys with several shas or no file."""
import collections, json, os, sqlite3, sys
S = os.path.dirname(os.path.abspath(__file__))
keys = sys.argv[1:] or open(os.path.join(S, 'castlekeys.txt')).read().split()
db = sqlite3.connect(r'C:\Game Dev\Emulators\re4dc-recovery\harvest.db')
OUT = r'C:\Game Dev\Emulators\re4-assets-private\ch3regen-20261018'
man = {}
for l in open(os.path.join(OUT, 'MANIFEST.tsv'), encoding='utf-8'):
    f = l.rstrip('\n').split('\t')
    if len(f) > 2: man.setdefault(f[2], os.path.join(OUT, f[0], f[1]))
def wsl(p):
    q = p.replace('\\', '/')
    if q.startswith('//wsl.localhost/Ubuntu-24.04'): return q[len('//wsl.localhost/Ubuntu-24.04'):]
    if q[1:3] == ':/': return '/mnt/' + q[0].lower() + q[2:]
    return q
res = {}; bad = collections.Counter()
for k in keys:
    p = 'dc/tex/%s/%s.re4tex' % (k[0], k)
    shas = [r[0] for r in db.execute("select distinct sha from targets where lane='castle-20261015' and path=?", (p,))]
    if not shas: bad['no target'] += 1; print('notarget', k); continue
    if len(shas) > 1: print('multi', k, [s[:8] for s in shas])
    src = None
    for s in shas:
        if s in man: src = man[s]; break
        r = db.execute("select path from files where sha=? and path not like '%!%' and path not like '%::%' limit 1", (s,)).fetchone()
        if r and os.path.exists(r[0]): src = r[0]; break
    if not src: bad['nofile'] += 1; print('nofile', k, [s[:8] for s in shas]); continue
    res[k] = wsl(src)
json.dump(res, open(os.path.join(S, 'castleloose.json'), 'w'), indent=0)
print('mapped', len(res), dict(bad))
