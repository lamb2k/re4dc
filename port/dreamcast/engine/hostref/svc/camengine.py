#!/usr/bin/env python3
"""camengine.py: the engine image's camera record, tick by tick, as a cam.txt for camcheck.py (lane eng-e1l).

    camengine.py <serial.txt> <scene> <ref dir> <out dir> [--ticks N]

<serial.txt> is the serial log of a test disc (tools/engine/build_console_disc.sh) whose E1-family scenes ran traced
(no NOTRACE file): each tick the image prints "CAMLOG t=<tick> e=<eye> g=<target> r=<roll> f=<fov> d=<area>,<cut>,
<routine>,<blend frames left>" (services/camera/camera_svc.cpp eng_cam_trace_line; floats as bit patterns), the camera
service's record at the end of the tick and the controller's decisions. <scene> names the scene run (the lines between
its "CDISC RUN <n> <scene> " and "CDISC RESULT <n> <scene> " lines). <ref dir> holds the PC reference's cam.txt
(re4ref odump on the scene's fixture, hostref/svc/svc4_dump.cpp: one line per CameraMove, "tick eye target roll fov
area cut routine blend").

The engine's tick t is the reference's tick t (both count the ticks after the fixture's set-up from 1; the village
route's engine trace and re4ref agree bit for bit at offset 0, lane eng-e1g). The reference's ticks set the window
(the fixture's length): out/cam.txt gets the engine's line for every tick the reference has, in the reference's order,
written as svc4_dump.cpp writes its own (decimal floats, %.9g). Exit 0 written; 2 when the scene is not in the log, an
engine tick of the window is missing, a tick is repeated, or a value is not finite (camcheck.py then compares).
--ticks N (lane eng-e1o, H-017.8): the fixture's length. The window must then be every tick 1..N, once each and in order,
in the reference as in the engine: a reference or an engine run that lost ticks at either side of the same window can no
longer pass with a shorter one (exit 2).
"""
import os
import re
import struct
import sys


def f32(h):
    return struct.unpack('<f', struct.pack('<I', int(h, 16)))[0]


def scene_lines(lines, name):
    out, on = [], False
    for s in lines:
        if re.match(r'^CDISC RUN \d+ %s ' % re.escape(name), s):
            on, out = True, []
            continue
        if on and re.match(r'^CDISC RESULT \d+ %s ' % re.escape(name), s):
            return out
        if on:
            out.append(s)
    return None


def main():
    args = sys.argv[1:]
    want = None
    if len(args) == 6 and args[4] == '--ticks':
        want = int(args[5])
        args = args[:4]
    if len(args) != 4:
        print(__doc__)
        return 2
    serial, scene, ref, out = args
    lines = open(serial, errors='replace').read().replace('\r', '').splitlines()
    seg = scene_lines(lines, scene)
    if seg is None:
        print('camengine: ERROR scene %s not in %s' % (scene, serial))
        return 2
    eng, dups = {}, []
    for s in seg:
        if not s.startswith('CAMLOG t='):
            continue
        kv = dict(t.split('=', 1) for t in s.split()[1:] if '=' in t)
        t = int(kv['t'])
        if t in eng:
            dups.append(t)
            continue
        e = [f32(x) for x in kv['e'].split(',')]
        g = [f32(x) for x in kv['g'].split(',')]
        v = e + g + [f32(kv['r']), f32(kv['f'])]
        eng[t] = (v, [int(x) for x in kv['d'].split(',')])
    if not eng:
        print('camengine: ERROR no CAMLOG lines in scene %s (a NOTRACE run?)' % scene)
        return 2
    if dups:
        print('camengine: ERROR repeated ticks %s' % dups[:5])
        return 2
    ref_ticks = []
    with open(os.path.join(ref, 'cam.txt')) as f:
        for ln in f:
            t = ln.split()
            if t and t[0] != 'R':
                ref_ticks.append(int(t[0]))
    if want is not None and ref_ticks != list(range(1, want + 1)):
        print('camengine: ERROR the reference window is %d lines (%s..%s), not the fixture's ticks 1..%d' % (
            len(ref_ticks), ref_ticks[0] if ref_ticks else '-', ref_ticks[-1] if ref_ticks else '-', want))
        return 2
    missing = [t for t in ref_ticks if t not in eng]
    if missing:
        print('camengine: ERROR %d reference ticks without an engine line (first %s); engine ticks %d..%d' % (
            len(missing), missing[:5], min(eng), max(eng)))
        return 2
    bad = [t for t in ref_ticks if any(x != x or abs(x) == float('inf') for x in eng[t][0])]
    if bad:
        print('camengine: ERROR a value not finite at engine ticks %s' % bad[:5])
        return 2
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'cam.txt'), 'w') as f:
        for t in ref_ticks:
            v, d = eng[t]
            f.write('%u %s %d %d %d %d\n' % (t, ' '.join('%.9g' % x for x in v), d[0], d[1], d[2], d[3]))
    print('camengine: %s %d engine ticks (%d..%d), %d written for the reference window %d..%d' % (
        scene, len(eng), min(eng), max(eng), len(ref_ticks), min(ref_ticks), max(ref_ticks)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
