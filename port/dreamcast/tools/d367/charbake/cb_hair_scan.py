#!/usr/bin/env python3
"""charbake: scan leon_hair_runs.h (14 source-ordered material runs) for regroup safety.

Reports per material the triangle count, the coincident groups (two or more triangles over the same three positions)
and whether a group spans runs / materials (a regroup by material would change the relative order of a group that
spans materials). Stdlib only; private input, prints statistics only.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cb_blob import Blob, c_arrays  # noqa: E402

RUN = re.compile(r'\{run(\d+),sizeof\(run\d+\),(\d+),(\d+),(\d+)\}')


def runs_of(header):
    text = Path(header).read_text()
    arrays = c_arrays(header)
    out = []
    for m in RUN.finditer(text):
        i, tris, mat, aid = map(int, m.groups())
        out.append(dict(index=i, triangles=tris, material=mat, asset_id=aid, blob=Blob(arrays['run%d' % i])))
    return out, arrays


def main():
    runs, arrays = runs_of(sys.argv[1])
    tris = []   # (run, material, order, (vi,ni,ti) x3)
    order = 0
    for r in runs:
        for t in r['blob'].triangles():
            tris.append((r['index'], r['material'], order, t))
            order += 1
    groups = {}
    for run, mat, o, t in tris:
        key = tuple(sorted(c[0] for c in t))
        groups.setdefault(key, []).append((run, mat, o, t))
    co = [g for g in groups.values() if len(g) > 1]
    span_runs = [g for g in co if len({x[0] for x in g}) > 1]
    span_mats = [g for g in co if len({x[1] for x in g}) > 1]
    same_uv = [g for g in co if len({tuple(c[2] for c in x[3]) for x in g}) == 1]
    uvset_same = [g for g in co if len({frozenset(c[2] for c in x[3]) for x in g}) == 1]
    per_mat = {}
    for run, mat, o, t in tris:
        per_mat[mat] = per_mat.get(mat, 0) + 1
    print(json.dumps(dict(
        runs=[(r['index'], r['material'], r['triangles']) for r in runs],
        triangles=len(tris), per_material=per_mat, coincident_groups=len(co),
        group_sizes=sorted({len(g) for g in co}), groups_spanning_runs=len(span_runs),
        groups_spanning_materials=len(span_mats), groups_same_uv_order=len(same_uv), groups_same_uv_set=len(uvset_same),
        span_material_examples=[[(x[0], x[1], x[2]) for x in g] for g in span_mats[:6]],
        span_run_examples=[[(x[0], x[1], x[2]) for x in g] for g in span_runs[:6]],
        uv_bytes=len(arrays.get('uv', b''))), indent=1))


if __name__ == '__main__':
    main()
