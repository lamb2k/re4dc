#!/usr/bin/env python3
"""Coalesce consecutive R4IM meshlets without restripifying their triangles.

Extends the existing world ladder's R4IM writer. A batch stays inside one
part, cluster, LOD and spatial cell in every placement. Transparent parts
stay unchanged. Material/placement/cluster identities, strips, vertex pool,
UVs, colours and palette stay intact. Rebuild .r4sg after this pass.
"""
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path

import ps2_world_far_lod as F


def level_strips(p, level):
    result = []
    for li in range(level[0], level[0] + level[1]):
        corners, strips = F.let_corners(p, p['lets'][li])
        result.extend(tuple(p['verts'][corners[i]] for i in strip) for strip in strips)
    return result


def verify(src, out, same_pool=True):
    """Check the ordered vertex attributes of EVERY strip at EVERY LOD."""
    assert src['meshes'] == out['meshes']
    if same_pool:
        assert src['verts'] == out['verts']
    assert src['pal'] == out['pal']
    assert src['plods'] == out['plods'] and src['clusters'] == out['clusters']
    assert len(src['parts']) == len(out['parts']) and len(src['levels']) == len(out['levels'])
    for a, b in zip(src['parts'], out['parts']):
        assert a[:6] == b[:6] and a[8:] == b[8:]
    strips = corners = 0
    for a, b in zip(src['levels'], out['levels']):
        assert a[2] == b[2]
        x, y = level_strips(src, a), level_strips(out, b)
        assert x == y, 'strip geometry/order/attributes changed'
        strips += len(x)
        corners += sum(map(len, x))
    return dict(levels=len(src['levels']), strips=strips, corners=corners,
                ordered_strip_attributes='IDENTICAL')


def coalesce(src, passes, placements, cell_mm=4000.0, max_vertices=256):
    assert cell_mm > 0 and 1 <= max_vertices <= 256
    out = copy.deepcopy(src)
    out['lets'], out['strip'] = [], bytearray()
    mesh_of = {pi: mi for mi, m in enumerate(src['meshes']) for pi in range(m[6], m[6] + m[7])}
    places = {}
    for mi, aff in placements:
        places.setdefault(mi, []).append(aff)
    emitted, merged, named = {}, 0, set()

    def emit(group):
        nonlocal merged
        key = tuple(group)
        if key in emitted:
            return emitted[key]
        index = len(out['lets'])
        emitted[key] = index
        if len(group) == 1:
            m = list(src['lets'][group[0]])
            if len(out['strip']) & 1:
                out['strip'].append(0)
            start = m[1]
            end = start + m[2] + (2 * m[3] if m[4] & F.INDEXED else 0)
            m[1] = len(out['strip'])
            out['strip'].extend(src['strip'][start:end])
            out['lets'].append(m)
            return index
        corners, strips = [], []
        lookup = {}
        for li in group:
            old_corners, old_strips = F.let_corners(src, src['lets'][li])
            for c in old_corners:
                if c not in lookup:
                    lookup[c] = len(corners)
                    corners.append(c)
            strips.extend([lookup[old_corners[i]] for i in s] for s in old_strips)
        assert len(corners) <= max_vertices and len(strips) < F.INDEXED
        first = min(corners)
        assert max(corners) - first <= 65535
        if len(out['strip']) & 1:
            out['strip'].append(0)
        start = len(out['strip'])
        indexed = corners != list(range(first, first + len(corners)))
        if indexed:
            out['strip'].extend(struct.pack('<%dH' % len(corners), *[c - first for c in corners]))
        begin = len(out['strip'])
        for s in strips:
            assert 3 <= len(s) <= 255
            out['strip'].append(len(s))
            out['strip'].extend(s)
        lo = [min(src['lets'][li][5 + k] for li in group) for k in range(3)]
        hi = [max(src['lets'][li][8 + k] for li in group) for k in range(3)]
        out['lets'].append([first, start, len(out['strip']) - begin, len(corners),
                            len(strips) | (F.INDEXED if indexed else 0), *lo, *hi])
        merged += len(group) - 1
        return index

    for pi, part in enumerate(src['parts']):
        first = len(out['lets'])
        mi = mesh_of[pi]
        mesh = src['meshes'][mi]
        affs = places.get(mi, [])

        def cell(li):
            m = src['lets'][li]
            boxes = [F.world_box(mesh, aff, m[5:8], m[8:11]) for aff in affs]
            # No placement means unused geometry: preserve it without batching.
            if not boxes or passes[pi] == 2:
                return ('keep', li)
            return tuple(tuple(math.floor((lo[k] + hi[k]) * 0.5 / cell_mm) for k in range(3))
                         for lo, hi in boxes)

        cfirst, count = src['plods'][pi]
        for ci in range(cfirst, cfirst + count):
            c = src['clusters'][ci]
            for lv in range(c[6], c[6] + c[7]):
                old = src['levels'][lv]
                groups, group, used, last_cell = [], [], set(), None
                for li in range(old[0], old[0] + old[1]):
                    named.add(li)
                    ids, _ = F.let_corners(src, src['lets'][li])
                    key = cell(li)
                    union = used | set(ids)
                    if group and (key != last_cell or len(union) > max_vertices):
                        groups.append(group)
                        group, used = [], set()
                    group.append(li)
                    used.update(ids)
                    last_cell = key
                if group:
                    groups.append(group)
                indices = [emit(g) for g in groups]
                assert not indices or indices == list(range(indices[0], indices[0] + len(indices))), 'shared noncontiguous levels'
                out['levels'][lv][:2] = [indices[0] if indices else len(out['lets']), len(indices)]
        for li in range(part[6], part[6] + part[7]):
            if li not in named:
                emit([li])
        out['parts'][pi][6:8] = [first, len(out['lets']) - first]
    return out, merged


