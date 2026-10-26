#!/usr/bin/env python3
"""PS2_INTERIOR_CULL: build an interior cell (sub-cells + portals) for a PS2 world package (lane pc, 2026-10-05).

The runtime (game/platform/native_static.cpp, namespace pc) draws a PS2 world box that lies wholly outside the cell's
outer box only if it meets the frustum from the eye through one of the eye's sub-cell portals. This tool derives the
portals from the package's own geometry, conservatively by dense sampling:

* occluders: every OPAQUE (pass 0) level-0 triangle of the package whose centroid lies in the occluder box. A one-sided
  triangle (part cull 2) occludes only from its front (the side its (b-a)x(c-a) normal points to: the r100 floors face
  up, ceilings down); cull 0 occludes from both sides. Translucent / punch-through triangles never occlude. The PS2
  world's opaque pass draws every such triangle near the camera (no fog or class cull inside 25 m), so whatever blocks
  a view ray here is drawn in front of what it hides.
* the hull: a union of boxes enclosing the house including its walls (config "hull").
* eye boxes (config "eye_boxes"), split into sub-cells of at most subcell_size along each axis; each is sampled on a camera_step grid that
  includes its faces and corners. From every sample eye a ray goes to every target (a target_step grid on the hull
  union's outer surface); the ray is followed to where it first leaves the hull union, and if no occluder lies on it
  between near_max and that exit point, the exit point is a portal sample (cast_cell.cpp). Hits nearer than near_max
  are ignored: the runtime requires the near plane's corners within near_max of the eye, so a wall the near plane
  could cut away is treated as see-through.
* cracks: a thin seam between wall pieces falls between the face targets (the first r100 check walk found a 3 mm
  vertical seam in the west wall at z -37746 this way). Every boundary edge of the occluder mesh (an edge only one
  occluder triangle uses: seams, T-junctions, open borders; 0.5 mm welding) inside the hull is therefore sampled every
  edge_step mm as a second target set; rays to those points ignore hits within eps of the point (the edge's own
  triangles: the ray goes through the crack the edge may leave) and are followed to the hull exit like the others.
* portals: per sub-cell and hull face, exit samples binned at exit_cell, dilated by dilate_cells (unsampled
  neighbours), connected components -> bounding rectangles + margin (sampling spacing, and coarser LOD levels moving
  a wall edge by up to their error), overlapping rectangles merged.
Sampling cannot prove that no crack is missed: PS2_INTERIOR_CULL=2 (the magenta check build) is the runtime proof.

usage (Windows Python with numpy + PIL for prepare / emit; cast_cell.sh in WSL):
  build_cell.py prepare <cfg.json> <package dir> <work dir>
  bash cast_cell.sh <work dir (WSL path)>
  build_cell.py emit <cfg.json> <package dir> <work dir> <out .inc> <out .cell> [--sheets]   (the constants header
      game/platform/include/ps2_interior_cell.inc and the disc file interior-r100.cell: cell_file.py)
  bash cast_cell.sh --verify <work dir> [threads] [directions]   (probe_eye.cpp from each sub-cell's 3x3x3 eyes; its
      misses go to exits_v_<i>.txt: emit + --verify again until 0 directions fall outside the portals; r100: 2 rounds)
  build_cell.py eval <cfg.json> <package dir> <work dir> x,y,z ...   (offline culled-triangle estimate per eye)
"""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r4im import Pkg  # noqa: E402

