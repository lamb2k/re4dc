#!/usr/bin/env python3
"""ch5regen gate fixtures: for each island room's recorded run (stage.json + payload-manifest.json), a fixture over the
current stager base (Test 16.3 disc a61dfc16) whose staged payload equals the recorded payload: every recorded path
whose sha differs from the base is replaced by a recovered file with that sha; base paths absent from the recorded
payload are removed. Recovered files: this lane's regenerated set (out/files), the recorded path if it still holds the
sha, harvested loose files (harvest.db), the recorded harness clone's program files.
usage: c5r_gatefix.py <harvest.db> <outdir> <room>=<recorded scenario dir> ...   (WSL python; paths /mnt/c)"""
import hashlib, json, os, sqlite3, sys
db, OUT = sys.argv[1:3]
L = '/root/probe/lanes-20261018/ch5regen'
BASE_PM = '/root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7/payload-manifest.json'
base = {k: v['sha256'] for k, v in json.load(open(BASE_PM)).items()}
regen = {}
for line in open(L + '/found.tsv'):
    p, s, _ = line.rstrip('\n').split('\t')
    regen.setdefault(s, L + '/out/files/' + p)
con = sqlite3.connect(db)
cache = {}
# lane-committed small files (warps) of the ch5found16 tree, by sha
committed = {}
G = L + '/game-249effe5/port/dreamcast/tools/d367/ch5found'
for root, _, files in list(os.walk(G)) + list(os.walk(L + '/fixtures')):
    for f in files:
        p = os.path.join(root, f)
        committed.setdefault(hashlib.sha256(open(p, 'rb').read()).hexdigest(), p)
# the chosen (recovered) target sha per disc path, used when the run's own sha is not recoverable
chosen = {p: s for p, s in con.execute("select path, sha from targets where lane='ch5found-20261016' and chosen=1")}


def fsha(p):
    if p not in cache:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 22), b''):
                h.update(b)
        cache[p] = h.hexdigest()
    return cache[p]


def winpath(p):
    if len(p) > 2 and p[1] == ':' and '::' not in p and '!' not in p:
        return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')
    return None


XC = L + '/gate/xcache'


