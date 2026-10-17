#!/usr/bin/env python3
"""motion_flags.py (lane zeroread17, 2026-10-17): set a prepared enemy archive's motion hot flags from a used-clip list.

  motion_flags.py show <em.drs>...
  motion_flags.py set <in.drs> <out.drs> <entries.txt>     entries.txt: one MTC record index per line (# comments)
  motion_flags.py used <out entries.txt> <archive bytes> <run-output.txt>...
      the record indices MOTION_USAGE_LOG=1 runs used ("motion use: archive=<bytes> entry=<i> ..."), union of the runs

A prepared archive (tools/prepare_enemy_motions.py; the container's last member, the bytes native_motion.cpp binds)
ends in an MTC table (R4MOTBL, version 2): per clip 20 bytes (offset, size, key crc, key fnv, flags), the table's
CRC-32 at +20, the archive size at +24. flags 1 = hot: native_motion.cpp's bind loads the clip at room entry; 0 = cold:
loaded on first use. Only the flags and the table CRC change: the clip payloads (dc/mot/*.fcv), the archive size and
every other byte stay, so the change is residency only (the same keys, byte for byte, load at other times).
Why not re-run prepare_enemy_motions.py --hot-audit: these archives were rewritten afterwards by later data sets
(acc12: the PS2 accessories in em12 / em13 / em15 / em17), so a re-preparation would have to repeat that chain."""
import re, struct, sys, zlib

U32 = lambda a, o: struct.unpack_from('<I', a, o)[0]


def mtc(a):
    p = a.find(b'R4MOTBL\x00')
    assert p > 0 and a.find(b'R4MOTBL\x00', p + 1) < 0, 'one MTC table'
    size = U32(a, p + 24)
    base = len(a) - size                      # the motion archive ends the container
    n = U32(a, base)
    assert 0 < n < 4096, 'archive header'
    assert a[base + 16 + 4 * n + 4 * (n - 1):base + 16 + 4 * n + 4 * (n - 1) + 3] == b'MTC', 'MTC is the last member'
    assert base + U32(a, base + 16 + 4 * (n - 1)) == p, 'MTC offset'
    assert U32(a, p + 8) == 2, 'MTC version'
    count = U32(a, p + 12)
    assert zlib.crc32(a[p + 32:p + 32 + 20 * count]) == U32(a, p + 20), 'MTC crc'
    return p, count, size


def show(path):
    a = open(path, 'rb').read()
    p, count, size = mtc(a)
    sz = [U32(a, p + 32 + 20 * i + 4) for i in range(count)]
    hot = [i for i in range(count) if U32(a, p + 32 + 20 * i + 16)]
    print('%s: archive %d B, %d clips (%d B), hot %d (%d B)' % (path, size, count, sum(sz), len(hot), sum(sz[i] for i in hot)))


def setf(src, dst, lst):
    a = bytearray(open(src, 'rb').read())
    p, count, size = mtc(bytes(a))
    want = {int(x.split('#')[0]) for x in open(lst) if x.split('#')[0].strip()}
    assert all(0 <= i < count for i in want), 'entry out of range'
    for i in range(count):
        struct.pack_into('<I', a, p + 32 + 20 * i + 16, 1 if i in want else 0)
    struct.pack_into('<I', a, p + 20, zlib.crc32(bytes(a[p + 32:p + 32 + 20 * count])))
    open(dst, 'wb').write(a)
    show(dst)


def used(out, size, logs):
    seen = {}
    for f in logs:
        for l in open(f, encoding='latin-1'):
            m = re.match(r'motion use: archive=(\d+) entry=(\d+) bytes=(\d+)', l)
            if m and int(m.group(1)) == int(size):
                seen[int(m.group(2))] = int(m.group(3))
    with open(out, 'w') as o:
        o.write('# motion_flags.py used: archive %s, %d runs: %d clips, %d B\n' % (size, len(logs), len(seen), sum(seen.values())))
        for i in sorted(seen):
            o.write('%d  # %d B\n' % (i, seen[i]))
    print(out, len(seen), sum(seen.values()))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'show': [show(p) for p in sys.argv[2:]]
    elif c == 'set': setf(*sys.argv[2:5])
    elif c == 'used': used(sys.argv[2], sys.argv[3], sys.argv[4:])
    else: raise SystemExit(__doc__)