FACE = ['-x', '+x', '-y', '+y', '-z', '+z']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(cfg_path, pkg_dir):
    cfg = json.loads(Path(cfg_path).read_text())
    mesh = Path(pkg_dir) / cfg['package']['mesh']; side = Path(pkg_dir) / cfg['package']['sidecar']
    for path, want in ((mesh, cfg['package']['mesh_sha256']), (side, cfg['package']['sidecar_sha256'])):
        got = sha(path)
        if got != want:
            sys.exit(f'{path}: sha256 {got} != {want} (the cell is built for one package)')
    p = Pkg(mesh, side)
    p.dynamic = set()
    ids = Path(pkg_dir) / 'ps2-world.ids'
    if cfg.get('exclude_dynamic') and ids.exists():
        # interior-cells26: a placement with a unique id may be moved or hidden by the runtime (doors, boards, breakable
        # windows), so it never occludes (same rule as the vis census, pvs_prep_let.py).
        d = ids.read_bytes(); magic, ver, count, crc = struct.unpack_from('<4sIII', d, 0)
        if magic != b'R4ID' or count != len(p.placements):
            sys.exit(f'{ids}: not this sidecar ({magic} count {count} != {len(p.placements)})')
        idv = d[16:16 + count]; seen = {}
        for x in idv:
            seen[x] = seen.get(x, 0) + 1
        p.dynamic = {i for i, x in enumerate(idv) if x < 250 and seen[x] == 1}
    return cfg, p


def occluders(cfg, p):
    B0 = np.array(cfg['occluder_box'][0], float); B1 = np.array(cfg['occluder_box'][1], float)
    tris = []; two = []
    for pi, part, c, ps, cull, lo, hi in p.iter_clusters():
        if ps != 0 or pi in p.dynamic or not (np.all(hi > B0) and np.all(lo < B1)):
            continue
        t = p.cluster_tris_world(pi, c)
        if not len(t):
            continue
        cen = t.mean(1)
        t = t[np.all((cen > B0) & (cen < B1), axis=1)]
        tris.append(t); two += [cull == 0] * len(t)
    return np.concatenate(tris), np.array(two)


def subcells(cfg):
    size = cfg['subcell_size']; out = []
    for bi, (lo, hi) in enumerate(cfg['eye_boxes']):
        n = [max(1, math.ceil((hi[t] - lo[t]) / size)) for t in range(3)]
        for i in range(n[0]):
            for j in range(n[1]):
                for k in range(n[2]):
                    ijk = (i, j, k)
                    a = [lo[t] + (hi[t] - lo[t]) * ijk[t] / n[t] for t in range(3)]
                    b = [lo[t] + (hi[t] - lo[t]) * (ijk[t] + 1) / n[t] for t in range(3)]
                    out.append(dict(box=bi, lo=a, hi=b))
    return out


def targets(cfg):
    H = cfg['hull']; step = cfg['target_step']; tg = []
    for lo, hi in H:
        for f in range(6):
            ax = f // 2; ua, va = (ax + 1) % 3, (ax + 2) % 3
            c = hi[ax] if f & 1 else lo[ax]
            for u in np.arange(lo[ua] + step / 2, hi[ua], step):
                for v in np.arange(lo[va] + step / 2, hi[va], step):
                    q = [0.0, 0.0, 0.0]; q[ax] = c + (1 if f & 1 else -1); q[ua] = u; q[va] = v
                    if any(all(l[a] <= q[a] <= h[a] for a in range(3)) for l, h in H):
                        continue  # inside another box: not the union's outer surface
                    q[ax] = c; tg.append(q)
    return np.array(tg, np.float32)


def edge_targets(cfg, T):
    """Points every edge_step mm along the occluders' boundary edges (used by one triangle) inside the hull (+300)."""
    q = np.round(T * 2).astype(np.int64); cnt = {}
    for t in q:
        for i in range(3):
            a, b = tuple(t[i]), tuple(t[(i + 1) % 3])
            k = (a, b) if a < b else (b, a)
            cnt[k] = cnt.get(k, 0) + 1
    H = np.array(cfg['hull'], float); lo = H[:, 0].min(0) - 300; hi = H[:, 1].max(0) + 300
    step = cfg['edge_step']; pts = []
    for (a, b), c in sorted(cnt.items()):
        if c != 1:
            continue
        a = np.array(a) / 2.0; b = np.array(b) / 2.0
        if not (np.all((a + b) / 2 > lo) and np.all((a + b) / 2 < hi)):
            continue
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for i in range(n + 1):
            pts.append(a + (b - a) * i / n)
    return np.unique(np.round(np.array(pts), 1), axis=0).astype(np.float32)


