"""discscan.py FP_ISO NEED.json OUTDIR LIST: for each GD track03 (raw or 2048, base 45000) in LIST, use fp_iso's reader to
find NEED files by sha256 among loose files and tex*.pak entries; record each disc's dc/tex.pak and dc/resident.bin sha."""
import hashlib, importlib.util, json, os, struct, sys
spec = importlib.util.spec_from_file_location('fp', sys.argv[1]); fp = importlib.util.module_from_spec(spec); spec.loader.exec_module(fp)
need = json.load(open(sys.argv[2]))['need']; out = sys.argv[3]
want = {}
for k, v in need.items(): want.setdefault(v['sha256'], []).append(k)
sizes = {v['size'] for v in need.values()}
pj = os.path.join(out, 'discscan.json')
st = json.load(open(pj)) if os.path.exists(pj) else {'got': {}, 'discs': {}}
got = st['got']
def take(b, src):
    if len(b) not in sizes: return
    h = hashlib.sha256(b).hexdigest()
    for k in want.get(h, []):
        if k not in got:
            got[k] = src; q = os.path.join(out, k); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(b)
for disc in [l.strip() for l in open(sys.argv[4]) if l.strip()]:
    if disc in st['discs']: continue
    rec = {}
    try:
        tr = fp.Track(disc, 45000); n0 = len(got)
        for p, e, s in fp.files(tr):
            q = p.lstrip('/')
            if q in ('dc/tex.pak', 'dc/resident.bin') or (q.startswith('dc/tex') and q.endswith('.pak')):
                b = tr.read_bytes(e, s); rec[q] = hashlib.sha256(b).hexdigest()
                if b[:8] == b'RE4PAK1\x00':
                    for i in range(struct.unpack_from('<I', b, 12)[0]):
                        c, f, o, z = struct.unpack_from('<4I', b, 2048 + 16 * i)
                        take(b[o:o + z], disc + '!' + q + '#%08x-%08x' % (c, f))
                take(b, disc + '!' + q)
            elif s in sizes:
                take(tr.read_bytes(e, s), disc + '!' + q)
        rec['new'] = len(got) - n0
    except Exception as ex:
        rec['error'] = str(ex)
    st['discs'][disc] = rec; print(disc, {k: (v[:16] if isinstance(v, str) else v) for k, v in rec.items()}, flush=True)
    json.dump(st, open(pj, 'w'), indent=0)
print('matched', len(got), 'of', len(need))
