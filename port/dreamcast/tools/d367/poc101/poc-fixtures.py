#!/usr/bin/env python3
"""poc-fixtures.py <resolved-knobs.txt> <out dir> [--look] [--short BEGIN:END] [--sweep-frame N] [--cam X,Y,Z,ANG]

POC101 disc fixtures (lane poc101 2026-10-15, bench.mk BENCH_POC=1). Every live row is the definitive disc's r101 cross
scene (benchpub/scene1-warp.txt: Leon by the cross, crowd alerted at room frame 30, god, no pad input, measured room
frames 300..1199) with a `poc <mask>` line after its `bench` line; bench.cpp turns the layers of the mask on.

Rows (live scenes 1..9, at most 9):
  1 ALL OFF           the control (test 14 as it ships)
  2.. each layer of this image alone, exact and render layers first ('*' = the look changes)
  ALL ON              every layer but the logic approximations (poc 0x8000)
  FARHALF!            logic approximation alone, warning row (decisions gate pending), if built
  ALL OFF 2           the control again (drift / noise bracket), if a slot is left
Scene 10 (bench10.txt): the frozen render sweep at room frame --sweep-frame (default 1000: definitive disc scene 6).
--look: also scene 11 (bench11.txt), the look sweep (all off / all on) for the still sheet; development discs only.
--short B:E: development gate discs (each Flycast run <= 1 min): live rows measure B..E instead of 300..1200.
--only N[,N]: write only these scenes (development discs: e.g. --only 1,6 for the logic hash pair). The first one written
  becomes warp.txt (bench.cpp runs a scene from its own `bench` number; the next scene is the next fixture on the disc).
Layer knobs (must match bench.mk BENCH_POC's POC_CPPFLAGS):"""
import os
import sys

LAYERS = [  # bit, row name, knobs (any on = built), kind (0 exact render, 1 look, 2 exact logic, 3 logic approx)
    (0x01, 'PVS', ['PS2_PVS'], 0),
    (0x08, 'UI OT', ['UI_OT_CACHE'], 0),
    (0x40, 'COLL', ['COLL_BROADPHASE_CACHE'], 2),
    (0x02, 'WORLD LOD*', ['WORLD_LOD', 'WORLD_LOD_PROBE'], 1),
    (0x04, 'LEON RUNG*', ['LEON_LOD'], 1),
    (0x10, 'FAR MESH*', ['CROWD_FAR'], 1),
    (0x20, 'FLATLIGHT*', ['CROWD_FLAT_LIGHT'], 1),
    (0x80, 'FARHALF!', ['FAR_HALF'], 3),
]
here = os.path.dirname(os.path.abspath(__file__))
SCENE1 = os.path.join(here, '..', 'benchpub', 'scene1-warp.txt')


def knobs(path):
    d = {}
    for tok in open(path).read().split():
        if '=' in tok:
            k, v = tok.split('=', 1)
            d[k] = v   # later wins, as on the make line
    return d


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    kn = knobs(argv[0]); out = argv[1]
    look = '--look' in argv
    short = None; sweep_frame = 1000; cam = None; only = None
    for i, a in enumerate(argv):
        if a == '--short': short = tuple(int(x) for x in argv[i + 1].split(':'))
        if a == '--sweep-frame': sweep_frame = int(argv[i + 1])
        if a == '--cam': cam = argv[i + 1].split(',')
        if a == '--only': only = [int(x) for x in argv[i + 1].split(',')]
    if kn.get('BENCH_POC') != '1':
        print('not a BENCH_POC=1 build: %s' % argv[0]); return 1
    built = []
    for bit, name, ks, kind in LAYERS:
        if any(kn.get(k, '0') not in ('0', '') for k in ks):
            if bit == 0x02 and kn.get('WORLD_LOD', '0') == '0': name = 'WLODPROBE*'   # the stand-in
            if bit == 0x04 and kn.get('LEON_LOD') == '70': name = 'LEON 70%*'
            built.append((bit, name, kind))
    rows = [('ALL OFF', 0)]
    rows += [(n, b) for b, n, k in built if k != 3]
    if len([1 for b, n, k in built if k != 3]) > 1:   # ALL ON differs from a single layer's row
        rows.append(('ALL ON', 0x8000))
    rows += [(n, b) for b, n, k in built if k == 3]
    if len(rows) < 9: rows.append(('ALL OFF 2', 0))
    if len(rows) > 9: print('too many rows: %r' % rows); return 1
    body = []
    for line in open(SCENE1).read().replace('\r', '').splitlines():
        if line.startswith('bench ') or line.startswith('name '): continue
        if cam and line.startswith('pos '): line = 'pos %s %s %s' % tuple(cam[:3])
        if cam and line.startswith('ang '): line = 'ang %s' % cam[3]
        body.append(line)
    b, e = short or (300, 1200)
    os.makedirs(out, exist_ok=True)
    scenes = []
    for i, (name, mask) in enumerate(rows):
        scenes.append((i + 1, 'poc-row%d' % (i + 1), 'bench %d %d %d %s' % (i + 1, b, e, name), mask))
    scenes.append((10, 'poc-sweep', 'bench 10 %d %d R101 CROSS' % (sweep_frame, sweep_frame), 0))
    if look: scenes.append((11, 'poc-look', 'bench 11 %d %d R101 LOOK' % (sweep_frame, sweep_frame), 0))
    if only: scenes = [s for s in scenes if s[0] in only]
    first = True
    for no, nm, bl, mask in scenes:
        fn = 'warp.txt' if first else 'bench%d.txt' % no
        first = False
        txt = 'name %s\n' % nm + '\n'.join(body) + '\n' + bl + '\n' + 'poc 0x%x\n' % mask
        if kn.get('FAR_HALF_RT', '0') != '0':
            # lane farhalf's own run-time switch (on unless a fixture says `farhalf 0`): on only in its own row
            txt += 'farhalf %d\n' % (1 if mask & 0x80 else 0)
        assert len(txt) < 2048, fn
        open(os.path.join(out, fn), 'w').write(txt)
        print('%-12s %-40s poc 0x%x' % (fn, bl, mask))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
