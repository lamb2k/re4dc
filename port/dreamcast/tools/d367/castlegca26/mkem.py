#!/usr/bin/env python3
"""mkem.py CGCA26 PMCGCA26 GC_EM1B GC_EM14   (WSL; lane castle-gca-26, gen-em.sh last step)
- CGCA26/provenance.tsv: + one row per model payload (gc_port23/build_catalog.member_rows, the catalog's own split) of
  the staged em/em1b.drs and em/em14.drs: a payload absent from the input archive = rebuilt from the PS2 BIN (ps2, PS2
  source = BIO4DAT emNN.dat), a payload the input already had = kept GameCube bytes (gc).
- PMCGCA26/graft.json: per room archive, the FCV / SEQ entries the motion rewrite changed (rr/member_census.dar_members
  against the cgca26 archive; the native tables are rebased by the graft itself)."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent / 'rr'), str(HERE.parent / 'gc_port23')]
import build_catalog as bc  # noqa: E402
from member_census import dar_members  # noqa: E402

s1, s2, gc1b, gc14 = (Path(x) for x in sys.argv[1:5])
rows = []
for em, src in (('em1b', gc1b), ('em14', gc14)):
    old = {i for k, i, _d, _s in bc.member_rows('em/%s.drs' % em, src.read_bytes()) if k == 'model'}
    seen = set()
    for k, i, data, _s in bc.member_rows('em/%s.drs' % em, (s1 / 'em' / ('%s.drs' % em)).read_bytes()):
        if k != 'model' or i in seen:
            continue
        seen.add(i)
        h = hashlib.sha256(data).hexdigest()
        ps2 = '' if i in old else 'ps2:%s.dat' % em
        rows.append((em, 'model', h, ps2, '%s.dat (BIO4DAT.AFS)' % em if ps2 else 'kept GameCube bytes'))
pt = s1 / 'provenance.tsv'
lines = pt.read_text().splitlines() if pt.exists() else ['room\tmember\toutput_sha256\tps2_sha256\tps2_source']
lines = [l for l in lines if not l.startswith(('em1b\t', 'em14\t'))]
pt.write_text('\n'.join(lines + ['\t'.join(r) for r in rows]) + '\n')
print('mkem: %d em model rows (%d ps2, %d gc)' % (len(rows), sum(1 for r in rows if r[3]), sum(1 for r in rows if not r[3])))
g = {}
for f in sorted((s2 / 'st2').glob('*.dar')):
    a = dar_members((s1 / 'st2' / f.name).read_bytes())
    b = dar_members(f.read_bytes())
    ch = [k for k in sorted(a) if a[k] != b.get(k) and k.split(' ')[-1] in ('FCV', 'SEQ')]
    other = [k for k in sorted(a) if a[k] != b.get(k) and k.split(' ')[-1] not in ('FCV', 'SEQ', 'NTR', 'ESQ', 'MTC')]
    assert not other, (f.name, other)
    g['st2/' + f.name] = ch
(s2 / 'graft.json').write_text(json.dumps(g, indent=1) + '\n')
print('mkem: motion graft', {k: v for k, v in g.items()})
