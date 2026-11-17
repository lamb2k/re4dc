#!/usr/bin/env python3
"""mkcpic34.py <base tex.pak> <out dir> key=path ...: pack set over a base pack (cpic pattern): each key's bytes
replace (or are added to) the base, written with texpack.py's layout. Writes dc/tex.pak, pak-derived.json, report.json."""
import hashlib, json, os, struct, subprocess, sys, tempfile, shutil
base, out = sys.argv[1], sys.argv[2]
rows = [a.split('=', 1) for a in sys.argv[3:]]
d = open(base, 'rb').read()
cnt, io = struct.unpack_from('<II', d, 12)[0], struct.unpack_from('<I', d, 16)[0]
tmp = tempfile.mkdtemp(prefix='cpic34-')
try:
    keys = {}
    for i in range(cnt):
        c, f, o, s = struct.unpack_from('<IIII', d, io + 16 * i)
        k = '%08x-%08x' % (c, f); keys[k] = d[o:o + s]
    changed, added, rep = [], [], []
    for k, p in rows:
        b = open(p, 'rb').read()
        if k in keys:
            if keys[k] == b: continue
            changed.append(k)
        else: added.append(k)
        rep.append({'key': k, 'source': p, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b),
                    'base_bytes': len(keys[k]) if k in keys else 0})
        keys[k] = b
    for k, b in keys.items():
        dd = os.path.join(tmp, 'dc', 'tex', k[0]); os.makedirs(dd, exist_ok=True)
        open(os.path.join(dd, k + '.re4tex'), 'wb').write(b)
    os.makedirs(os.path.join(out, 'dc'), exist_ok=True)
    tp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'texpack.py')
    tp = os.environ.get('TEXPACK', tp)
    subprocess.check_call([sys.executable, tp, os.path.join(tmp, 'dc', 'tex'), os.path.join(out, 'dc', 'tex.pak')])
    subprocess.check_call([sys.executable, tp, '--verify', os.path.join(out, 'dc', 'tex.pak')])
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    json.dump({'base': sha(base), 'out': sha(os.path.join(out, 'dc', 'tex.pak')), 'count': len(keys),
               'added': sorted(added), 'changed': sorted(changed), 'removed': []},
              open(os.path.join(out, 'pak-derived.json'), 'w'), indent=1)
    json.dump({'base_pak': base, 'rows': rep}, open(os.path.join(out, 'report.json'), 'w'), indent=1)
    print('count', len(keys), 'changed', changed, 'added', added)
finally:
    shutil.rmtree(tmp)