def write_points(path, pts):
    with open(path, 'wb') as f:
        f.write(struct.pack('<I', len(pts))); f.write(np.asarray(pts, np.float32).tobytes())


def prepare(a):
    cfg, p = load(a.cfg, a.pkg)
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    T, two = occluders(cfg, p)
    with open(work / 'tris.bin', 'wb') as f:
        f.write(struct.pack('<I', len(T)))
        for t, d in zip(T, two):
            f.write(struct.pack('<9fI', *t.reshape(-1).tolist(), 1 if d else 0))
    tg = targets(cfg); write_points(work / 'targets.bin', tg)
    te = edge_targets(cfg, T); write_points(work / 'targets_edges.bin', te)
    (work / 'hull.txt').write_text(''.join('%g %g %g %g %g %g\n' % (*lo, *hi) for lo, hi in cfg['hull']))
    SC = subcells(cfg); step = cfg['camera_step']; ncams = 0
    for i, sc in enumerate(SC):
        axes = [np.linspace(sc['lo'][t], sc['hi'][t], max(1, math.ceil((sc['hi'][t] - sc['lo'][t]) / step)) + 1) for t in range(3)]
        cams = [(x, y, z) for x in axes[0] for y in axes[1] for z in axes[2]]
        write_points(work / f'cams_{i}.bin', cams); ncams += len(cams)
    (work / 'subcells.json').write_text(json.dumps(SC, indent=1))
    (work / 'params.txt').write_text('%g %g %g\n' % (cfg['near_max'], cfg['exit_cell'], cfg['edge_eps']), newline='\n')
    print(f'occluders {len(T)} (two-sided {int(two.sum())}) targets {len(tg)} edge targets {len(te)} subcells {len(SC)} cameras {ncams}')


def exits(path, cell):
    out = {}; head = ''
    for line in open(path):
        if line.startswith('#'):
            head = line.strip(); continue
        b, f, iu, iv = map(int, line.split())
        out.setdefault((b, f), set()).add((iu, iv))
    return out, head


def portals_of(cfg, cells):
    H = cfg['hull']; cell = cfg['exit_cell']; dil = cfg['dilate_cells']; margin = cfg['margin']; P = []
    for (b, f), s in sorted(cells.items()):
        lo, hi = H[b]; ax = f // 2; ua, va = (ax + 1) % 3, (ax + 2) % 3
        pts = {(u + du, v + dv) for (u, v) in s for du in range(-dil, dil + 1) for dv in range(-dil, dil + 1)}
        seen = set()
        for p0 in sorted(pts):
            if p0 in seen:
                continue
            stack = [p0]; seen.add(p0); comp = []
            while stack:
                q = stack.pop(); comp.append(q)
                for r in ((q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)):
                    if r in pts and r not in seen:
                        seen.add(r); stack.append(r)
            us = [c[0] for c in comp]; vs = [c[1] for c in comp]
            u0 = max(min(us) * cell - margin, lo[ua]); u1 = min((max(us) + 1) * cell + margin, hi[ua])
            v0 = max(min(vs) * cell - margin, lo[va]); v1 = min((max(vs) + 1) * cell + margin, hi[va])
            P.append(dict(box=b, face=f, axis=ax, plane=float(hi[ax] if f & 1 else lo[ax]), u=[float(u0), float(u1)], v=[float(v0), float(v1)]))
    out = []
    for key in sorted({(p['box'], p['face']) for p in P}):
        rs = [p for p in P if (p['box'], p['face']) == key]
        merged = True
        while merged:
            merged = False
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    x, y = rs[i], rs[j]
                    if x['u'][0] <= y['u'][1] and y['u'][0] <= x['u'][1] and x['v'][0] <= y['v'][1] and y['v'][0] <= x['v'][1]:
                        x['u'] = [min(x['u'][0], y['u'][0]), max(x['u'][1], y['u'][1])]
                        x['v'] = [min(x['v'][0], y['v'][0]), max(x['v'][1], y['v'][1])]
                        rs.pop(j); merged = True; break
                if merged:
                    break
        out += rs
    return out


