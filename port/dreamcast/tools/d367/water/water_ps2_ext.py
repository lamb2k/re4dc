#!/usr/bin/env python3
"""water_ps2_ext.py: the PS2 river / waterfall layers of the chapter 2-1 side rooms as a C table (WATER_PS2_EXT, lane
fix-water-traps23, 2026-10-23; GitHub #55 item 2).

    python3 port/dreamcast/tools/d367/water/water_ps2_ext.py [--iso PS2.iso] [--out src/game/water_ps2_ext.inc] [--md FILE]

Lane water16 (water_ps2_table.py) drew the PS2 water of r107 / r108 / r10a / r10b / r11a / r11b. The rooms of the
mine / waterfall side path (r10c, r10d, r10e) carry their water the same way on the PS2 (SLUS_211.34 room EFF
records, no generator): Esp08 world planes of the room's water pictures (0xf7 dark base, 0xfe / 0xef animated noise,
0xf2 scrolling layers) plus, in r10c, the waterfall curtains (0xc5 falling-water streaks on vertical / tilted Esp08
planes). On the Dreamcast those records are drawn by no one (Esp08 draws through immediate GX; the GameCube room has
its own Esp08 water records, NO-DC like r108's), so the rivers show the bare river bed and the waterfall is missing.

This reads the PS2 room .dat straight from the PS2 disc (BIO4DAT AFS, ps2_room_extract.afs_index) and keeps, per
room, every SST (room ambient) Esp08 record that is world rotated (Tool_flg bit 0), at least 5 m on its long side and
textured with one of the water pictures. EST records (scripted, spawned by EstSet) are left out. Rows carry the
plane's two axes (sprite x, sprite y after the game's RotMatrix Rz * Ry * Rx), so tilted and vertical planes draw
through the same native layer as the horizontal ones (native_water_ps2.inc). Rows are sorted bottom-up like
water_ps2_table.py.
"""
import argparse
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))            # port/dreamcast/tools (ps2_room_extract)
sys.path.insert(0, str(HERE.parents[4] / 'tools'))  # repository tools/ (audit_ps2_fx_recipes)
import audit_ps2_fx_recipes as A  # noqa: E402
import ps2_room_extract as X  # noqa: E402
from water_ps2_table import BLEND  # noqa: E402

ROOMS = ('r10c', 'r10d', 'r10e')
WATER_TEX = (0xf2, 0xf7, 0xfe, 0xef, 0xc5)
ISO_FALLBACK = Path('/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso')


def dat_effs(blob):
    n = struct.unpack_from('<I', blob, 0)[0]
    offs = struct.unpack_from('<%dI' % n, blob, 0x10)
    types = [blob[0x10 + 4 * n + 4 * i:0x10 + 4 * n + 4 * i + 4].rstrip(b'\0').decode('latin1') for i in range(n)]
    ends = list(offs[1:]) + [len(blob)]
    return [(i, blob[offs[i]:ends[i]]) for i in range(n) if types[i] == 'EFF']


def rot(ax, ay, az):
    """The game's RotMatrix (math_sub.cpp): m = Rz * Ry * Rx, angles in degrees."""
    sx, sy, sz = (math.sin(math.radians(a)) for a in (ax, ay, az))
    cx, cy, cz = (math.cos(math.radians(a)) for a in (ax, ay, az))
    return [[cz * cy, cz * sx * sy - sz * cx, cz * cx * sy + sz * sx],
            [sz * cy, sz * sx * sy + cz * cx, sz * cx * sy - cz * sx],
            [-sy, cy * sx, cy * cx]]


def rows_for(room, blob):
    out = []
    for k, data in dat_effs(blob):
        for r in A.decode_eff(data, '<'):
            if r['table'] != 'sst' or r['id'] != 0x08 or not (r['tool_flags'] & 1) or r['tex'] not in WATER_TEX:
                continue
            if max(r['size_x'], r['size_y']) < 5000.0:
                continue
            o = r['offset']
            spd = struct.unpack_from('<2i', data, o + 0xCC)
            rate, = struct.unpack_from('<b', data, o + 0xBD)
            m = rot(*r['angle'])
            out.append(dict(room=int(room[1:], 16), area=r['area'], pos=r['position'], sx=r['size_x'], sy=r['size_y'],
                            ax=[m[i][0] for i in range(3)], bz=[m[i][1] for i in range(3)], ang=r['angle'],
                            tex=r['tex'], blend=r['blend'], tf=r['tool_flags'], rgba=r['rgba'], w8=r['work8'],
                            spd=spd, rate=rate + 0x20, ptn0=data[o + 0xBC], disp=r['no'] if r['no'] < 32 else 0xff,
                            src='%s.dat eff%d %s %d rec %d' % (room, k, r['table'], r['no'], r['index'])))
    # bottom-up; a base (0xf7) on the same height as its layers draws first
    out.sort(key=lambda x: (round(x['pos'][1]), x['tex'] != 0xf7, x['src']))
    noise, seen_f2 = set(), set()
    for x in out:   # FX level dial, as water_ps2_table.py, per effect area
        g = x['area']
        if x['tex'] in (0xf7, 0xc5):
            x['level'] = 2
        elif x['tex'] in (0xfe, 0xef) and g not in noise and x['blend'] in (0, 1) and x['rgba'][:3] != [0, 0, 0]:
            x['level'] = 2
            noise.add(g)
        elif x['tex'] == 0xf2 and g not in seen_f2:
            x['level'] = 1
            seen_f2.add(g)
        else:
            x['level'] = 0
    return out


