#!/usr/bin/env python3
"""Compact a Standard world index (low/index.txt) under the runtime's 4,096 B reader limit (lane t25-fixes 10-25).

  std_compact.py <in index.txt> <out index.txt> [--decimals 1]

native_static.cpp re4dc_std_room_enter() reads the index into a kStdText=4096 buffer and rejects n >= 4096. stdindex.py
writes every float as %.3f, so r103's index (4,280 B) has been rejected since 10-19 ("larger than 4096 B: Original
packages"). This rewrites only the float tokens (imp / impt centre + half sizes, source units): rounded to --decimals,
trailing zeros dropped. Records, record count and every integer / key token are unchanged; the result is checked with
assetpipe.stdindex.parse and against the limit.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from assetpipe import stdindex  # noqa: E402

LIMIT = 4096


def compact(text, decimals):
    def f(m):
        s = '%.*f' % (decimals, float(m.group(0)))
        s = s.rstrip('0').rstrip('.') if '.' in s else s
        return '0' if s in ('-0', '') else s
    return re.sub(r'(?<![\w.-])-?\d+\.\d+(?![\w.])', f, text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('--decimals', type=int, default=1)
    a = ap.parse_args()
    t = Path(a.src).read_text()
    c = compact(t, a.decimals)
    i0, i1 = stdindex.parse(t), stdindex.parse(c)
    for k in ('room', 'mesh', 'orig', 'tex', 'drop'):
        assert i0[k] == i1[k], k
    assert [len(x.split()) for x in t.splitlines()] == [len(x.split()) for x in c.splitlines()]
    n = len(c.encode())
    if n >= LIMIT:
        raise SystemExit('std_compact: %d B still >= %d' % (n, LIMIT))
    Path(a.dst).write_text(c)
    print('STD_COMPACT_OK %s %d -> %d B (limit %d)' % (i1['room'], len(t.encode()), n, LIMIT))


if __name__ == '__main__':
    main()