def build_portals(cfg, work):
    SC = json.loads((work / 'subcells.json').read_text()); heads = []
    for i, sc in enumerate(SC):
        cells, head = exits(work / f'exits_{i}.txt', cfg['exit_cell'])
        ecells, ehead = exits(work / f'exits_e_{i}.txt', cfg['exit_cell'])
        v = work / f'exits_v_{i}.txt'  # misses found by cast_cell.sh --verify (probe_eye.cpp)
        if v.exists():
            vcells, _ = exits(v, cfg['exit_cell'])
            for k, s in vcells.items():
                cells.setdefault(k, set()).update(s)
        if cfg.get('edge_rays', True):  # interior-cells26: off for rooms whose pieces overlap (no real cracks)
            for k, s in ecells.items():
                cells.setdefault(k, set()).update(s)
        sc['portals'] = portals_of(cfg, cells); heads += [head, ehead]
    return SC, heads


def policy_crc(room, p):
    """The sidecar identity the runtime compares (native_static.cpp policySourceCrc): with WORLD_RECT21 the certified
    policy source crc of the package's provenance row (texture_rect21/provenance_certificates*.inc: room, r4pw bytes,
    placements, parts, meshes, r4pw crc, ..., mesh crc, mesh bytes, policy crc), else the R4PW crc itself."""
    import re
    side_bytes = len(p.side) if hasattr(p, 'side') else None
    here = Path(__file__).resolve().parent.parent.parent / 'texture_rect21'
    for inc in ('provenance_certificates_n256.inc', 'provenance_certificates.inc'):
        for m in re.finditer(r'\{(0x[0-9a-fA-F]+)U,(\d+)U,(\d+)U,(\d+)U,(\d+)U,(0x[0-9a-fA-F]+)U,(0x[0-9a-fA-F]+)U,'
                             r'(0x[0-9a-fA-F]+)U,(\d+)U,(0x[0-9a-fA-F]+)U\}', (here / inc).read_text()):
            g = m.groups()
            if int(g[0], 16) == room and int(g[5], 16) == p.sidecar_crc and int(g[7], 16) == p.mesh_crc and int(g[8]) == p.mesh_bytes:
                print(f'policy crc {g[9]} from {inc}')
                return int(g[9], 16)
    print(f'no provenance row: policy crc = the R4PW crc {p.sidecar_crc:08x}')
    return p.sidecar_crc


