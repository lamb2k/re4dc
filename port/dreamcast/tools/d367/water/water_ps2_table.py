#!/usr/bin/env python3
"""water_ps2_table.py: the PS2 water layers of the chapter 1 rooms as a C table (WATER_PS2, lane water16, 2026-10-16).

    python3 port/dreamcast/tools/d367/water/water_ps2_table.py [--cache /root/probe/worldfx-cache] [--out FILE] [--md FILE]

What the PS2 did (SLUS_211.34): Espgen42_Trans is `jr ra` and Espgen45_Trans only clears Status_flg[1] 0x20, so the
PS2 draws no generator water surface at all (no height field, no screen-copy refraction, no bump). Its rooms carry the
water as stacked Esp08 records instead: large horizontal scrolling tiled planes (Tool_flg bit 0 = world rotated,
angle x = 90), a flat dark base (core texture 0xf7, white), two scrolling layers of the room's water picture 0xf2 and
an animated noise top layer (0xfe / 0xef, sometimes additive). The GameCube keeps the generator (espgen42 r10a / r11a,
espgen45 r107 / r10b / r11b) and has Esp08 water only in r108 and r11b (both NO-DC on the Dreamcast).

This reads the PS2 room EFF records from the worldfx cache (rNNN.ps2.effN, little endian) and keeps, per water room,
every Esp08 record that is a world-space horizontal plane of 5 m or more. The runtime (espgen45.cpp WATER_PS2) draws
them render-side from the room's GameCube water anchor (the espgen42 / 45 generator's OT entry, or the r108 / r11b
GameCube Esp08 water sprite): no PS2 record is spawned, so no effect slot, generator or Rnd() draw changes.

Rows are sorted bottom-up (y ascending, then record order): the PS2 sorts these sprites by depth, and looking down
at the water the lowest plane is the farthest, so the dark base draws first and the noise layer last.
"""
import argparse
import math
import struct
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[5] / 'tools'   # the repository's tools/ (audit_ps2_fx_recipes.py)
sys.path.insert(0, str(TOOLS))
import audit_ps2_fx_recipes as A  # noqa: E402

ROOMS = ('r107', 'r108', 'r10a', 'r10b', 'r11a', 'r11b')
# FX level dial (FX_LEVEL, render side): a row is drawn while re4dc_fx_level <= its level. The base and the first
# noise layer always draw; the first 0xf2 layer to level 1; the rest only at level 0 (PS2 as-is).


def rows_for(cache, room):
    out = []
    for path in sorted(cache.glob('%s.ps2.eff[0-9]' % room)):
        data = path.read_bytes()
        for r in A.decode_eff(data, '<'):
            if r['id'] != 0x08 or not (r['tool_flags'] & 1) or abs(r['angle'][0] - 90.0) > 0.5:
                continue
            if min(r['size_x'], r['size_y']) < 5000.0:
                continue
            o = r['offset']
            spd = struct.unpack_from('<2i', data, o + 0xCC)
            anm_rate, = struct.unpack_from('<b', data, o + 0xBD)
            ptn0 = data[o + 0xBC]
            shimmer = data[o + 0xC3]
            out.append(dict(room=int(room[1:], 16), area=r['area'], pos=r['position'], sx=r['size_x'], sy=r['size_y'],
                            ry=r['angle'][1], tex=r['tex'], blend=r['blend'], tf=r['tool_flags'], rgba=r['rgba'],
                            w8=r['work8'], spd=spd, rate=anm_rate + 0x20, ptn0=ptn0, shimmer=shimmer,
                            src='%s %s %d rec %d' % (path.name, r['table'], r['no'], r['index'])))
    out.sort(key=lambda x: (x['pos'][1], x['src']))
    # dial levels per room
    seen_f2 = 0
    noise = False
    for x in out:
        if x['tex'] == 0xf7:
            x['level'] = 2
        elif x['tex'] in (0xfe, 0xef) and not noise and x['blend'] in (0, 1) and x['rgba'][:3] != [0, 0, 0]:
            x['level'] = 2
            noise = True
        elif x['tex'] == 0xf2 and seen_f2 == 0:
            x['level'] = 1
            seen_f2 += 1
        else:
            x['level'] = 0
    return out


