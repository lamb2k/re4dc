#!/usr/bin/env python3
"""door_check.py: is each door request of a fixture one the game's own area check would make? (lane eng-load1)

    door_check.py <fixture> <trace> --tree <data tree> [--control early=N] [--out <table>]

Neither the engine's default image nor the PC reference hosts the area check (sce_at.cpp SceAtCheck); the fixture's
"door <tick> <area>" lines plant the door handler's request at that tick (core/room_change.cpp, hostref/replay.cpp).
This check reads the trace (the reference's "T t=" lines or the engine's "LT t=" lines: position and angle as IEEE bits)
and, for each request at tick T, asks what the area check at tick T would see (sce_at.cpp sceAtCheck_main and
sceAtHitCheck, area.cpp areaHitCheck_xz4):
  - the record: an area of type 1 (door) with that number in the room's AEV section (the room the fixture is in then);
  - the trigger: the record's trigger is 2 (the action key pressed) or 8 (the action button), and A (0x100) is newly
    pressed in the fixture's pads at T-1 (the player's move at T-1 sets the key status; the check at T reads it);
  - the point: Leon's state at the start of T (the trace's record of T-1): the front point (position + 250 up, 550
    ahead along his yaw) when the record's checkFlag bit 0 is set, else the position + 250 up, inside the area's
    quadrilateral and height band (floor - 100 .. floor + height).
Not modelled: the wall clip the game applies to the front point (SatMgr.hitCheck shortens it towards Leon), the
angle check (checkFlag bit 1; neither door here sets it), Ashley's veto, locks. A request passes when every item holds.
Controls (each must FAIL): --control early=N moves every request N ticks earlier (A not pressed then); --control at0
takes Leon's point from his start (tick 0) instead of the tick before the request (outside every door's area).
Exit: 0 all pass, 1 a request fails, 2 bad input.
"""
import argparse, math, os, struct, sys


def fbits(h):
    return struct.unpack('>f', bytes.fromhex(h))[0]


def read_fixture(path):
    fx = {'room': 0x101, 'pads': [], 'doors': []}
    for line in open(path):
        line = line.split('#', 1)[0].split()
        if not line:
            continue
        k = line[0]
        if k == 'room':
            fx['room'] = int(line[1], 0)
        elif k == 'pad':
            fx['pads'].append((int(line[1]), int(line[2], 0)))
        elif k == 'door':
            fx['doors'].append((int(line[1]), int(line[2], 0)))
    fx['pads'].sort()
    return fx


def buttons_at(pads, t):
    b = 0
    for tick, bt in pads:
        if tick <= t:
            b = bt
    return b


def read_trace(path):
    rec = {}
    for line in open(path, errors='replace'):
        if line.startswith('T t=') or line.startswith('LT t='):
            w = dict(kv.split('=', 1) for kv in line.split()[1:] if '=' in kv)
            try:
                t = int(w['t'])
                p = [fbits(x) for x in w['p'].split(',')]
                a = fbits(w['a'].split(',')[1])
            except (KeyError, ValueError):
                continue
            rec[t] = (p, a)
    return rec


def aev_records(tree, room):
    path = os.path.join(tree, 'st%x' % (room >> 8), 'r%03x.arc' % room)
    b = open(path, 'rb').read()
    num = struct.unpack_from('<I', b, 0)[0]
    offs = struct.unpack_from('<%dI' % num, b, 0x10)
    for i in range(num):
        if b[0x10 + 4 * num + 4 * i:0x10 + 4 * num + 4 * i + 3] == b'AEV':
            off = offs[i]
            n = struct.unpack_from('<H', b, off + 6)[0]
            out = {}
            for k in range(n):
                w = b[off + 0x10 + k * 0x9C: off + 0x10 + (k + 1) * 0x9C]
                out[w[0x36]] = w
            return out
    return {}


def inside_xz4(w, x, y, z):
    floor, height = struct.unpack_from('<2f', w, 8)
    pts = [struct.unpack_from('<2f', w, 0x14 + 8 * i) for i in range(4)]
    if y + 100.0 < floor or y >= floor + height:
        return False
    (x0, z0), (x1, z1), (x2, z2), (x3, z3) = pts
    if (x3 - x0) * (z - z0) > (z3 - z0) * (x - x0) or (x1 - x0) * (z - z0) < (z1 - z0) * (x - x0):
        return False
    if (x3 - x2) * (z - z2) < (z3 - z2) * (x - x2) or (x1 - x2) * (z - z2) > (z1 - z2) * (x - x2):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fixture')
    ap.add_argument('trace')
    ap.add_argument('--tree', required=True)
    ap.add_argument('--control', default='')
    ap.add_argument('--out')
    o = ap.parse_args()
    early = int(o.control.split('=')[1]) if o.control.startswith('early=') else 0
    fx = read_fixture(o.fixture)
    tr = read_trace(o.trace)
    if not fx['doors'] or not tr:
        print('door_check: no door lines in the fixture or no records in the trace', file=sys.stderr)
        return 2
    rows, ok_all, room = [], True, fx['room']
    for tick, area in fx['doors']:
        t = tick - early
        recs = aev_records(o.tree, room)
        w = recs.get(area)
        why = []
        if w is None or w[0x35] != 1:
            why.append('no door area %d in r%03x' % (area, room))
            rows.append((tick, room, area, 'FAIL', '; '.join(why)))
            ok_all = False
            continue
        trig, chk = w[0x38], w[0x37]
        b1, b2 = buttons_at(fx['pads'], t - 1), buttons_at(fx['pads'], t - 2)
        if not (trig & 0x0A):
            why.append('trigger %02x is not the action key' % trig)
        if not (b1 & 0x100) or (b2 & 0x100):
            why.append('A not newly pressed at tick %d' % (t - 1))
        at = 0 if o.control == 'at0' else t - 1   # control at0: the point taken from Leon's start (tick 0)
        if at not in tr:
            why.append('no trace record for tick %d' % at)
            pt = None
        else:
            p, a = tr[at]
            if chk & 1:
                pt = (p[0] + 550.0 * math.sin(a), p[1] + 250.0, p[2] + 550.0 * math.cos(a))
            else:
                pt = (p[0], p[1] + 250.0, p[2])
            if not inside_xz4(w, *pt):
                why.append('%s point %.1f %.1f %.1f outside the area' % ('front' if chk & 1 else 'body', *pt))
        verdict = 'PASS' if not why else 'FAIL'
        ok_all &= not why
        dst = w[0x6C] << 8 | w[0x6D]
        rows.append((tick, room, area, verdict, '; '.join(why) or 'in the area, A pressed at %d, -> r%03x' % (t - 1, dst)))
        room = dst
    lines = ['door_check %s on %s%s' % (os.path.basename(o.fixture), os.path.basename(o.trace),
                                         ' (control early=%d)' % early if early else '')]
    lines += ['door tick %d room r%03x area %d: %s (%s)' % r for r in rows]
    lines.append('RESULT %s' % ('PASS' if ok_all else 'FAIL'))
    text = '\n'.join(lines) + '\n'
    sys.stdout.write(text)
    if o.out:
        open(o.out, 'w').write(text)
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
