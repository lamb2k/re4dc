#!/usr/bin/env python3
# geninc_bake.py <cert-rows.txt> [<base inc> <out inc> <out rooms inc>]: the WORLD_BAKE=1 certificate table (lane bakeall,
# 2026-11-02) = provenance_certificates.inc (the release table, SCENERY_N256 off) with the row of every baked room
# replaced by the row post_room.sh computed for its baked package (all fields: R4PW bytes, placements, parts, meshes,
# physical crc + fnv of the shipped (rekeyed) R4PW, mesh crc + bytes, and the converter's own R4PW crc as the policy
# source every regenerated sidecar is bound to). Same table size (no static growth); the rooms list feeds the
# compile-time check that no other row differs.
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
rect = os.path.join(here, '..', 'texture_rect21')
rows_txt = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else os.path.join(rect, 'provenance_certificates.inc')
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(rect, 'provenance_certificates_bake.inc')
rooms_out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(rect, 'provenance_bake_rooms.inc')
ROW = re.compile(r'\{0x([0-9a-f]+)U,(.*)\},\s*$')
new = {}
for line in open(rows_txt):
    m = ROW.match(line.strip())
    if m:
        room = int(m.group(1), 16)
        assert room not in new, 'room %x twice' % room
        new[room] = line.strip()
lines = ['// GENERATED (lane bakeall 2026-11-02, tools/d367/bakeall/geninc_bake.py) from provenance_certificates.inc for\n',
         '// WORLD_BAKE=1: the same 27 rows; each room in the bake set has its baked package\'s row. world_rect_provenance.h\n',
         '// checks every other row against the base table at compile time.\n']
done = set()
for line in open(base):
    m = ROW.match(line.strip())
    if not m:
        if not line.startswith('//'):
            lines.append(line)
        continue
    room = int(m.group(1), 16)
    if room in new:
        lines.append(new[room] + '\n'); done.add(room)
    else:
        lines.append(line)
assert done == set(new), 'rooms without a base row: %s' % sorted('%x' % r for r in set(new) - done)
open(out, 'w').write(''.join(lines))
open(rooms_out, 'w').write('// GENERATED (geninc_bake.py): the rooms whose WORLD_BAKE certificate row differs from the base table\n' +
                           ''.join('0x%xU,\n' % r for r in sorted(done)))
print('baked rows', ' '.join('%x' % r for r in sorted(done)))
