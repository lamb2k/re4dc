#!/usr/bin/env python3
"""pack_keep_check.py: the engine images' resident pack (frame 0 of the recording kept) against the whole pack (lane eng-mem1).

    pack_keep_check.py <pack.PAK>... [--control pad|nopad|drop]

render/native_scene.inc keeps, in an engine image (E1, FIGHT, BOSS, SENDABLE), frame 0's row of each of the recording's
nine delta tables (sections 4-12) and drops frames 1-299; the camera row carries a pad of repeated writes so the models
(section 13) keep their file offset modulo 32. This check builds the same kept layout from the file (the same rules:
pack_keep, keep_layout, keep_pad) and holds, per pack:
  - sections 1-3, 13 and 14 byte-identical to the file's, at offsets equal to the file's modulo 32;
  - every kept delta table a valid table (table(): offsets, size) whose rows pass validate_patch;
  - frame 0's state of each of the nine tables (native_update(s, 0)) identical, word for word, to the whole pack's;
  - the resident bytes (31 + 68 + the kept rest) printed beside the whole pack's.
Controls (each must FAIL on every pack): pad (one value of the camera pad changed: frame 0's camera differs; a pack
whose pad is 0 has none to change), nopad (the pad left out: the models' offset modulo 32 differs from the file's), drop
(the last delta table's row cut by 4 bytes: its patch is invalid).
Exit 0 every pack holds, 1 one does not, 2 bad input.
"""
import struct, sys


def u32s(b, off, n):
    return list(struct.unpack_from('<%dI' % n, b, off))


def table(b, off, size):
    """render/replay_pack.c table(): (n, offsets, base) or None"""
    if size < 8:
        return None
    n, w1 = struct.unpack_from('<2I', b, off)
    if n > (size - 8) // 4 or w1 != 0:
        return None
    hdr = 8 + 4 * n
    o = u32s(b, off + 4, n + 1)
    for i in range(n):
        if o[i] > o[i + 1] or o[i + 1] > size - hdr or o[i + 1] % 4:
            return None
    if o[n] != size - hdr:
        return None
    return n, o, off + hdr


def validate_patch(w):
    if not w or w[0] > 96 * 1024:
        return False
    size, used = w[0], 1
    while used < len(w):
        if len(w) - used < 2:
            return False
        st, bits = w[used], w[used + 1]
        used += 2
        if not bits or st >= size or bits.bit_length() > size - st:
            return False
        c = bin(bits).count('1')
        if c > len(w) - used:
            return False
        used += c
    return True


def apply(w):
    st = [0] * w[0]
    i = 1
    while i < len(w):
        s, bits = w[i], w[i + 1]
        i += 2
        for b in range(32):
            if bits >> b & 1:
                st[s + b] = w[i]
                i += 1
    return st


def check(path, control):
    d = open(path, 'rb').read()
    if d[:4] != b'NAT3':
        print(path, 'not a NAT3 pack')
        return 2
    root = u32s(d, 20, 17)
    tex = root[2]
    sec = [88 + root[s + 1] for s in range(16)]
    rest = len(d) - 88 - tex
    # frame 0's refs
    fr = table(d, sec[3], sec[4] - sec[3])
    if not fr or fr[0] != 300:
        print(path, 'frames table bad')
        return 2
    refs = u32s(d, fr[2] + fr[1][0], 10)
    rows = []
    for k in range(9):
        t = table(d, sec[4 + k], sec[5 + k] - sec[4 + k])
        if not t or refs[k + 1] >= t[0]:
            print(path, 'delta', k, 'bad')
            return 2
        a, b2 = t[2] + t[1][refs[k + 1]], t[2] + t[1][refs[k + 1] + 1]
        rows.append(u32s(d, a, (b2 - a) // 4))
    whole = [apply(r) for r in rows]
    # keep_layout
    c = root[5] - tex
    s_ = sum(12 + 4 * len(r) for r in rows)
    want = (root[14] - tex) % 32
    g = (want + 32 - (c + s_) % 32) % 32
    if g and g < 12:
        g += 32
    kept = [list(r) for r in rows]
    if g:   # keep_pad
        r = kept[0]
        sizes = [g] if g <= 28 else [g - 24, 24]
        s0, b0 = r[1], r[2]
        cmax = max((e - 8) // 4 for e in sizes)
        if bin(b0).count('1') < cmax:
            print(path, 'pad refused: first entry too short')
            return 1
        for e in sizes:
            cc = (e - 8) // 4
            bits, mm = 0, b0
            for _ in range(cc):
                low = mm & -mm
                bits |= low
                mm &= mm - 1
            r += [s0, bits] + r[3:3 + cc]
    if control == 'pad' and g:
        kept[0][-1] ^= 1
    if control == 'drop':
        kept[8] = kept[8][:-1]
    bad = 0
    for k in range(9):
        w = kept[k]
        blob = struct.pack('<3I', 1, 0, 4 * len(w)) + struct.pack('<%dI' % len(w), *w)
        t = table(blob, 0, len(blob))
        if not t or not validate_patch(w):
            print('  delta %d: kept table or patch INVALID' % k)
            bad = 1
            continue
        if apply(w) != whole[k]:
            print('  delta %d: frame 0 state DIFFERS from the whole pack' % k)
            bad = 1
    at13 = c + s_ + (0 if control == 'nopad' else g)
    if at13 % 32 != want:
        print('  models offset %d mod 32 = %d, file %d: DIFFERS' % (at13, at13 % 32, want))
        bad = 1
    kept_rest = at13 + (root[16] - root[14])
    print('%s: whole resident %d B, kept %d B (frame 0 of the recording; pad %d B): %s' %
          (path, max(31 + 68 + rest, 0), 31 + 68 + kept_rest, g, 'FAIL' if bad else 'PASS'))
    return bad


def main():
    a = sys.argv[1:]
    control = None
    if '--control' in a:
        i = a.index('--control')
        control = a[i + 1]
        del a[i:i + 2]
    if not a:
        print(__doc__)
        return 2
    rc = 0
    for p in a:
        rc = max(rc, check(p, control))
    return rc


if __name__ == '__main__':
    sys.exit(main())
