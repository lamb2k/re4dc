#!/usr/bin/env python3
"""loop_align.py <in .dar> <out .dar> [--align N] [--blocks 6]   (lane fix60b-26, #60 item 6; data only)

Rounds the loop start of every looped wavetable region of the room-bank (block 6) samples UP, and the loop end DOWN,
to a multiple of N AICA samples (default 4; AICA samples = GC samples >> the sample's decimation shift), as the
AICA plays them (audio_aica.cpp: lsa = loopStart >> sh, len = (loopStart + loopLength) >> sh). The sample data is
not touched; only the WTREGION loopStart / loopLength words move by fewer than N AICA samples. Prints one row per
changed region. Same size, same header; the r100 room bank's PS2 loops (ps2_audio.py 'ps2 loop') land on odd starts.
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import ps2_audio as pa

def main():
    a = sys.argv[1:]
    src, dst = a[0], a[1]
    n = int(a[a.index('--align') + 1]) if '--align' in a else 4
    blocks = {int(x) for x in a[a.index('--blocks') + 1].split(',')} if '--blocks' in a else {6}
    d = bytearray(open(src, 'rb').read())
    changed = 0
    for (t, mo, ms, ao, h, smp) in pa.gc_blocks(bytes(d), 0):
        if t not in blocks:
            continue
        m = bytes(d[mo:mo + ms])
        base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
        num, dls, sit, seq = struct.unpack_from('<4I', m, base)
        wt = base + dls
        offs = struct.unpack_from('<6I', m, wt)
        rgn = offs[2]
        later = [o for o in offs[1:] if o > rgn]
        for i in range((min(later) - rgn) // 24 if later else 0):
            p = wt + rgn + 24 * i
            unity, kg, fine, attn, ls, ll, art, si = struct.unpack_from('<BBhiIIII', m, p)
            if not ll or si >= len(smp):
                continue
            sh = smp[si][2]
            q = n << sh
            le = ls + ll
            ls2 = (ls + q - 1) // q * q
            le2 = le // q * q
            if le2 - ls2 < q * 4 or (ls2, le2) == (ls, le):
                continue
            struct.pack_into('<II', d, mo + p + 8, ls2, le2 - ls2)
            changed += 1
            print('blk %d region %d sample %d shift %d: loop %d..%d -> %d..%d (GC samples)' % (t, i, si, sh, ls, le, ls2, le2))
    assert len(d) == os.path.getsize(src)
    open(dst, 'wb').write(d)
    print('loop_align: %d regions changed -> %s' % (changed, dst))

main()