BLEND = {0: (4, 5), 1: (4, 1), 2: (1, 1), 3: (2, 1), 4: (2, 0), 5: (4, 3)}   # esp_sub.cpp bl[]: PVR src, dst


def c_row(x):
    src, dst = BLEND[x['blend']]
    div_x = x['w8'][0] * 0.1 + 1.0
    div_y = x['w8'][1] * 0.1 + 1.0
    r, g, b, a = x['rgba']
    if x['tf'] & 0x80:      # TEV colour scale 4 (ChannelSet)
        r, g, b = (min(255, 4 * v) for v in (r, g, b))
    if x['tf'] & 0x20000:   # TEV alpha scale 4
        a = min(255, 4 * a)
    return ('    {0x%03x, %5d, %9.1ff, %8.1ff, %9.1ff, %8.1ff, %8.1ff, %7.4ff, %8.6ff, %8.6ff, %6.4ff, %6.4ff, '
            '0x%02x%02x%02x%02x, 0x%02x, %d, %d, %d, %3d, %d},   // %s tex %02x tf %x w8 %s' % (
                x['room'], x['area'] if x['area'] != 0xffff else -1, x['pos'][0], x['pos'][1], x['pos'][2],
                x['sx'] * 0.5, x['sy'] * 0.5, math.radians(x['ry']), div_x / x['sx'], div_y / x['sy'],
                x['spd'][0] * 0.001, x['spd'][1] * 0.001, a, r, g, b, x['tex'], src, dst, x['level'], x['rate'],
                x['ptn0'], x['src'], x['tex'], x['tf'], x['w8']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', type=Path, default=Path('/root/probe/worldfx-cache'))
    ap.add_argument('--out', type=Path)
    ap.add_argument('--md', type=Path)
    a = ap.parse_args()
    allrows = []
    for room in ROOMS:
        allrows += rows_for(a.cache, room)
    lines = ['// GENERATED by port/dreamcast/tools/d367/water/water_ps2_table.py from the worldfx cache PS2 room EFF records:',
             '// do not edit. WATER_PS2 (espgen45.cpp): the PS2 water layers (Esp08 world planes), bottom-up per room.',
             '// room, area (-1: always), centre x y z (mm), half size x z (mm), rotation y (rad), texture repeats per mm',
             '// u v, scroll per tick u v (repeats), ARGB (TEV x4 scales applied), texture id, PVR blend src dst, dial level,',
             '// animation rate (x32), first pattern.',
             'static const WaterPs2Row kWaterPs2[] = {']
    lines += [c_row(x) for x in allrows]
    lines += ['};', '']
    text = '\n'.join(lines)
    if a.out:
        a.out.write_text(text)
    else:
        sys.stdout.write(text)
    if a.md:
        md = ['| Room | Area | Texture | Blend | RGBA (record) | Tool_flg | Repeats (Work8/10+1) | Scroll /tick | y (mm) | Size (m) | Level |',
              '|---|---|---|---|---|---|---|---|---|---|---|']
        for x in allrows:
            md.append('| r%03x | %s | %02x | %d | %s | %x | %.1f x %.1f | %s | %.0f | %.1f x %.1f | %d |' % (
                x['room'], 'all' if x['area'] == 0xffff else x['area'], x['tex'], x['blend'], x['rgba'], x['tf'],
                x['w8'][0] * 0.1 + 1, x['w8'][1] * 0.1 + 1, x['spd'], x['pos'][1], x['sx'] / 1000, x['sy'] / 1000,
                x['level']))
        a.md.write_text('\n'.join(md) + '\n')
    print('rows', len(allrows), file=sys.stderr)


if __name__ == '__main__':
    main()
