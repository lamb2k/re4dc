#!/usr/bin/env python3
"""composite_record.py <set dir> <room> <PS2 room input dir>   (lane bakeall, coordinator 11-03, GC-ASSET design b)

Appends the room's row to <set dir>/ps2-composite.tsv: the sha256 of every file the bake wrote for the room
(dc/native/<room>/ps2-world.re4mesh, .r4pw, .ids, .r4tc, room.r4rc; '-' when the room has none) and the sha256 of the
PS2 sources it was converted from (<room>_004.SMD, the world; <room>_004.scenario.obj, the extracted rows).
gc_port23/provenance.py turns a PS2-recipe store's rows into composite-records.json; judge.py --composite-records
classifies a runtime world composite (kind=layout) as PS2 when its GC-ASSET-NOTE geometry (= re4mesh) and r4pw digests
match a row."""
import hashlib
import sys
from pathlib import Path

COLS = ('room', 're4mesh_sha256', 'r4pw_sha256', 'ids_sha256', 'r4tc_sha256', 'r4rc_sha256',
        'ps2_smd_sha256', 'ps2_obj_sha256', 'ps2_source')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else '-'


def main(set_dir, room, src):
    s, src = Path(set_dir), Path(src)
    d = s / 'dc' / 'native' / room
    smd = src / f'{room}_004.SMD'
    if not smd.is_file() or not (d / 'ps2-world.re4mesh').is_file() or not (d / 'ps2-world.r4pw').is_file():
        raise SystemExit('composite_record: missing %s or the baked package in %s' % (smd, d))
    row = dict(room=room, re4mesh_sha256=sha(d / 'ps2-world.re4mesh'), r4pw_sha256=sha(d / 'ps2-world.r4pw'),
               ids_sha256=sha(d / 'ps2-world.ids'), r4tc_sha256=sha(d / 'ps2-world.r4tc'), r4rc_sha256=sha(d / 'room.r4rc'),
               ps2_smd_sha256=sha(smd), ps2_obj_sha256=sha(src / f'{room}_004.scenario.obj'),
               ps2_source='PS2 %s world %s_004.SMD (ps2rooms extract)' % (room, room))
    out = s / 'ps2-composite.tsv'
    rows = [l for l in out.read_text().splitlines()[1:] if l and l.split('\t')[0] != room] if out.is_file() else []
    rows.append('\t'.join(row[c] for c in COLS))
    out.write_text('\t'.join(COLS) + '\n' + '\n'.join(sorted(rows)) + '\n')
    print('composite_record', room, row['re4mesh_sha256'][:12], row['r4pw_sha256'][:12], 'smd', row['ps2_smd_sha256'][:12])


if __name__ == '__main__':
    main(*sys.argv[1:4])
