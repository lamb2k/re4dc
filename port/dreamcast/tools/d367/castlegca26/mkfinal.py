#!/usr/bin/env python3
"""mkfinal.py CGCA26 PMCGCA26 WORK   (WSL; lane castle-gca-26, gen-all.sh last step)
Assembles the two Disc 2 data sets (recipe.conf D2_DATA="cgca26,pmcgca26") from the generator's work dir:
  CGCA26/st2/rNNN.dar   castle room archive: PS2 objects (ps2_objects.py) + PS2 items / debris (ps2_items.py) + PS2
                        pictures (ps2_objects_tex.py) + PS2 motion (ps2_motion_prepared.py) + PS2 PCM (ps2_audio.py banks)
  CGCA26/em/emNN.drs    em19 em1a em1b em1c (castle) + em14 (Disc 1 copy): PS2 BIN geometry (+ PS2 motion; em19 / em1a
                        + PS2 PCM)
  CGCA26/tex/*.re4tex   the PS2 picture packages (loose keys) of the objects, items and debris
  CGCA26/provenance.tsv one row per model payload of every staged file (gc_port23/build_catalog.member_rows): a payload
                        the input file did not have = our PS2 conversion (ps2, PS2 source = the BIO4DAT.AFS member), a
                        payload the input already had = GameCube bytes kept (gc); + the sound bank rows of snd28_store.py
                        (a bank with at least one PS2 sample = ps2). Rows provenance.py reads: output_sha256, ps2_sha256.
  PMCGCA26/             the same em / st2 files + the new dc/mot keys: the PS2 motion store (provenance.py credits motion
                        keys only to pm* sets); RECIPE.txt names the PS2 sources."""
import hashlib, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent / 'gc_port23')]
import build_catalog as bc  # noqa: E402
import ps2_objects as po  # noqa: E402

s1, s2, wk = (Path(x) for x in sys.argv[1:4])
CT = Path('/root/re4data/private/castle-d2-j-20261021')
D1 = Path((wk / 'd1tree.txt').read_text().strip())
ROOMS = ['r201', 'r202', 'r204', 'r208']
CEM = ['em19', 'em1a', 'em1b', 'em1c']
snd = wk / 'snd' / 'store'
sha = lambda b: hashlib.sha256(b).hexdigest()
idx = po.pb.afs_index(po.PS2_ISO)
ps2sha = lambda n: sha(po.pb.afs_read(po.PS2_ISO, n, idx))
for s in (s1, s2):
    s.mkdir(parents=True, exist_ok=False)
files = {}   # dest -> (final path, input path, PS2 member)
for r in ROOMS:
    f = snd / 'st2' / ('%s.dar' % r)
    files['st2/%s.dar' % r] = (f if f.exists() else wk / 'm' / r / 'em' / ('%s.dar' % r), CT / 'st2' / ('%s.dar' % r), r + '.dat')
for e in CEM:
    f = snd / 'em' / ('%s.drs' % e)
    files['em/%s.drs' % e] = (f if f.exists() else wk / 'm' / e / 'em' / ('%s.drs' % e), CT / 'em' / ('%s.drs' % e), e + '.dat')
files['em/em14.drs'] = (wk / 'em' / 'em14.drs', D1 / 'em' / 'em14.drs', 'em14.dat')
rows = []
for dest, (fin, inp, p2) in files.items():
    (s1 / dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fin, s1 / dest)
    if dest.endswith('.dar'):   # the .arc beside it = the .dar's type-0 payload (the copy the catalog also reads)
        import struct
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
    if dest != 'em/em14.drs':   # em14 has no PS2 motion step (its motion is not a castle row)
        (s2 / dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fin, s2 / dest)
em3b = wk / 'm' / 'em3b' / 'em' / 'em3b.drs'
(s2 / 'em').mkdir(exist_ok=True); shutil.copyfile(em3b, s2 / 'em' / 'em3b.drs')
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
        # the same picture converted in two rooms: the package label (header) and at most a few VQ codebook bytes differ
        # (each room's PS2 copy of the shared object picture); the first room's package is kept, the count is reported
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
    'cgca26 (lane castle-gca-26, 2026-11-01): Disc 2 castle data from the PS2 version (user 11-01 "Convert in Test 26";\n'
    'DISC 2 ONLY, recipe.conf D2_DATA). PS2 source: Resident Evil 4 (USA) PS2 ISO, BIO4DAT.AFS r201.dat r202.dat r204.dat\n'
    'r208.dat (ETM etc models, room BINs, ITM items, EFF debris, TPL pictures, FCV/SEQ motion, .snd banks) and em14 em19\n'
    'em1a em1b em1c .dat (enemy BINs, motion, banks). Tools: ps2_objects.py, ps2_items.py, ps2_objects_tex.py,\n'
    'ps2_items_tex.py, ps2cast/ps2_ganado_bins.py, motion/ps2_motion_prepared.py, ps2_audio.py banks; generator\n'
    'tools/d367/castlegca26/gen-all.sh. provenance.tsv credits each model / bank: ps2 only where our PS2 conversion\n'
    'changed it, gc where GameCube bytes are kept (sound-kept-gc.tsv lists kept GC samples). Reports: reports/.\n')
(s2 / 'RECIPE.txt').write_text(
    'pmcgca26 (lane castle-gca-26, 2026-11-01): Disc 2 castle motion from the PS2 version: BIO4DAT.AFS em19 em1a em1b em1c\n'
    'em3b r201 r202 r204 r208 .dat of the PS2 USA ISO, motion/ps2_motion_prepared.py rewrite + verify (VERIFY PASS each,\n'
    'reports/). Files = cgca26\'s final bytes (+ em3b, clips already PS2-identical) and the new dc/mot keys.\n')
(s1 / 'reports' / 'tex-duplicates.txt').write_text(''.join(x + chr(10) for x in dup))
print('mkfinal: %d files, %d provenance rows (%d ps2), %d tex keys (%d room duplicates), %d mot keys' % (
    len(files), len(rows), sum(1 for r in rows if r[3]), n, len(dup), k))
