#!/usr/bin/env python3
"""island_tex_prov.py ROWS.tsv OUT.tsv  (lane island-gca, 2026-11-17)
Reviewed exact-bytes provenance rows for the Disc 3 texture keys the GC-ASSET judge lists as unknown.
ROWS.tsv = room, kind, id, sha256, provenance (unique rows of the judge's failures).
A key is credited to PS2 only with a trace, in this order:
  A  an assets-dc store provenance.tsv names the output sha (dcf3isl, isl15 ...): its ps2_sha256 / ps2_source row is copied.
  B  no row, but a loose store file or tex.pak member has exactly these bytes and its picture header names a PS2 conversion
     (material 'PS2 rNNN texture N', 'ps2-source', 'ps2cast_...', 'ps2mask_...'): the store file is the source (ps2_sha256 = same bytes).
Everything else is printed as UNPROVEN and gets no row."""
import glob, hashlib, re, struct, sys
PRIV = '/root/re4data/private/'
rows = [l.rstrip('\n').split('\t') for l in open(sys.argv[1]) if l.strip()]
tx = [r for r in rows if r[1] == 'texture' and r[4] == 'unknown']
def rdpak(p):
    b = open(p, 'rb').read(); _m, _v, n, io, _d = struct.unpack_from('<8s4I', b, 0)
    return {'%08x-%08x' % (c, f): b[o:o + s] for c, f, o, s in (struct.unpack_from('<4I', b, io + 16 * i) for i in range(n))}
prov = {}
for f in glob.glob(PRIV + '*/provenance.tsv'):
    st = f.split('/')[-2]
    for l in open(f):
        c = l.rstrip('\n').split('\t')
        if len(c) >= 5 and len(c[1]) == 64:
            prov.setdefault(c[1], (st, c[2], c[3], c[4]))
loose = {}
for l in open(sys.argv[3]):
    h, p = l.rstrip('\n').split('  ', 1); loose.setdefault(h, p[2:])
pak = {}
for n in ('dcf3pak-20261102', 'island-d3-20261102'):
    for k, v in rdpak(PRIV + n + '/dc/tex.pak').items():
        pak.setdefault(hashlib.sha256(v).hexdigest(), (n, k, v))
PS2 = re.compile(rb'PS2 r[0-9a-f]+ texture \d+|ps2-source|ps2cast_[ -~]{3,30}|ps2mask_[ -~]{3,30}')
out, bad = [], []
seen = set()
for r in tx:
    h = r[3]
    if h in seen: continue
    seen.add(h)
    if h in prov and 'PS2' in prov[h][2]:
        st, ps, src, ev = prov[h]
        out.append(('texture', r[2], h, ps, src, 'exact bytes = store %s provenance.tsv row (%s)' % (st, ev[:160])))
        continue
    d = None; where = None
    if h in loose:
        d = open(PRIV + loose[h], 'rb').read(); where = 'store file %s' % loose[h]
    elif h in pak:
        d = pak[h][2]; where = '%s dc/tex.pak member %s' % (pak[h][0], pak[h][1])
    if d is not None:
        m = PS2.search(d[:400])
        if m:
            out.append(('texture', r[2], h, h, 'PS2 USA picture conversion: header names "%s"' % m.group(0).decode()[:48],
                        'exact bytes = %s (picture header material names its PS2 source)' % where))
            continue
    bad.append((r[0], r[2], h[:12], where or 'no byte match'))
open(sys.argv[2], 'w').write('\n'.join('\t'.join(x) for x in out) + '\n')
print('texture unknown keys (unique sha)', len(seen), 'rows written', len(out), 'UNPROVEN', len(bad))
for b in bad: print('UNPROVEN', *b)
