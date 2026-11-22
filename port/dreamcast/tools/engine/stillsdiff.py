#!/usr/bin/env python3
"""stillsdiff.py: exact differing-pixel counts between engine stills (lane eng-draw2).

Stills are the PNG files a Flycast runner saves when an image hands a picture over (m1_state request / acknowledge /
frame buffer): pic-<image>-s<k>-<request>.png, where <image> names the program (bench, e1, fight), <k> counts the
image's runs on the disc (it grows when the request number falls: a new bench pass, or the next E1 scene of the same
image) and <request> is the picture's number (bench: room * 600 + picture). A pixel differs when any of R, G, B differs
(the frame buffer's RGB565 widened, so the smallest step counts).

  stillsdiff.py pair <before> <after> [--only <image>]   every still present in both folders: the counts per image and
                                                         run, the worst still; exit 1 when any pixel differs or no
                                                         still pairs (the "must be 0" check of a pixel-identical step)
  stillsdiff.py repeat <folder>                          the bench's repeat check (boot file DRAWLAB5): every window
                                                         of a room must equal the room's first window at each picture,
                                                         and each picture's second lap (picture + 300) its first; exit 1
                                                         on any difference or when fewer than two windows a room exist
  stillsdiff.py --selftest                               the control: two pictures one pixel apart must count 1 and fail
"""
import re, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

NAME = re.compile(r'pic-([0-9A-Za-z_]+)-s(\d+)-(\d+)\.png$')

def index(folder):
    out = {}
    for p in Path(folder).glob('pic-*.png'):
        m = NAME.match(p.name)
        if m: out[(m.group(1), int(m.group(2)), int(m.group(3)))] = p
    return out

def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.int16)

def differing(a, b):
    if a.shape != b.shape: return a.shape[0] * a.shape[1]
    return int((np.abs(a - b).max(axis=2) > 0).sum())

def pair(before, after, only=None):
    A, B = index(before), index(after)
    keys = sorted(k for k in A if k in B and (only is None or k[0] == only))
    if not keys:
        print('FAIL: no still is present in both folders'); return 1
    total, worst, per = 0, (0, None), {}
    for k in keys:
        n = differing(load(A[k]), load(B[k]))
        total += n; per.setdefault(k[:2], []).append(n)
        if n > worst[0]: worst = (n, k)
    for (img, run), v in sorted(per.items()):
        print('%-6s run %2d: %3d stills, differing pixels total %8d, worst still %7d' % (img, run, len(v), sum(v), max(v)))
    print('pairs %d, differing pixels %d, worst %s' % (len(keys), total, worst))
    missing = len(set(A) ^ set(B))
    if missing: print('note: %d stills are in only one of the folders' % missing)
    print('PASS' if total == 0 else 'FAIL')
    return 0 if total == 0 else 1

def repeat(folder):
    S = index(folder); fail = 0
    bench = {k: p for k, p in S.items() if k[0] == 'bench'}
    # windows: a run k holds one window of each room in turn (the request number falls at each new window)
    for room, lo, hi in (('CROSS', 1, 600), ('FARM', 601, 1200)):
        wins = sorted({k[1] for k in bench if lo <= k[2] <= hi})
        if len(wins) < 2:
            print('%s: FAIL fewer than two windows' % room); fail = 1; continue
        reqs = sorted({k[2] for k in bench if k[1] == wins[0] and lo <= k[2] <= hi})
        base = {r: load(bench[('bench', wins[0], r)]) for r in reqs}
        for w in wins[1:]:
            v = [(r, differing(base[r], load(bench[('bench', w, r)]))) for r in reqs if ('bench', w, r) in bench]
            bad = [(r, n) for r, n in v if n]
            print('%s window run %d against run %d: %d stills, %d differ %s' % (room, w, wins[0], len(v), len(bad), bad[:6]))
            fail |= bool(bad) or not v
        laps = [(r, differing(base[r], base[r + 300])) for r in reqs if r + 300 in base]
        bad = [(r, n) for r, n in laps if n]
        print('%s lap 2 against lap 1 (run %d): %d pairs, %d differ %s' % (room, wins[0], len(laps), len(bad), bad[:6]))
        fail |= bool(bad)
    print('PASS' if not fail else 'FAIL')
    return fail

def selftest():
    d = Path(tempfile.mkdtemp())
    a = np.zeros((480, 640, 3), np.uint8); b = a.copy(); b[100, 200, 1] = 4
    (d / 'x').mkdir(); (d / 'y').mkdir()
    Image.fromarray(a).save(d / 'x' / 'pic-e1-s0-0001.png'); Image.fromarray(b).save(d / 'y' / 'pic-e1-s0-0001.png')
    n = differing(load(d / 'x' / 'pic-e1-s0-0001.png'), load(d / 'y' / 'pic-e1-s0-0001.png'))
    rc = pair(d / 'x', d / 'y')
    ok = n == 1 and rc == 1 and pair(d / 'x', d / 'x') == 0
    print('selftest', 'PASS' if ok else 'FAIL', '(one pixel apart counted %d, pair exit %d)' % (n, rc))
    return 0 if ok else 1

if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--selftest']: sys.exit(selftest())
    if a[:1] == ['pair'] and len(a) >= 3:
        sys.exit(pair(a[1], a[2], a[a.index('--only') + 1] if '--only' in a else None))
    if a[:1] == ['repeat'] and len(a) == 2: sys.exit(repeat(a[1]))
    print(__doc__); sys.exit(2)
