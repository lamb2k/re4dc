#!/usr/bin/env python3
"""aica_bank_copy.py <prepared archive> <sound-banked reference archive> <out>   (lane ch3found16, 2026-10-17)

Re-applies prebuilt AICA banks to an archive that was rebuilt from the GC source (prepare_enemy_motions /
prepare_native_ui textures-only output): every sound block of the prepared archive whose GC wavetable (MRAM table
FNV) and ARAM part size match a block of the reference archive (the same file from an aica_banks.py build, e.g. the
castle disc's snd/aica-c32/em/em3c.drs) gets the reference's ARAM part (AICA header + image) byte for byte. Refuses
(exit 1) when any block has no match, the reference part is not a prebuilt bank, or the counts differ."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aica_banks as ab


def blocks(d):
    out = []
    for (t, mo, ms, ao, asz) in ab.sound_blocks(d, 0) or []:
        table, samples, coefs = ab.wavetable(d, t, mo, ms)
        out.append((t, ab.fnv1a(table), ao, asz))
    return out


def main(prep, ref, out):
    d = bytearray(open(prep, 'rb').read()); r = open(ref, 'rb').read()
    bp, br = blocks(bytes(d)), blocks(r)
    if len(bp) != len(br) or not bp:
        print('aica_bank_copy: %s has %d sound blocks, %s %d' % (prep, len(bp), ref, len(br))); return 1
    for (t, f, ao, asz) in bp:
        m = [x for x in br if x[0] == t and x[1] == f and x[3] == asz]
        if not m:
            print('aica_bank_copy: t=%d fnv %08x size %d has no reference block' % (t, f, asz)); return 1
        part = r[m[0][2]:m[0][2] + asz]
        if struct.unpack_from('<I', part)[0] != ab.MAGIC:
            print('aica_bank_copy: reference block t=%d is not a prebuilt AICA bank' % t); return 1
        d[ao:ao + asz] = part
        print('  t=%-2d fnv %08x %8d B  AICA image fnv %08x' % (t, f, asz, ab.fnv1a(part)))
    open(out, 'wb').write(d)
    print('aica_bank_copy: %d banks -> %s' % (len(bp), out)); return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
