"""navplan.py: walk path through one room's scenario collision (SAT) for steer.py (lane castle31, test tooling only).

    python navplan.py <room .arc/.dar or raw SAT> X0 Z0 Y0 X1 Z1 [--cell 150] [--png out.png]

Reads the room's first SAT piece (the static room collision: floor, slope and wall triangles, in that order; either byte
order), builds a walk grid (a cell is walkable at a floor height when a floor/slope triangle covers it; a move between
neighbour cells must climb at most STEP and must not pass within BODY_R of a wall triangle spanning the body's height),
runs A* from (X0, Y0, Z0) to the floor nearest (X1, Z1), and prints steer.py `goto X Z` lines (straight runs merged).
Movable pieces (doors, gates, puzzle walls) are other SAT pieces and are ignored: the plan assumes they are open.
"""
import argparse, heapq, math, struct, sys

BODY_R, STEP, HEIGHT = 330.0, 450.0, 1500.0


def sat_bytes(path):
    d = open(path, 'rb').read()
    if path.lower().endswith('.sat'):
        return d
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'enginebake'))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    import room_smd
    if d[:32] == room_smd.CONTAINER_MAGIC:
        d = room_smd.decode_das(d)
    e = room_smd.archive_endian(d)
    return [d[a:b] for tag, a, b in room_smd.tagged_entries(d, e) if tag == b'SAT\0'][0]


def parse(d):
    for E in '<>':
        try:
            offs = [0]
            if d[0] & 0x80:
                offs = list(struct.unpack_from(E + '%dI' % d[1], d, 4))
            b = offs[0]
            _, _, nv, nn, ne, _, npoly, nf, ns, nw, nb = struct.unpack_from(E + 'BB9H', d, b)
            if nf + ns + nw != npoly or nv > 20000 or b + 0x14 + 12 * nv > len(d):
                continue
            o = b + 0x14
            v = [struct.unpack_from(E + '3f', d, o + 12 * i) for i in range(nv)]
            o += 12 * (nv + nn + ne)
            polys = [struct.unpack_from(E + '3H', d, o + 20 * i) for i in range(npoly)]
            if max(max(p) for p in polys) >= nv:
                continue
            tri = [(v[a], v[b2], v[c]) for a, b2, c in polys]
            return tri[:nf + ns], tri[nf + ns:]
        except struct.error:
            continue
    return None


def plane_y(t, x, z):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
    if abs(den) < 1e-6:
        return None
    l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / den
    l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / den
    l3 = 1 - l1 - l2
    if min(l1, l2, l3) < -1e-4:
        return None
    return l1 * ay + l2 * by + l3 * cy


