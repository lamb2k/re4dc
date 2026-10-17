#!/usr/bin/env python3
"""verify_groups.py SRC.re4mesh OUT.re4mesh  (lane batch17)
Lossless check of a coalesced + regrouped PS2 world against its source (bake13 level 0):
  - same meshes, parts (minus meshlet ranges), clusters, plods, levels' error values, palette;
  - for every part / cluster / level, the multiset of strips (each strip = its ordered tuple of full vertex records:
    grid position, UV, colour) is identical, i.e. the same triangles with the same winding and attributes;
  - totals: corners per level identical.
Prints LOSSLESS PASS or raises."""
import sys, collections
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else '.')
import ps2_world_far_lod as F


def level_strips(p, level):
    out = []
    for li in range(level[0], level[0] + level[1]):
        corners, strips = F.let_corners(p, p['lets'][li])
        out.extend(tuple(p['verts'][corners[i]] for i in s) for s in strips)
    return out


def main():
    a = F.read(open(sys.argv[1], 'rb').read())
    b = F.read(open(sys.argv[2], 'rb').read())
    assert a['meshes'] == b['meshes'], 'meshes'
    assert a['pal'] == b['pal'], 'palette'
    assert a['plods'] == b['plods'], 'plods'
    assert len(a['parts']) == len(b['parts'])
    for x, y in zip(a['parts'], b['parts']):
        assert x[:6] == y[:6] and x[8:] == y[8:], 'part fields'
    assert len(a['clusters']) == len(b['clusters'])
    for x, y in zip(a['clusters'], b['clusters']):
        assert x[:6] == y[:6] and x[7] == y[7], 'cluster boxes / level counts'
    assert len(a['levels']) == len(b['levels'])
    strips = corners = 0
    for la, lb in zip(a['levels'], b['levels']):
        assert la[2] == lb[2], 'level error'
        x, y = level_strips(a, la), level_strips(b, lb)
        assert collections.Counter(x) == collections.Counter(y), 'strip set changed'
        strips += len(x); corners += sum(map(len, x))
    # every part's level-0 meshlet range covers the same strips too (parts without clusters)
    for pi, (x, y) in enumerate(zip(a['parts'], b['parts'])):
        sx = level_strips(a, (x[6], x[7], 0)); sy = level_strips(b, (y[6], y[7], 0))
        assert collections.Counter(sx) == collections.Counter(sy), 'part %d strip set changed' % pi
    print('LOSSLESS PASS levels=%d strips=%d corners=%d meshlets %d -> %d' % (
        len(a['levels']), strips, corners, len(a['lets']), len(b['lets'])))


if __name__ == '__main__':
    main()
