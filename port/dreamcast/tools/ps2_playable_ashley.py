#!/usr/bin/env python3
"""Offline PS2 pl01 conversion; distinct from the pl11 partner profile.

All geometry, colours, masks, normals and authored skin influences come from
pl01.dat. pl01.drs supplies only the existing owner's source identity contract.
The animation adapter uses the existing game cloth solver; this adds no solver,
game tick, gameplay RNG or motion data. Full geometry is retained at every hand
state. Runtime admission still requires the player owner and every BIN/TPL fact.
"""
import argparse
import json
from pathlib import Path

import ps2_ashley as ash


def profile(right='normal', left='open'):
    if right not in ('normal', 'r20e') or left not in ('open', 'closed'):
        raise ValueError('Unsupported playable Ashley hand contract')
    rbin, rtpl, ps2r, ps2tpl = (0x11, 5, 0x11, 0xA7) if right == 'normal' else (0xA7, 0xA8, 0xA8, 0xA9)
    lbin = 0x14 if left == 'open' else 0x15
    sections = [('body', 4, 5), ('head', 7, 9), ('hair', 6, 0xB),
                ('extra9', 8, 5), ('extraA', 0xA, 5),
                ('right-hand', rbin, rtpl), ('left-hand', lbin, 5)]
    # pl01 body4 and hair8 are independently pinned PS2 members. The merged
    # PS2 head/hair materials are partitioned against these pl01 source roles.
    sources = [(4, [2, 3, 4, 5, 6, 7], 5, ['body']),
               (4, [0], 5, ['head', 'hair']), (4, [1], 5, ['head']),
               (4, [8], 5, ['extra9', 'extraA']),
               (8, [0, 1, 2], 0xB, ['extra9', 'hair']),
               (8, [3], 0xB, ['head', 'hair']),
               (ps2r, [0] if right == 'normal' else [0, 1], ps2tpl, ['right-hand']),
               (lbin, [0], 0xA7, ['left-hand'])]
    return dict(archive='pl01', model_id=0, preset=f'ashley01-{right[0]}-{left[0]}',
                rooms=['r20d', 'r20e'], cloth_donor='extra9', sections=sections, ps2_sources=sources)


def register(p):
    ash.pc.PRESETS[p['preset']] = dict(archive='pl01', model_id=0,
        sections=[(arc, role, tpl) for role, arc, tpl in p['sections']], tpl=5,
        rooms=p['rooms'], types=[], category='registry', converter='ps2_playable_ashley.py --rig')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    c = sub.add_parser('convert')
    c.add_argument('out', type=Path)
    c.add_argument('--ps2-dat', type=Path, required=True)
    c.add_argument('--gc-drs', type=Path, required=True)
    c.add_argument('--right', choices=['normal', 'r20e'], default='normal')
    c.add_argument('--left', choices=['open', 'closed'], default='open')
    c.add_argument('--poses', type=int, default=24)
    c.add_argument('--max-slots', type=int, default=64)
    f = sub.add_parser('finish')
    f.add_argument('out', type=Path)
    r = sub.add_parser('regcast')
    r.add_argument('cast', type=Path)
    r.add_argument('overlay')
    r.add_argument('outs', type=Path, nargs='+')
    a = ap.parse_args()
    for right in ('normal', 'r20e'):
        for left in ('open', 'closed'):
            register(profile(right, left))
    if a.command == 'convert':
        ash.convert(a.out, a.ps2_dat, a.gc_drs, a.max_slots, a.poses,
                    rig=True, profile=profile(a.right, a.left))
    elif a.command == 'finish':
        ash.pc.finish(a.out)
    else:
        ash.pc.regcast(a.cast, a.overlay, a.outs)


if __name__ == '__main__':
    main()