def iso_read(img, member):
    """read one file out of a disc image (2048 / 2352-byte sectors, ISO at LBA 16 or GD LBA 45016)."""
    import struct
    f = open(img, 'rb')
    for ss, off, base in ((2048, 0, 0), (2048, 0, 45000), (2352, 16, 45000), (2352, 16, 0)):
        def sect(lba, n=1, ss=ss, off=off, base=base):
            b = bytearray()
            for i in range(n):
                f.seek((lba - base + i) * ss + off); b += f.read(2048)
            return bytes(b)
        try:
            pvd = sect(base + 16)
        except Exception:
            continue
        if pvd[1:6] != b'CD001':
            continue
        ext, size = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
        comps = member.upper().split('/')
        for c in comps:
            data = sect(ext, (size + 2047) // 2048); o = 0; hit = None
            while o < len(data):
                ln = data[o]
                if not ln:
                    o = (o // 2048 + 1) * 2048; continue
                e, s_ = struct.unpack_from('<I', data, o + 2)[0], struct.unpack_from('<I', data, o + 10)[0]
                nl = data[o + 32]; name = data[o + 33:o + 33 + nl].decode('latin1').split(';')[0].upper()
                if name == c:
                    hit = (e, s_); break
                o += ln
            if hit is None:
                return None
            ext, size = hit
        return sect(ext, (size + 2047) // 2048)[:size]
    return None


def harvested(s):
    for (p,) in con.execute("select path from files where sha=? and source_kind='loose'", (s,)):
        w = winpath(p)
        if w and os.path.isfile(w):
            return w
    x = os.path.join(XC, s)
    if os.path.isfile(x):
        return x
    for (p,) in con.execute("select path from files where sha=? and source_kind='disc'", (s,)):
        img, member = p.split('::', 1)
        w = winpath(img)
        if not w or not os.path.isfile(w) or w.endswith('.gdi'):
            continue
        try:
            b = iso_read(w, member)
        except Exception:
            b = None
        if b is not None and hashlib.sha256(b).hexdigest() == s:
            os.makedirs(XC, exist_ok=True); open(x, 'wb').write(b); return x
    return None


os.makedirs(OUT, exist_ok=True)
for arg in sys.argv[3:]:
    room, sd = arg.split('=', 1)
    st = json.load(open(sd + '/stage.json')); pm = json.load(open(sd + '/payload-manifest.json'))
    rec = st['fixture']['replace']
    harness = os.path.dirname(os.path.dirname(sd)); arm = st['arm']
    rep, unres, how, subs = {}, [], {}, []
    for path, meta in pm.items():
        s = meta['sha256']
        if base.get(path) == s:
            continue
        src = None
        if path == '1ST_READ.BIN' or (path.startswith('dc/') and path.endswith('.ovl')):
            cand = os.path.join(harness, 'programs', arm, os.path.basename(path))
            if os.path.isfile(cand) and fsha(cand) == s:
                src = cand; how['program'] = how.get('program', 0) + 1
        if src is None and s in regen:
            src = regen[s]; how['regen'] = how.get('regen', 0) + 1
        if src is None:
            r = rec.get(path)
            if r and r.startswith('/') and os.path.isfile(r) and fsha(r) == s:
                src = r; how['recorded'] = how.get('recorded', 0) + 1
        if src is None:
            src = harvested(s)
            if src:
                how['harvest'] = how.get('harvest', 0) + 1
        if src is None and s in committed:
            src = committed[s]; how['committed'] = how.get('committed', 0) + 1
        if src is None and path == 'dc/warp.txt':
            import re as _re
            m = _re.search(rb'warp: /cd/dc/warp.txt (\S+)', open(sd + '/capture/run-output.txt', 'rb').read())
            wn = m.group(1).decode() if m else None
            for d in ('/mnt/c/Flycast-Evidence/re4-dreamcast/st3-20261014/fixtures/' + room, '/mnt/c/tmp/ch5b', '/mnt/c/tmp/ch5/w', '/mnt/c/tmp/ch5'):
                if wn and os.path.isfile('%s/%s.txt' % (d, wn)):
                    src = '%s/%s.txt' % (d, wn); subs.append((path, s[:8], 'by name ' + src)); how['warp-name'] = 1; break
        if src is None and path == 'dc/warp.txt':
            for n in ('warps2/cx-%s-r2.txt' % room, 'warps/cx-%s-door.txt' % room, 'warps/cx-%s-stagejump.txt' % room):
                if os.path.isfile(os.path.join(G, n)):
                    src = os.path.join(G, n); subs.append((path, s[:8], 'committed ' + n)); how['warp-committed'] = 1; break
        if src is None and path in chosen and chosen[path] != s and path != 'dc/warp.txt':
            c = chosen[path]
            src = regen.get(c) or harvested(c) or committed.get(c)
            if src:
                how['chosen-sub'] = how.get('chosen-sub', 0) + 1; subs.append((path, s[:8], c[:8]))
        if src is None:
            unres.append((path, s[:8], rec.get(path, '')[-80:])); continue
        rep[path] = src
    remove = sorted(k for k in base if k not in pm)
    fx = dict(replace=rep, remove=remove, provenance=dict(
        ch5regen='gate fixture: recorded payload of %s over the stager base; %d unresolved' % (sd, len(unres)), arm=arm))
    json.dump(fx, open('%s/%s.json' % (OUT, room), 'w'), indent=1, sort_keys=True)
    fx['provenance']['substituted'] = [list(x) for x in subs]
    fx['provenance']['unresolved_kept_base'] = [list(x) for x in unres]
    json.dump(fx, open('%s/%s.json' % (OUT, room), 'w'), indent=1, sort_keys=True)
    print(room, arm, 'payload', len(pm), 'replace', len(rep), how, 'remove', len(remove), 'UNRESOLVED', len(unres), flush=True)
    for u in unres[:12]:
        print('   ', *u)