def emit(a):
    cfg, p = load(a.cfg, a.pkg)
    work = Path(a.work)
    SC, heads = build_portals(cfg, work)
    n = [len(s['portals']) for s in SC]
    if max(n) > 24:
        sys.exit(f'a sub-cell has {max(n)} portals (the runtime takes 24): smaller sub-cells or a larger margin')
    O = cfg['outer']
    rays = sum(int(h.split()[2]) for h in heads); esc = sum(int(h.split()[4]) for h in heads)
    import cell_file
    cells, portals, first = [], [], 0
    for c in SC:
        cells.append(([float(f'{float(x):.1f}') for x in c['lo']], [float(f'{float(x):.1f}') for x in c['hi']], first, len(c['portals'])))
        first += len(c['portals'])
        portals += [(q['axis'], float(f'{q["plane"]:.1f}'), float(f'{q["u"][0]:.1f}'), float(f'{q["u"][1]:.1f}'),
                     float(f'{q["v"][0]:.1f}'), float(f'{q["v"][1]:.1f}')) for q in c['portals']]
    if getattr(a, 'pcl2', False):
        data = cell_file.pack2(cfg['room'], p.mesh_crc, policy_crc(cfg['room'], p), p.mesh_bytes, cfg['near_max'], [(O[0] + O[1], cells, portals)])
    else:
        data = cell_file.pack(cfg['room'], p.mesh_crc, p.sidecar_crc, p.mesh_bytes, cells, portals)
    Path(a.cell).write_bytes(data)
    comment = [
        '// Generated by tools/d367/ps2world/interior/build_cell.py emit (cell_file.py); do not edit.',
        f'// Package: {cfg["package"]["mesh"]} sha256 {cfg["package"]["mesh_sha256"]},',
        f'//          {cfg["package"]["sidecar"]} sha256 {cfg["package"]["sidecar_sha256"]}.',
        f'// Config {Path(a.cfg).name} sha256 {sha(a.cfg)}: {len(SC)} sub-cells, {sum(n)} portals; {rays} sample rays, {esc} escaped.',
    ]
    lines = cell_file.header_lines(comment, cfg['room'], p.mesh_crc, p.sidecar_crc, p.mesh_bytes, cfg['near_max'], O[0] + O[1],
                                   len(cells), len(portals), len(data))
    Path(a.out).write_text('\n'.join(lines) + '\n', newline='\n')
    (work / 'cell.json').write_text(json.dumps(dict(cfg=cfg, cells=SC), indent=1))
    for i, s in enumerate(SC):  # cast_cell.sh --verify inputs
        (work / f'portals_{i}.txt').write_text(''.join('%d %r %r %r %r %r\n' % (q['axis'], q['plane'], q['u'][0], q['u'][1], q['v'][0], q['v'][1])
                                                       for q in s['portals']), newline='\n')
        eyes = [[s['lo'][t] + (s['hi'][t] - s['lo'][t]) * k[t] / 2 for t in range(3)]  # 3x3x3: corners, edges, faces, centre
                for k in [(a, b, c) for a in range(3) for b in range(3) for c in range(3)]]
        (work / f'verify_eyes_{i}.txt').write_text(' '.join('%.1f,%.1f,%.1f' % tuple(e) for e in eyes) + '\n', newline='\n')
    print(f'{a.out}: {len(SC)} sub-cells, portals per sub-cell max {max(n)} mean {sum(n) / len(n):.1f}, rays {rays} escaped {esc}')
    if a.sheets:
        sheets(cfg, p, SC, work)


def portal_pass(E, lo, hi, P, slack=64.0):
    lo = lo - slack; hi = hi + slack; c = (lo + hi) / 2 - E; h = (hi - lo) / 2
    for p in P:
        ax = p['axis']; ua, va = (ax + 1) % 3, (ax + 2) % 3; pl = p['plane']
        if (pl > E[ax] and hi[ax] <= pl) or (pl <= E[ax] and lo[ax] >= pl):
            continue
        q = []
        for uu, vv in ((p['u'][0], p['v'][0]), (p['u'][1], p['v'][0]), (p['u'][1], p['v'][1]), (p['u'][0], p['v'][1])):
            r = np.zeros(3); r[ax] = pl; r[ua] = uu; r[va] = vv; q.append(r - E)
        cen = sum(q) / 4; ok = True
        for i in range(4):
            n = np.cross(q[i], q[(i + 1) % 4])
            if np.dot(n, cen) < 0:
                n = -n
            if np.dot(n, c) + np.dot(np.abs(n), h) < 0:
                ok = False; break
        if ok:
            return True
    return False


def evaluate(a):
    cfg, p = load(a.cfg, a.pkg)
    SC, _ = build_portals(cfg, Path(a.work))
    O0 = np.array(cfg['outer'][0], float); O1 = np.array(cfg['outer'][1], float)
    rows = list(p.iter_clusters()); tri = {}
    for pi, part, c, ps, cu, lo, hi in rows:
        cl = p.clusters[c]; fm, mc, _ = p.levels[cl['first_level']]
        tri[c] = sum(len(p.let_tris(li)[1]) for li in range(fm, fm + mc))
    for e in a.eyes:
        E = np.array([float(x) for x in e.split(',')])
        cell = next((s for s in SC if all(s['lo'][k] <= E[k] <= s['hi'][k] for k in range(3))), None)
        if cell is None:
            print('eye', e, 'not in a sub-cell'); continue
        inO = tot = cull = 0
        for pi, part, c, ps, cu, lo, hi in rows:
            if np.linalg.norm(np.maximum(np.maximum(lo - E, E - hi), 0)) > 25000:
                continue
            if np.all(hi > O0) and np.all(lo < O1):
                inO += tri[c]; continue
            tot += tri[c]
            if not portal_pass(E, lo, hi, cell['portals']):
                cull += tri[c]
        print(f'eye {e}: portals {len(cell["portals"])}, level-0 triangles within 25 m: touching the house box {inO}, outside {tot}, hidden {cull} ({100 * cull / max(tot, 1):.0f}%)')


