#!/usr/bin/env python3
"""shoot_reads.py <track03.bin> <run-output.txt>... [--room 101]   (lane codex22, 2026-10-22)

Disc reads after the room-entry preload, from a twin with DISC_READ_METER=1 DISC_READ_LOG=1 VRAM_ROOM_LOG=1
MOTION_MISS_LOG=1 (shoot.conf): the window starts at the last "native texture preload: frame=" line after the last
"room lifecycle: phase=enter room=<room>" and runs to the end of the log. Each "DRL: S|T sec=<lba> n=<sectors>"
line is mapped to its disc file through the ISO9660 tree of track03 (fp_iso.py; KOS sector numbers carry +150).
Prints the files read in play (count, sectors), the textures loaded on first sight ("native UI: load") and the
motion misses. Streams (T: music and movie audio) are listed apart: they are the BGM ring, not first-use reads.
Exit 0 always; the verdict line is "SHOOT-READS room=<r> sector_reads=<n> tex_loads=<n> motion_miss=<n>".
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fp_iso  # noqa: E402

ENTER = re.compile(r'room lifecycle: phase=enter room=([0-9a-f]+)')
PRE = re.compile(r'^native texture preload: frame=')
DRL = re.compile(r'DRL: ([ST]) sec=(-?\d+) n=(-?\d+) thr=(\S+)')
TEX = re.compile(r'native UI: load /cd/dc/tex/./([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)')
MISS = re.compile(r'motion miss #\d+: archive=(\d+) entry=(\d+) bytes=(\d+)')


def extents(track):
    tr = fp_iso.Track(track, 45000)
    out = []
    for p, e, s in ((x[0], x[1], x[2]) for x in fp_iso.files(tr)):
        out.append((e, e + (s + 2047) // 2048, p))
    out.sort()
    return out


def which(ext, lba):
    for off in (150, 0):
        l = lba - off
        for a, b, p in ext:
            if a <= l < b:
                return p
    return '?%d' % lba


def main(a):
    room = None
    if '--room' in a:
        i = a.index('--room'); room = a[i + 1]; del a[i:i + 2]
    ext = extents(a[0])
    for log in a[1:]:
        lines = Path(log).read_text(errors='replace').splitlines()
        start = None
        for i, ln in enumerate(lines):
            m = ENTER.search(ln)
            if m and (room is None or m.group(1) == room):
                start = i
        if start is None:
            print('%s: no room entry' % log)
            continue
        r = ENTER.search(lines[start]).group(1)
        for i in range(start, len(lines)):
            if PRE.match(lines[i]):
                start = i
        files, streams, tex, miss = {}, {}, [], []
        for ln in lines[start + 1:]:
            m = DRL.search(ln)
            if m:
                p = which(ext, int(m.group(2)))
                d = streams if m.group(1) == 'T' else files
                c = d.setdefault(p, [0, 0]); c[0] += 1; c[1] += int(m.group(3))
                continue
            m = TEX.search(ln)
            if m:
                tex.append(m.groups())
                continue
            m = MISS.search(ln)
            if m:
                miss.append(m.groups())
        print('== %s room %s (after line %d)' % (log, r, start + 1))
        for p, (n, s) in sorted(files.items(), key=lambda x: -x[1][1]):
            print('  read %-40s calls=%-4d sectors=%d' % (p, n, s))
        for p, (n, s) in sorted(streams.items()):
            print('  stream %-38s starts=%-4d sectors=%d' % (p, n, s))
        for t in tex:
            print('  tex %s %sx%s fmt=%s' % t)
        for mm in miss:
            print('  motion miss archive=%s entry=%s bytes=%s' % mm)
        print('SHOOT-READS room=%s sector_reads=%d tex_loads=%d motion_miss=%d streams=%d' % (
            r, sum(v[0] for v in files.values()), len(tex), len(miss), sum(v[0] for v in streams.values())))


if __name__ == '__main__':
    main(sys.argv[1:])
