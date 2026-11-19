#!/usr/bin/env python3
"""stress_fcv_pose.py <source .drs> <out .drs> --keep 0xA,0x1D,...: a STRESS-ONLY archive (lane stress16b, Saddler
stress disc; never a play disc). Every FCV motion not in --keep becomes a one-key pose of itself: same maxFrame, joints,
kinds and parts (so a motion that does play keeps its length and its skeleton), each axis keeping only its first key.
Why: em31 (Saddler) holds 1.83 MB of FCV motions resident (no motion cold pool for em31 yet); with the r119 stand-in
world in heap 4 the 2.96 MB textures-only archive does not fit (Flycast: "DVD: Memory allocate failed", read.cpp 725).
The stress loop plays only the kept motions, so the drawn and animated cost is the real one."""
import argparse, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(here, '../../../../tools')]
import drs  # noqa: E402
from motion import fcv  # noqa: E402

ARC_BASE = 4
p = argparse.ArgumentParser()
p.add_argument('src'); p.add_argument('out'); p.add_argument('--keep', required=True)
a = p.parse_args()
keep = {int(x, 0) for x in a.keep.split(',')}
d = drs.load(a.src)
before = after = n = 0
for i, (tag, data) in enumerate(d.entries):
    if drs.tag_name(tag) != 'FCV' or (i + ARC_BASE) in keep:
        continue
    m = fcv.parse(data)
    if not m.joints:
        continue
    for j in m.joints:
        for ax in j.axes:
            ax.frames, ax.keys = ax.frames[:1], ax.keys[:1]
    m.block_padding = {}
    raw = fcv.serialise(m)
    # 4-byte aligned key blocks (parse accepts 1..3 byte gaps when aligned): rebuild with explicit padding
    pos = (3 + 3 * len(m.joints) + 3 & ~3) + 4 + 4 * len(m.joints)
    for k in m.layout:
        pad = (-pos) & 3
        if pad:
            m.block_padding[k] = bytes(pad)
            pos += pad
        pos += m.joints[k].block_size()
    raw = fcv.serialise(m)
    fcv.parse(raw)
    before += len(data); after += len(raw); n += 1
    d.entries[i] = (tag, raw)
open(a.out, 'wb').write(d.pack())
print('posed %d FCV: %d -> %d bytes; kept %s' % (n, before, after, sorted(hex(x) for x in keep)))