def c_row(x):
    src, dst = BLEND[x['blend']]
    div_x = x['w8'][0] * 0.1 + 1.0
    div_y = x['w8'][1] * 0.1 + 1.0
    r, g, b, a = x['rgba']
    if x['tf'] & 0x80:
        r, g, b = (min(255, 4 * v) for v in (r, g, b))
    if x['tf'] & 0x20000:
        a = min(255, 4 * a)
    return ('    {0x%03x, %5d, {%9.1ff, %8.1ff, %9.1ff}, {%8.5ff, %8.5ff, %8.5ff}, {%8.5ff, %8.5ff, %8.5ff}, %8.1ff, %8.1ff, '
            '%8.6ff, %8.6ff, %6.4ff, %6.4ff, 0x%02x%02x%02x%02x, 0x%02x, %d, %d, %d, %3d, %d, %d},   // %s ang %s tf %x' % (
                x['room'], x['area'] if x['area'] != 0xffff else -1, x['pos'][0], x['pos'][1], x['pos'][2],
                x['ax'][0], x['ax'][1], x['ax'][2], x['bz'][0], x['bz'][1], x['bz'][2], x['sx'] * 0.5, x['sy'] * 0.5,
                div_x / x['sx'], div_y / x['sy'], x['spd'][0] * 0.001, x['spd'][1] * 0.001, a, r, g, b, x['tex'],
                src, dst, x['level'], x['rate'], x['ptn0'], x['disp'], x['src'], [round(v) for v in x['ang']], x['tf']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--md', type=Path)
    a = ap.parse_args()
    iso = a.iso or (X.ISO if X.ISO.exists() else ISO_FALLBACK)
    allrows = []
    with open(iso, 'rb') as f:
        idx, _ = X.afs_index(f)
        for room in ROOMS:
            e = idx[room + '.dat']
            f.seek(e['offset'])
            allrows += rows_for(room, f.read(e['size']))
    lines = ['// GENERATED by port/dreamcast/tools/d367/water/water_ps2_ext.py from the PS2 disc room EFF records (SST Esp08',
             '// world planes): do not edit. WATER_PS2_EXT (espgen45.cpp): the r10c / r10d / r10e rivers and the r10c',
             '// waterfall, bottom-up per room. room, area (-1: always), centre (mm), plane axis x and axis y (unit, world),',
             '// half size x y (mm), texture repeats per mm u v, scroll per tick u v (repeats), ARGB (TEV x4 scales applied),',
             '// texture id, PVR blend src dst, dial level, animation rate (x32), first pattern, SST display flag (0xff: none).',
             'static const WaterPs2ExtRow kWaterPs2Ext[] = {']
    lines += [c_row(x) for x in allrows]
    lines += ['};', '']
    text = '\n'.join(lines)
    if a.out:
        a.out.write_text(text)
    else:
        sys.stdout.write(text)
    if a.md:
        md = ['| Room | Area | Texture | Blend | RGBA | Angle | Size (m) | y (mm) | Level |', '|---|---|---|---|---|---|---|---|---|']
        for x in allrows:
            md.append('| r%03x | %s | %02x | %d | %s | %s | %.1f x %.1f | %.0f | %d |' % (
                x['room'], 'all' if x['area'] == 0xffff else x['area'], x['tex'], x['blend'], x['rgba'],
                [round(v) for v in x['ang']], x['sx'] / 1000, x['sy'] / 1000, x['pos'][1], x['level']))
        a.md.write_text('\n'.join(md) + '\n')
    print('rows', len(allrows), file=sys.stderr)


if __name__ == '__main__':
    main()
