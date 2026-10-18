"""print the AICA HDR layout fields of converted blocks in archives (ch3regen c3r_aichdr method). usage: tools file..."""
import sys, struct
sys.path.insert(0, sys.argv[1])
import aica_banks as A
for p in sys.argv[2:]:
    d = open(p, 'rb').read()
    seen = set()
    for (t, mo, ms, ao, asz) in A.sound_blocks(d, 0) or []:
        if struct.unpack_from('<I', d, ao)[0] != A.MAGIC: continue
        h = A.HDR.unpack_from(d, ao)
        seen.add(tuple(h[9:9 + 9]))
    print(p.split('/')[-1], sorted(seen))
