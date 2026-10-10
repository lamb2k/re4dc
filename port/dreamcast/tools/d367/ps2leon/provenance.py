#!/usr/bin/env python3
"""Provenance of today's play Leon (leon4k, leon-hair-v2 mesh.json, 3,989 triangles): per role, how close its
vertex positions and UVs are to the GameCube pl00 sections and to the PS2 pl00 sections.

Positions: for each leon4k vertex, the distance to the nearest source vertex (mm) and the share that coincide
(< 0.05 mm). UVs: each leon4k corner's atlas UV is mapped back to its source image (the 512 atlas tiles of
build_leon_4k.py: u_src = (u * 512 - x - 2) / inner_w) and compared with the source corners' UVs (nearest in UV
space, in texels of a 256 image).
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa

TILES = json.loads((ls.PROTO / 'deliverables/leon-4k/asset-report.json').read_text())['source_uv_tiles']
TL = [(t['x'], t['y'], t['width'], t['height'], t['inner_width'], t['inner_height'], k) for k, t in TILES.items()]


def src_uv(u, v):
    # export_coarse_actor.py writes (u, 1 - v) of the Blender atlas UV; build_blender.py imported the source UVs as
    # (u, 1 - v); the atlas tiles are in Blender UV space.
    x, y = u * 512, (1 - v) * 512
    for tx, ty, w, h, iw, ih, k in TL:
        if tx <= x < tx + w and ty <= y < ty + h:
            return ((x - tx - 2) / iw, 1 - (y - ty - 2) / ih), k
    return None, None


def nearest(a, b):
    """distance from each row of a to the nearest row of b (brute force in blocks)."""
    out = np.empty(len(a))
    for i in range(0, len(a), 512):
        d = ((a[i:i + 512, None, :] - b[None, :, :]) ** 2).sum(-1)
        out[i:i + 512] = np.sqrt(d.min(1))
    return out


m = ls.leon_mesh()
P = np.asarray(m['positions_mm'])
rows = []
for r in range(8):
    ts = [t for t in m['triangles'] if t['source_info'] == r]
    vids = sorted({c['vertex'] for t in ts for c in t['corners']})
    lp = P[vids]
    g = ls.gc_role(r)
    p = ls.ps2_role(r)
    gp = g['positions']
    pp = np.asarray(sorted({tuple(c['p']) for _, cs in p['tris'] for c in cs}))
    dg, dp = nearest(lp, gp), nearest(lp, pp)
    # discriminating positions: source vertices the other source does not have (> 0.05 mm from any of its vertices)
    g_only = gp[nearest(gp, pp) > .05]
    p_only = pp[nearest(pp, gp) > .05]
    hit_g_only = int((nearest(lp, g_only) < .05).sum()) if len(g_only) else 0
    hit_p_only = int((nearest(lp, p_only) < .05).sum()) if len(p_only) else 0
    print(f'   role {r}: GC-only source vertices {len(g_only)}, PS2-only {len(p_only)}; leon4k vertices on a GC-only vertex {hit_g_only}, on a PS2-only vertex {hit_p_only}')
    # UVs
    luv, tiles = [], set()
    for t in ts:
        for c in t['corners']:
            s, k = src_uv(*c['uv'])
            if s is not None:
                luv.append(s); tiles.add(k)
    luv = np.asarray(luv)
    guv = np.asarray(sorted({tuple(np.round(c[2], 6)) for cs in g['corners'] for c in cs}))
    puv = np.asarray(sorted({tuple(np.round(c['uv'], 6)) for _, cs in p['tris'] for c in cs}))
    ug, up = nearest(luv, guv) * 256, nearest(luv, puv) * 256
    row = dict(role=r, name=ls.ROLES[r][2], leon4k_vertices=len(vids), gc_vertices=len(gp), ps2_vertices=len(pp),
               pos_to_gc_mm=dict(median=float(np.median(dg)), coincide=float((dg < .05).mean())),
               pos_to_ps2_mm=dict(median=float(np.median(dp)), coincide=float((dp < .05).mean())),
               uv_to_gc_texels=dict(median=float(np.median(ug)), within_0_1=float((ug < .1).mean())),
               uv_to_ps2_texels=dict(median=float(np.median(up)), within_0_1=float((up < .1).mean())), tiles=sorted(tiles), on_gc_only=hit_g_only, on_ps2_only=hit_p_only, gc_only=len(g_only), ps2_only=len(p_only))
    rows.append(row)
    print(f"role {r} {row['name']:10s} leon4k v {len(vids):5d} | pos->GC median {row['pos_to_gc_mm']['median']:.3f} mm coincide {row['pos_to_gc_mm']['coincide']:.0%}"
          f" | pos->PS2 median {row['pos_to_ps2_mm']['median']:.3f} mm coincide {row['pos_to_ps2_mm']['coincide']:.0%}"
          f" | uv->GC median {row['uv_to_gc_texels']['median']:.3f} tx ({row['uv_to_gc_texels']['within_0_1']:.0%})"
          f" | uv->PS2 median {row['uv_to_ps2_texels']['median']:.3f} tx ({row['uv_to_ps2_texels']['within_0_1']:.0%})")
all_g = sum(r['pos_to_gc_mm']['coincide'] * r['leon4k_vertices'] for r in rows) / sum(r['leon4k_vertices'] for r in rows)
all_p = sum(r['pos_to_ps2_mm']['coincide'] * r['leon4k_vertices'] for r in rows) / sum(r['leon4k_vertices'] for r in rows)
print(f'all roles: leon4k vertices coinciding with a GC vertex {all_g:.1%}, with a PS2 vertex {all_p:.1%}')
(ls.WORK / 'provenance.json').write_text(json.dumps(dict(rows=rows, coincide_gc=all_g, coincide_ps2=all_p), indent=1))
