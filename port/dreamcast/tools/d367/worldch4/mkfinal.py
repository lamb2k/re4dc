#!/usr/bin/env python3
"""mkfinal.py C4GCA PMC4GCA WORK   (WSL; lane world-ch4 2026-11-02; castlegca26/mkfinal.py for chapter 4)
Assembles the two Disc 2 data sets (recipe.conf D2_DATA += c4gca,pmc4gca) from the generator's work dir:
  C4GCA/st2/rNNN.{dar,arc}  chapter 4 room archive (base: env.sh w4_base) + PS2 objects / items / pictures / motion / PCM
  C4GCA/em/emNN.drs         chapter 4 enemies with PS2 BIN geometry (+ PS2 motion, + PS2 PCM where converted)
  C4GCA/tex/*.re4tex        PS2 picture packages of objects, items and debris
  C4GCA/provenance.tsv      one row per model payload (ps2 = our conversion, gc = kept GameCube bytes) + bank rows
  PMC4GCA/                  the same em / st2 files + the new dc/mot keys (the PS2 motion store)
Rooms / enemies come from env W4_ROOMS / W4_CEM (gen-all.sh exports them) and WORK/em-ok.txt."""
import hashlib, os, shutil, struct, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent / 'gc_port23')]
import build_catalog as bc  # noqa: E402
import ps2_objects as po  # noqa: E402

s1, s2, wk = (Path(x) for x in sys.argv[1:4])
CT = Path(os.environ.get('D2_CASTLE_TREE', '/root/re4data/private/castle-d2-j-20261021'))
ROOMS = os.environ['W4_ROOMS'].split()
CEM = (wk / 'em-ok.txt').read_text().split()
base = lambda r: Path(subprocess.check_output(['bash', '-c', 'source "%s/env.sh"; w4_base %s dar' % (HERE, r)], text=True).strip())
snd = wk / 'snd' / 'store'
sha = lambda b: hashlib.sha256(b).hexdigest()
idx = po.pb.afs_index(po.PS2_ISO)
ps2sha = lambda n: sha(po.pb.afs_read(po.PS2_ISO, n, idx))
for s in (s1, s2):
    s.mkdir(parents=True, exist_ok=False)
files = {}
for r in ROOMS:
    f = snd / 'st2' / ('%s.dar' % r)
    files['st2/%s.dar' % r] = (f if f.exists() else wk / 'm' / r / 'em' / ('%s.dar' % r), base(r), r + '.dat')
for e in CEM:
    f = snd / 'em' / ('%s.drs' % e)
    files['em/%s.drs' % e] = (f if f.exists() else wk / 'm' / e / 'em' / ('%s.drs' % e), CT / 'em' / ('%s.drs' % e), e + '.dat')
rows = []
for dest, (fin, inp, p2) in files.items():
    (s1 / dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fin, s1 / dest)
    if dest.endswith('.dar'):   # the .arc beside it = the .dar's type-0 payload
        fb = fin.read_bytes(); _k, size, _d, off = struct.unpack_from('<4I', fb, 0x20)
        for s_ in (s1, s2):
            (s_ / 'st2').mkdir(parents=True, exist_ok=True)
            (s_ / dest.replace('.dar', '.arc')).write_bytes(fb[off:off + size])
    old = {i for k, i, _d, _s in bc.member_rows(dest, inp.read_bytes()) if k == 'model'}
    seen, ps = set(), ps2sha(p2)
    for k, i, data, _s in bc.member_rows(dest, fin.read_bytes()):
        if k != 'model' or i in seen:
            continue
        seen.add(i)
        new = i not in old
        rows.append(('model', dest, sha(data), ps if new else '', 'PS2 USA BIO4DAT.AFS %s' % p2 if new else 'kept GameCube bytes'))
    (s2 / dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fin, s2 / dest)
if (snd / 'provenance.tsv').exists():
    for l in (snd / 'provenance.tsv').read_text().splitlines()[1:]:
        c = l.split('\t')
        rows.append((c[0], c[5].split(':')[0] if len(c) > 5 else '', c[2], c[3], c[4]))
with open(s1 / 'provenance.tsv', 'w') as f:
    f.write('kind\tfile\toutput_sha256\tps2_sha256\tps2_source\n')
    for r in rows:
        f.write('\t'.join(r) + '\n')
(s1 / 'tex').mkdir()
n, dup = 0, []
for t in sorted(wk.glob('obj/*/x/tex/*.re4tex')) + sorted(wk.glob('itemlib/*/tex/*.re4tex')):
    o = s1 / 'tex' / t.name.lower()
    if o.exists():
        a, b = o.read_bytes(), t.read_bytes()
        d = sum(x != y for x, y in zip(a, b))
        if len(a) != len(b) or d > 16:
            raise SystemExit('tex key %s twice with different pictures (%d bytes)' % (t.name, d))
        dup.append('%s %d' % (t.name, d))
        continue
    shutil.copyfile(t, o); n += 1
(s2 / 'dc' / 'mot').mkdir(parents=True)
k = 0
for t in sorted(wk.glob('m/*/dc/mot/*.fcv')):
    shutil.copyfile(t, s2 / 'dc' / 'mot' / t.name); k += 1
(s1 / 'reports').mkdir(); (s2 / 'reports').mkdir()
for t in list(wk.glob('obj/*/*.json')) + list(wk.glob('obj/*/x/tex.json')) + list(wk.glob('obj/*/i/items.json')) + list(wk.glob('reports/*')):
    shutil.copyfile(t, s1 / 'reports' / ('%s-%s' % (t.parent.name if t.parent.name not in ('x', 'i') else t.parent.parent.name + t.parent.name, t.name)))
for t in wk.glob('m/*/report-*.json'):
    shutil.copyfile(t, s2 / 'reports' / t.name)
if (snd / '_map').exists():
    shutil.copytree(snd / '_map', s1 / 'reports' / 'snd-map')
(s1 / 'RECIPE.txt').write_text(
    'c4gca (lane world-ch4, 2026-11-02): Disc 2 chapter 4 data from the PS2 version (DISC 2 ONLY, recipe.conf D2_DATA).\n'
    'Rooms: %s. Enemies: %s.\nPS2 source: Resident Evil 4 (USA) PS2 ISO BIO4DAT.AFS rNNN.dat / emNN.dat. Tools: ps2_objects.py,\n'
    'ps2_items.py, ps2_objects_tex.py, ps2_items_tex.py, ps2cast/ps2_ganado_bins.py, motion/ps2_motion_prepared.py,\n'
    'ps2_audio.py banks; generator tools/d367/worldch4/gen-all.sh. provenance.tsv credits each model / bank.\n' % (' '.join(ROOMS), ' '.join(CEM)))
(s2 / 'RECIPE.txt').write_text(
    'pmc4gca (lane world-ch4, 2026-11-02): Disc 2 chapter 4 motion from the PS2 version (ps2_motion_prepared.py rewrite +\n'
    'verify, reports/). Files = c4gca\'s final bytes and the new dc/mot keys.\n')
(s1 / 'reports' / 'tex-duplicates.txt').write_text(''.join(x + chr(10) for x in dup))
print('mkfinal: %d files, %d provenance rows (%d ps2), %d tex keys (%d room duplicates), %d mot keys' % (
    len(files), len(rows), sum(1 for r in rows if r[3]), n, len(dup), k))
