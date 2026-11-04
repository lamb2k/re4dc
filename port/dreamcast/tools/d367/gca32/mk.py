#!/usr/bin/env python3
"""mk.py CGCA32 CPIC32B WORK PMCW32 CASTLE_TREE   (WSL; lane world-ch31 11-03; gen.sh last step)
cgca32 (Disc 2 only, recipe.conf D2_DATA after cpic27):
  st2/rNNN.dar   r205 r20a r20b: gen.sh step 1 output (pmcw32's archive with et1400 / et0c00 emptied); r209: pmcw32's
                 archive unchanged (staged for its .arc only)
  st2/rNNN.arc   the .dar's type-0 payload (the copy the GC-ASSET catalog also reads, as castlegca26/mkfinal.py): the
                 catalog keeps the first source of a member, st2/rNNN.arc, so without it cw32's PS2 models in these rooms
                 are attributed to the GameCube base .arc
  dc/native/r20a|r20b/partner.re4nmr   Ashley's PS2 partner package (ashley_reroom.py from the castle r201 package)
  provenance.tsv one row per model payload of every staged archive (gc_port23/build_catalog.member_rows): a payload the
                 castle content's archive did not have = our PS2 conversion (ps2), else GameCube bytes kept (gc); the
                 partner packages' models = ps2 (PS2 pl11.dat)
cpic32b: dc/tex.pak (em_eff_pics.py output), pak-derived.json, report.json."""
import hashlib, shutil, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent / 'gc_port23')]
import build_catalog as bc  # noqa: E402

s1, s2, wk, pm, ct = (Path(x) for x in sys.argv[1:6])
sha = lambda b: hashlib.sha256(b).hexdigest()
ps2 = lambda n: sha((wk / 'ps2' / n).read_bytes()) if (wk / 'ps2' / n).exists() else None
for s in (s1, s2):
    s.mkdir(parents=True, exist_ok=False)
(s1 / 'st2').mkdir()
rows = []
import subprocess
iso = '/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
for r in ('r205', 'r209', 'r20a', 'r20b'):
    fin = wk / 'obj' / ('%s.dar' % r)
    fin = fin if fin.exists() else pm / 'st2' / ('%s.dar' % r)
    if not (wk / 'ps2' / ('%s.dat' % r)).exists():
        subprocess.run(['python3', str(HERE / 'afsx.py'), iso, str(wk / 'ps2'), r + '.dat'], check=True, capture_output=True)
    dest = 'st2/%s.dar' % r
    shutil.copyfile(fin, s1 / dest)
    fb = fin.read_bytes()
    _k, size, _d, off = struct.unpack_from('<4I', fb, 0x20)
    (s1 / dest.replace('.dar', '.arc')).write_bytes(fb[off:off + size])
    old = {i for k, i, _d, _s in bc.member_rows(dest, (ct / dest).read_bytes()) if k == 'model'}
    seen, ps = set(), ps2(r + '.dat')
    for k, i, data, _s in bc.member_rows(dest, fb):
        if k != 'model' or i in seen:
            continue
        seen.add(i)
        new = i not in old
        rows.append(('model', dest, sha(data), ps if new else '', 'PS2 USA BIO4DAT.AFS %s.dat' % r if new else 'kept GameCube bytes'))
subprocess.run(['python3', str(HERE / 'afsx.py'), iso, str(wk / 'ps2'), 'pl11.dat'], check=True, capture_output=True)
for r in ('r20a', 'r20b'):
    dest = 'dc/native/%s/partner.re4nmr' % r
    src = wk / 'partner' / r / 'ashley-pl11' / dest
    (s1 / dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, s1 / dest)
    b = src.read_bytes()
    rows.append(('package', dest, sha(b), ps2('pl11.dat'), 'PS2 USA BIO4DAT.AFS pl11.dat (Ashley partner, castle r201 package re-roomed)'))
    for k, i, data, _s in bc.member_rows(dest, b):
        rows.append((k, dest, sha(data), ps2('pl11.dat'), 'PS2 USA BIO4DAT.AFS pl11.dat (Ashley partner package member)'))
with open(s1 / 'provenance.tsv', 'w') as f:
    f.write('kind\tfile\toutput_sha256\tps2_sha256\tps2_source\n')
    for r in rows:
        f.write('\t'.join(r) + '\n')
(s1 / 'reports').mkdir()
for t in sorted((wk / 'obj').glob('*.json')):
    shutil.copyfile(t, s1 / 'reports' / t.name)
(s1 / 'RECIPE.txt').write_text(
    'cgca32 (lane world-ch31, 2026-11-03): Disc 2 chapter 3-2 GC-ASSET for r20a / r20b from the PS2 version (DISC 2 ONLY,\n'
    'recipe.conf D2_DATA, after cw32 / pmcw32 / cpic32 / cpic27). PS2 source: Resident Evil 4 (USA) PS2 ISO, BIO4DAT.AFS\n'
    'r205.dat r209.dat r20a.dat r20b.dat (ETM etc models: et1400 and et0c00 are in no PS2 ETM, so the GC copies are emptied,\n'
    'ps2_objects.py --etm-empty) and pl11.dat (Ashley partner package, ps2cast/ashley_reroom.py from the castle r201\n'
    'package). Archives = pmcw32 (world-ch32) + those two models; .arc = each .dar\'s payload. Generator:\n'
    'tools/d367/gca32/gen.sh. provenance.tsv credits each model: ps2 where our PS2 conversion changed it, gc where\n'
    'GameCube bytes are kept.\n')
for n in ('tex.pak',):
    (s2 / 'dc').mkdir()
    shutil.copyfile(wk / 'cpic' / 'dc' / n, s2 / 'dc' / n)
for n in ('pak-derived.json', 'report.json'):
    shutil.copyfile(wk / 'cpic' / n, s2 / n)
(s2 / 'RECIPE.txt').write_text(
    'cpic32b 2026-11-03 lane world-ch31 (no-GameCube-assets rule, Disc 2 only). provenance: ps2.\n'
    'dc/tex.pak = cpic27\'s pack with 5 pictures as PS2 pixels under their keys, by tools/d367/ps2cast/em_eff_pics.py from\n'
    'PS2 USA BIO4DAT.AFS: 3d9d333a-125fadf1 <- em23.dat TPL image 1 (NCC 1.000); e75f4f42-b5f65a4f <- r20b.dat image 108\n'
    '(0.995); fcb60a5d-e940e957 <- r20a.dat image 157, 7b86c92d-e0871570 <- image 2, db1febac-00a38398 <- image 52 (1.000).\n'
    'castle_fixture merges its changed keys (pak-derived.json) over the composed pack. Generator: tools/d367/gca32/gen.sh.\n')
print('mk: %d provenance rows (%d ps2)' % (len(rows), sum(1 for r in rows if r[3])))
