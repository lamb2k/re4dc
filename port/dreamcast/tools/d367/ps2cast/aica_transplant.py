#!/usr/bin/env python3
"""aica_transplant.py <released.drs> <mirror(unconverted LE).drs or -> <prepared.drs> <out.drs>

The release disc's enemy archive went through aica_banks.py build: every sound bank's type-2 (ARAM) part was
rewritten IN PLACE (same offset, same size) as AicaBankHeader + AICA ADPCM. A texture-prepared archive
(prepare_enemy_motions.py) moves offsets but keeps each bank's GC type-2 bytes. This copies the release's converted
type-2 bytes into the prepared archive bank by bank (matched by block index t, equal size, and equal MRAM part
bytes), so the result equals what an aica_banks build with the release's caps would write. Refuses on any mismatch.
"""
import sys, hashlib
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import aica_banks as ab

rel_p, mir_p, prep_p, out_p = sys.argv[1:5]
rel = open(rel_p, 'rb').read()
prep = bytearray(open(prep_p, 'rb').read())
rb = ab.sound_blocks(rel, 0) or []
pb = ab.sound_blocks(bytes(prep), 0) or []
print('release banks', [(t, ms, asz) for t, mo, ms, ao, asz in rb])
print('prepared banks', [(t, ms, asz) for t, mo, ms, ao, asz in pb])
if len(rb) != len(pb):
    sys.exit('bank count differs')
done = 0
for (t, mo, ms, ao, asz), (t2, mo2, ms2, ao2, asz2) in zip(sorted(rb), sorted(pb)):
    if t != t2 or ms != ms2 or asz != asz2:
        sys.exit('bank shape differs %r %r' % ((t, ms, asz), (t2, ms2, asz2)))
    if rel[mo:mo + ms] != prep[mo2:mo2 + ms2]:
        sys.exit('MRAM part differs for bank %d' % t)
    import struct
    if struct.unpack_from('<I', rel, ao)[0] != ab.MAGIC:
        sys.exit('release bank %d is not AICA-converted' % t)
    if mir_p != '-':
        mir = open(mir_p, 'rb').read()
        mbs = ab.sound_blocks(mir, 0) or []
        src = [m for m in mbs if m[0] == t]
        if not src or mir[src[0][3]:src[0][3] + src[0][4]] != prep[ao2:ao2 + asz2]:
            sys.exit('prepared GC type-2 part of bank %d differs from the mirror' % t)
    prep[ao2:ao2 + asz2] = rel[ao:ao + asz]
    done += 1
open(out_p, 'wb').write(prep)
print('transplanted', done, 'banks; out', len(prep), hashlib.sha256(prep).hexdigest())
