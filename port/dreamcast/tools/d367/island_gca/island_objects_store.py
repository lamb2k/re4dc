#!/usr/bin/env python3
"""island_objects_store.py OBJDIR STORE  (lane island-gca round 3, after island_objects.py)
STORE/st3/<room>.dar = OBJDIR/<room>/<room>.dar for every room the tool changed; STORE/provenance.tsv = one row per model payload
(gc_port23/build_catalog.member_rows, the catalog's own split) of those dars that the input dar did not carry: rebuilt from the PS2
BIN / ETM model of the same room (ps2_sha256 = the PS2 rNNN.dat BIO4DAT entry). No RECIPE file on purpose (members without a row keep unknown)."""
import hashlib, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'gc_port23'), str(HERE.parent)]
import build_catalog as bc  # noqa: E402
sys.path.insert(0, str(HERE.parents[1]))
import ps2_bin as pb  # noqa: E402
PS2 = '/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso'
obj, store = Path(sys.argv[1]), Path(sys.argv[2])
if store.exists():
    raise SystemExit('store exists')
(store / 'st3').mkdir(parents=True)
idx = pb.afs_index(PS2)
rows = ['room\tmember\toutput_sha256\tps2_sha256\tps2_source']
sha = lambda b: hashlib.sha256(b).hexdigest()
nroom = nps2 = 0
for rd in sorted(p for p in obj.iterdir() if p.is_dir()):
    room = rd.name
    if not (rd / (room + '.json')).exists():
        continue
    j = json.load(open(rd / (room + '.json')))
    new = (rd / (room + '.dar')).read_bytes(); old = Path(j['dar_in']).read_bytes()
    if new == old:
        continue
    shutil.copy(rd / (room + '.dar'), store / 'st3' / (room + '.dar'))
    have = {i for k, i, d, s in bc.member_rows('st3/%s.dar' % room, old) if k == 'model'}
    dat = sha(pb.afs_read(PS2, room + '.dat', idx))
    seen = set(); nroom += 1
    for k, i, d, s in bc.member_rows('st3/%s.dar' % room, new):
        if k != 'model' or i in have or i in seen:
            continue
        seen.add(i); nps2 += 1
        rows.append('\t'.join((room, 'st3/%s.dar#model' % room, sha(d), dat, 'PS2 USA BIO4DAT.AFS %s.dat (ps2_objects.py room: PS2 geometry in the GameCube ModelData)' % room)))
(store / 'provenance.tsv').write_text('\n'.join(rows) + '\n')
print('rooms', nroom, 'ps2 model rows', nps2)