def sheets(cfg, p, SC, work):
    from PIL import Image, ImageDraw
    T, two = occluders(cfg, p)
    X0, Z0 = cfg['occluder_box'][0][0], cfg['occluder_box'][0][2]; X1, Z1 = cfg['occluder_box'][1][0], cfg['occluder_box'][1][2]
    S = 0.05; W = int((X1 - X0) * S); H = int((Z1 - Z0) * S)
    px = lambda x, z: ((x - X0) * S, (z - Z0) * S)
    for y in (1300, 2300, 3000, 4300, 5500, 6800):
        im = Image.new('RGB', (W, H + 16), (255, 255, 255)); d = ImageDraw.Draw(im)
        for t, tw in zip(T, two):
            if t[:, 1].min() > y or t[:, 1].max() < y:
                continue
            pts = []
            for i in range(3):
                u, v = t[i], t[(i + 1) % 3]
                if (u[1] - y) * (v[1] - y) < 0:
                    f = (y - u[1]) / (v[1] - u[1]); q = u + f * (v - u); pts.append(px(q[0], q[2]))
            if len(pts) >= 2:
                d.line(pts[:2], fill=(0, 0, 0) if tw else (0, 90, 255), width=2)
        for s in SC:
            if s['lo'][1] <= y <= s['hi'][1]:
                d.rectangle([*px(s['lo'][0], s['lo'][2]), *px(s['hi'][0], s['hi'][2])], outline=(0, 170, 0))
        for lo, hi in cfg['hull']:
            if lo[1] <= y <= hi[1]:
                d.rectangle([*px(lo[0], lo[2]), *px(hi[0], hi[2])], outline=(255, 140, 0))
        O = cfg['outer']; d.rectangle([*px(O[0][0], O[0][2]), *px(O[1][0], O[1][2])], outline=(150, 0, 150))
        seen = set()
        for s in SC:
            for q in s['portals']:
                ax = q['axis']; ua, va = (ax + 1) % 3, (ax + 2) % 3
                lo = [0, 0, 0]; hi = [0, 0, 0]; lo[ax] = hi[ax] = q['plane']; lo[ua], hi[ua] = q['u']; lo[va], hi[va] = q['v']
                if not (lo[1] <= y <= hi[1]):
                    continue
                key = (tuple(lo), tuple(hi))
                if key in seen:
                    continue
                seen.add(key); d.line([px(lo[0], lo[2]), px(hi[0], hi[2])], fill=(220, 0, 0), width=3)
        d.text((4, H + 2), f'y={y}: blue one-sided / black two-sided opaque, green sub-cells, orange hull, purple outer box, red portals', fill=(0, 0, 0))
        im.save(work / f'sheet_plan_y{y}.png')
    print('sheets in', work)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('prepare', 'emit', 'eval'):
        s = sub.add_parser(name); s.add_argument('cfg'); s.add_argument('pkg'); s.add_argument('work')
        if name == 'emit':
            s.add_argument('out'); s.add_argument('cell'); s.add_argument('--sheets', action='store_true')
            s.add_argument('--pcl2', action='store_true', help='PS2_INTERIOR_CELLS disc file (one house; cell_file.py merge2 joins houses)')
        if name == 'eval':
            s.add_argument('eyes', nargs='+')
    a = ap.parse_args()
    dict(prepare=prepare, emit=emit, eval=evaluate)[a.cmd](a)


if __name__ == '__main__':
    main()
