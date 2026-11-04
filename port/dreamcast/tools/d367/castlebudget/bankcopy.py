# bankcopy.py <release.drs> <prepared.drs> <out.drs>: copy every sound bank's ARAM part from the release archive
# (same block index, MRAM part and size; GC-format or AICA) into the prepared archive (castlebudget em14p).
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import aica_banks as ab
rel = open(sys.argv[1], 'rb').read(); prep = bytearray(open(sys.argv[2], 'rb').read())
rb = sorted(ab.sound_blocks(rel, 0) or []); pb = sorted(ab.sound_blocks(bytes(prep), 0) or [])
assert len(rb) == len(pb)
for (t, mo, ms, ao, asz), (t2, mo2, ms2, ao2, asz2) in zip(rb, pb):
    assert (t, ms, asz) == (t2, ms2, asz2), 'shape'
    assert rel[mo:mo + ms] == prep[mo2:mo2 + ms2], 'MRAM part'
    prep[ao2:ao2 + asz2] = rel[ao:ao + asz]
    print('bank', t, 'copied', asz)
open(sys.argv[3], 'wb').write(prep)