def contiguous(src):
    """Use the existing nonindexed R4IM meshlet path: remove runtime gathers.

    This duplicates pool records across meshlets, never inside a meshlet or at
    runtime. It changes no strip, local index, triangle, LOD or culling bound.
    The caller must provide an explicit package byte ceiling if it grows.
    """
    out = copy.deepcopy(src)
    out['verts'], out['strip'], out['lets'] = [], bytearray(), []
    for m in src['lets']:
        corners, strips = F.let_corners(src, m)
        first, start = len(out['verts']), len(out['strip'])
        out['verts'].extend(src['verts'][c] for c in corners)
        for s in strips:
            out['strip'].append(len(s))
            out['strip'].extend(s)
        out['lets'].append([first, start, len(out['strip']) - start, len(corners), len(strips), *m[5:]])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mesh'); ap.add_argument('out')
    ap.add_argument('--sidecar', required=True)
    ap.add_argument('--cell-mm', type=float, default=4000)
    ap.add_argument('--max-vertices', type=int, default=256)
    ap.add_argument('--no-batch', action='store_true', help='storage-only comparison arm')
    ap.add_argument('--contiguous', action='store_true', help='remove indexed vertex gathers using existing nonindexed meshlets')
    ap.add_argument('--max-bytes', type=int, help='explicit resident package ceiling; default is input size')
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    blob = Path(a.mesh).read_bytes()
    src = F.read(blob)
    passes, placements = F.read_sidecar(a.sidecar, len(src['parts']))
    out, merged = (src, 0) if a.no_batch else coalesce(src, passes, placements, a.cell_mm, a.max_vertices)
    if a.contiguous:
        out = contiguous(out)
    result = F.write(out)
    checked = verify(src, F.read(result), same_pool=not a.contiguous)
    ceiling = a.max_bytes if a.max_bytes is not None else len(blob)
    assert len(result) <= ceiling, 'output exceeds the explicit resident package ceiling'
    report = dict(input=a.mesh, output=a.out, input_sha256=hashlib.sha256(blob).hexdigest(),
                  output_sha256=hashlib.sha256(result).hexdigest(), sidecar_sha256=hashlib.sha256(Path(a.sidecar).read_bytes()).hexdigest(),
                  cell_mm=a.cell_mm, max_vertices=a.max_vertices, bytes_in=len(blob), bytes_out=len(result),
                  contiguous=a.contiguous, no_batch=a.no_batch, max_bytes=ceiling,
                  meshlets_in=len(src['lets']), meshlets_out=len(out['lets']), merged=merged,
                  transforms_in=sum(m[3] for m in src['lets']), transforms_out=sum(m[3] for m in out['lets']),
                  verification=checked)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(result)
    Path(a.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
