#!/usr/bin/env python3
"""cgca27b builder (lane assets-dc 11-03): the chapter 3-1 rows world-ch31 left, PS2-dropped the way the PS2 dropped them.
  st2/r203.dar: ETM et1400.bin (the GC torch etc model, le_mirror(GC r10c)) emptied: the PS2 r203.dat ETM has no et1400
                (ps2_objects.py --etm-empty, as castle-gca-26 did for r201 / r202).
  st2/r207.dar: FOOT samples 7-11 silenced: no GC cue reaches them (54 cues -> samples 0-6, 12-22) and the PS2 r207.snd
                FOOT block has exactly the 18 cue-reached VAGs; the PS2 removed the 5 unused samples.
  st2/rNNN.arc beside each = the .dar's type-0 payload (as castlegca26/mkfinal.py).
  provenance.tsv: rows for the members whose bytes changed."""
import hashlib, json, os, shutil, struct, subprocess, sys
from pathlib import Path
T = '/root/work/lanes/assets-dc/port/dreamcast/tools'
sys.path[:0] = [T, T + '/d367/gc_port23']
import ps2_audio as pa
import build_catalog as bc
import ps2_objects as po

SRC = Path('/root/re4data/private/pmcgca27-20261102')
OUT = Path(sys.argv[1]); WK = Path(sys.argv[2])
if OUT.exists():
    raise SystemExit('store exists')
(OUT / 'st2').mkdir(parents=True); WK.mkdir(parents=True, exist_ok=True)
sha = lambda b: hashlib.sha256(b).hexdigest()
idx = po.pb.afs_index(po.PS2_ISO)
ps2sha = {n: sha(po.pb.afs_read(po.PS2_ISO, n, idx)) for n in ('r203.dat', 'r207.snd')}

# r203: et1400 emptied
subprocess.run([sys.executable, T + '/ps2_objects.py', 'room', '--dar', str(SRC / 'st2/r203.dar'), '--room', 'r203',
                '--etm', 'et1400.bin', '--etm-empty', 'et1400.bin', '--out', str(WK / 'r203.dar'),
                '--json', str(WK / 'r203.json')], check=True)
rep = json.load(open(WK / 'r203.json'))
et = [o for o in rep['objects'] if o.get('name') == 'et1400.bin']
print('r203 et1400:', et)
if not et or et[0].get('skipped'):
    raise SystemExit('et1400 not emptied')

# r207: FOOT 7-11 silenced
spec = 'st2/r207.dar'
d = bytearray((SRC / 'st2/r207.dar').read_bytes())
_p, bases = pa.ab.archive_bases(str(SRC), spec)
done = 0
for base in bases:
    for (t, mo, ms, ao, h, smp) in pa.gc_blocks(bytes(d), base, False):
        if t != 5:
            continue
        reach = {gs for k, gs, f in pa.gc_cue_samples(bytes(d), t, mo, ms) if gs is not None}
        for si in range(7, 12):
            if si in reach:
                raise SystemExit('FOOT %d is cue-reached' % si)
            rate, length, sh, p, nb, loop = smp[si]
            n = (length + (1 << sh) - 1) >> sh
            enc = pa.ab.yamaha_encode([0] * n)
            d[p:p + nb] = enc[:nb] + bytes(nb - min(nb, len(enc)))
            done += 1
if done != 5:
    raise SystemExit('FOOT samples silenced: %d' % done)
(WK / 'r207.dar').write_bytes(bytes(d))

rows = []
for r, srcps2 in (('r203', 'r203.dat'), ('r207', 'r207.snd')):
    rel = 'st2/%s.dar' % r
    new = (WK / ('%s.dar' % r)).read_bytes(); old = (SRC / rel).read_bytes()
    shutil.copyfile(WK / ('%s.dar' % r), OUT / rel)
    _k, size, _d, off = struct.unpack_from('<4I', new, 0x20)
    (OUT / rel.replace('.dar', '.arc')).write_bytes(new[off:off + size])
    oldm = {(k, sha(b)) for k, i, b, w in bc.member_rows(rel, old)}
    for k, i, b, w in bc.member_rows(rel, new):
        if (k, sha(b)) in oldm:
            continue
        if r == 'r203':
            rows.append((k, rel, sha(b), ps2sha['r203.dat'], 'PS2 USA BIO4DAT.AFS r203.dat (ETM has no et1400: emptied, PS2-dropped)'))
        else:
            rows.append((k, rel, sha(b), ps2sha['r207.snd'], 'PS2 USA BIO4DAT.AFS r207.snd (FOOT 7-11 not in the PS2 bank: silenced, PS2-dropped)'))
with open(OUT / 'provenance.tsv', 'w') as f:
    f.write('kind\tfile\toutput_sha256\tps2_sha256\tps2_source\n')
    for x in rows:
        f.write('\t'.join(x) + '\n')
(OUT / 'README-cgca27b.txt').write_text(__doc__)
print('cgca27b: rows', len(rows), [(x[0], x[1]) for x in rows])
