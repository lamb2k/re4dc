#!/usr/bin/env python3
"""ch5tex: rebuild a recorded scenario's dc/tex loose map as an armed.json whose replace paths hold the recorded shas.
usage: c5t_fixmat.py <harvest.db> <outdir> <scenario dir>...   (WSL python)
Resolution by sha: ch5regen found.tsv (out/files), recorded path if it still holds the sha, harvested loose file,
harvested disc member, harvested pak entry (pak:<sha>/<key>), cache. Prints unresolved."""
import hashlib, json, os, sqlite3, struct, sys
db, OUT = sys.argv[1:3]
L = '/root/probe/lanes-20261018/ch5regen'
XC = '/root/probe/lanes-20261018/ch5tex/xcache'
os.makedirs(XC, exist_ok=True); os.makedirs(OUT, exist_ok=True)
regen = {}
for line in open(L + '/found.tsv'):
    p, s, _ = line.rstrip('\n').split('\t')
    regen.setdefault(s, L + '/out/files/' + p)
for root, _, fs in os.walk(L):
    for f in fs:
        if f.endswith('.re4tex'):
            p = os.path.join(root, f)
            regen.setdefault(hashlib.sha256(open(p, 'rb').read()).hexdigest(), p)
con = sqlite3.connect(db)
paks = {}


def winpath(p):
    if len(p) > 2 and p[1] == ':' and '::' not in p and '!' not in p:
        return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')
    return None


def fsha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def pakfile(psha):
    if psha in paks:
        return paks[psha]
    paks[psha] = None
    for (p,) in con.execute("select path from files where sha like ? and source_kind='loose'", (psha + '%',)):
        w = winpath(p)
        if w and os.path.isfile(w):
            paks[psha] = w; break
    if paks[psha] is None:
        for d in ('/root/probe/lanes-20261018', '/root/probe/lanes-20261017r', '/root/re4data/private', '/root/re4payload'):
            pass
    return paks[psha]


def from_pak(s):
    for (p,) in con.execute("select path from files where sha=? and source_kind='pakentry'", (s,)):
        if not p.startswith('pak:'):
            continue
        psha, name = p[4:].split('/', 1)
        pf = pakfile(psha)
        if not pf:
            continue
        b = open(pf, 'rb').read()
        n, io = struct.unpack_from('<II', b, 12)
        key = name.split('.')[0]
        c, f = (int(x, 16) for x in key.split('-'))
        for i in range(n):
            a, bb, o, z = struct.unpack_from('<4I', b, io + 16 * i)
            if (a, bb) == (c, f):
                blob = b[o:o + z]
                if hashlib.sha256(blob).hexdigest() == s:
                    x = os.path.join(XC, s); open(x, 'wb').write(blob); return x
    return None


def resolve(s, rec):
    if s in regen:
        return regen[s], 'regen'
    x = os.path.join(XC, s)
    if os.path.isfile(x):
        return x, 'cache'
    if rec and rec.startswith('/') and os.path.isfile(rec) and fsha(rec) == s:
        return rec, 'recorded'
    for (p,) in con.execute("select path from files where sha=? and source_kind='loose'", (s,)):
        w = winpath(p)
        if w and os.path.isfile(w):
            return w, 'harvest'
    r = from_pak(s)
    if r:
        return r, 'pakentry'
    return None, None


for sd in sys.argv[3:]:
    st = json.load(open(sd + '/stage.json')); pm = json.load(open(sd + '/payload-manifest.json'))
    rec = st['fixture']['replace']
    rep, how, un = {}, {}, []
    for path in rec:
        if not (path.startswith('dc/tex/') and path.endswith('.re4tex')):
            continue
        s = pm.get(path, {}).get('sha256')
        if not s:
            un.append((path, 'no-sha')); continue
        src, h = resolve(s, rec[path])
        if not src:
            un.append((path, s[:8])); continue
        rep[path] = src; how[h] = how.get(h, 0) + 1
    name = os.path.basename(sd.rstrip('/'))
    json.dump({'replace': rep}, open('%s/%s.armed.json' % (OUT, name), 'w'), indent=1, sort_keys=True)
    print(name, 'tex', len(rep), how, 'UNRESOLVED', len(un), un[:5], flush=True)
