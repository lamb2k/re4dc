#!/usr/bin/env python3
"""Protected PS2 Ashley rungs using mesh_lod's UV guarded half-edge collapse.

lod.py <conversion> <output> --pct 70|50
The face and hands remain full. Eight height bands and eight radial extrema per
role protect the rest silhouette; open borders and every source component stay.
Survivors keep original positions and PS2 rig weights. No generated game assets
are stored in the repository.
"""
import argparse
import copy
import json
import math
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
import mesh_lod as ml
import ps2_cast as pc


def protected(mesh, triangles):
    p = mesh['positions_mm']
    vids = {c['vertex'] for t in triangles for c in t['corners']}
    ymin, ymax = min(p[v][1] for v in vids), max(p[v][1] for v in vids)
    bands = defaultdict(list)
    for v in sorted(vids):
        bands[min(7, int(8 * (p[v][1] - ymin) / max(.001, ymax - ymin)))].append(v)
    lock = set()
    for values in bands.values():
        for a in range(8):
            x, z = math.cos(a * math.pi / 4), math.sin(a * math.pi / 4)
            lock.add(max(values, key=lambda v: (p[v][0] * x + p[v][2] * z, -v)))
    # Preserve open borders, role joins, and at least one vertex of every shell.
    edges = Counter()
    tris = []
    for t in triangles:
        vs = tuple(c['vertex'] for c in t['corners'])
        tris.append((vs, ()))
        for a, b in zip(vs, vs[1:] + vs[:1]):
            edges[tuple(sorted((a, b)))] += 1
    for edge, n in edges.items():
        if n == 1:
            lock.update(edge)
    for component in ml.components(tris):
        lock.add(min(v for ti in component for v in tris[ti][0]))
    return lock


class SkinnedSimplifier(ml.Simplifier):
    def __init__(self, mesh, triangles, locks):
        self.weights = [dict(w) for w in mesh['weights']]
        super().__init__(dict(enumerate(map(tuple, mesh['positions_mm']))), triangles, locks)

    def _valid(self, u, v):
        a, b = self.weights[u], self.weights[v]
        # Bound deformation changes while retaining the survivor's authored skin.
        if sum(abs(a.get(k, 0) - b.get(k, 0)) for k in a.keys() | b.keys()) > .5:
            return False
        return super()._valid(u, v)


def reduce(mesh, pct, body_only=False):
    groups = defaultdict(list)
    for t in mesh['triangles']:
        groups[t['source_info']].append(t)
    keep = {1, 2, 3, 4, 5, 6} if body_only else {1, 5, 6}
    fixed = sum(len(ts) for r, ts in groups.items() if r in keep)
    reducible = len(mesh['triangles']) - fixed
    ratio = max(.02, (len(mesh['triangles']) * pct / 100 - fixed) / reducible)
    out, report = [], dict(tool='mesh_lod', uv_guard=.02, requested_percent=pct,
                          keep_roles=sorted(keep), roles={})
    old = ml.UV_GUARD
    ml.UV_GUARD = .02
    try:
        for role, ts in sorted(groups.items()):
            if role in keep:
                out.extend(copy.deepcopy(ts))
                report['roles'][role] = dict(before=len(ts), after=len(ts), full=True)
                continue
            locks = protected(mesh, ts)
            raw = [(tuple(c['vertex'] for c in t['corners']),
                    tuple((tuple(c['uv']), tuple(c['normal']), 0) for c in t['corners'])) for t in ts]
            s = SkinnedSimplifier(mesh, raw, locks)
            target = max(1, round(len(ts) * ratio))
            # Distinct guarded error budgets when the requested percentage hits
            # the protected floor. Report achieved counts, never relabel a floor.
            for step in range(1, (32 if pct == 70 else 80) + 1):
                s.run_to(step * .25)
                if len(s.triangles()) <= target:
                    break
            got = s.triangles()
            if not got:
                raise ValueError(f'Protected role {role} disappeared')
            for vs, attrs in got:
                out.append(dict(source_info=role, corners=[dict(vertex=v, uv=list(a[0]), normal=list(a[1]))
                                                           for v, a in zip(vs, attrs)]))
            report['roles'][role] = dict(before=len(ts), after=len(got), target=target,
                                        locked_vertices=len(locks), max_plane_error_mm=s.error)
    finally:
        ml.UV_GUARD = old
    result = copy.deepcopy(mesh)
    result['triangles'] = out
    report.update(triangles_before=len(mesh['triangles']), triangles_after=len(out),
                  vertices_before=len({c['vertex'] for t in mesh['triangles'] for c in t['corners']}),
                  vertices_after=len({c['vertex'] for t in out for c in t['corners']}))
    report['achieved_percent'] = 100 * len(out) / len(mesh['triangles'])
    return result, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--pct', type=int, choices=(70, 50), required=True)
    ap.add_argument('--body-only', action='store_true', help='Keep face, hair/cards, hands and trim full (bounded five-descriptor package)')
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    mesh = json.loads((a.source / 'mesh.json').read_text())
    if 'ps2_rig' not in json.loads((a.source / 'source.json').read_text()):
        raise ValueError('ASHLEY_PS2_RIG conversion required')
    reduced, report = reduce(mesh, a.pct, a.body_only)
    for f in ('source.json', 'source-bindings.json', 'validation.json', 'atlas.png', 'atlas-rgba.png'):
        shutil.copy2(a.source / f, a.output / f)
    (a.output / 'mesh.json').write_text(json.dumps(reduced))
    pk = pc.load_module('pack_coarse_actor', pc.PROTO / 'tools/pack_coarse_actor.py')
    pk.pack(a.output / 'mesh.json', a.output / 'source.json', a.output / 'native', 'castmodel')
    pc.host_fixture(a.output / 'native', reduced)
    (a.output / 'lod-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
