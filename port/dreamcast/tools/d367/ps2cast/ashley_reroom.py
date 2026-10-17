#!/usr/bin/env python3
"""ashley_reroom.py (lane ashley17, 2026-10-17, PS2_ASHLEY_ROOMS; offline): Ashley's partner package for more rooms.

  ashley_reroom.py check <ps2lib cast dir>                      prove the rule on the shipped packages
  ashley_reroom.py make  <source partner.re4nmr> <out dir> <room>...   write <out>/<room>/ashley-pl11/dc/native/<room>/partner.re4nmr

Why this and not ashley_rooms.py + model_registry.py: the 10-17 WSL wipe lost that path's inputs (ps2_ashley.py conv dirs,
mask runs, regcast-ashley11 under /root/probe/lanes-20261014/ps2cast/ashley, Codex's pl11-PS2.dat extract). Rebuilding them
needs the Windows convert stages. It is not needed: model_registry.py write_package puts the room in exactly one header
word (offset 32) and the header crc32 (offset 44, computed with that word zeroed); the payload, its crc/fnv (36/40) and
every other byte do not depend on the room. `check` proves it on every shipped partner package (r111 r112 r113 r118 r11c
r11f, the ps2lib cast rows from ashley_rooms.py + model_registry.py --slots@bc30f311): each one is reproduced byte for
byte from r111's by this rewrite. `make` applies the same rewrite for new rooms, so its output is the package
model_registry.py would write for them from the same spec (the r117 spec with the room's package list).
"""
import glob, hashlib, os, struct, sys, zlib

MAGIC = b'RE4NMR1\0'


def room_word(name):
    n = name.lower().lstrip('r')
    v = int(n, 16)
    if not 0x100 <= v <= 0x7ff:
        raise SystemExit('bad room %s' % name)
    return v


def check_header(b):
    if b[:8] != MAGIC or len(b) < 64:
        raise SystemExit('not an RE4NMR1 package')
    h = bytearray(b[:64]); want = struct.unpack_from('<I', h, 44)[0]; h[44:48] = b'\0\0\0\0'
    if zlib.crc32(bytes(h)) & 0xffffffff != want:
        raise SystemExit('header crc mismatch')


def reroom(b, room):
    check_header(b)
    h = bytearray(b[:64])
    struct.pack_into('<I', h, 32, room)
    struct.pack_into('<I', h, 44, 0)
    struct.pack_into('<I', h, 44, zlib.crc32(bytes(h)) & 0xffffffff)
    return bytes(h) + b[64:]


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == 'check':
        cast = sys.argv[2]
        pk = sorted(glob.glob(os.path.join(cast, 'r*', 'ashley-pl11', 'dc', 'native', 'r*', 'partner.re4nmr')))
        if len(pk) < 2:
            raise SystemExit('need at least two shipped partner packages')
        src = open(pk[0], 'rb').read()
        for p in pk:
            b = open(p, 'rb').read(); r = struct.unpack_from('<I', b, 32)[0]
            ok = reroom(src, r) == b
            print('%s room %03x %s' % (p, r, 'IDENTICAL' if ok else 'DIFFERS'))
            if not ok:
                raise SystemExit(1)
        print('check: %d packages reproduced from %s' % (len(pk), pk[0]))
    elif len(sys.argv) >= 5 and sys.argv[1] == 'make':
        src = open(sys.argv[2], 'rb').read()
        for name in sys.argv[4:]:
            r = room_word(name); rn = 'r%03x' % r
            d = os.path.join(sys.argv[3], rn, 'ashley-pl11', 'dc', 'native', rn)
            os.makedirs(d, exist_ok=True)
            out = reroom(src, r); p = os.path.join(d, 'partner.re4nmr')
            open(p, 'wb').write(out)
            print(hashlib.sha256(out).hexdigest(), len(out), p)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
