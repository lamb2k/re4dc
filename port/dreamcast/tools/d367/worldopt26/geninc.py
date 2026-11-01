#!/usr/bin/env python3
# geninc.py <store> <n256 inc> <out inc>: the WORLD_SG26 certificate table = the n256 table with the mesh crc of
# every wsg26 room swapped (same bytes, same rows).
import re, sys
store, src, out = sys.argv[1:4]
swap = {}
for line in open(store + '/cert-rows.txt'):
    room, a, b = line.split()
    swap[int(room[1:], 16)] = (int(a, 16), int(b, 16))
lines = []
done = set()
hdr = ['// GENERATED (lane worldopt26 2026-10-26, wo26 geninc.py) from provenance_certificates_n256.inc for WORLD_SG26=1:',
       '// the same 27 rows; the mesh crc of each room in data set wsg26 (spatial strip groups: corners renumbered in group',
       '// order, same bytes, placements, parts, meshes, R4PW and policy source crc) is swapped. world_rect_provenance.h',
       '// checks every other field against the n256 table at compile time.']
lines += [h + '\n' for h in hdr]
for line in open(src):
    m = re.match(r'\{0x([0-9a-f]+)U,(.*)\},\s*$', line.strip())
    if not m:
        if line.startswith('//'):
            continue
        lines.append(line); continue
    room = int(m.group(1), 16)
    v = m.group(2).split(',')
    if room in swap:
        a, b = swap[room]
        assert int(v[6].rstrip('U'), 0) == a, (hex(room), v[6])
        v[6] = '0x%08xU' % b
        done.add(room)
    lines.append('{0x%xU,%s},\n' % (room, ','.join(v)))
assert done == set(swap), set(swap) - done
open(out, 'w').write(''.join(lines))
print('swapped', len(done), ' '.join('%x' % r for r in sorted(done)))
