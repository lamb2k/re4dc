#!/usr/bin/env python3
"""fit-r113.py (lane ch2code16, 2026-10-16): r113's room-arena banks refit so the Ganados' em17 bank fits.

Run 10-16 e3-r113: "aica: blk 9 (607364 bytes) does not fit the room arena (440320 of 1004192 used), block silent":
r113's ROOM bank was prebuilt at 11025 Hz (269,528 B) by the ch22 lane; with em17 (607,364 B at 11025, frozen by
chapter 1's r108) and pl11 (68,064) the arena is 43.5 KB over, so every Ganado voice in r113 is silent. r113.dar is a
chapter 2 file only, so its own ROOM / FOOT banks are re-prebuilt with aica_banks.py fit against the test 15 + ch2 disc
tree (frozen layout, arena 1,004,192): ROOM 11025 -> 8000 Hz (195,236 B), FOOT 8000 (102,696), 30,752 B left.
Chapter 1 files are unchanged. The disc r113.dar equals the GC mirror outside its two slot-8 sound blocks, so the GC
blocks are spliced back from the mirror and refit.
Out: LANE/snd/fit113/out/st1/r113.dar (mkch2data.py picks it up), fit-r113.json.
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
import aica_banks as A

LANE = '/root/probe/lanes-20261016/ch2'
W = LANE + '/snd/fit113'
M = '/root/probe/lanes-20261013/ch22w/rooms/mirror-aica-c22'   # the ch22 lane's unconverted mirror
FIX = LANE + '/k/fix/e-r113-c2rW.json'                         # a ch2 fixture: the disc's resident + r113 files


def main():
    rep = json.load(open(FIX))['replace']
    for spec in A.RESIDENT + A.ROOMS['r113']:
        n = spec.partition('#')[0]
        exts = ('.dat', '.hed') if n.endswith('.dat') else ('',)
        for e in exts:
            nn = os.path.splitext(n)[0] + e if e else n
            src = os.path.splitext(rep[n])[0] + e if e else rep[n]
            dst = os.path.join(W, 'tree', nn)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.lexists(dst):
                os.remove(dst)
            os.symlink(src, dst)
    d = bytearray(open(W + '/tree/st1/r113.dar', 'rb').read())
    g = open(M + '/st1/r113.dar', 'rb').read()
    assert len(d) == len(g)
    for (t, mo, ms, ao, asz) in A.sound_blocks(bytes(d), 0):
        if A.slot_of(t) == 8:
            d[ao:ao + asz] = g[ao:ao + asz]
    if bytes(d) != g:
        raise SystemExit('disc r113.dar differs from the GC mirror outside its sound blocks')
    os.makedirs(W + '/gc', exist_ok=True)
    open(W + '/gc/r113.dar', 'wb').write(d)
    A.fit(W + '/gc/r113.dar', W + '/out/st1/r113.dar', W + '/tree', 'r113', W + '/cache', json_out=W + '/fit-r113.json')


if __name__ == '__main__':
    main()
