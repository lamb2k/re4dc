#!/usr/bin/env python3
"""walk.py SAT OUT.json [--step 1000]: walkable sample points of a PS2 room collision file (lane worldlod 2026-10-15).

Every SAT section's polygons whose normal points up (ny > 0.4: floors and slopes), sampled on a ~step mm grid per
triangle (vertices included), world mm. ps2_world_far_lod.py --walk uses them: a cluster farther than --far-only-mm from
every point is never seen inside the 12 m switch distance (far-only: its level 0 is replaced by the reduced mesh).
PS2 SAT files are little-endian: tools/convert_sat.py's parsers (big-endian GameCube layout) are re-read with '<'.
"""
import inspect, json, math, pathlib, struct, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import convert_sat as cs  # noqa: E402

cs.SAT_HEADER = struct.Struct('<BB9H')
cs.SAT_VECTOR = struct.Struct('<3f')
cs.SAT_POLYGON = struct.Struct('<7H2xI')
cs.SAT_BLOCK = struct.Struct('<6f4HI')
for _fn in ('_sat_offsets', 'parse_sat', '_parse_blocks'):
    _src = inspect.getsource(getattr(cs, _fn)).replace('f">', 'f"<').replace("'>", "'<").replace('">', '"<')
    exec(_src, cs.__dict__)


def sections(path):
    out = []
    for idx in range(16):
        try:
            out.append(cs.parse_sat(pathlib.Path(path), idx, 1.0))
        except Exception as e:  # noqa: BLE001
            if 'out of range' in str(e):
                break
            print('%s section %d: %s' % (path, idx, e), file=sys.stderr)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    step = float(sys.argv[sys.argv.index('--step') + 1]) if '--step' in sys.argv else 1000.0
    pts, tris = set(), 0
    for d in sections(src):
        V, N = d['vertices'], d['normals']
        for poly in d['polygons']:
            a, b, c, ni = poly[0], poly[1], poly[2], poly[3]
            n = N[ni] if ni < len(N) else (0, 1, 0)
            ln = math.sqrt(sum(x * x for x in n)) or 1.0
            if n[1] / ln <= 0.4:
                continue
            tris += 1
            A, B, C = V[a], V[b], V[c]
            k = max(1, int(math.ceil(max(math.dist(A, B), math.dist(B, C), math.dist(C, A)) / step)))
            for i in range(k + 1):
                for j in range(k + 1 - i):
                    u, v = i / k, j / k
                    w = 1 - u - v
                    pts.add(tuple(round(A[x] * w + B[x] * u + C[x] * v) for x in range(3)))
    pts = sorted(pts)
    json.dump(dict(source=src, step=step, floor_triangles=tris, points=pts), open(dst, 'w'))
    print('walk %s: %d floor triangles, %d points, x %d..%d y %d..%d z %d..%d' % (
        pathlib.Path(src).name, tris, len(pts), min(p[0] for p in pts), max(p[0] for p in pts),
        min(p[1] for p in pts), max(p[1] for p in pts), min(p[2] for p in pts), max(p[2] for p in pts)))


if __name__ == '__main__':
    main()
