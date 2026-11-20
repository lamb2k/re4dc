"""mot_list.py <archive .drs>: the dc/mot file names the archive's MTC (R4MOTBL) table lists, one per line.

The engine images read a character's motion clips from /cd/dc/mot (the hill path: Ashley, pl11.drs; the fight: the
Ganados, em15.drs). build_console_disc.sh copies exactly these files. From lane eng-e1d's s/mtclist.py (2026-11-19),
unchanged in what it prints."""
import struct
import sys

d = open(sys.argv[1], 'rb').read()
e = struct.unpack_from('<8I', d, 0x20)
body = d[e[3]:e[3] + e[1]]
n = struct.unpack_from('<I', body, 0)[0]
for i in range(n):
    if body[16 + 4 * n + 4 * i:16 + 4 * n + 4 * i + 3] == b'MTC':
        m = body[struct.unpack_from('<I', body, 16 + 4 * i)[0]:]
        for j in range(struct.unpack_from('<I', m, 12)[0]):
            r = struct.unpack_from('<5I', m, 32 + 20 * j)
            print('%08x-%08x.fcv' % (r[2], r[3]))
