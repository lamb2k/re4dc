#!/usr/bin/env python3
"""pack_trim.py <in NAT3 pack> <out pack> <out effect map> (lane eng-e2)

The E2 fight image draws the village bake (world, models, HUD layout) with live state from the engine tables; it reads
no recorded picture after the first (core/draw_e1.c opens the pack with picture 0 and writes camera and HUD itself).
The pack's nine recorded streams (sections 4..12: 300 pictures of camera, poses, effects, lights ...; 4.1 MB of main
RAM for the cross) are cut to picture 0's rows, every picture pointing at them: the file the renderer validates and
opens is the same format, about 2.5 MB smaller in RAM, so the fight's room data (the Ganado module and its motion keys)
fits beside it.

Before cutting, every recorded effect sprite of the 300 pictures (stream 3, NativeEffect records: texture id, pattern,
material header, glow header) gives the effect map: (texture id, pattern) -> the pack's material header for that
sprite picture, the table the native effect service's sprites are drawn with (FXMAP.BIN: u32 count, then count records
of u16 texture, u16 pattern, u32 header, u32 glow header).
"""
import struct, sys, zlib


def table(blob):
    n = struct.unpack_from('<I', blob, 0)[0]
    offs = struct.unpack_from('<%dI' % (n + 1), blob, 4)
    base = 8 + 4 * n
    return [blob[base + offs[i]:base + offs[i + 1]] for i in range(n)]


def make_table(rows):
    offs = [0]
    for r in rows:
        offs.append(offs[-1] + len(r))
    return struct.pack('<%dI' % (len(rows) + 2), len(rows), *offs) + b''.join(rows)


def main():
    src, dst, fxmap = sys.argv[1:4]
    d = open(src, 'rb').read()
    head = list(struct.unpack_from('<5I', d, 0))
    root = list(struct.unpack_from('<17I', d, 20))
    assert d[:4] == b'NAT3' and root[0] == 15
    secs = [d[88 + root[k + 1]:88 + root[k + 2]] for k in range(15)]
    frames = table(secs[3])
    assert len(frames) == 300
    refs = [list(struct.unpack('<10I', f)) for f in frames]
    deltas = [table(secs[4 + k]) for k in range(9)]
    # the effect map from every picture's effect stream (k = 3), replaying the patches as native_update does
    state, words, fx = [], 0, {}
    for i in range(300):
        p = deltas[3][refs[i][4]]
        w = list(struct.unpack('<%dI' % (len(p) // 4), p))
        nxt = w[0]
        used = words if i else 0
        if nxt > len(state): state += [0] * (nxt - len(state))
        for j in range(used, nxt): state[j] = 0
        words = nxt
        at = 1
        while at < len(w):
            start, bits = w[at], w[at + 1]; at += 2
            dest = start
            while bits:
                if bits & 1:
                    state[dest] = w[at]; at += 1
                bits >>= 1; dest += 1
        for e in range(0, words, 38):
            r = state[e:e + 38]
            tex, hdr, fnv, ptn = r[2], r[32], r[33], r[34]
            if hdr != 0xFFFFFFFF:
                fx.setdefault((tex & 0xFFFF, ptn & 0xFFFF), (hdr, fnv))
    with open(fxmap, 'wb') as f:
        f.write(struct.pack('<I', len(fx)))
        for (tex, ptn), (hdr, fnv) in sorted(fx.items()):
            f.write(struct.pack('<2H2I', tex, ptn, hdr, fnv))
    # cut the streams to picture 0's rows
    for k in range(9):
        secs[4 + k] = make_table([deltas[k][refs[0][k + 1]]])
    newframes = []
    for i in range(300):
        r = list(refs[i])
        for k in range(9): r[k + 1] = 0
        newframes.append(struct.pack('<10I', *r))
    secs[3] = make_table(newframes)
    off = [0]
    for s in secs: off.append(off[-1] + len(s))
    body = struct.pack('<17I', 15, *off) + b''.join(secs)
    head[3] = len(body)
    head[4] = zlib.crc32(body) & 0xFFFFFFFF
    out = struct.pack('<5I', *head) + body
    # lane eng-e1i: the input must be a pack with the HUD fix (bake/hud_fix.py: native_pack.build's last step); the cut
    # keeps picture 0's HUD rows, so the output must still pass; never write one that does not
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bake'))
    import hud_fix
    try:
        hud_fix.verify(out)
    except ValueError as e:
        sys.exit('pack_trim: %s: %s' % (src, e))
    open(dst, 'wb').write(out)
    rest = len(out) - 88 - len(secs[0])
    print('pack %d -> %d B (RAM part %d B), effect map %d sprite pictures' % (len(d), len(out), rest, len(fx)))


if __name__ == '__main__':
    main()
