#!/usr/bin/env python3
"""ps2leon: the GameCube Leon (debug disc pl00 / wep02, the eight roles) as a render-mesh JSON for the comparison
renders and the counts (not packed: up to four influences, its own materials). UVs mapped into today's atlas tiles
like the arms (the GC images are the atlas's pictures); hair corners carry src_uv / material.

  build_gc_mesh.py <out dir>
"""
import json, sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa: E402
from build_arm_a import atlas_uv, HAIR_MATERIAL  # noqa: E402

GC_KEY = {
    0: {0: '1f625c95-7aed4809', 2: '23f6b950-9ea131c1', 3: '15f7e18c-11dc93e0', 7: '2a8a368f-76c02b02'},
    1: {3: '15f7e18c-11dc93e0', 5: '878b23c0-e7038833'},
    2: {0: '1f625c95-7aed4809'},
    3: {4: 'dde6f32a-0b7cfdcf'},
    4: {4: 'dde6f32a-0b7cfdcf'},
    5: {0: 'cd026c6d-3a54bfa9'},
    6: {0: 'cd026c6d-3a54bfa9'},
    7: {0: 'ac381b1a-3ade84b1', 2: '7a9de1fd-0e415f15'},
}


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    today = ls.leon_mesh()
    positions, weights, triangles = [], [], []
    rep = []
    for role in range(8):
        g = ls.gc_role(role)
        base = len(positions)
        for i, p in enumerate(g['positions']):
            positions.append([float(x) for x in p])
            weights.append([[int(b), float(w)] for b, w in g['weights'][i]])
        mats = Counter()
        for k, cs in enumerate(g['corners']):
            key = GC_KEY[role][g['tri_material'][k][0]]
            mats[key] += 1
            tc = []
            for pi, n, uv in cs:
                c = dict(vertex=base + int(pi), normal=[float(x) for x in n], uv=atlas_uv(key, float(uv[0]), float(uv[1])))
                if role == 7:
                    c['src_uv'] = [float(uv[0]), float(uv[1])]
                tc.append(c)
            t = dict(source_info=role, corners=tc)
            if role == 7:
                t['material'] = HAIR_MATERIAL[key]
            triangles.append(t)
        rep.append(dict(role=role, triangles=len(g['corners']), positions=len(g['positions']), images=dict(mats),
                        max_influences=max(len(w) for w in g['weights'])))
        print(rep[-1])
    mesh = {'schema': 're4dc-approved-render-mesh-1', 'blend_sha256': None, 'source_sha256': today['source_sha256'],
            'mesh': 'Leon_GC_Source', 'positions_mm': positions, 'weights': weights, 'bones': today['bones'], 'triangles': triangles,
            'source_info_counts': {str(i): sum(t['source_info'] == i for t in triangles) for i in range(8)},
            'policy': 'GC reference for renders and counts; not a runtime asset.'}
    (out / 'mesh.json').write_text(json.dumps(mesh, separators=(',', ':')))
    print('GC', len(triangles), 'triangles', len(positions), 'positions')


if __name__ == '__main__':
    main()