def seg_dist(p, q, a, b):
    def pt(px, pz, ax, az, bx, bz):
        dx, dz = bx - ax, bz - az; L = dx * dx + dz * dz
        t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L))
        return math.hypot(px - ax - t * dx, pz - az - t * dz)

    def cross(o, a1, b1):
        return (a1[0] - o[0]) * (b1[1] - o[1]) - (a1[1] - o[1]) * (b1[0] - o[0])
    d1, d2, d3, d4 = cross(a, b, p), cross(a, b, q), cross(p, q, a), cross(p, q, b)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return 0.0
    return min(pt(p[0], p[1], *a, *b), pt(q[0], q[1], *a, *b), pt(a[0], a[1], *p, *q), pt(b[0], b[1], *p, *q))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('room'); ap.add_argument('x0', type=float); ap.add_argument('z0', type=float)
    ap.add_argument('y0', type=float); ap.add_argument('x1', type=float); ap.add_argument('z1', type=float)
    ap.add_argument('--cell', type=float, default=150.0); ap.add_argument('--png')
    a = ap.parse_args()
    floors, walls = parse(sat_bytes(a.room))
    if a.png:  # top-down map: floors shaded by height, walls red, start/goal marked; grid labels every 5 m
        from PIL import Image, ImageDraw
        pts = [p for t in floors + walls for p in t]
        mx, Mx = min(p[0] for p in pts), max(p[0] for p in pts); mz, Mz = min(p[2] for p in pts), max(p[2] for p in pts)
        my, My = min(p[1] for t in floors for p in t), max(p[1] for t in floors for p in t)
        S = 1000.0 / max(Mx - mx, Mz - mz)
        P = lambda x, z: ((x - mx) * S + 20, (Mz - z) * S + 20)   # +z up
        im = Image.new('RGB', (int((Mx - mx) * S) + 40, int((Mz - mz) * S) + 40), (0, 0, 0)); dr = ImageDraw.Draw(im)
        for t in sorted(floors, key=lambda t: sum(p[1] for p in t)):
            v = int(60 + 190 * (sum(p[1] for p in t) / 3 - my) / max(1, My - my))
            dr.polygon([P(p[0], p[2]) for p in t], fill=(v // 3, v, v // 2))
        for t in walls:
            dr.line([P(p[0], p[2]) for p in t] + [P(t[0][0], t[0][2])], fill=(220, 40, 40))
        for x in range(int(mx // 5000) * 5000, int(Mx) + 1, 5000):
            dr.text(P(x, Mz), str(x // 1000), fill=(255, 255, 0)); dr.line([P(x, mz), P(x, Mz)], fill=(50, 50, 90))
        for z in range(int(mz // 5000) * 5000, int(Mz) + 1, 5000):
            dr.text(P(mx, z), str(z // 1000), fill=(255, 255, 0)); dr.line([P(mx, z), P(Mx, z)], fill=(50, 50, 90))
        for (x, z), c in (((a.x0, a.z0), (0, 128, 255)), ((a.x1, a.z1), (255, 0, 255))):
            q = P(x, z); dr.ellipse([q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6], fill=c)
        im.save(a.png); print('map', a.png, 'floor y %d..%d' % (my, My))
        return
    C = a.cell
    xs = [p[0] for t in floors for p in t]; zs = [p[2] for t in floors for p in t]
    x0, z0 = min(xs), min(zs); W_, H_ = int((max(xs) - x0) / C) + 2, int((max(zs) - z0) / C) + 2
    # floor heights per cell (several levels allowed)
    fl = {}
    for t in floors:
        tx = [p[0] for p in t]; tz = [p[2] for p in t]
        for i in range(int((min(tx) - x0) / C), int((max(tx) - x0) / C) + 2):
            for j in range(int((min(tz) - z0) / C), int((max(tz) - z0) / C) + 2):
                y = plane_y(t, x0 + i * C, z0 + j * C)
                if y is not None:
                    fl.setdefault((i, j), []).append(y)
    # wall segments (longest XZ edge of each wall triangle) in a coarse hash
    wh = {}; G = 2000.0
    for t in walls:
        es = [(t[k], t[(k + 1) % 3]) for k in range(3)]
        p, q = max(es, key=lambda e: math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2]))
        ylo, yhi = min(v[1] for v in t), max(v[1] for v in t)
        s = ((p[0], p[2]), (q[0], q[2]), ylo, yhi)
        for gi in range(int(min(p[0], q[0]) // G) - 1, int(max(p[0], q[0]) // G) + 2):
            for gj in range(int(min(p[2], q[2]) // G) - 1, int(max(p[2], q[2]) // G) + 2):
                wh.setdefault((gi, gj), []).append(s)

    def blocked(pa, pb, y):
        for s in wh.get((int(pb[0] // G), int(pb[1] // G)), ()):
            if s[3] < y + STEP or s[2] > y + HEIGHT:
                continue
            if seg_dist(pa, pb, s[0], s[1]) < BODY_R:
                return True
        return False

    def node_near(x, z, y=None):
        i, j = int(round((x - x0) / C)), int(round((z - z0) / C))
        best = None
        for di in range(-6, 7):
            for dj in range(-6, 7):
                for fy in fl.get((i + di, j + dj), ()):
                    d = math.hypot(di, dj) * C + (abs(fy - y) if y is not None else 0)
                    if best is None or d < best[0]:
                        best = (d, (i + di, j + dj, fy))
        return best[1]
    s = node_near(a.x0, a.z0, a.y0); g = node_near(a.x1, a.z1)
    pos = lambda n: (x0 + n[0] * C, z0 + n[1] * C)
    openq = [(0, 0, s)]; came = {s: None}; cost = {s: 0}
    while openq:
        _, c, n = heapq.heappop(openq)
        if n[:2] == g[:2]:
            g = n; break
        if c > cost.get(n, 1e18):
            continue
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            k = (n[0] + di, n[1] + dj)
            for fy in fl.get(k, ()):
                if abs(fy - n[2]) > STEP * math.hypot(di, dj):
                    continue
                m = (k[0], k[1], fy)
                if blocked(pos(n), pos(m), max(n[2], fy)):
                    continue
                nc = c + C * math.hypot(di, dj)
                if nc < cost.get(m, 1e18):
                    cost[m] = nc; came[m] = n
                    heapq.heappush(openq, (nc + math.hypot(*(p - q for p, q in zip(pos(m), pos(g)))), nc, m))
    else:
        n = min(cost, key=lambda m: math.hypot(*(p - q for p, q in zip(pos(m), pos(g)))))
        dn = math.hypot(*(p - q for p, q in zip(pos(n), pos(g))))
        if dn > 2000:  # a door centre sits inside the wall margin: the nearest reachable cell within 2 m is the goal
            sys.exit('navplan: no path (%d nodes; closest %d %d y %d; start %s goal %s)' % (len(cost), *pos(n), n[2], s, g))
        g = n
    path = []; n = g
    while n:
        path.append(n); n = came[n]
    path.reverse()
    # merge straight runs: keep a point when the next one cannot be reached in a straight wall-free line
    out = [path[0]]; k = 0
    while k < len(path) - 1:
        j = len(path) - 1
        while j > k + 1:
            pa, pb = pos(path[k]), pos(path[j])
            nseg = int(math.hypot(pb[0] - pa[0], pb[1] - pa[1]) / C) + 1
            ok = True
            for t in range(nseg):
                p1 = (pa[0] + (pb[0] - pa[0]) * t / nseg, pa[1] + (pb[1] - pa[1]) * t / nseg)
                p2 = (pa[0] + (pb[0] - pa[0]) * (t + 1) / nseg, pa[1] + (pb[1] - pa[1]) * (t + 1) / nseg)
                if blocked(p1, p2, min(path[k][2], path[j][2])):
                    ok = False; break
            if ok and abs(path[j][2] - path[k][2]) < 50 or ok and j - k < 6:
                break
            j -= 1
        out.append(path[j]); k = j
    for n in out[1:]:
        x, z = pos(n)
        print('goto %d %d 500   # y %d' % (x, z, n[2]))


if __name__ == '__main__':
    main()
