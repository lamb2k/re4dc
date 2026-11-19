#!/usr/bin/env python3
"""isl15 (lane assets-dc 11-03, for world-ch5's D3_DATA): the 15 island picture keys no pack and no loose file held
(14 island rooms failed TEXCHK on them). Each is a PS2 world picture the castle / chapter 4 PS2 world packages already
carry (c4world-20261102 tex/, castle-d2-j-20261021 dc/tex/): the same key, the same bytes, staged as loose
dc/tex/<c>/<key>.re4tex. Already Dreamcast form (VQ, or 16-bit twiddled under 64 px; non-square or world pictures
without mips, as the PS2 world pass ships them)."""
import hashlib, os, re, shutil, sys
from pathlib import Path
T = '/root/work/lanes/assets-dc/port/dreamcast/tools'
sys.path[:0] = [T]
import convert_tpl as tpl
import ps2_objects as po
OUT = Path(sys.argv[1])
if OUT.exists():
    raise SystemExit('store exists')
keys = open('/root/probe/lanes/world-ch5/judge3/k15.txt').read().split()
idx = po.pb.afs_index(po.PS2_ISO)
sha = lambda b: hashlib.sha256(b).hexdigest()
man, prov, dats = [], [], {}
for k in keys:
    cands = [Path('/root/re4data/private/c4world-20261102/tex/%s.re4tex' % k),
             Path('/root/re4data/private/castle-d2-j-20261021/dc/tex/%s/%s.re4tex' % (k[0], k))]
    src = next(p for p in cands if p.is_file())
    b = src.read_bytes()
    h = tpl.HEADER.unpack_from(b); t = tpl.TEXTURE.unpack_from(b, h[5])
    mat = t[0].split(b'\0')[0].decode('latin1')
    m = re.match(r'PS2 (r[0-9a-f]{3}) texture (\d+)', mat)
    if not m:
        raise SystemExit('%s: not a PS2 world picture (%s)' % (k, mat))
    dat = m.group(1) + '.dat'
    if dat not in dats:
        dats[dat] = sha(po.pb.afs_read(po.PS2_ISO, dat, idx))
    rel = 'dc/tex/%s/%s.re4tex' % (k[0], k)
    (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, OUT / rel)
    man.append('%s\t%s\n' % (rel, sha(b)))
    prov.append('texture\t%s\t%s\t%s\tPS2 USA BIO4DAT.AFS %s world TPL picture %s (%s, %dx%d fmt %d payload %d)\n' % (
        k, sha(b), dats[dat], dat, m.group(2), src.parent.parent.name if 'c4world' not in str(src) else 'c4world-20261102',
        t[1], t[2], t[3], t[7]))
    print(k, mat, t[1], t[2], t[3], t[7], src)
(OUT / 'manifest.tsv').write_text(''.join(man))
(OUT / 'provenance.tsv').write_text('kind\tid\toutput_sha256\tps2_sha256\tps2_source\n' + ''.join(prov))
(OUT / 'RECIPE.txt').write_text(__doc__)
print('isl15:', len(man), 'files')
