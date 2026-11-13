#!/usr/bin/env python3
"""Append the entries of one bgm/aica_str.dat to another (lane radio66, GitHub #66 bug 3).

  str_append.py BASE EXTRA OUT

BASE keeps every byte of its data and its entries 0..n-1 (only the header grows); EXTRA's streams are copied after
BASE's data (2 KB aligned) and their entries appended with the offsets moved. Keys already in BASE are refused. The
header must still fit BASE's header sectors (16 + 32 x count bytes), and the game needs AICA_STR_ENT_MAX >= count.
Used to add the radio call voices that the route runs never requested (aica_banks.py streams + ps2_audio.py streams
make EXTRA from the PS2 ADX) without rebuilding the release stream file.
"""
import struct
import sys

MAGIC = 0x31534941   # "AIS1"
ENT = struct.Struct('<8I')


def entries(d):
    magic, n = struct.unpack_from('<2I', d, 0)
    assert magic == MAGIC, 'not an aica_str.dat'
    return [list(ENT.unpack_from(d, 16 + ENT.size * i)) for i in range(n)]


def key(e):
    return ((e[2] >> 8) & 255, e[2] >> 16)


def main():
    base_p, extra_p, out_p = sys.argv[1:4]
    base, extra = open(base_p, 'rb').read(), open(extra_p, 'rb').read()
    be, xe = entries(base), entries(extra)
    hsz = min(e[6] for e in be)
    xh = min(e[6] for e in xe)
    have = {key(e) for e in be}
    for e in xe:
        assert key(e) not in have, 'stream %d:%d already in the base file' % key(e)
    n = len(be) + len(xe)
    assert 16 + ENT.size * n <= hsz, '%d entries do not fit the %d-byte header' % (n, hsz)
    pad = (-len(base)) % 2048
    shift = len(base) + pad - xh
    for e in xe:
        e[6] += shift
        if e[7]:
            e[7] += shift
    hdr = struct.pack('<4I', MAGIC, n, 0, 0) + b''.join(ENT.pack(*e) for e in be + xe)
    out = hdr + bytes(hsz - len(hdr)) + base[hsz:] + bytes(pad) + extra[xh:]
    # BASE's own header padding was zero: keep its data bytes exactly
    assert out[hsz:len(base)] == base[hsz:]
    with open(out_p, 'wb') as f:
        f.write(out)
    for e in xe:
        print('  + stream %d:%d  %.1f s  at %d' % (key(e) + (e[4] / e[1], e[6])))
    print('aica_str.dat: %d + %d entries, %d -> %d bytes' % (len(be), len(xe), len(base), len(out)))


if __name__ == '__main__':
    main()
